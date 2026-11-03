import { type FormEvent, useEffect, useState } from "react";
import { Modal, readApiError } from "./OrganizationsPanel";

export type EntryCategory = "food" | "hygiene" | "sleep" | "mood" | "activity" | "health" | "incident" | "other";
export type CareEntry = {
  id: string;
  care_recipient_id: string;
  recipient_name: string;
  category: EntryCategory;
  category_label: string;
  text: string;
  important: boolean;
  occurred_at: string;
  recorded_by_name: string;
  voided: boolean;
  void_reason: string | null;
  voided_by_name: string | null;
  can_void: boolean;
};
export type CareTask = {
  id: string;
  title: string;
  details: string | null;
  due_on: string | null;
  status: "open" | "done" | "cancelled";
  care_recipient_id: string | null;
  recipient_name: string | null;
  created_by_name: string;
  created_at: string;
  closed_by_name: string | null;
  closing_note: string | null;
  can_cancel: boolean;
};
type Shift = { label: string; start: string; end: string };
export type EntrySettings = { categories: { code: EntryCategory; label: string }[]; max_backdate_days: number; incident_always_important: boolean };
type Handover = { current_shift: Shift; previous_shift: Shift; entries: CareEntry[]; open_tasks: CareTask[]; settings: EntrySettings };
type Organization = { id: string; name: string };
type Unit = { id: string; name: string };
type Recipient = { id: string; display_name: string; preferred_name?: string | null };

async function send<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!response.ok) throw new Error(await readApiError(response));
  return (await response.json()) as T;
}

const time = (value: string) => new Date(value).toLocaleString("es-AR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const hour = (value: string) => new Date(value).toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const today = () => new Date().toLocaleDateString("en-CA");

/** Pantalla del turno: lo ocurrido desde el turno anterior y los pendientes del servicio. */
export default function CareShiftPanel() {
  const [units, setUnits] = useState<Unit[]>([]);
  const [unitId, setUnitId] = useState("");
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [data, setData] = useState<Handover | null>(null);
  const [error, setError] = useState("");
  const [recording, setRecording] = useState(false);
  const [addingTask, setAddingTask] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch("/api/organizations");
        if (!response.ok) throw new Error(await readApiError(response));
        const all: Unit[] = [];
        for (const organization of (await response.json()) as Organization[]) {
          const unitResponse = await fetch(`/api/organizations/${organization.id}/care-units`);
          if (unitResponse.ok) all.push(...((await unitResponse.json()) as Unit[]));
        }
        setUnits(all);
        setUnitId(all[0]?.id ?? "");
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "No se pudieron cargar los servicios.");
      }
    })();
  }, []);

  async function reload(id = unitId) {
    if (!id) return;
    setError("");
    try {
      const [handover, people] = await Promise.all([fetch(`/api/care-units/${id}/handover`), fetch(`/api/care-units/${id}/care-recipients`)]);
      if (!handover.ok) throw new Error(await readApiError(handover));
      setData((await handover.json()) as Handover);
      setRecipients(people.ok ? ((await people.json()) as Recipient[]) : []);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo cargar el turno.");
    }
  }

  useEffect(() => { void reload(unitId); }, [unitId]);

  const previousStart = data ? new Date(data.previous_shift.start).getTime() : 0;
  const currentStart = data ? new Date(data.current_shift.start).getTime() : 0;
  const inPrevious = data?.entries.filter((entry) => new Date(entry.occurred_at).getTime() < currentStart) ?? [];
  const inCurrent = data?.entries.filter((entry) => new Date(entry.occurred_at).getTime() >= currentStart) ?? [];
  const important = data?.entries.filter((entry) => entry.important && new Date(entry.occurred_at).getTime() >= previousStart) ?? [];

  return (
    <section className="management-view">
      <header className="view-heading">
        <div>
          <p className="eyebrow">Continuidad del cuidado</p>
          <h2>Turno y registros</h2>
          <p>Lo que pasó desde el turno anterior, lo importante y los pendientes. La familia no ve estos registros.</p>
        </div>
        <div className="view-heading-actions">
          {units.length > 1 && (
            <select aria-label="Servicio" value={unitId} onChange={(event) => setUnitId(event.target.value)}>
              {units.map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
            </select>
          )}
          <button className="secondary-action" type="button" disabled={!unitId} onClick={() => setAddingTask(true)}>+ Pendiente</button>
          <button className="primary-action" type="button" disabled={!recipients.length || !data} onClick={() => setRecording(true)}>+ Registrar</button>
        </div>
      </header>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {!data ? <p className="empty-state" role="status">{units.length || error ? "Cargando turno…" : "Cargando…"}</p> : (
        <div className="shift-grid">
          <article className="management-card shift-important">
            <h3>Para tener en cuenta <span className="count-badge">{important.length}</span></h3>
            {important.length === 0 ? <p className="list-empty">Nada marcado como importante desde el turno anterior.</p> : <EntryList entries={important} showPerson onChanged={() => void reload()} unitId={unitId} />}
          </article>
          <article className="management-card">
            <h3>Pendientes <span className="count-badge">{data.open_tasks.length}</span></h3>
            <TaskList tasks={data.open_tasks} unitId={unitId} onChanged={() => void reload()} />
          </article>
          <article className="management-card">
            <h3>Turno actual · {data.current_shift.label} <small>desde {hour(data.current_shift.start)}</small></h3>
            {inCurrent.length === 0 ? <p className="list-empty">Todavía no hay registros en este turno.</p> : <EntryList entries={inCurrent} showPerson onChanged={() => void reload()} unitId={unitId} />}
          </article>
          <article className="management-card">
            <h3>Turno anterior · {data.previous_shift.label} <small>{hour(data.previous_shift.start)} a {hour(data.previous_shift.end)}</small></h3>
            {inPrevious.length === 0 ? <p className="list-empty">No hubo registros en el turno anterior.</p> : <EntryList entries={inPrevious} showPerson onChanged={() => void reload()} unitId={unitId} />}
          </article>
        </div>
      )}
      {recording && data && <EntryModal unitId={unitId} recipients={recipients} settings={data.settings} onClose={() => setRecording(false)} onSaved={() => { setRecording(false); void reload(); }} />}
      {addingTask && <TaskModal unitId={unitId} recipients={recipients} onClose={() => setAddingTask(false)} onSaved={() => { setAddingTask(false); void reload(); }} />}
    </section>
  );
}

