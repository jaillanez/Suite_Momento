import { type FormEvent, useEffect, useState } from "react";
import { readApiError } from "./OrganizationsPanel";

type Contact = {
  id: string;
  full_name: string;
  relationship_label: string | null;
  phone: string | null;
  email: string | null;
  is_emergency: boolean;
  is_legal_representative: boolean;
  notes: string | null;
};

type Profile = Record<string, string | boolean | null | Contact[]> & {
  id: string;
  display_name: string;
  birth_date: string | null;
  room: string | null;
  is_active: boolean;
  contacts: Contact[];
  can_edit: boolean;
  can_edit_health: boolean;
  can_deactivate: boolean;
};

type Field = { key: string; label: string; type?: "date" | "textarea" | "select"; options?: string[]; wide?: boolean };
type Section = { id: string; title: string; note?: string; health?: boolean; fields: Field[] };

const sections: Section[] = [
  {
    id: "identity",
    title: "Identificación",
    fields: [
      { key: "display_name", label: "Nombre visible" },
      { key: "preferred_name", label: "Cómo prefiere que le digan" },
      { key: "first_name", label: "Nombres" },
      { key: "last_name", label: "Apellidos" },
      { key: "birth_date", label: "Fecha de nacimiento", type: "date" },
      { key: "document_type", label: "Tipo de documento", type: "select", options: ["DNI", "CI", "Pasaporte", "Otro"] },
      { key: "document_number", label: "Número de documento" },
      { key: "gender", label: "Género (como la persona lo indique)" },
      { key: "nationality", label: "Nacionalidad" },
      { key: "languages", label: "Idiomas" },
      { key: "admission_date", label: "Fecha de ingreso", type: "date" },
      { key: "room", label: "Habitación / cama" },
      { key: "address", label: "Domicilio (cuidado domiciliario)", wide: true },
    ],
  },
  {
    id: "coverage",
    title: "Cobertura y médico de cabecera",
    fields: [
      { key: "health_coverage", label: "Obra social, prepaga o mutualista" },
      { key: "coverage_member_number", label: "Número de afiliado" },
      { key: "primary_physician", label: "Médico de cabecera" },
      { key: "primary_physician_phone", label: "Teléfono del médico" },
    ],
  },
  {
    id: "health",
    title: "Salud y apoyos",
    note: "Información de referencia cargada por el encargado o el médico. No reemplaza la historia clínica ni son indicaciones.",
    health: true,
    fields: [
      { key: "allergies", label: "Alergias", type: "textarea" },
      { key: "relevant_conditions", label: "Antecedentes relevantes", type: "textarea" },
      { key: "diet_notes", label: "Dieta y restricciones", type: "textarea" },
      { key: "mobility_support", label: "Movilidad y ayudas técnicas", type: "textarea" },
      { key: "sensory_communication", label: "Audición, visión y comunicación", type: "textarea" },
      { key: "support_needs", label: "Apoyos y cuidados especiales", type: "textarea" },
    ],
  },
  {
    id: "story",
    title: "Historia de vida y preferencias",
    fields: [
      { key: "life_history", label: "Historia de vida", type: "textarea", wide: true },
      { key: "preferences", label: "Gustos y preferencias", type: "textarea" },
      { key: "routines", label: "Rutinas", type: "textarea" },
      { key: "beliefs", label: "Creencias y prácticas espirituales", type: "textarea" },
    ],
  },
];

function formatValue(field: Field, value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (field.type === "date" && typeof value === "string") return new Date(`${value}T12:00:00`).toLocaleDateString("es-AR");
  return String(value);
}

function ageFrom(birthDate: string | null): number | null {
  if (!birthDate) return null;
  const birth = new Date(`${birthDate}T12:00:00`);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  if (today < new Date(today.getFullYear(), birth.getMonth(), birth.getDate())) age -= 1;
  return age;
}

