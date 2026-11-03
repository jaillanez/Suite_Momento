import { type FormEvent, useEffect, useState } from "react";
import { Modal, readApiError } from "./OrganizationsPanel";

type FamilyUpdate = {
  id: string;
  text: string;
  published_at: string;
  published_by_name: string;
  from_entry: boolean;
  withdrawn: boolean;
  withdraw_reason: string | null;
  withdrawn_by_name: string | null;
  can_withdraw: boolean;
};
type Listing = { updates: FamilyUpdate[]; readers: string[]; can_publish: boolean };

const time = (value: string) => new Date(value).toLocaleString("es-AR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

const updatesPath = (unitId: string, recipientId: string) => `/api/care-units/${unitId}/care-recipients/${recipientId}/family-updates`;

/** Sección de la ficha: lo publicado para la familia y quién lo puede leer. */
export function FamilyUpdatesSection({ unitId, recipientId, recipientName }: { unitId: string; recipientId: string; recipientName: string }) {
  const [data, setData] = useState<Listing | null>(null);
  const [error, setError] = useState("");
  const [writing, setWriting] = useState(false);
  const path = updatesPath(unitId, recipientId);

  async function reload() {
    try {
      const response = await fetch(path);
      if (!response.ok) throw new Error(await readApiError(response));
      setData((await response.json()) as Listing);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudieron cargar las novedades.");
    }
  }

  useEffect(() => { void reload(); }, [path]);

  async function withdraw(update: FamilyUpdate) {
    const reason = window.prompt("¿Por qué se retira esta novedad? La familia deja de verla.");
    if (!reason?.trim()) return;
    try {
      const response = await fetch(`/api/care-units/${unitId}/family-updates/${update.id}/withdraw`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      void reload();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo retirar.");
    }
  }

  return (
    <article className="profile-section">
      <div className="profile-section-heading">
        <h4>Novedades para la familia</h4>
        {data?.can_publish && data.readers.length > 0 && (
          <div className="section-actions">
            <button className="primary-action" type="button" onClick={() => setWriting(true)}>+ Novedad</button>
          </div>
        )}
      </div>
      {data && (
        <p className="modal-help">
          {data.readers.length
            ? `La leen: ${data.readers.join(", ")}. Solo ven lo que se publica acá, nunca el registro diario.`
            : "Ningún familiar tiene el permiso «Novedades» para esta persona. Se habilita en Usuarios y vínculos."}
        </p>
      )}
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {data && (data.updates.length === 0 ? <p className="list-empty">Todavía no se publicó nada.</p> : (
        <ul className="care-entries">
          {data.updates.map((update) => (
            <li key={update.id} className={update.withdrawn ? "voided" : ""}>
              <div className="care-entry-meta">
                <span className="entry-tag entry-family">Familia</span>
                <small>{time(update.published_at)} · {update.published_by_name}{update.from_entry ? " · a partir de un registro" : ""}</small>
              </div>
              <p>{update.text}</p>
              {update.withdrawn && <small className="void-note">Retirada por {update.withdrawn_by_name}: {update.withdraw_reason}</small>}
              {update.can_withdraw && <button className="link-action danger" type="button" onClick={() => void withdraw(update)}>Retirar</button>}
            </li>
          ))}
        </ul>
      ))}
      {writing && <FamilyUpdateModal unitId={unitId} recipientId={recipientId} recipientName={recipientName} onClose={() => setWriting(false)} onPublished={() => { setWriting(false); void reload(); }} />}
    </article>
  );
}

/** Escribir o revisar el texto antes de publicarlo. Si parte de un registro, se puede reescribir. */
export function FamilyUpdateModal({ unitId, recipientId, recipientName, initialText = "", sourceEntryId, onClose, onPublished }: {
  unitId: string;
  recipientId: string;
  recipientName: string;
  initialText?: string;
  sourceEntryId?: string;
  onClose: () => void;
  onPublished: () => void;
}) {
  const [text, setText] = useState(initialText);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const response = await fetch(updatesPath(unitId, recipientId), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, source_entry_id: sourceEntryId ?? null }),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      onPublished();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo publicar.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title={`Novedad para la familia de ${recipientName}`} onClose={onClose}>
      <form className="modal-form" onSubmit={submit}>
        <p className="modal-help">La familia va a leer exactamente este texto. Escribilo pensando en ella y revisá que no incluya datos de salud ni de otras personas que no corresponda compartir.</p>
        <label>Texto
          <textarea value={text} onChange={(event) => setText(event.target.value)} maxLength={1000} rows={5} required autoFocus />
        </label>
        {error && <p className="form-message error-message" role="alert">{error}</p>}
        <div className="modal-actions">
          <button className="secondary-action" type="button" onClick={onClose}>Cancelar</button>
          <button className="primary-action" type="submit" disabled={saving || !text.trim()}>{saving ? "Publicando…" : "Publicar para la familia"}</button>
        </div>
      </form>
    </Modal>
  );
}
