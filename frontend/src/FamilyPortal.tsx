import { type FormEvent, useEffect, useState } from "react";
import { categoryClass, formatDate } from "./InboxPanel";
import { type Category, categoryLabels, readApiError } from "./OrganizationsPanel";

type LinkedPerson = {
  care_recipient_id: string;
  display_name: string;
  care_unit_name: string;
  categories: { category: Category; can_view: boolean; can_respond: boolean; can_request: boolean }[];
};

type FamilyRequest = {
  id: string;
  care_recipient_name: string;
  category: Category;
  subject: string;
  message: string;
  status_label: string;
  shared_response: string | null;
  responded_at: string | null;
  created_at: string;
};

export default function FamilyPortal({ userName, onLogout }: { userName: string; onLogout: () => void }) {
  const [people, setPeople] = useState<LinkedPerson[]>([]);
  const [requests, setRequests] = useState<FamilyRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [composing, setComposing] = useState(false);

  async function load() {
    setError("");
    try {
      const [peopleResponse, requestsResponse] = await Promise.all([fetch("/api/family/people"), fetch("/api/family/requests")]);
      if (!peopleResponse.ok) throw new Error(await readApiError(peopleResponse));
      if (!requestsResponse.ok) throw new Error(await readApiError(requestsResponse));
      setPeople((await peopleResponse.json()) as LinkedPerson[]);
      setRequests((await requestsResponse.json()) as FamilyRequest[]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo cargar la información.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  const canRequest = people.some((person) => person.categories.some((item) => item.can_request));

  return (
    <div className="family-portal">
      <header className="public-header">
        <div className="app-brand"><img src="/brand/iso-momento.png" alt="" /><span>Momento</span></div>
        <div className="topbar-actions">
          <span className="demo-user-badge">{userName}</span>
          <button className="login-button" type="button" onClick={onLogout}>Salir</button>
        </div>
      </header>
      <main className="family-content">
        <div className="dashboard-heading-row">
          <div><p className="eyebrow">Acceso familiar</p><h1>Hola, {userName.split(" ")[0]}.</h1><p>Acá ves la información que la residencia te autorizó y tus consultas al equipo.</p></div>
          {canRequest && !composing && <button className="primary-action" type="button" onClick={() => setComposing(true)}>Nueva consulta</button>}
        </div>
        {error && <p className="form-message error-message" role="alert">{error}</p>}
        {loading ? <p className="empty-state" role="status">Cargando…</p> : (
          <>
            {composing && <RequestForm people={people} onCancel={() => setComposing(false)} onSent={() => { setComposing(false); void load(); }} />}
            <section className="family-section" aria-labelledby="family-people">
              <h2 id="family-people">Personas a cargo</h2>
              {people.length === 0 ? (
                <div className="empty-panel"><h3>Todavía no tenés autorizaciones</h3><p>Pedile a la residencia que habilite tu acceso. Lo puede hacer el encargado, un administrativo o el médico.</p></div>
              ) : (
                <div className="family-people">
                  {people.map((person) => (
                    <article className="family-person" key={person.care_recipient_id}>
                      <h3>{person.display_name}</h3>
                      <p>{person.care_unit_name}</p>
                      <div className="family-categories">
                        {person.categories.map((item) => <span key={item.category} className={"request-type " + categoryClass[item.category]}>{categoryLabels[item.category]}</span>)}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
            <section className="family-section" aria-labelledby="family-requests">
              <h2 id="family-requests">Mis consultas</h2>
              {requests.length === 0 ? <p className="list-empty">Todavía no enviaste consultas.</p> : (
                <div className="inbox-list">
                  {requests.map((item) => (
                    <article className="inbox-item" key={item.id}>
                      <div className="inbox-item-top">
                        <span className={"request-type " + categoryClass[item.category]}>{categoryLabels[item.category]}</span>
                        <span className="request-date">{formatDate(item.created_at)}</span>
                      </div>
                      <h3>{item.subject}</h3>
                      <p>Sobre <strong>{item.care_recipient_name}</strong></p>
                      <p className="inbox-message">{item.message}</p>
                      {item.shared_response && <div className="inbox-response"><span>Respuesta del equipo</span><p>{item.shared_response}</p></div>}
                      <div className="inbox-item-actions"><span className="status-pill status-blue">{item.status_label}</span></div>
                    </article>
                  ))}
                </div>
              )}
            </section>
            <p className="dashboard-preview-note">Tus consultas llegan a la bandeja de la residencia. Una consulta no cambia por sí sola la medicación, la dieta ni las actividades indicadas.</p>
          </>
        )}
      </main>
    </div>
  );
}

function RequestForm({ people, onCancel, onSent }: { people: LinkedPerson[]; onCancel: () => void; onSent: () => void }) {
  const requestable = people.filter((person) => person.categories.some((item) => item.can_request));
  const [personId, setPersonId] = useState(requestable[0]?.care_recipient_id ?? "");
  const person = requestable.find((item) => item.care_recipient_id === personId);
  const categories = person?.categories.filter((item) => item.can_request).map((item) => item.category) ?? [];
  const [category, setCategory] = useState<Category | "">(categories[0] ?? "");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function choosePerson(id: string) {
    setPersonId(id);
    const next = requestable.find((item) => item.care_recipient_id === id)?.categories.find((item) => item.can_request);
    setCategory(next?.category ?? "");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const response = await fetch("/api/family/requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ care_recipient_id: personId, category, subject, message }),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      onSent();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo enviar la consulta.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="family-request-form" onSubmit={submit}>
      <h2>Nueva consulta</h2>
      <div className="modal-form-grid">
        <label>Persona
          <select value={personId} onChange={(event) => choosePerson(event.target.value)} required>
            {requestable.map((item) => <option value={item.care_recipient_id} key={item.care_recipient_id}>{item.display_name}</option>)}
          </select>
        </label>
        <label>Tema
          <select value={category} onChange={(event) => setCategory(event.target.value as Category)} required>
            {categories.map((item) => <option value={item} key={item}>{categoryLabels[item]}</option>)}
          </select>
        </label>
      </div>
      <label>Asunto<input value={subject} onChange={(event) => setSubject(event.target.value)} maxLength={160} required /></label>
      <label>Mensaje<textarea value={message} onChange={(event) => setMessage(event.target.value)} maxLength={2000} rows={4} required /></label>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      <div className="modal-actions">
        <button className="secondary-action" type="button" onClick={onCancel}>Cancelar</button>
        <button className="primary-action" type="submit" disabled={saving || !category}>{saving ? "Enviando…" : "Enviar consulta"}</button>
      </div>
    </form>
  );
}
