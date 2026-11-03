"""Envío de correos con la biblioteca estándar (smtplib), sin servicios agregados.

Parámetros (archivo .env):
- MOMENTO_MAIL_FROM: remitente. Por defecto illanezjorgea@gmail.com.
- MOMENTO_SMTP_PASSWORD: la "contraseña de aplicación" de Gmail. Es lo único que falta
  para enviar de verdad; sin ella el correo NO se envía.
- MOMENTO_SMTP_HOST (smtp.gmail.com) y MOMENTO_SMTP_USER (el remitente): ya vienen
  armados para Gmail; cambiarlos solo si se usa otro proveedor.
- MOMENTO_MAIL_DEBUG: solo para desarrollo local. Con true y sin servidor SMTP, el
  correo completo (con el enlace) se muestra en la consola de la API para copiarlo.
  Nunca activarlo en un entorno real: el enlace da acceso a la cuenta.
- MOMENTO_SMTP_PORT (587), MOMENTO_SMTP_USER, MOMENTO_SMTP_PASSWORD,
  MOMENTO_SMTP_STARTTLS (true; con false no se envía usuario ni contraseña).
- MOMENTO_PUBLIC_URL: dirección de la pantalla de Momento que va en los enlaces.

Los correos nunca incluyen datos de salud: solo el nombre de la persona destinataria,
la organización y el enlace.
"""

from __future__ import annotations

import os
import smtplib
import ssl
import sys
from dataclasses import dataclass
from email.message import EmailMessage

DEFAULT_MAIL_FROM = "illanezjorgea@gmail.com"
DEFAULT_SMTP_HOST = "smtp.gmail.com"
DEFAULT_PUBLIC_URL = "http://127.0.0.1:5173"

# Últimos correos del modo de desarrollo (MOMENTO_MAIL_DEBUG); lo usan las pruebas.
outbox: list[EmailMessage] = []


@dataclass(frozen=True)
class MailSettings:
    sender: str
    host: str
    port: int
    user: str
    password: str
    starttls: bool
    debug: bool
    public_url: str


def mail_settings() -> MailSettings:
    sender = os.getenv("MOMENTO_MAIL_FROM", "").strip() or DEFAULT_MAIL_FROM
    return MailSettings(
        sender=sender,
        host=os.getenv("MOMENTO_SMTP_HOST", "").strip() or DEFAULT_SMTP_HOST,
        port=int(os.getenv("MOMENTO_SMTP_PORT", "587") or 587),
        user=os.getenv("MOMENTO_SMTP_USER", "").strip() or sender,
        password=os.getenv("MOMENTO_SMTP_PASSWORD", ""),
        starttls=os.getenv("MOMENTO_SMTP_STARTTLS", "true").strip().lower() in {"1", "true", "yes"},
        debug=os.getenv("MOMENTO_MAIL_DEBUG", "").strip().lower() in {"1", "true", "yes"},
        public_url=(os.getenv("MOMENTO_PUBLIC_URL", "").strip() or DEFAULT_PUBLIC_URL).rstrip("/"),
    )


def _tls_context() -> ssl.SSLContext:
    """Contexto que verifica certificado y nombre del servidor.

    El Python de python.org en macOS no trae certificados raíz propios; en ese caso se
    usan los del sistema (/etc/ssl/cert.pem) en lugar de desactivar la verificación.
    """
    context = ssl.create_default_context()
    if not context.cert_store_stats().get("x509_ca") and os.path.exists("/etc/ssl/cert.pem"):
        context.load_verify_locations(cafile="/etc/ssl/cert.pem")
    return context


def send_mail(to: str, subject: str, body: str) -> None:
    """Envía o, en modo local, muestra el correo. Los errores se informan sin cortar la API."""
    settings = mail_settings()
    message = EmailMessage()
    message["From"] = settings.sender
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    if not settings.password:
        if not settings.debug:
            print("[Momento · correo descartado: falta MOMENTO_SMTP_PASSWORD]", file=sys.stderr, flush=True)
            return
        outbox.append(message)
        del outbox[:-50]
        print(
            f"\n[Momento · correo sin enviar: falta MOMENTO_SMTP_PASSWORD (MOMENTO_MAIL_DEBUG, solo desarrollo)]\n"
            f"De: {settings.sender}\nPara: {to}\nAsunto: {subject}\n\n{body}\n",
            file=sys.stderr,
            flush=True,
        )
        return
    try:
        with smtplib.SMTP(settings.host, settings.port, timeout=20) as client:
            if settings.starttls:
                client.ehlo()
                client.starttls(context=_tls_context())  # verifica certificado y nombre
                client.ehlo()
            elif settings.user:
                print("[Momento · correo no enviado: no se envían credenciales sin STARTTLS]", file=sys.stderr, flush=True)
                return
            client.login(settings.user, settings.password)
            client.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        # No se muestra el destinatario ni el enlace en el error.
        print(f"[Momento · no se pudo enviar el correo: {type(error).__name__}]", file=sys.stderr, flush=True)
