import { type FormEvent, type ReactNode, useEffect, useRef, useState } from "react";

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

type CareRecipient = {
  id: string;
  care_unit_id: string;
  display_name: string;
  is_active: boolean;
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

export type OrganizationView = "organizations" | "people" | "users";

export default function OrganizationsPanel({ view }: { view: OrganizationView }) {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [unitsByOrganization, setUnitsByOrganization] = useState<Record<string, CareUnit[]>>({});
  const [organizationName, setOrganizationName] = useState("");
  const [showOrganizationModal, setShowOrganizationModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const copy: Record<OrganizationView, { eyebrow: string; title: string; description: string }> = {
    organizations: {
      eyebrow: "Administración",
      title: "Organizaciones y servicios",
      description: "Organizá prestadores, residencias y servicios de cuidado domiciliario.",
    },
    people: {
      eyebrow: "Directorio",
      title: "Personas cuidadas",
      description: "Consultá fichas mínimas asociadas a cada residencia o servicio.",
    },
    users: {
      eyebrow: "Acceso y vínculos",
      title: "Usuarios",
      description: "Administrá cuentas de prueba y el ámbito en el que se vinculan.",
    },
  };

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
          const unitResponse = await fetch(`/api/organizations/${organization.id}/care-units`);
          if (!unitResponse.ok) throw new Error(await readApiError(unitResponse));
          return [organization.id, (await unitResponse.json()) as CareUnit[]] as const;
        }),
      );
      setUnitsByOrganization(Object.fromEntries(unitEntries));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudieron cargar los datos.");
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
      setShowOrganizationModal(false);
      setNotice("La organización se guardó.");
      await loadOrganizations();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo guardar la organización.");
    } finally {
      setSaving(false);
    }
  }

  async function createCareUnit(
    organizationId: string,
    payload: { name: string; service_type: CareUnitType; country_code: "AR" | "UY" },
  ) {
    setError("");
    setNotice("");
    const response = await fetch(`/api/organizations/${organizationId}/care-units`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(await readApiError(response));
    setNotice("El servicio se guardó.");
    const unitResponse = await fetch(`/api/organizations/${organizationId}/care-units`);
    if (!unitResponse.ok) throw new Error(await readApiError(unitResponse));
    const units = (await unitResponse.json()) as CareUnit[];
    setUnitsByOrganization((current) => ({ ...current, [organizationId]: units }));
  }

  const heading = copy[view];

  return (
    <section className="management-view" aria-labelledby="management-title">
      <header className="view-heading">
        <div>
          <p className="eyebrow">{heading.eyebrow}</p>
          <h2 id="management-title">{heading.title}</h2>
          <p>{heading.description}</p>
        </div>
        {view === "organizations" && (
          <button className="primary-action" type="button" onClick={() => setShowOrganizationModal(true)}>
            Nueva organización
          </button>
        )}
      </header>

      <div className="view-meta">
        <span className="local-only-badge">Entorno local · datos ficticios</span>
        {view === "organizations" && <span>{organizations.length} organizaciones</span>}
      </div>

      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {notice && <p className="form-message success-message" role="status">{notice}</p>}

      {loading ? (
        <p className="empty-state" role="status">Cargando…</p>
      ) : organizations.length === 0 ? (
        <div className="empty-panel">
          <span className="empty-panel-mark">00</span>
          <h3>{view === "organizations" ? "Todavía no hay organizaciones" : "No hay información para mostrar"}</h3>
          <p>{view === "organizations" ? "Creá una organización para empezar a configurar servicios y usuarios." : "Primero creá una organización y agregá un servicio."}</p>
          {view === "organizations" && (
            <button className="primary-action" type="button" onClick={() => setShowOrganizationModal(true)}>Crear organización</button>
          )}
        </div>
      ) : view === "organizations" ? (
        <div className="management-list">
          {organizations.map((organization) => (
            <article className="management-card" key={organization.id}>
              <div className="management-card-heading">
                <div>
                  <span className="card-kicker">ORGANIZACIÓN</span>
                  <h3>{organization.name}</h3>
                </div>
                <span className="item-count">{(unitsByOrganization[organization.id] ?? []).length} servicios</span>
              </div>
              <div className="service-list">
                {(unitsByOrganization[organization.id] ?? []).length === 0 ? (
                  <p className="list-empty">Todavía no tiene servicios.</p>
                ) : (
                  (unitsByOrganization[organization.id] ?? []).map((unit) => (
                    <div className="service-card" key={unit.id}>
                      <div className="service-card-heading">
                        <div>
                          <span className="service-type-label">{unit.service_type === "residence" ? "RESIDENCIA" : "CUIDADO DOMICILIARIO"}</span>
                          <h4>{unit.name}</h4>
                        </div>
                        <span className="country-label">{unit.country_code === "AR" ? "Argentina" : "Uruguay"}</span>
                      </div>
                      <WorkflowStatusEditor organizationId={organization.id} careUnitId={unit.id} />
                    </div>
                  ))
                )}
              </div>
              <CareUnitForm onSubmit={(payload) => createCareUnit(organization.id, payload)} />
            </article>
          ))}
        </div>
      ) : view === "people" ? (
        <div className="management-list">
          {organizations.map((organization) => (
            <article className="management-card" key={organization.id}>
              <div className="management-card-heading">
                <div><span className="card-kicker">ORGANIZACIÓN</span><h3>{organization.name}</h3></div>
              </div>
              {(unitsByOrganization[organization.id] ?? []).length === 0 ? (
                <p className="list-empty">Agregá un servicio para asociar fichas.</p>
              ) : (
                <div className="service-list">
                  {(unitsByOrganization[organization.id] ?? []).map((unit) => (
                    <section className="service-card" key={unit.id}>
                      <div className="service-card-heading">
                        <div><span className="service-type-label">{unit.service_type === "residence" ? "RESIDENCIA" : "CUIDADO DOMICILIARIO"}</span><h4>{unit.name}</h4></div>
                        <span className="country-label">{unit.country_code === "AR" ? "Argentina" : "Uruguay"}</span>
                      </div>
                      <CareRecipientPanel careUnitId={unit.id} />
                    </section>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      ) : (
        <div className="management-list">
          {organizations.map((organization) => (
            <article className="management-card" key={organization.id}>
              <div className="management-card-heading">
                <div><span className="card-kicker">ORGANIZACIÓN</span><h3>{organization.name}</h3></div>
              </div>
              <MembershipsPanel organizationId={organization.id} careUnits={unitsByOrganization[organization.id] ?? []} />
            </article>
          ))}
        </div>
      )}

      {showOrganizationModal && (
        <Modal title="Nueva organización" onClose={() => setShowOrganizationModal(false)}>
          <form className="modal-form" onSubmit={createOrganization}>
            <label>Nombre de la organización
              <input value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} maxLength={160} required autoFocus />
            </label>
            <div className="modal-actions">
              <button className="secondary-action" type="button" onClick={() => setShowOrganizationModal(false)}>Cancelar</button>
              <button className="primary-action" type="submit" disabled={saving}>{saving ? "Guardando…" : "Crear organización"}</button>
            </div>
          </form>
        </Modal>
      )}
    </section>
  );
}

function CareUnitForm({
  onSubmit,
}: {
  onSubmit: (payload: { name: string; service_type: CareUnitType; country_code: "AR" | "UY" }) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [serviceType, setServiceType] = useState<CareUnitType>("residence");
  const [countryCode, setCountryCode] = useState<"AR" | "UY">("AR");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      await onSubmit({ name, service_type: serviceType, country_code: countryCode });
      setName("");
      setOpen(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo guardar el servicio.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <button className="secondary-action add-service-button" type="button" onClick={() => setOpen(true)}>Agregar servicio</button>
      {open && (
        <Modal title="Agregar sede o servicio" onClose={() => setOpen(false)}>
          <form className="modal-form" onSubmit={submit}>
            <label>Nombre
              <input value={name} onChange={(event) => setName(event.target.value)} maxLength={160} placeholder="Ej.: Residencia Centro" required autoFocus />
            </label>
            <div className="modal-form-grid">
              <label>Tipo
                <select value={serviceType} onChange={(event) => setServiceType(event.target.value as CareUnitType)}>
                  <option value="residence">Residencia</option>
                  <option value="home_care">Cuidado domiciliario</option>
                </select>
              </label>
              <label>País
                <select value={countryCode} onChange={(event) => setCountryCode(event.target.value as "AR" | "UY")}>
                  <option value="AR">Argentina</option>
                  <option value="UY">Uruguay</option>
                </select>
              </label>
            </div>
            {error && <p className="form-message error-message" role="alert">{error}</p>}
            <div className="modal-actions">
              <button className="secondary-action" type="button" onClick={() => setOpen(false)}>Cancelar</button>
              <button className="primary-action" type="submit" disabled={saving}>{saving ? "Guardando…" : "Guardar servicio"}</button>
            </div>
          </form>
        </Modal>
      )}
    </>
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

function CareRecipientPanel({ careUnitId }: { careUnitId: string }) {
  const [recipients, setRecipients] = useState<CareRecipient[]>([]);
  const [displayName, setDisplayName] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [open, setOpen] = useState(false);
  const path = `/api/care-units/${careUnitId}/care-recipients`;

  async function loadRecipients() {
    setError("");
    try {
      const response = await fetch(path);
      if (!response.ok) throw new Error(await readApiError(response));
      setRecipients((await response.json()) as CareRecipient[]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudieron cargar las personas cuidadas.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadRecipients();
  }, [path]);

  async function createRecipient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ display_name: displayName }),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      setDisplayName("");
      setOpen(false);
      setNotice("La ficha de prueba se guardó.");
      await loadRecipients();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo guardar la ficha.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="directory-panel" aria-label="Personas cuidadas">
      <div className="directory-heading">
        <div>
          <h4>Personas cuidadas</h4>
          <p>Fichas mínimas sin información clínica.</p>
        </div>
        <button className="secondary-action" type="button" onClick={() => setOpen(true)}>Nueva ficha</button>
      </div>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {notice && <p className="form-message success-message" role="status">{notice}</p>}
      {loading ? (
        <p className="list-empty" role="status">Cargando fichas…</p>
      ) : recipients.length === 0 ? (
        <p className="list-empty">Todavía no hay fichas para este servicio.</p>
      ) : (
        <ul className="record-list">{recipients.map((recipient) => <li key={recipient.id}>{recipient.display_name}</li>)}</ul>
      )}
      {open && (
        <Modal title="Nueva ficha de persona cuidada" onClose={() => setOpen(false)}>
          <form className="modal-form" onSubmit={createRecipient}>
            <label>Nombre visible
              <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={160} required autoFocus />
            </label>
            <p className="modal-help">Usá datos ficticios mientras el acceso no tenga autenticación.</p>
            <div className="modal-actions">
              <button className="secondary-action" type="button" onClick={() => setOpen(false)}>Cancelar</button>
              <button className="primary-action" type="submit" disabled={saving}>{saving ? "Guardando…" : "Guardar ficha"}</button>
            </div>
            {error && <p className="form-message error-message" role="alert">{error}</p>}
          </form>
        </Modal>
      )}
    </section>
  );
}

type Membership = {
  id: string;
  user_account_id: string;
  care_unit_id: string | null;
  user_group: "staff" | "family" | "older_adult";
  role_label: string | null;
  user: {
    display_name: string;
    email: string | null;
    phone: string | null;
  };
};

function MembershipsPanel({
  organizationId,
  careUnits,
}: {
  organizationId: string;
  careUnits: CareUnit[];
}) {
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [group, setGroup] = useState<Membership["user_group"]>("staff");
  const [roleLabel, setRoleLabel] = useState("");
  const [careUnitId, setCareUnitId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [open, setOpen] = useState(false);
  const path = `/api/organizations/${organizationId}/memberships`;

  async function loadMemberships() {
    setError("");
    try {
      const response = await fetch(path);
      if (!response.ok) throw new Error(await readApiError(response));
      setMemberships((await response.json()) as Membership[]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudieron cargar los usuarios.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadMemberships();
  }, [path]);

  async function createMembership(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          display_name: name,
          email,
          phone,
          user_group: group,
          care_unit_id: careUnitId || null,
          role_label: roleLabel || null,
        }),
      });
      if (!response.ok) throw new Error(await readApiError(response));
      setName("");
      setEmail("");
      setPhone("");
      setRoleLabel("");
      setOpen(false);
      setNotice("La cuenta de prueba se vinculó a la organización.");
      await loadMemberships();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo guardar la cuenta.");
    } finally {
      setSaving(false);
    }
  }

  const groupLabel = (value: Membership["user_group"]) =>
    value === "staff" ? "Personal" : value === "family" ? "Familia / persona de confianza" : "Persona mayor";

  return (
    <section className="directory-panel" aria-label="Usuarios de la organización">
      <div className="directory-heading">
        <div>
          <h4>Usuarios y vínculos</h4>
          <p>Las funciones registradas no conceden permisos.</p>
        </div>
        <button className="secondary-action" type="button" onClick={() => setOpen(true)}>Agregar usuario</button>
      </div>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {notice && <p className="form-message success-message" role="status">{notice}</p>}
      {loading ? (
        <p className="list-empty" role="status">Cargando usuarios…</p>
      ) : memberships.length === 0 ? (
        <p className="list-empty">Todavía no hay cuentas vinculadas a esta organización.</p>
      ) : (
        <ul className="record-list">
          {memberships.map((membership) => {
            const unit = careUnits.find((item) => item.id === membership.care_unit_id);
            return (
              <li key={membership.id}>
                <div><strong>{membership.user.display_name}</strong><span>{groupLabel(membership.user_group)}</span></div>
                <div className="record-meta">
                  {membership.role_label && <span>{membership.role_label}</span>}
                  <span>{unit?.name ?? "Toda la organización"}</span>
                  {membership.user.email && <span>{membership.user.email}</span>}
                </div>
              </li>
            );
          })}
        </ul>
      )}
      {open && (
        <Modal title="Agregar usuario" onClose={() => setOpen(false)}>
          <form className="modal-form" onSubmit={createMembership}>
            <label>Nombre visible
              <input value={name} onChange={(event) => setName(event.target.value)} maxLength={160} required autoFocus />
            </label>
            <div className="modal-form-grid">
              <label>Grupo
                <select value={group} onChange={(event) => setGroup(event.target.value as Membership["user_group"])}>
                  <option value="staff">Personal</option>
                  <option value="family">Familia / persona de confianza</option>
                  <option value="older_adult">Persona mayor</option>
                </select>
              </label>
              <label>Servicio
                <select value={careUnitId} onChange={(event) => setCareUnitId(event.target.value)}>
                  <option value="">Toda la organización</option>
                  {careUnits.map((unit) => <option value={unit.id} key={unit.id}>{unit.name}</option>)}
                </select>
              </label>
            </div>
            {group === "staff" && (
              <label>Función descriptiva
                <input value={roleLabel} onChange={(event) => setRoleLabel(event.target.value)} maxLength={80} placeholder="Ej.: Encargado" />
              </label>
            )}
            <div className="modal-form-grid">
              <label>Correo electrónico (opcional)
                <input type="email" autoComplete="off" value={email} onChange={(event) => setEmail(event.target.value)} maxLength={254} />
              </label>
              <label>Teléfono (opcional)
                <input type="tel" autoComplete="off" value={phone} onChange={(event) => setPhone(event.target.value)} maxLength={32} />
              </label>
            </div>
            <p className="modal-help">Registro local de prueba. No crea credenciales ni habilita el inicio de sesión.</p>
            {error && <p className="form-message error-message" role="alert">{error}</p>}
            <div className="modal-actions">
              <button className="secondary-action" type="button" onClick={() => setOpen(false)}>Cancelar</button>
              <button className="primary-action" type="submit" disabled={saving}>{saving ? "Guardando…" : "Guardar usuario"}</button>
            </div>
          </form>
        </Modal>
      )}
    </section>
  );
}

function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal();
    return () => {
      if (dialog?.open) dialog.close();
    };
  }, []);

  return (
    <dialog
      ref={dialogRef}
      className="moment-modal"
      aria-labelledby="modal-title"
      onCancel={(event) => { event.preventDefault(); onClose(); }}
      onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}
    >
      <div className="modal-heading">
        <h2 id="modal-title">{title}</h2>
        <button className="modal-close" type="button" aria-label="Cerrar" onClick={onClose}>×</button>
      </div>
      {children}
    </dialog>
  );
}
