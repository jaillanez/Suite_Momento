import { type FormEvent, useEffect, useState } from "react";
import { readApiError } from "./OrganizationsPanel";

type Option = { value: string; label: string };
type Extra = { for: string[]; label: string; min?: number; max?: number };
type FormField = {
  key: string;
  label: string;
  type: "choice" | "multi" | "number" | "text";
  options?: Option[];
  detail?: Extra;
  number?: Extra;
  min?: number;
  max?: number;
  unit?: string;
  step?: number;
};
type FormSection = { id: string; title: string; fields: FormField[] };
type Answers = Record<string, unknown>;

let cachedForm: Promise<FormSection[]> | null = null;
function loadForm(): Promise<FormSection[]> {
  cachedForm ??= fetch("/api/forms/background").then(async (response) => {
    if (!response.ok) throw new Error(await readApiError(response));
    return (await response.json()) as FormSection[];
  });
  return cachedForm;
}

function enabled(extra: Extra | undefined, value: unknown): boolean {
  if (!extra || value === undefined || value === null || (Array.isArray(value) && value.length === 0)) return false;
  return extra.for.includes("*") || extra.for.includes(String(value));
}

function describe(field: FormField, answers: Answers): string {
  const value = answers[field.key];
  if (value === undefined || value === null || value === "") return "—";
  let text: string;
  if (field.type === "choice") text = field.options?.find((option) => option.value === value)?.label ?? String(value);
  else if (field.type === "multi") text = (value as string[]).map((item) => field.options?.find((option) => option.value === item)?.label ?? item).join(", ");
  else if (field.type === "number") text = `${String(value).replace(".", ",")}${field.unit ? ` ${field.unit}` : ""}`;
  else text = String(value);
  const number = answers[`${field.key}__number`];
  const detail = answers[`${field.key}__detail`];
  if (number !== undefined) text += ` · ${field.number?.label}: ${String(number)}`;
  if (detail) text += ` · ${String(detail)}`;
  return text;
}

export default function BackgroundSection({ path, background, canEdit, onSaved }: { path: string; background: Answers | null; canEdit: boolean; onSaved: (profile: unknown) => void }) {
  const [form, setForm] = useState<FormSection[]>([]);
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState("");
  const answers = background ?? {};

  useEffect(() => {
    loadForm().then(setForm).catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "No se pudo cargar el formulario."));
  }, []);

  async function save(values: Answers) {
    const response = await fetch(path, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answers: values }),
    });
    if (!response.ok) throw new Error(await readApiError(response));
    onSaved(await response.json());
    setEditing(null);
  }

  return (
    <>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {form.map((section) => (
        <article className="profile-section" key={section.id}>
          <div className="profile-section-heading">
            <h4>{section.title}</h4>
            {canEdit && editing !== section.id && <button className="link-action" type="button" onClick={() => setEditing(section.id)}>Editar</button>}
          </div>
          {section.id === "personal" && <p className="modal-help">Antecedentes registrados por el encargado o el médico. Momento no interpreta estos datos.</p>}
          {editing === section.id ? (
            <SectionEditor section={section} answers={answers} onCancel={() => setEditing(null)} onSave={save} />
          ) : (
            <dl className="profile-fields">
              {section.fields.map((field) => (
                <div key={field.key} className={field.type === "text" || field.type === "multi" ? "wide" : undefined}>
                  <dt>{field.label}</dt>
                  <dd>{describe(field, answers)}</dd>
                </div>
              ))}
              {section.id === "admission" && (
                <div><dt>IMC (calculado)</dt><dd>{answers.bmi !== undefined ? String(answers.bmi).replace(".", ",") : "—"}</dd></div>
              )}
            </dl>
          )}
        </article>
      ))}
    </>
  );
}

function SectionEditor({ section, answers, onCancel, onSave }: { section: FormSection; answers: Answers; onCancel: () => void; onSave: (values: Answers) => Promise<void> }) {
  const [values, setValues] = useState<Answers>(() => ({ ...answers }));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const set = (key: string, value: unknown) => setValues((current) => ({ ...current, [key]: value }));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSave(values);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo guardar.");
    } finally {
      setSaving(false);
    }
  }

  const weight = Number(values.weight);
  const height = Number(values.height);
  const bmi = section.id === "admission" && weight > 0 && height > 0 ? (weight / (height * height)).toFixed(1).replace(".", ",") : null;

  return (
    <form className="profile-form" onSubmit={submit}>
      <div className="background-fields">
        {section.fields.map((field) => {
          const value = values[field.key];
          return (
            <fieldset key={field.key} className="background-field">
              <legend>{field.label}</legend>
              {field.type === "choice" && (
                <div className="option-row">
                  {field.options?.map((option) => (
                    <label key={option.value} className="inline-check">
                      <input type="radio" name={field.key} checked={value === option.value} onChange={() => set(field.key, option.value)} />
                      {option.label}
                    </label>
                  ))}
                  {value !== undefined && <button className="link-action" type="button" onClick={() => set(field.key, null)}>Borrar</button>}
                </div>
              )}
              {field.type === "multi" && (
                <div className="option-row">
                  {field.options?.map((option) => {
                    const list = (value as string[] | undefined) ?? [];
                    return (
                      <label key={option.value} className="inline-check">
                        <input type="checkbox" checked={list.includes(option.value)} onChange={(event) => set(field.key, event.target.checked ? [...list, option.value] : list.filter((item) => item !== option.value))} />
                        {option.label}
                      </label>
                    );
                  })}
                </div>
              )}
              {field.type === "number" && (
                <label className="number-input">
                  <input type="number" min={field.min} max={field.max} step={field.step ?? 1} value={value === undefined || value === null ? "" : String(value)} onChange={(event) => set(field.key, event.target.value === "" ? null : Number(event.target.value))} />
                  <span>{field.unit}</span>
                </label>
              )}
              {field.type === "text" && <textarea rows={3} value={(value as string | undefined) ?? ""} onChange={(event) => set(field.key, event.target.value)} />}
              {enabled(field.number, value) && (
                <label className="sub-input">{field.number?.label}
                  <input type="number" min={field.number?.min} max={field.number?.max} value={values[`${field.key}__number`] === undefined || values[`${field.key}__number`] === null ? "" : String(values[`${field.key}__number`])} onChange={(event) => set(`${field.key}__number`, event.target.value === "" ? null : Number(event.target.value))} />
                </label>
              )}
              {enabled(field.detail, value) && (
                <label className="sub-input">{field.detail?.label}
                  <input value={(values[`${field.key}__detail`] as string | undefined) ?? ""} onChange={(event) => set(`${field.key}__detail`, event.target.value)} />
                </label>
              )}
            </fieldset>
          );
        })}
        {bmi && <p className="bmi-preview">IMC calculado: <strong>{bmi}</strong></p>}
      </div>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      <div className="modal-actions">
        <button className="secondary-action" type="button" onClick={onCancel}>Cancelar</button>
        <button className="primary-action" type="submit" disabled={saving}>{saving ? "Guardando…" : "Guardar"}</button>
      </div>
    </form>
  );
}
