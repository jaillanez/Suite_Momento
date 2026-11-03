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
  has_photo: boolean;
};
type Consent = { given_by: string; given_on: string };
type Listing = {
  updates: FamilyUpdate[];
  readers: string[];
  can_publish: boolean;
  photos_enabled: boolean;
  image_consent: Consent | null;
  can_manage_consent: boolean;
};
type Photo = { content_type: "image/jpeg" | "image/png"; data: string; preview: string };

const MAX_PHOTO_BYTES = 5 * 1024 * 1024;

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
      {data?.photos_enabled && <ImageConsent path={`/api/care-units/${unitId}/care-recipients/${recipientId}/image-consent`} consent={data.image_consent} canManage={data.can_manage_consent} onChanged={() => void reload()} />}
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
              {update.has_photo && <img className="family-photo" src={`/api/care-units/${unitId}/family-updates/${update.id}/photo`} alt={`Foto compartida con la familia de ${recipientName}`} loading="lazy" />}
              {update.withdrawn && <small className="void-note">Retirada por {update.withdrawn_by_name}: {update.withdraw_reason}</small>}
              {update.can_withdraw && <button className="link-action danger" type="button" onClick={() => void withdraw(update)}>Retirar</button>}
            </li>
          ))}
        </ul>
      ))}
      {writing && <FamilyUpdateModal unitId={unitId} recipientId={recipientId} recipientName={recipientName} photoAllowed={Boolean(data?.photos_enabled && data.image_consent)} onClose={() => setWriting(false)} onPublished={() => { setWriting(false); void reload(); }} />}
    </article>
  );
}

/** Quién dio el consentimiento de imagen y cuándo. Sin él no se comparten fotos. */
function ImageConsent({ path, consent, canManage, onChanged }: { path: string; consent: Consent | null; canManage: boolean; onChanged: () => void }) {
  const [editing, setEditing] = useState(false);
  const [givenBy, setGivenBy] = useState("");
  const [givenOn, setGivenOn] = useState(new Date().toLocaleDateString("en-CA"));
  const [error, setError] = useState("");

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const response = await fetch(path, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ given_by: givenBy, given_on: givenOn }) });
    if (!response.ok) { setError(await readApiError(response)); return; }
    setEditing(false);
    onChanged();
  }

  async function revoke() {
    if (!window.confirm("¿Quitar el consentimiento? La familia deja de ver las fotos ya publicadas.")) return;
    const response = await fetch(path, { method: "DELETE" });
    if (!response.ok) { setError(await readApiError(response)); return; }
    onChanged();
  }

  return (
    <div className="image-consent">
      {consent ? (
        <p>Consentimiento de imagen: <strong>{consent.given_by}</strong>, el {new Date(`${consent.given_on}T12:00:00`).toLocaleDateString("es-AR")}.
          {canManage && <> <button className="link-action danger" type="button" onClick={() => void revoke()}>Quitar</button></>}
        </p>
      ) : (
        <p>Sin consentimiento de imagen: no se pueden compartir fotos.
          {canManage && !editing && <> <button className="link-action" type="button" onClick={() => setEditing(true)}>Registrar consentimiento</button></>}
        </p>
      )}
      {editing && (
        <form className="image-consent-form" onSubmit={save}>
          <label>Quién lo dio<input value={givenBy} onChange={(event) => setGivenBy(event.target.value)} placeholder="La persona, o su representante con nombre" maxLength={160} required /></label>
          <label>Fecha<input type="date" value={givenOn} max={new Date().toLocaleDateString("en-CA")} onChange={(event) => setGivenOn(event.target.value)} required /></label>
          <p className="modal-help">Guardá el consentimiento firmado en Documentos, con el tipo «Consentimiento».</p>
          <div className="modal-actions">
            <button className="secondary-action" type="button" onClick={() => setEditing(false)}>Cancelar</button>
            <button className="primary-action" type="submit">Guardar</button>
          </div>
        </form>
      )}
      {error && <p className="form-message error-message" role="alert">{error}</p>}
    </div>
  );
}

/** Escribir o revisar el texto antes de publicarlo. Si parte de un registro, se puede reescribir. */
export function FamilyUpdateModal({ unitId, recipientId, recipientName, initialText = "", sourceEntryId, photoAllowed = false, onClose, onPublished }: {
  unitId: string;
  recipientId: string;
  recipientName: string;
  initialText?: string;
  sourceEntryId?: string;
  photoAllowed?: boolean;
  onClose: () => void;
  onPublished: () => void;
}) {
  const [text, setText] = useState(initialText);
  const [photo, setPhoto] = useState<Photo | null>(null);
  const [othersConfirmed, setOthersConfirmed] = useState(false);
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
        body: JSON.stringify({
          text,
          source_entry_id: sourceEntryId ?? null,
          photo: photo ? { content_type: photo.content_type, data: photo.data } : null,
          others_confirmed: othersConfirmed,
        }),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      onPublished();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo publicar.");
    } finally {
      setSaving(false);
    }
  }

  function choosePhoto(file: File | undefined) {
    setError("");
    if (!file) { setPhoto(null); return; }
    if (file.type !== "image/jpeg" && file.type !== "image/png") { setError("La foto debe ser JPG o PNG."); return; }
    if (file.size > MAX_PHOTO_BYTES) { setError("La foto supera los 5 MB."); return; }
    const reader = new FileReader();
    reader.onload = () => {
      const url = String(reader.result);
      setPhoto({ content_type: file.type as Photo["content_type"], data: url.slice(url.indexOf(",") + 1), preview: url });
    };
    reader.readAsDataURL(file);
  }

  return (
    <Modal title={`Novedad para la familia de ${recipientName}`} onClose={onClose}>
      <form className="modal-form" onSubmit={submit}>
        <p className="modal-help">La familia va a leer exactamente este texto. Escribilo pensando en ella y revisá que no incluya datos de salud ni de otras personas que no corresponda compartir.</p>
        <label>Texto
          <textarea value={text} onChange={(event) => setText(event.target.value)} maxLength={1000} rows={5} required autoFocus />
        </label>
        {photoAllowed && (
          <>
            <label>Foto (opcional, JPG o PNG hasta 5 MB)
              <input type="file" accept="image/jpeg,image/png" onChange={(event) => choosePhoto(event.target.files?.[0])} />
            </label>
            {photo && (
              <>
                <img className="family-photo" src={photo.preview} alt="Vista previa de la foto" />
                <label className="inline-check">
                  <input type="checkbox" checked={othersConfirmed} onChange={(event) => setOthersConfirmed(event.target.checked)} />
                  En la foto no aparecen otras personas, o también dieron su consentimiento
                </label>
              </>
            )}
          </>
        )}
        {error && <p className="form-message error-message" role="alert">{error}</p>}
        <div className="modal-actions">
          <button className="secondary-action" type="button" onClick={onClose}>Cancelar</button>
          <button className="primary-action" type="submit" disabled={saving || !text.trim() || (photo !== null && !othersConfirmed)}>{saving ? "Publicando…" : "Publicar para la familia"}</button>
        </div>
      </form>
    </Modal>
  );
}