/** Sección de la ficha: registros de los últimos 7 días y pendientes de la persona. */
export function CareLogSection({ unitId, recipientId, recipientName }: { unitId: string; recipientId: string; recipientName: string }) {
  const [entries, setEntries] = useState<CareEntry[]>([]);
  const [tasks, setTasks] = useState<CareTask[]>([]);
  const [settings, setSettings] = useState<EntrySettings | null>(null);
  const [error, setError] = useState("");
  const [recording, setRecording] = useState(false);
  const [addingTask, setAddingTask] = useState(false);
  const path = `/api/care-units/${unitId}/care-recipients/${recipientId}/care-entries`;

  async function reload() {
    try {
      const response = await fetch(path);
      if (!response.ok) throw new Error(await readApiError(response));
      const data = (await response.json()) as { entries: CareEntry[]; open_tasks: CareTask[]; settings: EntrySettings };
      setEntries(data.entries);
      setTasks(data.open_tasks);
      setSettings(data.settings);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo cargar el registro.");
    }
  }

  useEffect(() => { void reload(); }, [path]);
  const person = [{ id: recipientId, display_name: recipientName }];

  return (
    <article className="profile-section">
      <div className="profile-section-heading">
        <h4>Registro diario</h4>
        <div className="section-actions">
          <button className="link-action" type="button" onClick={() => setAddingTask(true)}>+ Pendiente</button>
          <button className="primary-action" type="button" disabled={!settings} onClick={() => setRecording(true)}>+ Registrar</button>
        </div>
      </div>
      <p className="modal-help">Últimos 7 días. Los registros no se editan; si hay un error, se anulan con un motivo.</p>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {tasks.length > 0 && <TaskList tasks={tasks} unitId={unitId} onChanged={() => void reload()} />}
      {entries.length === 0 ? <p className="list-empty">Sin registros en los últimos 7 días.</p> : <EntryList entries={entries} unitId={unitId} onChanged={() => void reload()} />}
      {recording && settings && <EntryModal unitId={unitId} recipients={person} settings={settings} onClose={() => setRecording(false)} onSaved={() => { setRecording(false); void reload(); }} />}
      {addingTask && <TaskModal unitId={unitId} recipients={person} onClose={() => setAddingTask(false)} onSaved={() => { setAddingTask(false); void reload(); }} />}
    </article>
  );
}

