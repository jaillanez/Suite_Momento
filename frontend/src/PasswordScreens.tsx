import { type FormEvent, useState } from "react";

async function errorText(response: Response, fallback: string): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    return typeof data.detail === "string" ? data.detail : fallback;
  } catch {
    return fallback;
  }
}

export function ForgotPasswordForm({ onBack }: { onBack: () => void }) {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSending(true);
    try {
      const response = await fetch("/api/auth/password-reset/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!response.ok) throw new Error(await errorText(response, "No se pudo enviar el pedido."));
      setMessage("Si el correo corresponde a una cuenta con acceso, te enviamos un enlace. Revisá tu bandeja de entrada.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo enviar el pedido.");
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <p className="login-intro">Escribí tu correo y te mandamos un enlace para elegir una contraseña nueva.</p>
      {message ? <p className="form-message" role="status">{message}</p> : (
        <form className="login-form" onSubmit={submit}>
          <label>Correo electrónico<input type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required autoFocus /></label>
          {error && <p className="form-message error-message" role="alert">{error}</p>}
          <button type="submit" disabled={sending}>{sending ? "Enviando…" : "Enviar enlace"}</button>
        </form>
      )}
      <button className="back-link" type="button" onClick={onBack}>Volver a iniciar sesión</button>
    </>
  );
}

export function ResetPasswordScreen({ token, onDone }: { token: string; onDone: () => void }) {
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (password !== repeat) {
      setError("Las dos contraseñas no coinciden.");
      return;
    }
    setSaving(true);
    try {
      const response = await fetch("/api/auth/password-reset/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      if (!response.ok) throw new Error(await errorText(response, "No se pudo guardar la contraseña."));
      setDone(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo guardar la contraseña.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="login-brand"><img src="/brand/iso-momento.png" alt="" /><span>Momento</span></div>
        <p className="eyebrow">Acceso al sistema</p>
        <h1>Elegí tu contraseña</h1>
        {done ? (
          <>
            <p className="form-message" role="status">Listo. Ya podés ingresar con tu correo y la contraseña nueva.</p>
            <form className="login-form" onSubmit={(event) => { event.preventDefault(); onDone(); }}>
              <button type="submit">Ir a iniciar sesión</button>
            </form>
          </>
        ) : (
          <form className="login-form" onSubmit={submit}>
            <label>Contraseña nueva<input type="password" autoComplete="new-password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} required autoFocus /></label>
            <label>Repetir contraseña<input type="password" autoComplete="new-password" minLength={8} value={repeat} onChange={(event) => setRepeat(event.target.value)} required /></label>
            <p className="login-intro">Al menos 8 caracteres.</p>
            {error && <p className="form-message error-message" role="alert">{error}</p>}
            <button type="submit" disabled={saving}>{saving ? "Guardando…" : "Guardar contraseña"}</button>
          </form>
        )}
        {!done && <button className="back-link" type="button" onClick={onDone}>Volver a iniciar sesión</button>}
      </section>
    </main>
  );
}
