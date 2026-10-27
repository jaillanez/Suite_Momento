"""Crea datos sintéticos locales y configura una cuenta encargada."""

from __future__ import annotations

import getpass
import os
import re
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from momento_api.auth import hash_password
from momento_api.models import (
    CareRecipient,
    CareUnit,
    CareUnitType,
    Organization,
    OrganizationMembership,
    UserAccount,
    UserCredential,
    UserGroup,
)

ORG_NAME = "Residencia Los Aromos"
UNIT_NAME = "Residencia Los Aromos · Sede Palermo"
FIRST_NAMES = [
    "Elena", "Ricardo", "Beatriz", "Marta", "Héctor", "Amalia", "José", "Norma",
    "Raúl", "Teresa", "Carlos", "Irene", "Alberto", "Rosa", "Hugo", "Celia",
    "Manuel", "Lidia", "Oscar", "Nélida", "Pedro", "Alicia", "Julio", "Sara",
    "Rafael", "Elisa", "Ernesto", "Miriam", "Juan", "Estela", "Eduardo", "Olga",
    "Enrique", "Silvia", "Miguel", "Clara", "Andrés", "Dora", "Mario", "Eva",
    "Ramón", "Luz",
]
LAST_NAMES = [
    "Suárez", "Molina", "Acosta", "Ferreyra", "Benítez", "Sosa", "Pereyra",
    "Giménez", "Romero", "Torres", "Álvarez", "Ruiz", "Medina", "Herrera",
    "Castro", "Rojas", "Vega", "Navarro", "Arias", "Domínguez", "Ortiz",
    "Silva", "Méndez", "Cabrera", "Luna", "Ibarra", "Paz", "Campos",
    "Figueroa", "Carrizo", "Ledesma", "Correa", "Vargas", "Ponce", "Ríos",
    "Varela", "Bravo", "Márquez", "Díaz", "Gómez", "López", "Costa",
]


def main() -> None:
    load_dotenv()
    database_url = os.getenv("MOMENTO_DATABASE_URL")
    if not database_url:
        raise SystemExit("Configurá MOMENTO_DATABASE_URL en backend/.env y aplicá las migraciones.")

    email = input("Correo de acceso para la cuenta encargada [encargado@losaromos.demo]: ").strip().lower()
    if not email:
        email = "encargado@losaromos.demo"
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise SystemExit("Ingresá un correo con formato válido.")

    password_hash = None
    for attempt in range(3):
        password = getpass.getpass("Elegí una contraseña (mínimo 12 caracteres): ")
        confirmation = getpass.getpass("Repetí la contraseña: ")
        if password != confirmation:
            print("Las contraseñas no coinciden. Volvé a ingresarlas.")
            continue
        try:
            password_hash = hash_password(password)
            break
        except ValueError as error:
            print(error)
    if password_hash is None:
        raise SystemExit("No se pudo validar la contraseña. Ejecutá el asistente nuevamente.")

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session, session.begin():
            existing = session.scalar(select(Organization).where(Organization.name == ORG_NAME))
            if existing:
                raise SystemExit(f"Ya existe «{ORG_NAME}». No se modificó la base.")
            if session.scalar(select(UserAccount.id).where(UserAccount.email.ilike(email))):
                raise SystemExit("Ese correo ya está asociado a otra cuenta. No se modificó la base.")

            organization = Organization(name=ORG_NAME)
            unit = CareUnit(
                name=UNIT_NAME,
                service_type=CareUnitType.RESIDENCE,
                country_code="AR",
            )
            organization.care_units.append(unit)
            session.add(organization)
            session.flush()

            manager = UserAccount(display_name="Mariana López", email=email, phone=None)
            manager.memberships.append(OrganizationMembership(
                organization=organization,
                care_unit=None,
                user_group=UserGroup.STAFF,
                role_label="Encargada de residencia",
            ))
            session.add(manager)
            session.flush()
            session.add(UserCredential(user_account_id=manager.id, password_hash=password_hash))

            for index, (first, last) in enumerate(zip(FIRST_NAMES, LAST_NAMES, strict=True), start=1):
                session.add(CareRecipient(
                    care_unit_id=unit.id,
                    display_name=f"{first} {last}",
                ))

            caregivers = [
                "Sofía Pereyra", "Ramiro Costa", "Camila Sosa", "Luciano Ríos",
                "Paula Medina", "Federico Luna", "Valentina Paz", "Bruno Castro",
                "Agustina Vega", "Mateo Ortiz", "Milagros Silva", "Tomás Acosta",
                "Julieta Torres", "Franco Cabrera", "Malena Ruiz", "Nicolás Herrera",
                "Candela Romero", "Julián Benítez",
            ]
            physicians = [
                "Dra. Laura Méndez", "Dr. Pablo Navarro", "Dra. Elena Campos",
            ]
            for index, name in enumerate(caregivers, start=1):
                account = UserAccount(display_name=name, email=f"cuidador{index:02d}@losaromos.demo")
                account.memberships.append(OrganizationMembership(
                    organization=organization,
                    care_unit=unit,
                    user_group=UserGroup.STAFF,
                    role_label="Cuidador/a",
                ))
                session.add(account)
            for index, name in enumerate(physicians, start=1):
                account = UserAccount(display_name=name, email=f"medico{index:02d}@losaromos.demo")
                account.memberships.append(OrganizationMembership(
                    organization=organization,
                    care_unit=unit,
                    user_group=UserGroup.STAFF,
                    role_label="Médico/a",
                ))
                session.add(account)

            family_names = [
                "Lucía Ferreyra", "Andrés Molina", "Nicolás Acosta", "Paula Benítez",
                "Marcos Sosa", "Carolina Giménez", "Gabriel Romero", "Ana Torres",
                "Diego Álvarez", "María Ruiz", "Pablo Medina", "Julia Herrera",
                "Santiago Castro", "Florencia Rojas", "Daniel Vega", "Verónica Navarro",
                "Martín Arias", "Gabriela Domínguez", "Leandro Ortiz", "Natalia Silva",
                "Federico Cabrera", "Mónica Luna", "Ezequiel Ibarra", "Patricia Paz",
                "Ramiro Campos", "Luciana Figueroa", "Hernán Carrizo", "Cecilia Ledesma",
                "Emiliano Correa", "Romina Vargas", "Joaquín Ponce",
            ]
            for index, name in enumerate(family_names, start=1):
                account = UserAccount(display_name=name, email=f"familia{index:02d}@losaromos.demo")
                account.memberships.append(OrganizationMembership(
                    organization=organization,
                    care_unit=unit,
                    user_group=UserGroup.FAMILY,
                    role_label="Familiar de demostración",
                ))
                session.add(account)

        print("Escenario local creado:")
        print(f"  Organización: {ORG_NAME}")
        print(f"  Servicio: {UNIT_NAME}")
        print("  Personas cuidadas: 42")
        print("  Equipo: 18 cuidadores, 3 profesionales médicos y 1 encargada")
        print("  Vínculos familiares: 31")
        print(f"  Cuenta de acceso: {email}")
        print("  Contraseña: la que acabás de elegir; no se guarda en texto legible.")
        print("  Todos los nombres y registros son ficticios y se guardan solo en tu base local.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