function EntryList({ entries, unitId, showPerson = false, onChanged }: { entries: CareEntry[]; unitId: string; showPerson?: boolean; onChanged: () => void }) {
  const [error, setError] = useState("");

  async function voidEntry(entry: CareEntry) {
    const reason = window.prompt("¿Por qué se anula este registro? (queda visible tachado)");
    if (!reason?.trim()) return;
    try {
      await send(`/api/care-units/${unitId}/care-entries/${entry.id}/void`, { reason });
      onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo anular.");
    }
  }

  return (
    <>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      <ul className="care-entries">
        {entries.map((entry) => (
          <li key={entry.id} className={(entry.voided ? "voided" : "") + (entry.important ? " important" : "")}>
            <div className="care-entry-meta">
              <span className={`entry-tag entry-${entry.category}`}>{entry.category_label}</span>
              {showPerson && <strong>{entry.recipient_name}</strong>}
              <small>{time(entry.occurred_at)} · {entry.recorded_by_name}</small>
              {entry.important && !entry.voided && <span className="status-pill status-amber">Importante</span>}
            </div>
            <p>{entry.text}</p>
            {entry.voided && <small className="void-note">Anulado por {entry.voided_by_name}: {entry.void_reason}</small>}
            {entry.can_void && <button className="link-action danger" type="button" onClick={() => void voidEntry(entry)}>Anular</button>}
          </li>
        ))}
      </ul>
    </>
  );
}

function TaskList({ tasks, unitId, onChanged }: { tasks: CareTask[]; unitId: string; onChanged: () => void }) {
  const [error, setError] = useState("");

  async function close(task: CareTask, action: "complete" | "cancel") {
    const note = action === "complete" ? window.prompt("Nota (opcional): ¿cómo se resolvió?") : window.prompt("¿Por qué se cancela? (opcional)");
    if (note === null) return;
    try {
      await send(`/api/care-units/${unitId}/care-tasks/${task.id}/${action}`, { note });
      onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo actualizar el pendiente.");
    }
  }

  if (tasks.length === 0) return <p className="list-empty">No hay pendientes abiertos.</p>;
  return (
    <>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      <ul className="care-tasks">
        {tasks.map((task) => {
          const overdue = task.due_on !== null && task.due_on < today();
          return (
            <li key={task.id}>
              <div>
                <strong>{task.title}</strong>
                {task.recipient_name && <span> · {task.recipient_name}</span>}
                {task.details && <p>{task.details}</p>}
                <small>
                  {task.due_on ? <span className={overdue ? "overdue" : undefined}>Para el {new Date(`${task.due_on}T12:00:00`).toLocaleDateString("es-AR")} · </span> : null}
                  Cargó {task.created_by_name}
                </small>
              </div>
              <div className="section-actions">
                <button className="secondary-action" type="button" onClick={() => void close(task, "complete")}>Hecho</button>
                {task.can_cancel && <button className="link-action" type="button" onClick={() => void close(task, "cancel")}>Cancelar</button>}
              </div>
            </li>
          );
        })}
      </ul>
    </>
  );
}

