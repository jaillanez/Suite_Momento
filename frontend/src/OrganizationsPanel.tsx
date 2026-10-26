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
                    <div className="unit-row" key={unit.id}>
                      <span className="unit-type-mark" aria-hidden="true" />
                      <span className="unit-name">{unit.name}</span>
                      <span className="unit-description">
                        {unit.service_type === "residence"
                          ? "Residencia"
                          : "Cuidado domiciliario"}{" "}
                        · {unit.country_code === "AR" ? "Argentina" : "Uruguay"}
                      </span>
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
