import { type FormEvent, useEffect, useState } from "react";
import { readApiError, type StaffRole, staffRoleLabels } from "./OrganizationsPanel";

type Organization = { id: string; name: string };
type CareUnit = { id: string; name: string; service_type: "residence" | "home_care"; country_code: "AR" | "UY" };
type Member = { id: string; user_group: "staff" | "family" | "older_adult"; staff_role: StaffRole | null; handles_inbox: boolean; user: { display_name: string; email: string | null } };
type AuditEvent = { id: string; occurred_at: string; actor_name: string | null; action: string; outcome: "success" | "denied"; target_type: string | null; details: Record<string, unknown> | null };

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as T;
}

const actionLabels: Record<string, string> = {
  "auth.login": "Inicio de sesión (equipo)",
  "auth.family_login": "Inicio de sesión (familia)",
  "auth.logout": "Cierre de sesión",
  "membership.created": "Alta de usuario",
  "membership.updated": "Cambio de usuario",
  "account.password_set": "Cambio de contraseña",
  "account.invitation_sent": "Invitación enviada por correo",
  "account.password_set_by_invite": "Contraseña creada desde la invitación",
  "account.password_set_by_reset": "Contraseña recuperada por correo",
  "auth.password_reset_requested": "Pedido de recuperación de contraseña",
  "organization.renamed": "Cambio de nombre de la organización",
  "family_authorization.granted": "Autorización familiar otorgada",
  "family_authorization.revoked": "Autorización familiar quitada",
  "family_authorization.listed": "Consulta de autorizaciones",
  "request.created": "Consulta enviada por familia",
  "request.assigned": "Solicitud asignada",
  "request.status_changed": "Cambio de estado de solicitud",
  "request.responded": "Solicitud respondida",
  "request.inbox_viewed": "Ingreso a la bandeja",
  "request.assignees_viewed": "Consulta de responsables",
  "care_entry.created": "Registro diario cargado",
  "care_entry.voided": "Registro diario anulado",
  "care_log.viewed": "Consulta del registro diario",
  "handover.viewed": "Consulta de la entrega de turno",
  "care_task.created": "Pendiente creado",
  "care_task.completed": "Pendiente resuelto",
  "care_task.cancelled": "Pendiente cancelado",
  "care_settings.updated": "Cambio en la configuración del registro diario",
  "family_update.published": "Publicación de una novedad para la familia",
  "family_update.withdrawn": "Retiro de una novedad para la familia",
  "family_updates.viewed": "Consulta de novedades por la familia",
  "audit.purged": "Depuración del registro vencido",
  "image_consent.recorded": "Registro del consentimiento de imagen",
  "image_consent.revoked": "Retiro del consentimiento de imagen",
};

const detailLabels: Record<string, string> = {
  staff_role: "puesto",
  handles_inbox: "atiende bandeja",
  is_active: "activa",
  categories: "temas",
  category: "tema",
  from: "de",
  to: "a",
  can_sign_in: "con contraseña",
  user_group: "grupo",
  invitation_sent: "invitación enviada",
  important: "importante",
  changed: "cambió",
};

function describeDetails(details: AuditEvent["details"]): string {
  if (!details) return "";
  return Object.entries(details)
    .filter(([key]) => key in detailLabels)
    .map(([key, value]) => {
      const text = Array.isArray(value) ? value.join(", ") : typeof value === "boolean" ? (value ? "sí" : "no") : key === "staff_role" && typeof value === "string" ? staffRoleLabels[value as StaffRole] ?? value : String(value);
      return `${detailLabels[key]}: ${text}`;
    })
    .join(" · ");
}