function EntryModal({ unitId, recipients, settings, onClose, onSaved }: { unitId: string; recipients: Recipient[]; settings: EntrySettings; onClose: () => void; onSaved: () => void }) {
  const [recipientId, setRecipientId] = useState(recipients.length === 1 ? recipients[0].id : "");
  const [category, setCategory] = useState<EntryCategory | "">("");
  const [text, setText] = useState("");
  const [important, setImportant] = useState(false);
  const [earlier, setEarlier] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const forcedImportant = category === "incident" && settings.incident_always_important;
  const toLocalInput = (date: Date) => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!category) { setError("Elegí el tipo de registro."); return; }
    setSaving(true);
    setError("");
    try {
      await send(`/api/care-units/${unitId}/care-recipients/${recipientId}/care-entries`, {
        category, text, important: important || forcedImportant,
        occurred_at: earlier ? new Date(earlier).toISOString() : null,
      });
      onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo guardar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title="Nuevo registro" onClose={onClose}>
      <form className="modal-form" onSubmit={submit}>
        {recipients.length > 1 && (
          <label>Persona
            <select value={recipientId} onChange={(event) => setRecipientId(event.target.value)} required autoFocus>
              <option value="">Elegí a la persona…</option>
              {recipients.map((person) => <option key={person.id} value={person.id}>{person.preferred_name || person.display_name}</option>)}
            </select>
          </label>
        )}
        <fieldset className="category-chips">
          <legend>Tipo</legend>
          {settings.categories.map(({ code, label }) => (
            <label key={code} className={"chip" + (category === code ? " selected" : "")}>
              <input type="radio" name="category" value={code} checked={category === code} onChange={() => setCategory(code)} />
              {label}
            </label>
          ))}
        </fieldset>
        <label>Qué pasó
          <textarea rows={3} value={text} onChange={(event) => setText(event.target.value)} maxLength={2000} required placeholder="Ej.: Almorzó la mitad; dijo que no tenía hambre." />
        </label>
        <label className="inline-check">
          <input type="checkbox" checked={important || forcedImportant} disabled={forcedImportant} onChange={(event) => setImportant(event.target.checked)} />
          Importante para el próximo turno {forcedImportant && "(en este servicio los incidentes siempre lo son)"}
        </label>
        {settings.max_backdate_days > 0 && (
          <label>¿Pasó antes? (opcional; hasta {settings.max_backdate_days} {settings.max_backdate_days === 1 ? "día" : "días"})
            <input type="datetime-local" value={earlier} min={toLocalInput(new Date(Date.now() - settings.max_backdate_days * 86400000))} max={toLocalInput(new Date())} onChange={(event) => setEarlier(event.target.value)} />
          </label>
        )}
        <p className="modal-help">Momento no interpreta los registros. Ante una urgencia, seguí el protocolo de la residencia.</p>
        {error && <p className="form-message error-message" role="alert">{error}</p>}
        <div className="modal-actions">
          <button className="secondary-action" type="button" onClick={onClose}>Cancelar</button>
          <button className="primary-action" type="submit" disabled={saving || !recipientId}>{saving ? "Guardando…" : "Guardar registro"}</button>
        </div>
      </form>
    </Modal>
  );
}

function TaskModal({ unitId, recipients, onClose, onSaved }: { unitId: string; recipients: Recipient[]; onClose: () => void; onSaved: () => void }) {
  const single = recipients.length === 1;
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const [dueOn, setDueOn] = useState("");
  const [recipientId, setRecipientId] = useState(single ? recipients[0].id : "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await send(`/api/care-units/${unitId}/care-tasks`, { title, details: details || null, due_on: dueOn || null, care_recipient_id: recipientId || null });
      onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo guardar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title="Nuevo pendiente" onClose={onClose}>
      <form className="modal-form" onSubmit={submit}>
        <label>Pendiente
          <input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} required autoFocus placeholder="Ej.: Llamar a la hija para avisar del turno médico" />
        </label>
        {!single && (
          <label>Persona (opcional)
            <select value={recipientId} onChange={(event) => setRecipientId(event.target.value)}>
              <option value="">Del servicio en general</option>
              {recipients.map((person) => <option key={person.id} value={person.id}>{person.preferred_name || person.display_name}</option>)}
            </select>
          </label>
        )}
        <div className="modal-form-grid">
          <label>Para cuándo (opcional)<input type="date" value={dueOn} onChange={(event) => setDueOn(event.target.value)} /></label>
          <label>Detalle (opcional)<input value={details} onChange={(event) => setDetails(event.target.value)} maxLength={2000} /></label>
        </div>
        <p className="modal-help">El pendiente pasa de turno en turno hasta que alguien lo marque como hecho.</p>
        {error && <p className="form-message error-message" role="alert">{error}</p>}
        <div className="modal-actions">
          <button className="secondary-action" type="button" onClick={onClose}>Cancelar</button>
          <button className="primary-action" type="submit" disabled={saving}>{saving ? "Guardando…" : "Guardar pendiente"}</button>
        </div>
      </form>
    </Modal>
  );
}
