import { type FormEvent, useEffect, useState } from "react";
import { type Category, categoryLabels, readApiError, type StaffRole, staffRoleLabels } from "./OrganizationsPanel";

type Organization = { id: string; name: string };
type CareUnit = { id: string; name: string };
type WorkflowStatus = { code: string; label: string; display_order: number; is_active: boolean };
type Assignee = { membership_id: string; display_name: string; staff_role: StaffRole };

export type InboxRequest = {
  id: string;
  care_unit_id: string;
  care_recipient_name: string;
  family_name: string;
  category: Category;
  subject: string;
  message: string;
  status_code: string;
  status_label: string;
  assigned_to_membership_id: string | null;
  assigned_to_name: string | null;
  shared_response: string | null;
  responded_at: string | null;
  created_at: string;
};

type UnitInbox = {
  organizationId: string;
  unit: CareUnit;
  requests: InboxRequest[];
  statuses: WorkflowStatus[];
  assignees: Assignee[];
};

export const categoryClass: Record<Category, string> = {
  diet: "type-diet",
  activities: "type-activity",
  medication: "type-medication",
};

export function formatDate(value: string): string {
  const date = new Date(value);
  const today = new Date();
  const sameDay = date.toDateString() === today.toDateString();
  return sameDay
    ? date.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" })
    : date.toLocaleDateString("es-AR", { day: "2-digit", month: "short" });
}

/** Carga la bandeja de todos los servicios a los que la cuenta tiene acceso. */
export async function loadInboxes({ isManager }: { isManager: boolean }): Promise<UnitInbox[]> {
  const orgResponse = await fetch("/api/organizations");
  if (!orgResponse.ok) throw new Error(await readApiError(orgResponse));
  const organizations = (await orgResponse.json()) as Organization[];
  const result: UnitInbox[] = [];
  for (const organization of organizations) {
    const unitResponse = await fetch(`/api/organizations/${organization.id}/care-units`);
    if (!unitResponse.ok) continue;
    const units = (await unitResponse.json()) as CareUnit[];
    for (const unit of units) {
      const base = `/api/organizations/${organization.id}/care-units/${unit.id}`;
      // Solo el encargado asigna; el resto no consulta la lista de responsables.
      const [requests, statuses, assignees] = await Promise.all([
        fetch(`${base}/requests`),
        fetch(`${base}/workflow-statuses`),
        isManager ? fetch(`${base}/requests/assignees`) : Promise.resolve(null),
      ]);
      // Sin permiso de bandeja para este servicio: se omite sin error.
      if (requests.status === 403) continue;
      if (!requests.ok) throw new Error(await readApiError(requests));
      result.push({
        organizationId: organization.id,
        unit,
        requests: (await requests.json()) as InboxRequest[],
        statuses: statuses.ok ? ((await statuses.json()) as WorkflowStatus[]) : [],
        assignees: assignees?.ok ? ((await assignees.json()) as Assignee[]) : [],
      });
    }
  }
  return result;
}