export default function RecipientProfile({ careUnitId, recipientId, onBack }: { careUnitId: string; recipientId: string; onBack: () => void }) {
  const path = `/api/care-units/${careUnitId}/care-recipients/${recipientId}`;
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void fetch(path)
      .then(async (response) => {
        if (!response.ok) throw new Error(await readApiError(response));
        return (await response.json()) as Profile;
      })
      .then((data) => { if (active) setProfile(data); })
      .catch((caught: unknown) => { if (active) setError(caught instanceof Error ? caught.message : "No se pudo cargar la ficha."); });
    return () => { active = false; };
  }, [path]);

  async function save(changes: Record<string, unknown>) {
    const response = await fetch(path, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(changes),
    });
    if (!response.ok) throw new Error(await readApiError(response));
    setProfile((await response.json()) as Profile);
  }

  async function deactivate() {
    if (!profile || !window.confirm(`¿Dar de baja a ${profile.display_name}? Deja de aparecer en el listado; la ficha se conserva.`)) return;
    try {
      await save({ is_active: false });
      onBack();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo dar de baja.");
    }
  }

  if (!profile) {
    return <section className="profile-view"><button className="back-link inline" type="button" onClick={onBack}>← Volver al listado</button>{error ? <p className="form-message error-message" role="alert">{error}</p> : <p className="empty-state" role="status">Cargando ficha…</p>}</section>;
  }

  const age = ageFrom(profile.birth_date);
  const emergency = profile.contacts.find((contact) => contact.is_emergency);

  return (
    <section className="profile-view">
      <button className="back-link inline" type="button" onClick={onBack}>← Volver al listado</button>
      <header className="profile-header">
        <div>
          <p className="eyebrow">Ficha de la persona</p>
          <h3>{profile.display_name}</h3>
          <p className="profile-summary">
            {[age !== null ? `${age} años` : null, profile.room ? `Habitación ${profile.room}` : null, emergency ? `Emergencia: ${emergency.full_name} · ${emergency.phone}` : "Sin contacto de emergencia"].filter(Boolean).join(" · ")}
          </p>
        </div>
        {profile.can_deactivate && <button className="link-action danger" type="button" onClick={() => void deactivate()}>Dar de baja</button>}
      </header>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {sections.map((section) => {
        const canEdit = section.health ? profile.can_edit_health : profile.can_edit;
        return (
          <article className="profile-section" key={section.id}>
            <div className="profile-section-heading">
              <h4>{section.title}</h4>
              {canEdit && editing !== section.id && <button className="link-action" type="button" onClick={() => setEditing(section.id)}>Editar</button>}
            </div>
            {section.note && <p className="modal-help">{section.note}</p>}
            {editing === section.id ? (
              <SectionForm section={section} profile={profile} onCancel={() => setEditing(null)} onSave={async (changes) => { await save(changes); setEditing(null); }} />
            ) : (
              <dl className="profile-fields">
                {section.fields.map((field) => (
                  <div key={field.key} className={field.wide || field.type === "textarea" ? "wide" : undefined}>
                    <dt>{field.label}</dt>
                    <dd>{formatValue(field, profile[field.key])}</dd>
                  </div>
                ))}
              </dl>
            )}
          </article>
        );
      })}
      <ContactsSection path={`${path}/contacts`} contacts={profile.contacts} canEdit={profile.can_edit} onChanged={(contacts) => setProfile({ ...profile, contacts })} />
    </section>
  );
}

function SectionForm({ section, profile, onCancel, onSave }: { section: Section; profile: Profile; onCancel: () => void; onSave: (changes: Record<string, unknown>) => Promise<void> }) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(section.fields.map((field) => [field.key, (profile[field.key] as string | null) ?? ""])),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      // Vacío se envía como null para poder borrar un dato.
      await onSave(Object.fromEntries(Object.entries(values).map(([key, value]) => [key, value.trim() === "" ? null : value])));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo guardar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="profile-form" onSubmit={submit}>
      <div className="profile-form-grid">
        {section.fields.map((field) => (
          <label key={field.key} className={field.wide || field.type === "textarea" ? "wide" : undefined}>
            {field.label}
            {field.type === "textarea" ? (
              <textarea rows={3} value={values[field.key]} onChange={(event) => setValues({ ...values, [field.key]: event.target.value })} />
            ) : field.type === "select" ? (
              <select value={values[field.key]} onChange={(event) => setValues({ ...values, [field.key]: event.target.value })}>
                <option value="">—</option>
                {field.options?.map((option) => <option key={option} value={option}>{option}</option>)}
              </select>
            ) : (
              <input
                type={field.type === "date" ? "date" : "text"}
                value={values[field.key]}
                required={field.key === "display_name"}
                onChange={(event) => setValues({ ...values, [field.key]: event.target.value })}
              />
            )}
          </label>
        ))}
      </div>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      <div className="modal-actions">
        <button className="secondary-action" type="button" onClick={onCancel}>Cancelar</button>
        <button className="primary-action" type="submit" disabled={saving}>{saving ? "Guardando…" : "Guardar"}</button>
      </div>
    </form>
  );
}

