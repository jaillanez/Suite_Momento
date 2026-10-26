import { FormEvent, useEffect, useState } from "react";

type CareUnitType = "residence" | "home_care";

type Organization = {
  id: string;
  name: string;
};

type CareUnit = {
  id: string;
  organization_id: string;
  name: string;
  service_type: CareUnitType;
  country_code: "AR" | "UY";
};

type WorkflowStatus = {
  id: string;
  care_unit_id: string;
  code: string;
  label: string;
  display_order: number;
  is_active: boolean;
  family_visible: boolean;
};

async function readApiError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (body.detail) return body.detail;
  } catch {
    // Si la respuesta no tiene JSON, se muestra el mensaje genérico.
  }
  return "No se pudo completar la operación. Comprueba que la API esté disponible.";
}

export default function OrganizationsPanel() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [unitsByOrganization, setUnitsByOrganization] = useState<
    Record<string, CareUnit[]>
  >({});
  const [organizationName, setOrganizationName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function loadOrganizations() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/organizations");
      if (!response.ok) throw new Error(await readApiError(response));
      const items = (await response.json()) as Organization[];
      setOrganizations(items);

      const unitEntries = await Promise.all(
        items.map(async (organization) => {
          const unitResponse = await fetch(
            `/api/organizations/${organization.id}/care-units`,
          );
          if (!unitResponse.ok) throw new Error(await readApiError(unitResponse));
          return [
            organization.id,
            (await unitResponse.json()) as CareUnit[],
          ] as const;
        }),
      );
      setUnitsByOrganization(Object.fromEntries(unitEntries));
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "No se pudieron cargar las organizaciones.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadOrganizations();
  }, []);

  async function createOrganization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch("/api/organizations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: organizationName }),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      setOrganizationName("");
      setNotice("La organización se guardó.");
      await loadOrganizations();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "No se pudo guardar la organización.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function createCareUnit(
    organizationId: string,
    payload: {
      name: string;
      service_type: CareUnitType;
      country_code: "AR" | "UY";
    },
  ) {
    setError("");
    setNotice("");
    const response = await fetch(
      `/api/organizations/${organizationId}/care-units`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    if (!response.ok) throw new Error(await readApiError(response));
    setNotice("El servicio se guardó.");
    const unitResponse = await fetch(
      `/api/organizations/${organizationId}/care-units`,
    );
    if (!unitResponse.ok) throw new Error(await readApiError(unitResponse));
    const units = (await unitResponse.json()) as CareUnit[];
    setUnitsByOrganization((current) => ({
      ...current,
      [organizationId]: units,
    }));
  }

  return (
    <section className="organization-section" aria-labelledby="organization-title">
      <div className="organization-heading">
        <div>
          <p className="eyebrow">Fase 2 · estructura</p>
          <h2 id="organization-title">Organizaciones y servicios</h2>
          <p>
            Registra la organización prestadora y las residencias o servicios
            domiciliarios que dependen de ella.
          </p>
        </div>
        <span className="local-only-badge">Prueba local · datos ficticios</span>
      </div>

      <form className="organization-create-form" onSubmit={createOrganization}>
        <label htmlFor="organization-name">Nombre de la organización</label>
        <div className="organization-form-row">
          <input
            id="organization-name"
            value={organizationName}
            onChange={(event) => setOrganizationName(event.target.value)}
            maxLength={160}
            placeholder="Ej.: Organización de cuidado"
            required
          />
          <button type="submit" disabled={saving}>
            {saving ? "Guardando..." : "Agregar organización"}
          </button>
        </div>
      </form>

      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {notice && <p className="form-message success-message" role="status">{notice}</p>}

      {loading ? (
        <p className="empty-state" role="status">Cargando organizaciones…</p>
      ) : organizations.length === 0 ? (
        <p className="empty-state">
          Todavía no hay organizaciones. Puedes crear una con datos de prueba.
        </p>
      ) : (
        <div className="organization-list">
          {organizations.map((organization) => (
            <article className="organization-card" key={organization.id}>
              <h3>{organization.name}</h3>
              <div className="unit-list">
                {(unitsByOrganization[organization.id] ?? []).length === 0 ? (
                  <p className="unit-empty">Aún no tiene sedes o servicios.</p>
                ) : (
                  (unitsByOrganization[organization.id] ?? []).map((unit) => (
                    <div className="unit-item" key={unit.id}>
                      <div className="unit-row">
                        <span className="unit-type-mark" aria-hidden="true" />
                        <span className="unit-name">{unit.name}</span>
                        <span className="unit-description">
                          {unit.service_type === "residence"
                            ? "Residencia"
                            : "Cuidado domiciliario"}{" "}
                          · {unit.country_code === "AR" ? "Argentina" : "Uruguay"}
                        </span>
                      </div>
                      <WorkflowStatusEditor
                        organizationId={organization.id}
                        careUnitId={unit.id}
                      />
                    </div>
                  ))
                )}
              </div>
              <CareUnitForm
                onSubmit={(payload) => createCareUnit(organization.id, payload)}
              />
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function CareUnitForm({
  onSubmit,
}: {
  onSubmit: (payload: {
    name: string;
    service_type: CareUnitType;
    country_code: "AR" | "UY";
  }) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [serviceType, setServiceType] = useState<CareUnitType>("residence");
  const [countryCode, setCountryCode] = useState<"AR" | "UY">("AR");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSubmit({
        name,
        service_type: serviceType,
        country_code: countryCode,
      });
      setName("");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "No se pudo guardar el servicio.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="unit-create-form" onSubmit={submit}>
      <p className="unit-form-title">Agregar sede o servicio</p>
      <div className="unit-form-grid">
        <label>
          Nombre
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={160}
            placeholder="Ej.: Residencia Centro"
            required
          />
        </label>
        <label>
          Tipo
          <select
            value={serviceType}
            onChange={(event) =>
              setServiceType(event.target.value as CareUnitType)
            }
          >
            <option value="residence">Residencia</option>
            <option value="home_care">Cuidado domiciliario</option>
          </select>
        </label>
        <label>
          País
          <select
            value={countryCode}
            onChange={(event) =>
              setCountryCode(event.target.value as "AR" | "UY")
            }
          >
            <option value="AR">Argentina</option>
            <option value="UY">Uruguay</option>
          </select>
        </label>
        <button type="submit" disabled={saving}>
          {saving ? "Guardando..." : "Agregar"}
        </button>
      </div>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
    </form>
  );
}


function WorkflowStatusEditor({
  organizationId,
  careUnitId,
}: {
  organizationId: string;
  careUnitId: string;
}) {
  const [statuses, setStatuses] = useState<WorkflowStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const path =
    `/api/organizations/${organizationId}/care-units/${careUnitId}/workflow-statuses`;

  useEffect(() => {
    let active = true;
    setLoading(true);
    void fetch(path)
      .then(async (response) => {
        if (!response.ok) throw new Error(await readApiError(response));
        return (await response.json()) as WorkflowStatus[];
      })
      .then((items) => {
        if (active) setStatuses(items);
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(
            caught instanceof Error
              ? caught.message
              : "No se pudo cargar la configuración.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [path]);

  function updateStatus(
    code: string,
    field: "label" | "is_active" | "family_visible",
    value: string | boolean,
  ) {
    setStatuses((current) =>
      current.map((status) =>
        status.code === code ? { ...status, [field]: value } : status,
      ),
    );
  }

  function moveStatus(index: number, offset: -1 | 1) {
    setStatuses((current) => {
      const sorted = [...current].sort(
        (first, second) => first.display_order - second.display_order,
      );
      const nextIndex = index + offset;
      if (nextIndex < 0 || nextIndex >= sorted.length) return current;
      [sorted[index], sorted[nextIndex]] = [sorted[nextIndex], sorted[index]];
      return sorted.map((status, position) => ({
        ...status,
        display_order: position + 1,
      }));
    });
  }

  async function save() {
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(path, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          statuses: statuses.map(
            ({ code, label, display_order, is_active, family_visible }) => ({
              code,
              label,
              display_order,
              is_active,
              family_visible,
            }),
          ),
        }),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      setStatuses((await response.json()) as WorkflowStatus[]);
      setNotice("Configuración guardada.");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "No se pudo guardar la configuración.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="workflow-editor" aria-label="Estados de seguimiento familiar">
      <div className="workflow-editor-heading">
        <div>
          <h4>Seguimiento de solicitudes</h4>
          <p>Configura las etiquetas y lo que verá la familia.</p>
        </div>
        <button
          className="workflow-save-button"
          type="button"
          onClick={() => void save()}
          disabled={loading || saving || statuses.length === 0}
        >
          {saving ? "Guardando..." : "Guardar estados"}
        </button>
      </div>
      {loading ? (
        <p className="workflow-message">Cargando estados…</p>
      ) : (
        <div className="workflow-status-list">
          {[...statuses]
            .sort((first, second) => first.display_order - second.display_order)
            .map((status, index) => (
              <div className="workflow-status-row" key={status.code}>
                <div className="workflow-order-controls" aria-label="Orden">
                  <button
                    type="button"
                    aria-label={`Subir ${status.label}`}
                    disabled={index === 0}
                    onClick={() => moveStatus(index, -1)}
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    aria-label={`Bajar ${status.label}`}
                    disabled={index === statuses.length - 1}
                    onClick={() => moveStatus(index, 1)}
                  >
                    ↓
                  </button>
                </div>
                <label className="workflow-label-field">
                  Nombre del estado
                  <input
                    value={status.label}
                    maxLength={80}
                    onChange={(event) =>
                      updateStatus(status.code, "label", event.target.value)
                    }
                  />
                </label>
                <label className="workflow-check">
                  <input
                    type="checkbox"
                    checked={status.family_visible}
                    onChange={(event) =>
                      updateStatus(
                        status.code,
                        "family_visible",
                        event.target.checked,
                      )
                    }
                  />
                  Visible a familia
                </label>
                <label className="workflow-check">
                  <input
                    type="checkbox"
                    checked={status.is_active}
                    onChange={(event) =>
                      updateStatus(
                        status.code,
                        "is_active",
                        event.target.checked,
                      )
                    }
                  />
                  Activo
                </label>
              </div>
            ))}
        </div>
      )}
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {notice && <p className="form-message success-message" role="status">{notice}</p>}
      <p className="workflow-message">
        Desactivar un estado lo conserva en el historial; no borra registros.
      </p>
    </section>
  );
}