export function AuditPanel() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [organizationId, setOrganizationId] = useState("");
  const [onlyDenied, setOnlyDenied] = useState(false);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [retentionYears, setRetentionYears] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getJson<Organization[]>("/api/organizations")
      .then((items) => { setOrganizations(items); setOrganizationId(items[0]?.id ?? ""); if (!items.length) setLoading(false); })
      .catch((caught: unknown) => { setError(caught instanceof Error ? caught.message : "No se pudo cargar."); setLoading(false); });
  }, []);

  useEffect(() => {
    if (!organizationId) return;
    let active = true;
    setLoading(true);
    getJson<{ years: number }>(`/api/organizations/${organizationId}/audit-events/retention`)
      .then((data) => { if (active) setRetentionYears(data.years); })
      .catch(() => undefined);
    getJson<AuditEvent[]>(`/api/organizations/${organizationId}/audit-events${onlyDenied ? "?outcome=denied" : ""}`)
      .then((items) => { if (active) setEvents(items); })
      .catch((caught: unknown) => { if (active) setError(caught instanceof Error ? caught.message : "No se pudo cargar el registro."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [organizationId, onlyDenied]);

  return (
    <section className="management-view">
      <header className="view-heading">
        <div>
          <p className="eyebrow">Trazabilidad</p>
          <h2>Registro de control</h2>
          <p>Quién hizo cada acción sensible y cuándo. No guarda contraseñas ni el texto de los mensajes.{retentionYears ? ` Se conserva ${retentionYears} años.` : ""}</p>
        </div>
      </header>
      <div className="audit-filters">
        {organizations.length > 1 && (
          <label>Organización
            <select value={organizationId} onChange={(event) => setOrganizationId(event.target.value)}>
              {organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
        )}
        <label className="inline-check"><input type="checkbox" checked={onlyDenied} onChange={(event) => setOnlyDenied(event.target.checked)} /> Solo accesos rechazados</label>
      </div>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {loading ? <p className="empty-state" role="status">Cargando registro…</p> : events.length === 0 ? <p className="list-empty">No hay eventos para mostrar.</p> : (
        <div className="audit-table-wrap">
          <table className="audit-table">
            <thead><tr><th>Fecha</th><th>Persona</th><th>Acción</th><th>Detalle</th><th>Resultado</th></tr></thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id}>
                  <td>{new Date(event.occurred_at).toLocaleString("es-AR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}</td>
                  <td>{event.actor_name ?? "Desconocido"}</td>
                  <td>{actionLabels[event.action] ?? event.action}</td>
                  <td className="audit-detail">{describeDetails(event.details)}</td>
                  <td><span className={"status-pill " + (event.outcome === "denied" ? "status-amber" : "status-green")}>{event.outcome === "denied" ? "Rechazado" : "Correcto"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="dashboard-preview-note">Se muestran los últimos 200 eventos. Por ahora el registro no se borra; el plazo de conservación está pendiente de definir.</p>
    </section>
  );
}

type OrganizationSettings = { organization: Organization; units: CareUnit[]; members: Member[] };

export function SettingsPanel() {
  const [items, setItems] = useState<OrganizationSettings[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const organizations = await getJson<Organization[]>("/api/organizations");
        const loaded = await Promise.all(organizations.map(async (organization) => ({
          organization,
          units: await getJson<CareUnit[]>(`/api/organizations/${organization.id}/care-units`),
          members: await getJson<Member[]>(`/api/organizations/${organization.id}/memberships`),
        })));
        if (active) setItems(loaded);
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "No se pudo cargar la configuración.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, []);

  function renamed(updated: Organization) {
    setItems((current) => current.map((item) => item.organization.id === updated.id ? { ...item, organization: updated } : item));
  }

  return (
    <section className="settings-view">
      <p className="eyebrow">Datos del espacio de trabajo</p>
      <h2>Configuración</h2>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {loading ? <p className="empty-state" role="status">Cargando…</p> : items.map(({ organization, units, members }) => {
        const staff = members.filter((member) => member.user_group === "staff");
        const managers = staff.filter((member) => member.staff_role === "manager");
        const countBy = (role: StaffRole) => staff.filter((member) => member.staff_role === role).length;
        return (
          <article className="management-card" key={organization.id}>
            <OrganizationName organization={organization} onRenamed={renamed} />
            <div className="settings-grid">
              <article><span>Servicios</span><strong>{units.length}</strong><small>{units.map((unit) => `${unit.name} · ${unit.service_type === "residence" ? "Residencia" : "Domiciliario"} · ${unit.country_code === "AR" ? "Argentina" : "Uruguay"}`).join(" / ") || "Sin servicios"}</small></article>
              <article><span>Encargados</span><strong>{managers.length}</strong><small>{managers.map((member) => member.user.display_name).join(", ") || "Sin encargado"}</small></article>
              <article><span>Equipo</span><strong>{staff.length}</strong><small>{(["administrative", "physician", "caregiver"] as StaffRole[]).map((role) => `${countBy(role)} ${staffRoleLabels[role].toLowerCase()}`).join(" · ")}</small></article>
              <article><span>Atienden la bandeja</span><strong>{staff.filter((member) => member.handles_inbox).length}</strong><small>Se designan desde “Usuarios y vínculos”</small></article>
              <article><span>Familias</span><strong>{members.filter((member) => member.user_group === "family").length}</strong><small>Cuentas activas del grupo familiar</small></article>
              <article><span>Seguimiento de solicitudes</span><strong>Por servicio</strong><small>Estados y visibilidad familiar se editan en “Organizaciones”</small></article>
            </div>
          </article>
        );
      })}
    </section>
  );
}

function OrganizationName({ organization, onRenamed }: { organization: Organization; onRenamed: (item: Organization) => void }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(organization.name);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      const response = await fetch(`/api/organizations/${organization.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      onRenamed((await response.json()) as Organization);
      setEditing(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo guardar el nombre.");
    }
  }

  if (!editing) {
    return (
      <div className="management-card-heading">
        <div><span className="card-kicker">ORGANIZACIÓN</span><h3>{organization.name}</h3></div>
        <button className="link-action" type="button" onClick={() => { setName(organization.name); setEditing(true); }}>Cambiar nombre</button>
      </div>
    );
  }
  return (
    <form className="inline-form" onSubmit={submit}>
      <label>Nombre de la organización<input value={name} onChange={(event) => setName(event.target.value)} maxLength={160} required autoFocus /></label>
      <button className="secondary-action" type="button" onClick={() => setEditing(false)}>Cancelar</button>
      <button className="primary-action" type="submit">Guardar</button>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
    </form>
  );
}
