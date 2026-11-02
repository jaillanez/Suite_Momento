import { useEffect, useState } from "react";
import { readApiError } from "./OrganizationsPanel";

type Option = { value: string; label: string; points: number };
type Group = { key: string; label: string; options: string[]; recalled_by: string[] };
type Item = {
  key: string;
  label: string;
  type: "choice" | "checks" | "serial7" | "fluency" | "recognition";
  instruction?: string;
  options?: Option[];
  items?: string[];
  scoring?: string;
  max?: number;
  groups?: Group[];
  recall_key?: string;
};
type Scale = { code: string; name: string; description: string; max: number; sections: { title: string; items: Item[] }[] };
type Answers = Record<string, unknown>;
type Score = { total: number; max: number; subscores: Record<string, { score: number; max: number }> | null; interpretation: string | null; missing: string[]; credited_by_recall: string[] };
export type AssessmentSummary = {
  id: string;
  scale_code: string;
  scale_name: string;
  performed_on: string;
  total_score: number;
  max_score: number;
  subscores: Record<string, { score: number; max: number }> | null;
  interpretation: string | null;
  performed_by_name: string;
};
type AssessmentDetail = AssessmentSummary & { answers: Answers; notes: string | null };

let cachedScales: Promise<Scale[]> | null = null;
function loadScales(): Promise<Scale[]> {
  cachedScales ??= fetch("/api/scales").then(async (response) => {
    if (!response.ok) throw new Error(await readApiError(response));
    return (await response.json()) as Scale[];
  });
  return cachedScales;
}

const formatDate = (value: string) => new Date(`${value}T12:00:00`).toLocaleDateString("es-AR");
const today = () => new Date().toLocaleDateString("en-CA");

export function ScoreSummary({ subscores }: { subscores: AssessmentSummary["subscores"] }) {
  if (!subscores) return null;
  return (
    <div className="subscores">
      {Object.entries(subscores).map(([name, value]) => (
        <span key={name}><small>{name}</small><strong>{value.score}/{value.max}</strong></span>
      ))}
    </div>
  );
}