const emptyContact = { full_name: "", relationship_label: "", phone: "", email: "", is_emergency: false, is_legal_representative: false, notes: "" };

function ContactsSection({ path, contacts, canEdit, onChanged }: { path: string; contacts: Contact[]; canEdit: boolean; onChanged: (contacts: Contact[]) => void }) {
  const [editing, setEditing] = useState<string | "new" | null>(null);
  const [form, setForm] = useState(emptyContact);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function open(contact: Contact | null) {
    setError("");
    setEditing(contact ? contact.id : "new");
    setForm(contact ? { ...emptyContact, ...Object.fromEntries(Object.entries(contact).map(([key, value]) => [key, value ?? ""])) } as typeof emptyContact : emptyContact);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const isNew = editing === "new";
      const response = await fetch(isNew ? path : `${path}/${editing}`, {
        method: isNew ? "POST" : "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      const saved = (await response.json()) as Contact;
      onChanged(isNew ? [...contacts, saved] : contacts.map((item) => (item.id === saved.id ? saved : item)));
      setEditing(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo guardar el contacto.");
    } finally {
      setSaving(false);
    }
  }

  async function remove(contact: Contact) {
    if (!window.confirm(`¿Quitar a ${contact.full_name} de los contactos?`)) return;
    const response = await fetch(`${path}/${contact.id}`, { method: "DELETE" });
    if (!response.ok) { setError(await readApiError(response)); return; }
    onChanged(contacts.filter((item) => item.id !== contact.id));
  }

  return (
    <article className="profile-section">
      <div className="profile-section-heading">
        <h4>Contactos</h4>
        {canEdit && editing === null && <button className="link-action" type="button" onClick={() => open(null)}>Agregar contacto</button>}
      </div>
      <p className="modal-help">Agregar un contacto no le da acceso a Momento. El acceso a Momento de una familia se autoriza desde la sección de familias.</p>
      {contacts.length === 0 && editing === null && <p className="list-empty">Sin contactos cargados.</p>}
      <ul className="record-list compact">
        {contacts.map((contact) => (
          <li key={contact.id}>
            <div>
              <strong>{contact.full_name}{contact.relationship_label ? ` · ${contact.relationship_label}` : ""}</strong>
              <span>{[contact.phone, contact.email].filter(Boolean).join(" · ") || "Sin datos de contacto"}{contact.notes ? ` · ${contact.notes}` : ""}</span>
            </div>
            <div className="record-controls">
              {contact.is_emergency && <span className="status-pill status-amber">Emergencia</span>}
              {contact.is_legal_representative && <span className="status-pill status-blue">Referente legal</span>}
              {canEdit && <button className="link-action" type="button" onClick={() => open(contact)}>Editar</button>}
              {canEdit && <button className="link-action danger" type="button" onClick={() => void remove(contact)}>Quitar</button>}
            </div>
          </li>
        ))}
      </ul>
      {editing !== null && (
        <form className="profile-form" onSubmit={submit}>
          <div className="profile-form-grid">
            <label>Nombre y apellido<input value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} maxLength={160} required /></label>
            <label>Vínculo<input value={form.relationship_label} onChange={(event) => setForm({ ...form, relationship_label: event.target.value })} maxLength={60} placeholder="Ej.: Hija, vecino" /></label>
            <label>Teléfono<input type="tel" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} maxLength={40} /></label>
            <label>Correo<input type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} maxLength={254} /></label>
            <label className="wide">Notas<input value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} maxLength={200} placeholder="Ej.: llamar después de las 18" /></label>
          </div>
          <div className="check-row">
            <label className="inline-check"><input type="checkbox" checked={form.is_emergency} onChange={(event) => setForm({ ...form, is_emergency: event.target.checked })} />Contacto de emergencia</label>
            <label className="inline-check"><input type="checkbox" checked={form.is_legal_representative} onChange={(event) => setForm({ ...form, is_legal_representative: event.target.checked })} />Referente legal o apoderado</label>
          </div>
          {error && <p className="form-message error-message" role="alert">{error}</p>}
          <div className="modal-actions">
            <button className="secondary-action" type="button" onClick={() => setEditing(null)}>Cancelar</button>
            <button className="primary-action" type="submit" disabled={saving}>{saving ? "Guardando…" : "Guardar contacto"}</button>
          </div>
        </form>
      )}
      {error && editing === null && <p className="form-message error-message" role="alert">{error}</p>}
    </article>
  );
}
