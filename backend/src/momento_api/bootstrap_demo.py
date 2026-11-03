"""Crea datos sintéticos locales y usuarios de prueba con contraseñas simples."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from dotenv import load_dotenv
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from momento_api.auth import hash_password
from momento_api.models import (
    CareEntry,
    CareRecipient,
    CareTask,
    CareRecipientContact,
    CareUnit,
    CareUnitType,
    CareUnitWorkflowStatus,
    FamilyAuthorization,
    FamilyRequest,
    FamilyUpdate,
    Organization,
    OrganizationMembership,
    SharedCareCategory,
    StaffRole,
    UserAccount,
    UserCredential,
    UserGroup,
)
from momento_api.workflow_defaults import DEFAULT_WORKFLOW_STATUSES

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
CAREGIVERS = [
    "Sofía Pereyra", "Ramiro Costa", "Camila Sosa", "Luciano Ríos",
    "Paula Medina", "Federico Luna", "Valentina Paz", "Bruno Castro",
    "Agustina Vega", "Mateo Ortiz", "Milagros Silva", "Tomás Acosta",
    "Julieta Torres", "Franco Cabrera", "Malena Ruiz", "Nicolás Herrera",
    "Candela Romero", "Julián Benítez",
]
PHYSICIANS = ["Dra. Laura Méndez", "Dr. Pablo Navarro", "Dra. Elena Campos"]
ADMINISTRATIVES = ["Silvina Rey"]
# Personal que el encargado designa para la bandeja en el escenario.
INBOX_STAFF = {"Sofía Pereyra", "Ramiro Costa", "Dra. Laura Méndez"}
FAMILY_NAMES = [
    "Lucía Ferreyra", "Andrés Molina", "Nicolás Acosta", "Paula Benítez",
    "Marcos Sosa", "Carolina Giménez", "Gabriel Romero", "Ana Torres",
    "Diego Álvarez", "María Ruiz", "Pablo Medina", "Julia Herrera",
    "Santiago Castro", "Florencia Rojas", "Daniel Vega", "Verónica Navarro",
    "Martín Arias", "Gabriela Domínguez", "Leandro Ortiz", "Natalia Silva",
    "Federico Cabrera", "Mónica Luna", "Ezequiel Ibarra", "Patricia Paz",
    "Ramiro Campos", "Luciana Figueroa", "Hernán Carrizo", "Cecilia Ledesma",
    "Emiliano Correa", "Romina Vargas", "Joaquín Ponce",
]


@dataclass(frozen=True)
class DemoUser:
    email: str
    password: str
    display_name: str
    group: UserGroup
    role: StaffRole | None = None
    whole_organization: bool = False
    handles_inbox: bool = False


# Usuarios fáciles para probar cada puesto. Solo para el entorno local.
DEMO_USERS = [
    DemoUser("encargado1@momento.com.ar", "Encargado123", "Encargado Demo", UserGroup.STAFF, StaffRole.MANAGER, whole_organization=True),
    DemoUser("administrativo1@momento.com.ar", "Administrativo123", "Administrativo Demo", UserGroup.STAFF, StaffRole.ADMINISTRATIVE, whole_organization=True),
    DemoUser("medico1@momento.com.ar", "Medico123", "Médico Demo", UserGroup.STAFF, StaffRole.PHYSICIAN, handles_inbox=True),
    DemoUser("cuidador1@momento.com.ar", "Cuidador123", "Cuidador Demo", UserGroup.STAFF, StaffRole.CAREGIVER, handles_inbox=True),
    DemoUser("familia1@momento.com.ar", "Familia123", "Familia Demo", UserGroup.FAMILY),
]
COVERAGES = ["Cobertura Demo Salud", "Plan Ficticio Mayores", "Obra Social Ejemplo"]
# Fichas detalladas de ejemplo; todo es ficticio y no es información clínica real.
DETAILED_PROFILES = {
    0: {
        "preferred_name": "Elenita",
        "allergies": "Penicilina (dato ficticio)",
        "relevant_conditions": "Hipertensión controlada (dato ficticio)",
        "diet_notes": "Baja en sal (dato ficticio)",
        "mobility_support": "Camina con andador",
        "sensory_communication": "Usa anteojos para leer",
        "life_history": "Fue maestra rural en Entre Ríos durante 30 años. Tiene dos hijos y cinco nietos.",
        "preferences": "Le gustan el tango, las plantas y el mate dulce por la tarde.",
        "routines": "Se levanta temprano; prefiere ducharse por la mañana.",
        "beliefs": "Católica; le gusta ir a misa los domingos.",
    },
    1: {
        "mobility_support": "Silla de ruedas para distancias largas",
        "life_history": "Trabajó como tornero en un taller de Avellaneda. Hincha de Racing.",
        "preferences": "Disfruta de la radio y de jugar al truco.",
        "routines": "Siesta después del almuerzo.",
    },
    2: {
        "sensory_communication": "Hipoacusia leve: hablarle de frente y despacio",
        "life_history": "Costurera; tuvo su propio taller en el barrio.",
        "preferences": "Le gusta tejer y escuchar boleros.",
    },
}
ROLE_LABELS = {
    StaffRole.MANAGER: "Encargado/a",
    StaffRole.ADMINISTRATIVE: "Administrativo/a",
    StaffRole.PHYSICIAN: "Médico/a",
    StaffRole.CAREGIVER: "Cuidador/a",
}
# Solicitudes ficticias: (índice familiar, categoría, asunto, mensaje, estado, responsable, respuesta)
SAMPLE_REQUESTS = [
    (0, SharedCareCategory.DIET, "Consulta sobre menú de esta semana",
     "¿Podrían contarme qué opciones de postre tiene el menú?", "received", None, None),
    (1, SharedCareCategory.ACTIVITIES, "Confirmar participación en musicoterapia",
     "Quería saber si mi papá se anotó al taller del jueves.", "assigned", "Sofía Pereyra", None),
    (2, SharedCareCategory.MEDICATION, "Aviso: acercar receta actualizada",
     "Mañana acerco la receta nueva que nos dio el médico de cabecera.", "received", None, None),
    (0, SharedCareCategory.ACTIVITIES, "Agradecimiento por la celebración",
     "Gracias por organizar el cumpleaños, mi mamá lo disfrutó mucho.", "responded",
     "Ramiro Costa", "¡Gracias a ustedes por acompañarla! Fue una tarde muy linda."),
]
LAST_NAMES = [
    "Suárez", "Molina", "Acosta", "Ferreyra", "Benítez", "Sosa", "Pereyra",
    "Giménez", "Romero", "Torres", "Álvarez", "Ruiz", "Medina", "Herrera",
    "Castro", "Rojas", "Vega", "Navarro", "Arias", "Domínguez", "Ortiz",
    "Silva", "Méndez", "Cabrera", "Luna", "Ibarra", "Paz", "Campos",
    "Figueroa", "Carrizo", "Ledesma", "Correa", "Vargas", "Ponce", "Ríos",
    "Varela", "Bravo", "Márquez", "Díaz", "Gómez", "López", "Costa",
]


def add_membership(
    session: Session,
    *,
    user_account_id: UUID,
    organization_id: UUID,
    care_unit_id: UUID | None,
    user_group: UserGroup,
    role_label: str,
    staff_role: StaffRole | None = None,
    handles_inbox: bool = False,
) -> OrganizationMembership:
    """Persiste el alcance con claves explícitas para evitar relaciones ORM ambiguas."""
    membership = OrganizationMembership(
        user_account_id=user_account_id,
        organization_id=organization_id,
        care_unit_id=care_unit_id,
        user_group=user_group,
        role_label=role_label,
        staff_role=staff_role,
        handles_inbox=handles_inbox,
    )
    session.add(membership)
    return membership


def create_base_scenario(session: Session) -> Organization:
    """Crea organización, servicio, personal, familias y personas cuidadas."""
    organization = Organization(name=ORG_NAME)
    unit = CareUnit(name=UNIT_NAME, service_type=CareUnitType.RESIDENCE, country_code="AR")
    unit.workflow_statuses.extend(
        CareUnitWorkflowStatus(**item) for item in DEFAULT_WORKFLOW_STATUSES
    )
    organization.care_units.append(unit)
    session.add(organization)
    session.flush()

    for first, last in zip(FIRST_NAMES, LAST_NAMES, strict=True):
        session.add(CareRecipient(care_unit_id=unit.id, display_name=f"{first} {last}"))

    staff = (
        [(name, f"cuidador{i:02d}@losaromos.demo", StaffRole.CAREGIVER, "Cuidador/a")
         for i, name in enumerate(CAREGIVERS, start=1)]
        + [(name, f"medico{i:02d}@losaromos.demo", StaffRole.PHYSICIAN, "Médico/a")
           for i, name in enumerate(PHYSICIANS, start=1)]
        + [(name, f"administracion{i:02d}@losaromos.demo", StaffRole.ADMINISTRATIVE, "Administrativo/a")
           for i, name in enumerate(ADMINISTRATIVES, start=1)]
    )
    for name, email, role, label in staff:
        account = UserAccount(display_name=name, email=email)
        session.add(account)
        session.flush()
        add_membership(
            session,
            user_account_id=account.id,
            organization_id=organization.id,
            care_unit_id=unit.id,
            user_group=UserGroup.STAFF,
            role_label=label,
            staff_role=role,
        )

    for index, name in enumerate(FAMILY_NAMES, start=1):
        account = UserAccount(display_name=name, email=f"familia{index:02d}@losaromos.demo")
        session.add(account)
        session.flush()
        add_membership(
            session,
            user_account_id=account.id,
            organization_id=organization.id,
            care_unit_id=unit.id,
            user_group=UserGroup.FAMILY,
            role_label="Familiar de demostración",
        )
    session.flush()
    return organization


def ensure_demo_users(session: Session, organization: Organization, unit: CareUnit) -> list[str]:
    """Crea los usuarios fáciles que falten; no toca cuentas existentes."""
    created = []
    for user in DEMO_USERS:
        if session.scalar(select(UserAccount.id).where(func.lower(UserAccount.email) == user.email)):
            continue
        account = UserAccount(display_name=user.display_name, email=user.email)
        session.add(account)
        session.flush()
        session.add(UserCredential(user_account_id=account.id, password_hash=hash_password(user.password)))
        add_membership(
            session,
            user_account_id=account.id,
            organization_id=organization.id,
            care_unit_id=None if user.whole_organization else unit.id,
            user_group=user.group,
            role_label=ROLE_LABELS[user.role] if user.role else "Familiar",
            staff_role=user.role,
            handles_inbox=user.handles_inbox,
        )
        created.append(user.email)
    session.flush()
    return created


def complete_demo(session: Session, organization: Organization) -> list[str]:
    """Agrega lo que falte de Fase 2 sin modificar ni borrar lo existente."""
    added: list[str] = []
    unit = session.scalar(
        select(CareUnit).where(CareUnit.organization_id == organization.id).order_by(CareUnit.created_at)
    )
    if unit is None:
        return added

    has_statuses = session.scalar(
        select(func.count(CareUnitWorkflowStatus.id)).where(CareUnitWorkflowStatus.care_unit_id == unit.id)
    )
    if not has_statuses:
        session.add_all(
            CareUnitWorkflowStatus(care_unit_id=unit.id, **item) for item in DEFAULT_WORKFLOW_STATUSES
        )
        added.append("estados de seguimiento iniciales del servicio")

    demo_users = ensure_demo_users(session, organization, unit)
    if demo_users:
        added.append(f"{len(demo_users)} usuarios de prueba")

    staff = {
        m.user.display_name: m
        for m in session.scalars(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization.id,
                OrganizationMembership.user_group == UserGroup.STAFF,
            )
        ).all()
    }
    manager = next((m for m in staff.values() if m.staff_role is StaffRole.MANAGER), None)
    demo_family = session.scalar(
        select(OrganizationMembership)
        .join(UserAccount, UserAccount.id == OrganizationMembership.user_account_id)
        .where(
            UserAccount.email == "familia1@momento.com.ar",
            OrganizationMembership.organization_id == organization.id,
        )
    )
    if not any(staff[name].handles_inbox for name in INBOX_STAFF if name in staff):
        for name in INBOX_STAFF:
            if name in staff:
                staff[name].handles_inbox = True
        added.append("personal designado para la bandeja")

    families = {
        m.user.email: m
        for m in session.scalars(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization.id,
                OrganizationMembership.user_group == UserGroup.FAMILY,
            )
        ).all()
    }
    recipients = {
        r.display_name: r
        for r in session.scalars(select(CareRecipient).where(CareRecipient.care_unit_id == unit.id)).all()
    }
    pairs = []
    for index, (first, last) in enumerate(zip(FIRST_NAMES, LAST_NAMES), start=1):
        family = families.get(f"familia{index:02d}@losaromos.demo")
        recipient = recipients.get(f"{first} {last}")
        if family is not None and recipient is not None:
            pairs.append((family, recipient))

    if demo_family is not None and pairs:
        # La familia de prueba acompaña a la primera persona y recibe sus solicitudes de ejemplo.
        pairs.insert(0, (demo_family, pairs[0][1]))

    has_authorizations = session.scalar(
        select(func.count(FamilyAuthorization.id))
        .join(OrganizationMembership, OrganizationMembership.id == FamilyAuthorization.family_membership_id)
        .where(OrganizationMembership.organization_id == organization.id)
    )
    if manager is not None and not has_authorizations:
        for family, recipient in pairs:
            for category in SharedCareCategory:
                session.add(FamilyAuthorization(
                    care_recipient_id=recipient.id,
                    family_membership_id=family.id,
                    authorized_by_membership_id=manager.id,
                    category=category,
                ))
        added.append(f"autorizaciones de medicación, actividades, dietas y novedades para {len(pairs)} familias")
    elif manager is not None:
        # Bases creadas antes de que existiera el permiso "Novedades".
        has_updates = set(session.scalars(
            select(FamilyAuthorization.family_membership_id).where(FamilyAuthorization.category == SharedCareCategory.UPDATES)
        ).all())
        missing = [(family, recipient) for family, recipient in pairs if family.id not in has_updates]
        for family, recipient in missing:
            session.add(FamilyAuthorization(
                care_recipient_id=recipient.id, family_membership_id=family.id,
                authorized_by_membership_id=manager.id, category=SharedCareCategory.UPDATES,
            ))
        if missing:
            added.append(f"permiso de novedades para {len(missing)} familias")

    has_requests = session.scalar(
        select(func.count(FamilyRequest.id)).where(FamilyRequest.care_unit_id == unit.id)
    )
    if not has_requests and pairs:
        for family_index, category, subject, message, status, assignee, response in SAMPLE_REQUESTS:
            family, recipient = pairs[family_index]
            responder = staff.get(assignee) if assignee else None
            session.add(FamilyRequest(
                care_unit_id=unit.id,
                care_recipient_id=recipient.id,
                family_membership_id=family.id,
                category=category,
                subject=subject,
                message=message,
                status_code=status,
                assigned_to_membership_id=responder.id if responder else None,
                shared_response=response,
                responded_by_membership_id=responder.id if response and responder else None,
                responded_at=func.now() if response else None,
            ))
        added.append(f"{len(SAMPLE_REQUESTS)} solicitudes de ejemplo en la bandeja")

    added.extend(complete_profiles(session, unit, pairs[1:] if demo_family is not None else pairs))
    added.extend(sample_care_log(session, unit, staff, [recipient for _, recipient in pairs[1:4]]))
    added.extend(sample_family_updates(session, unit, staff, [recipient for _, recipient in pairs[:3]]))
    return added


SAMPLE_UPDATES = [
    (0, 2, "Hoy participó del taller de música y cantó con el grupo. Estuvo muy contenta."),
    (0, 26, "Almorzó bien y por la tarde recibió la visita de una vecina."),
    (2, 6, "Salió a caminar por el jardín con su cuidadora; disfrutó del sol."),
]


def sample_family_updates(session: Session, unit: CareUnit, staff: dict, recipients: list[CareRecipient]) -> list[str]:
    """Novedades de ejemplo para el portal familiar (solo si el servicio no tiene ninguna)."""
    caregivers = [m for m in staff.values() if m.staff_role is StaffRole.CAREGIVER and m.is_active]
    if not caregivers or len(recipients) < 3 or session.scalar(
        select(func.count(FamilyUpdate.id)).where(FamilyUpdate.care_unit_id == unit.id)
    ):
        return []
    now = datetime.now(timezone.utc)
    session.flush()
    for index, (person, hours, text) in enumerate(SAMPLE_UPDATES):
        session.add(FamilyUpdate(
            care_unit_id=unit.id, care_recipient_id=recipients[person].id, text=text,
            published_by_membership_id=caregivers[index % len(caregivers)].id,
            published_at=now - timedelta(hours=hours),
        ))
    return [f"{len(SAMPLE_UPDATES)} novedades de ejemplo para familias"]


# (horas atrás, índice de persona, categoría, texto, importante)
SAMPLE_ENTRIES = [
    (1, 0, "food", "Almorzó todo y pidió repetir el postre.", False),
    (3, 1, "mood", "Estuvo inquieta después de la visita; se tranquilizó con música.", True),
    (5, 2, "activity", "Participó del taller de jardinería.", False),
    (9, 0, "sleep", "Durmió de corrido hasta las 6.", False),
    (11, 1, "incident", "Resbaló en el baño sin golpearse; se avisó a la encargada.", True),
    (14, 2, "hygiene", "Ducha con ayuda parcial.", False),
]
SAMPLE_TASKS = [
    ("Avisar a la familia del control médico del jueves", 0, 2),
    ("Revisar zapatillas antideslizantes", 1, 0),
    ("Reponer jabón líquido en baños del primer piso", None, None),
]


def sample_care_log(session: Session, unit: CareUnit, staff: dict, recipients: list[CareRecipient]) -> list[str]:
    """Registros y pendientes de ejemplo para ver la entrega de turno (solo si no hay ninguno)."""
    caregivers = [m for m in staff.values() if m.staff_role is StaffRole.CAREGIVER and m.is_active]
    if not caregivers or len(recipients) < 3 or session.scalar(
        select(func.count(CareEntry.id)).where(CareEntry.care_unit_id == unit.id)
    ):
        return []
    now = datetime.now(timezone.utc)
    for index, (hours, person, category, text, important) in enumerate(SAMPLE_ENTRIES):
        session.add(CareEntry(
            care_unit_id=unit.id, care_recipient_id=recipients[person].id, category=category, text=text,
            important=important, occurred_at=now - timedelta(hours=hours),
            recorded_by_membership_id=caregivers[index % len(caregivers)].id,
        ))
    for title, person, days in SAMPLE_TASKS:
        session.add(CareTask(
            care_unit_id=unit.id, care_recipient_id=recipients[person].id if person is not None else None,
            title=title, due_on=(now + timedelta(days=days)).date() if days is not None else None,
            created_by_membership_id=caregivers[0].id,
        ))
    return [f"{len(SAMPLE_ENTRIES)} registros diarios y {len(SAMPLE_TASKS)} pendientes de ejemplo"]


def complete_profiles(session: Session, unit: CareUnit, pairs: list) -> list[str]:
    """Completa fichas ficticias si ninguna persona del servicio tiene datos cargados."""
    recipients = {
        r.display_name: r
        for r in session.scalars(select(CareRecipient).where(CareRecipient.care_unit_id == unit.id)).all()
    }
    if any(r.birth_date is not None for r in recipients.values()):
        return []
    family_by_recipient = {recipient.id: family for family, recipient in pairs}
    completed = 0
    for index, (first, last) in enumerate(zip(FIRST_NAMES, LAST_NAMES)):
        recipient = recipients.get(f"{first} {last}")
        if recipient is None:
            continue
        recipient.first_name = first
        recipient.last_name = last
        recipient.birth_date = date(1930 + (index * 7) % 19, (index * 5) % 12 + 1, (index * 11) % 28 + 1)
        recipient.document_type = "DNI"
        recipient.document_number = f"{3_100_000 + index * 137_911:,}".replace(",", ".")
        recipient.nationality = "Argentina"
        recipient.languages = "Español"
        recipient.admission_date = date(2022 + index % 4, (index * 7) % 12 + 1, (index * 13) % 28 + 1)
        recipient.room = f"{101 + index // 2}{'AB'[index % 2]}"
        recipient.health_coverage = COVERAGES[index % len(COVERAGES)]
        recipient.coverage_member_number = f"DEMO-{index + 1:05d}"
        recipient.primary_physician = PHYSICIANS[index % len(PHYSICIANS)]
        recipient.primary_physician_phone = f"11 5555-02{index % 100:02d}"
        for field, value in DETAILED_PROFILES.get(index, {}).items():
            setattr(recipient, field, value)
        family = family_by_recipient.get(recipient.id)
        if family is not None:
            session.add(CareRecipientContact(
                care_recipient_id=recipient.id,
                full_name=family.user.display_name,
                relationship_label="Familiar",
                phone=f"11 5555-{1000 + index}",
                email=family.user.email,
                is_emergency=True,
            ))
        completed += 1
    return [f"{completed} fichas completas con datos ficticios"] if completed else []


def main() -> None:
    load_dotenv()
    database_url = os.getenv("MOMENTO_DATABASE_URL")
    if not database_url:
        raise SystemExit("Configurá MOMENTO_DATABASE_URL en backend/.env y aplicá las migraciones.")

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session, session.begin():
            organization = session.scalar(select(Organization).where(Organization.name == ORG_NAME))
            created = organization is None
            if organization is None:
                organization = create_base_scenario(session)
            added = complete_demo(session, organization)

        if created:
            print(f"Escenario creado: {ORG_NAME} · {UNIT_NAME}")
            print(f"  {len(FIRST_NAMES)} personas cuidadas, {len(CAREGIVERS)} cuidadores, "
                  f"{len(PHYSICIANS)} médicos y {len(FAMILY_NAMES)} familias (todos ficticios).")
        else:
            print(f"Ya existe «{ORG_NAME}». No se borró ni reemplazó nada.")
        print("  Se agregó: " + "; ".join(added) + "." if added else "  No faltaba nada por completar.")
        print()
        print("Usuarios de prueba (solo para tu entorno local):")
        for user in DEMO_USERS:
            print(f"  {user.email:<32} {user.password}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