export default function ScalesSection({ path, canApply, canDelete }: { path: string; canApply: boolean; canDelete: boolean }) {
  const [scales, setScales] = useState<Scale[]>([]);
  const [items, setItems] = useState<AssessmentSummary[]>([]);
  const [mode, setMode] = useState<{ kind: "list" } | { kind: "new"; scale: Scale } | { kind: "view"; detail: AssessmentDetail; scale: Scale }>({ kind: "list" });
  const [error, setError] = useState("");

  async function reload() {
    const response = await fetch(path);
    if (!response.ok) throw new Error(await readApiError(response));
    setItems((await response.json()) as AssessmentSummary[]);
  }

  useEffect(() => {
    Promise.all([loadScales().then(setScales), reload()]).catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "No se pudieron cargar las escalas."));
  }, [path]);

  async function open(item: AssessmentSummary) {
    setError("");
    const response = await fetch(`${path}/${item.id}`);
    if (!response.ok) { setError(await readApiError(response)); return; }
    const detail = (await response.json()) as AssessmentDetail;
    const scale = scales.find((candidate) => candidate.code === detail.scale_code);
    if (scale) setMode({ kind: "view", detail, scale });
  }

  async function remove(item: AssessmentSummary) {
    if (!window.confirm(`¿Borrar la evaluación ${item.scale_name} del ${formatDate(item.performed_on)}? Usalo solo si se cargó por error.`)) return;
    const response = await fetch(`${path}/${item.id}`, { method: "DELETE" });
    if (!response.ok) { setError(await readApiError(response)); return; }
    await reload();
  }

  if (mode.kind === "new") {
    return <ScaleForm scale={mode.scale} path={path} onCancel={() => setMode({ kind: "list" })} onSaved={async () => { setMode({ kind: "list" }); await reload(); }} />;
  }
  if (mode.kind === "view") {
    return <ScaleForm scale={mode.scale} path={path} readOnly initial={mode.detail} onCancel={() => setMode({ kind: "list" })} onSaved={async () => undefined} />;
  }

  return (
    <article className="profile-section print-keep">
      <div className="profile-section-heading">
        <h4>Escalas</h4>
        {canApply && (
          <div className="scale-launchers no-print">
            {scales.map((scale) => (
              <button key={scale.code} className="secondary-action" type="button" onClick={() => setMode({ kind: "new", scale })}>
                {scale.code === "ace3" ? "ACE-III" : scale.code === "gds15" ? "Yesavage" : scale.code === "cqc" ? "CQC" : "Barthel"}
              </button>
            ))}
          </div>
        )}
      </div>
      <p className="modal-help">El sistema suma los puntos según la planilla del equipo. La interpretación clínica es del profesional.</p>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {items.length === 0 ? <p className="list-empty">Todavía no hay evaluaciones.</p> : (
        <ul className="record-list compact assessment-list">
          {items.map((item) => (
            <li key={item.id}>
              <div>
                <strong>{item.scale_name}</strong>
                <span>{formatDate(item.performed_on)} · {item.performed_by_name}</span>
                <ScoreSummary subscores={item.subscores} />
              </div>
              <div className="record-controls">
                <span className="score-badge">{item.total_score}/{item.max_score}</span>
                {item.interpretation && <span className="status-pill status-blue">{item.interpretation}</span>}
                <button className="link-action no-print" type="button" onClick={() => void open(item)}>Ver</button>
                {canDelete && <button className="link-action danger no-print" type="button" onClick={() => void remove(item)}>Borrar</button>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

function ScaleForm({ scale, path, readOnly = false, initial, onCancel, onSaved }: { scale: Scale; path: string; readOnly?: boolean; initial?: AssessmentDetail; onCancel: () => void; onSaved: () => Promise<void> }) {
  const [answers, setAnswers] = useState<Answers>(initial?.answers ?? {});
  const [performedOn, setPerformedOn] = useState(initial?.performed_on ?? today());
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [result, setResult] = useState<Score | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const set = (key: string, value: unknown) => setAnswers((current) => ({ ...current, [key]: value }));

  // El puntaje lo calcula siempre el servidor, para que pantalla y registro coincidan.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetch(`/api/scales/${scale.code}/score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers }),
      }).then(async (response) => {
        if (response.ok) { setResult((await response.json()) as Score); setError(""); }
        else setError(await readApiError(response));
      });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [answers, scale.code]);

  async function save() {
    setSaving(true);
    setError("");
    try {
      const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scale_code: scale.code, performed_on: performedOn, answers, notes: notes || null }),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      await onSaved();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo guardar.");
    } finally {
      setSaving(false);
    }
  }

  const credited = new Set(result?.credited_by_recall ?? []);

  return (
    <article className="profile-section scale-form">
      <div className="profile-section-heading">
        <div>
          <h4>{scale.name}</h4>
          <p className="modal-help">{scale.description}</p>
        </div>
        <button className="link-action no-print" type="button" onClick={onCancel}>← Volver a escalas</button>
      </div>
      <div className="scale-meta">
        <label>Fecha<input type="date" value={performedOn} max={today()} disabled={readOnly} onChange={(event) => setPerformedOn(event.target.value)} /></label>
        {initial && <span>Evaluó: <strong>{initial.performed_by_name}</strong></span>}
      </div>
      {scale.sections.map((section) => (
        <section key={section.title} className="scale-section">
          {scale.sections.length > 1 && <h5>{section.title}</h5>}
          {section.items.map((item) => (
            <div key={item.key} className="scale-item">
              <p className="scale-item-label">{item.label}</p>
              {item.instruction && <p className="modal-help">{item.instruction}</p>}
              <ItemInput item={item} value={answers[item.key]} readOnly={readOnly} credited={credited} onChange={(value) => set(item.key, value)} />
            </div>
          ))}
        </section>
      ))}
      <label className="scale-notes">Observaciones del evaluador
        <textarea rows={3} value={notes} disabled={readOnly} onChange={(event) => setNotes(event.target.value)} maxLength={4000} />
      </label>
      <div className="scale-total" role="status">
        <ScoreSummary subscores={result?.subscores ?? null} />
        <div>
          <strong>Total: {result?.total ?? 0}/{scale.max}</strong>
          {result?.interpretation && <span className="status-pill status-blue">{result.interpretation}</span>}
          {!readOnly && result && result.missing.length > 0 && <small>Faltan {result.missing.length} respuestas</small>}
        </div>
      </div>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {!readOnly && (
        <div className="modal-actions">
          <button className="secondary-action" type="button" onClick={onCancel}>Cancelar</button>
          <button className="primary-action" type="button" disabled={saving || (result?.missing.length ?? 1) > 0} onClick={() => void save()}>{saving ? "Guardando…" : "Guardar evaluación"}</button>
        </div>
      )}
    </article>
  );
}

function ItemInput({ item, value, readOnly, credited, onChange }: { item: Item; value: unknown; readOnly: boolean; credited: Set<string>; onChange: (value: unknown) => void }) {
  if (item.type === "choice") {
    return (
      <div className="option-row">
        {item.options?.map((option) => (
          <label key={option.value} className="inline-check">
            <input type="radio" name={item.key} disabled={readOnly} checked={value === option.value} onChange={() => onChange(option.value)} />
            {option.label} <small className="points">({option.points})</small>
          </label>
        ))}
      </div>
    );
  }
  if (item.type === "checks") {
    const selected = (value as string[] | undefined) ?? [];
    return (
      <div className="option-row">
        {item.items?.map((label) => (
          <label key={label} className="inline-check">
            <input type="checkbox" disabled={readOnly} checked={selected.includes(label)} onChange={(event) => onChange(event.target.checked ? [...selected, label] : selected.filter((entry) => entry !== label))} />
            {label}
          </label>
        ))}
        {item.scoring === "none" && <small className="points">No suma puntos</small>}
      </div>
    );
  }
  if (item.type === "serial7") {
    const values = (value as (number | null)[] | undefined) ?? [null, null, null, null, null];
    return (
      <div className="option-row">
        {[0, 1, 2, 3, 4].map((index) => (
          <label key={index} className="serial-input">{index + 1}ª
            <input type="number" min={0} max={100} disabled={readOnly} value={values[index] ?? ""} onChange={(event) => {
              const next = [...values];
              next[index] = event.target.value === "" ? null : Number(event.target.value);
              onChange(next);
            }} />
          </label>
        ))}
      </div>
    );
  }
  if (item.type === "fluency") {
    const data = (value as { raw?: number | null; score?: number | null } | undefined) ?? {};
    return (
      <div className="option-row">
        <label className="serial-input">Palabras válidas
          <input type="number" min={0} max={200} disabled={readOnly} value={data.raw ?? ""} onChange={(event) => onChange({ ...data, raw: event.target.value === "" ? null : Number(event.target.value) })} />
        </label>
        <label className="serial-input">Puntaje convertido (0–7)
          <select disabled={readOnly} value={data.score ?? ""} onChange={(event) => onChange({ ...data, score: event.target.value === "" ? null : Number(event.target.value) })}>
            <option value="">—</option>
            {[0, 1, 2, 3, 4, 5, 6, 7].map((points) => <option key={points} value={points}>{points}</option>)}
          </select>
        </label>
      </div>
    );
  }
  const data = (value as Record<string, string> | undefined) ?? {};
  return (
    <div className="recognition-groups">
      {item.groups?.map((group) => (
        <div key={group.key} className="recognition-group">
          <strong>{group.label}</strong>
          {credited.has(group.key) ? (
            <span className="status-pill status-green">Acreditado por el recuerdo</span>
          ) : group.options.map((option) => (
            <label key={option} className="inline-check">
              <input type="radio" name={`${item.key}-${group.key}`} disabled={readOnly} checked={data[group.key] === option} onChange={() => onChange({ ...data, [group.key]: option })} />
              {option}
            </label>
          ))}
        </div>
      ))}
    </div>
  );
}