export default function InboxPanel({ isManager }: { isManager: boolean }) {
  const [inboxes, setInboxes] = useState<UnitInbox[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    let active = true;
    loadInboxes({ isManager })
      .then((items) => { if (active) setInboxes(items); })
      .catch((caught: unknown) => { if (active) setError(caught instanceof Error ? caught.message : "No se pudo cargar la bandeja."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  function replaceRequest(updated: InboxRequest) {
    setInboxes((current) => current.map((inbox) => ({
      ...inbox,
      requests: inbox.requests.map((item) => (item.id === updated.id ? updated : item)),
    })));
  }

  const allRequests = inboxes.flatMap((inbox) => inbox.requests);
  const statusFilters = [...new Map(allRequests.map((item) => [item.status_code, item.status_label])).entries()];
  const closedCodes = new Set(["closed"]);
  const openCount = allRequests.filter((item) => !closedCodes.has(item.status_code)).length;

  return <section className="inbox-view">
    <div className="dashboard-heading-row">
      <div><p className="eyebrow">Comunicación con familias</p><h2>Bandeja de solicitudes</h2><p>El encargado asigna cada solicitud al personal designado. La familia ve el estado y la respuesta, nunca quién la atiende.</p></div>
      <span className="module-status">{openCount} abiertas</span>
    </div>
    {error && <p className="form-message error-message" role="alert">{error}</p>}
    {loading ? <p className="empty-state" role="status">Cargando bandeja…</p> : inboxes.length === 0 ? (
      <div className="empty-panel"><h3>No tenés acceso a ninguna bandeja</h3><p>El encargado puede designarte desde “Usuarios y vínculos”.</p></div>
    ) : (
      <>
        <div className="inbox-filters" role="group" aria-label="Filtrar por estado">
          <button type="button" className={"filter-chip" + (filter === "all" ? " selected" : "")} onClick={() => setFilter("all")}>Todas</button>
          {statusFilters.map(([code, label]) => (
            <button type="button" key={code} className={"filter-chip" + (filter === code ? " selected" : "")} onClick={() => setFilter(code)}>{label}</button>
          ))}
        </div>
        {inboxes.map((inbox) => {
          const visible = inbox.requests.filter((item) => filter === "all" || item.status_code === filter);
          return <div key={inbox.unit.id} className="inbox-unit">
            {inboxes.length > 1 && <h3 className="inbox-unit-title">{inbox.unit.name}</h3>}
            {visible.length === 0 ? <p className="list-empty">No hay solicitudes en este estado.</p> : (
              <div className="inbox-list">
                {visible.map((item) => <InboxItem key={item.id} item={item} inbox={inbox} onUpdated={replaceRequest} />)}
              </div>
            )}
          </div>;
        })}
      </>
    )}
  </section>;
}

function InboxItem({ item, inbox, onUpdated }: { item: InboxRequest; inbox: UnitInbox; onUpdated: (item: InboxRequest) => void }) {
  const [responding, setResponding] = useState(false);
  const [response, setResponse] = useState(item.shared_response ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const base = `/api/organizations/${inbox.organizationId}/care-units/${inbox.unit.id}/requests/${item.id}`;

  async function send(path: string, body: object) {
    setBusy(true);
    setError("");
    try {
      const result = await fetch(`${base}/${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!result.ok) throw new Error(await readApiError(result));
      onUpdated((await result.json()) as InboxRequest);
      return true;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo guardar el cambio.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function submitResponse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (await send("respond", { shared_response: response })) setResponding(false);
  }

  const statusTone = item.status_code === "closed" || item.status_code === "responded" ? "status-green" : item.status_code === "received" ? "status-amber" : "status-blue";
  const activeStatuses = inbox.statuses.filter((status) => status.is_active).sort((a, b) => a.display_order - b.display_order);

  return <article className="inbox-item">
    <div className="inbox-item-top">
      <span className={"request-type " + categoryClass[item.category]}>{categoryLabels[item.category]}</span>
      <span className="request-date">{formatDate(item.created_at)}</span>
    </div>
    <h3>{item.subject}</h3>
    <p>{item.family_name} · familiar de <strong>{item.care_recipient_name}</strong></p>
    <p className="inbox-message">{item.message}</p>
    {item.shared_response && !responding && <div className="inbox-response"><span>Respuesta compartida con la familia</span><p>{item.shared_response}</p></div>}
    <div className="inbox-item-actions">
      {inbox.assignees.length > 0 ? (
        <label>Responsable
          <select value={item.assigned_to_membership_id ?? ""} disabled={busy} onChange={(event) => event.target.value && void send("assign", { membership_id: event.target.value })}>
            <option value="" disabled>Sin asignar</option>
            {inbox.assignees.map((person) => <option value={person.membership_id} key={person.membership_id}>{person.display_name} · {staffRoleLabels[person.staff_role]}</option>)}
          </select>
        </label>
      ) : (
        <span className="inbox-assignee">{item.assigned_to_name ?? "Sin asignar"}</span>
      )}
      {activeStatuses.length > 0 ? (
        <label>Estado
          <select value={item.status_code} disabled={busy} onChange={(event) => void send("status", { status_code: event.target.value })}>
            {activeStatuses.map((status) => <option value={status.code} key={status.code}>{status.label}</option>)}
          </select>
        </label>
      ) : <span className={"status-pill " + statusTone}>{item.status_label}</span>}
      {!responding && <button className="resolve-button" type="button" onClick={() => setResponding(true)}>{item.shared_response ? "Editar respuesta" : "Responder"}</button>}
    </div>
    {responding && (
      <form className="inbox-response-form" onSubmit={submitResponse}>
        <label>Respuesta para la familia
          <textarea value={response} onChange={(event) => setResponse(event.target.value)} maxLength={2000} rows={3} required autoFocus />
        </label>
        <div className="modal-actions">
          <button className="secondary-action" type="button" onClick={() => setResponding(false)}>Cancelar</button>
          <button className="primary-action" type="submit" disabled={busy}>{busy ? "Enviando…" : "Enviar respuesta"}</button>
        </div>
      </form>
    )}
    {error && <p className="form-message error-message" role="alert">{error}</p>}
  </article>;
}
