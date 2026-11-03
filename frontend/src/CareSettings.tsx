import { useEffect, useState } from "react";
import { readApiError, type StaffRole, staffRoleLabels } from "./OrganizationsPanel";

type ShiftSetting = { label: string; start_hour: number };
type CategorySetting = { code: string; label: string; enabled: boolean };
type Settings = {
  shifts: ShiftSetting[];
  categories: CategorySetting[];
  max_backdate_days: number;
  incident_always_important: boolean;
  incident_void: "manager" | "author";
  incident_notify_roles: StaffRole[];
  incident_notify_email: boolean;
  family_update_roles: StaffRole[];
  family_update_notify: boolean;
};

const hours = Array.from({ length: 24 }, (_, hour) => hour);
const pad = (hour: number) => `${String(hour).padStart(2, "0")}:00`;

/** Cómo trabaja el servicio en el registro diario; lo decide el encargado de la organización. */
export default function CareSettingsEditor({ organizationId, careUnitId }: { organizationId: string; careUnitId: string }) {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [presets, setPresets] = useState<Record<string, ShiftSetting[]>>({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch(`/api/care-units/${careUnitId}/care-settings`);
        if (!response.ok) throw new Error(await readApiError(response));
        const { presets: loadedPresets, ...data } = (await response.json()) as Settings & { presets: Record<string, ShiftSetting[]> };
        setSettings(data);
        setPresets(loadedPresets);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "No se pudo cargar la configuración.");
      }
    })();
  }, [careUnitId]);

  function change(patch: Partial<Settings>) {
    setSettings((current) => (current ? { ...current, ...patch } : current));
    setMessage("");
  }

  async function save() {
    if (!settings) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const response = await fetch(`/api/organizations/${organizationId}/care-units/${careUnitId}/care-settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      const { presets: _presets, ...data } = (await response.json()) as Settings & { presets: unknown };
      setSettings(data);
      setMessage("Configuración guardada. Se aplica desde ahora.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo guardar.");
    } finally {
      setSaving(false);
    }
  }

  if (!settings) return error ? <p className="form-message error-message" role="alert">{error}</p> : null;
  const shifts = settings.shifts;

  return (
    <details className="care-settings">
      <summary>
        <span>
          <strong>Registro diario y turnos</strong>
          <small>{shifts.length} {shifts.length === 1 ? "turno" : "turnos"} · {settings.categories.filter((c) => c.enabled).length} tipos de novedad · avisos de incidentes: {settings.incident_notify_roles.length ? settings.incident_notify_roles.map((role) => staffRoleLabels[role]).join(", ") + (settings.incident_notify_email ? " (Momento y correo)" : " (en Momento)") : "nadie"}</small>
        </span>
      </summary>

      <fieldset>
        <legend>Turnos</legend>
        <p className="modal-help">Cada turno termina cuando empieza el siguiente. Define qué se muestra en "Turno y registros".</p>
        <div className="option-row">
          {presets["3x8"] && <button className="secondary-action" type="button" onClick={() => change({ shifts: presets["3x8"] })}>3 turnos de 8 h</button>}
          {presets["2x12"] && <button className="secondary-action" type="button" onClick={() => change({ shifts: presets["2x12"] })}>2 turnos de 12 h</button>}
        </div>
        <ul className="care-settings-rows">
          {shifts.map((shift, index) => (
            <li key={index}>
              <input aria-label="Nombre del turno" value={shift.label} maxLength={30} onChange={(event) => change({ shifts: shifts.map((item, i) => (i === index ? { ...item, label: event.target.value } : item)) })} />
              <label>empieza
                <select value={shift.start_hour} onChange={(event) => change({ shifts: shifts.map((item, i) => (i === index ? { ...item, start_hour: Number(event.target.value) } : item)) })}>
                  {hours.map((hour) => <option key={hour} value={hour}>{pad(hour)}</option>)}
                </select>
              </label>
              {shifts.length > 1 && <button className="link-action danger" type="button" onClick={() => change({ shifts: shifts.filter((_, i) => i !== index) })}>Quitar</button>}
            </li>
          ))}
        </ul>
        {shifts.length < 6 && (
          <button className="link-action" type="button" onClick={() => {
            const free = hours.find((hour) => !shifts.some((item) => item.start_hour === hour)) ?? 0;
            change({ shifts: [...shifts, { label: `Turno ${shifts.length + 1}`, start_hour: free }] });
          }}>+ Agregar turno</button>
        )}
      </fieldset>

      <fieldset>
        <legend>Tipos de novedad</legend>
        <p className="modal-help">Elegí cuáles usa el equipo y cómo se llaman en este servicio.</p>
        <ul className="care-settings-rows">
          {settings.categories.map((category, index) => (
            <li key={category.code}>
              <label className="inline-check">
                <input type="checkbox" checked={category.enabled} disabled={category.code === "incident"} onChange={(event) => change({ categories: settings.categories.map((item, i) => (i === index ? { ...item, enabled: event.target.checked } : item)) })} />
                <span className="visually-hidden">Habilitar</span>
              </label>
              <input aria-label="Nombre del tipo de novedad" value={category.label} maxLength={40} disabled={!category.enabled || category.code === "incident"} onChange={(event) => change({ categories: settings.categories.map((item, i) => (i === index ? { ...item, label: event.target.value } : item)) })} />
              {category.code === "incident" && <small className="modal-help">Siempre activo: de él dependen los avisos.</small>}
            </li>
          ))}
        </ul>
      </fieldset>

      <fieldset>
        <legend>Registros olvidados</legend>
        <label className="number-input">Se pueden cargar hasta
          <input type="number" min={0} max={31} value={settings.max_backdate_days} onChange={(event) => change({ max_backdate_days: Math.max(0, Math.min(31, Number(event.target.value) || 0)) })} />
          <span>días hacia atrás (0 = solo en el momento)</span>
        </label>
      </fieldset>

      <fieldset>
        <legend>Incidentes</legend>
        <label className="inline-check">
          <input type="checkbox" checked={settings.incident_always_important} onChange={(event) => change({ incident_always_important: event.target.checked })} />
          Siempre se marcan como importantes para el próximo turno
        </label>
        <div className="option-row">
          <span>Quién puede anular un incidente:</span>
          <label className="inline-check"><input type="radio" name={`void-${careUnitId}`} checked={settings.incident_void === "manager"} onChange={() => change({ incident_void: "manager" })} /> Solo el encargado</label>
          <label className="inline-check"><input type="radio" name={`void-${careUnitId}`} checked={settings.incident_void === "author"} onChange={() => change({ incident_void: "author" })} /> También quien lo cargó</label>
        </div>
        <div className="option-row">
          <span>Avisar en Momento a:</span>
          {(Object.keys(staffRoleLabels) as StaffRole[]).map((role) => (
            <label key={role} className="inline-check">
              <input type="checkbox" checked={settings.incident_notify_roles.includes(role)} onChange={(event) => change({ incident_notify_roles: event.target.checked ? [...settings.incident_notify_roles, role] : settings.incident_notify_roles.filter((item) => item !== role) })} />
              {staffRoleLabels[role]}
            </label>
          ))}
        </div>
        <label className="inline-check">
          <input type="checkbox" checked={settings.incident_notify_email} disabled={!settings.incident_notify_roles.length} onChange={(event) => change({ incident_notify_email: event.target.checked })} />
          Además, enviar un correo
        </label>
        <p className="modal-help">El aviso aparece en la campana de Momento (y en la futura app móvil) con el nombre de la persona; lo que pasó se lee en "Turno y registros". El correo solo dice que hubo un incidente en el servicio, sin nombre ni detalle. Si no se marca a nadie, no se avisa.</p>
      </fieldset>

      <fieldset>
        <legend>Novedades para la familia</legend>
        <p className="modal-help">Nada del registro diario llega solo a la familia: alguien del equipo escribe o revisa el texto y lo publica. La ven solo los familiares con el permiso «Novedades».</p>
        <div className="option-row">
          <span>Pueden publicar:</span>
          {(Object.keys(staffRoleLabels) as StaffRole[]).map((role) => (
            <label key={role} className="inline-check">
              <input type="checkbox" checked={settings.family_update_roles.includes(role)} onChange={(event) => change({ family_update_roles: event.target.checked ? [...settings.family_update_roles, role] : settings.family_update_roles.filter((item) => item !== role) })} />
              {staffRoleLabels[role]}
            </label>
          ))}
        </div>
        <label className="inline-check">
          <input type="checkbox" checked={settings.family_update_notify} onChange={(event) => change({ family_update_notify: event.target.checked })} />
          Avisar a la familia en Momento cuando hay una novedad
        </label>
      </fieldset>

      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {message && <p className="form-message" role="status">{message}</p>}
      <button className="primary-action" type="button" disabled={saving} onClick={() => void save()}>{saving ? "Guardando…" : "Guardar configuración"}</button>
    </details>
  );
}
