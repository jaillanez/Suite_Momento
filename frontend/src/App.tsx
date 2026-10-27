import { type FormEvent, useEffect, useState } from "react";
import OrganizationsPanel, { type OrganizationView } from "./OrganizationsPanel";

type Page = OrganizationView | "landing" | "login" | "dashboard" | "inbox" | "settings";
type ApiState = "checking" | "available" | "unavailable";

type Organization = { id: string; name: string };
type CareUnit = { id: string; name: string };
type Membership = { user_group: "staff" | "family" | "older_adult"; role_label: string | null };

type DashboardMetrics = {
  services: number;
  residents: number;
  caregivers: number;
  physicians: number;
  families: number;
  olderAdults: number;
};

const pageTitles: Record<Exclude<Page, "landing" | "login">, string> = {
  dashboard: "Panel de gestión",
  organizations: "Organizaciones y servicios",
  people: "Personas cuidadas",
  users: "Usuarios y vínculos",
  inbox: "Bandeja de solicitudes",
  settings: "Configuración",
};

export default function App() {
  const [page, setPage] = useState<Page>("landing");
  const [apiState, setApiState] = useState<ApiState>("checking");

  useEffect(() => {
    let active = true;
    void fetch("/api/health")
      .then((response) => { if (active) setApiState(response.ok ? "available" : "unavailable"); })
      .catch(() => { if (active) setApiState("unavailable"); });
    return () => { active = false; };
  }, []);

  if (page === "landing") return <PublicLanding onLogin={() => setPage("login")} />;
  if (page === "login") {
    return <LoginScreen onBack={() => setPage("landing")} onDemoAccess={() => setPage("dashboard")} />;
  }

  return (
    <div className="app-layout">
      <aside className="app-sidebar">
        <div className="app-brand">
          <img src="/brand/iso-momento.png" alt="" />
          <span>Momento</span>
        </div>
        <p className="sidebar-caption">GESTIÓN DEL CUIDADO</p>
        <nav className="main-navigation" aria-label="Navegación principal">
          <NavButton label="Dashboard" active={page === "dashboard"} onClick={() => setPage("dashboard")} mark="IN" />
          <NavButton label="Organizaciones" active={page === "organizations"} onClick={() => setPage("organizations")} mark="OR" />
          <NavButton label="Personas cuidadas" active={page === "people"} onClick={() => setPage("people")} mark="PC" />
          <NavButton label="Usuarios y vínculos" active={page === "users"} onClick={() => setPage("users")} mark="UV" />
          <NavButton label="Bandeja de solicitudes" active={page === "inbox"} onClick={() => setPage("inbox")} mark="BD" />
          <NavButton label="Configuración" active={page === "settings"} onClick={() => setPage("settings")} mark="CO" />
        </nav>
        <div className="sidebar-footer">
          <span className={"api-dot " + apiState} />
          <span>{apiState === "available" ? "API conectada" : apiState === "checking" ? "Comprobando API" : "API desconectada"}</span>
        </div>
      </aside>

      <main className="app-main">
        <header className="app-topbar">
          <div>
            <p className="topbar-context">Momento · entorno de desarrollo</p>
            <h1>{pageTitles[page]}</h1>
          </div>
          <div className="topbar-actions">
            <span className="demo-user-badge">Vista de prueba</span>
            <button className="login-button" type="button" onClick={() => setPage("landing")}>Salir</button>
          </div>
        </header>

        <div className="app-content">
          {page === "dashboard" && <Dashboard />}
          {(page === "organizations" || page === "people" || page === "users") && <OrganizationsPanel view={page} />}
          {page === "inbox" && (
            <EmptyModule
              title="Bandeja de solicitudes"
              description="Aquí se recibirán las solicitudes familiares para que el encargado las asigne al personal designado."
              status="Pendiente de desarrollo"
            />
          )}
          {page === "settings" && (
            <EmptyModule
              title="Configuración"
              description="Aquí se administrarán los parámetros de cada organización y servicio."
              status="Pendiente de desarrollo"
            />
          )}
        </div>
      </main>
    </div>
  );
}

function PublicLanding({ onLogin }: { onLogin: () => void }) {
  return (
    <main className="public-landing">
      <header className="public-header">
        <div className="app-brand">
          <img src="/brand/iso-momento.png" alt="" />
          <span>Momento</span>
        </div>
        <button className="primary-action" type="button" onClick={onLogin}>Iniciar sesión</button>
      </header>
      <section className="public-hero">
        <p className="eyebrow">Cuidado conectado</p>
        <h1>Más cerca de cada persona. Mejor coordinados en cada cuidado.</h1>
        <p>Momento acompaña el trabajo de residencias y equipos de cuidado, y conecta a las personas autorizadas con quienes las cuidan.</p>
        <button className="primary-action landing-login" type="button" onClick={onLogin}>Ingresar a Momento</button>
      </section>
      <footer className="public-footer">Plataforma de cuidado para residencias y atención domiciliaria</footer>
    </main>
  );
}

function LoginScreen({
  onBack,
  onDemoAccess,
}: {
  onBack: () => void;
  onDemoAccess: () => void;
}) {
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onDemoAccess();
  }

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="login-brand">
          <img src="/brand/iso-momento.png" alt="" />
          <span>Momento</span>
        </div>
        <p className="eyebrow">Acceso al sistema</p>
        <h1>Iniciar sesión</h1>
        <p className="login-intro">Ingresá con tu cuenta de la organización.</p>
        <p className="login-demo-note">Vista de prueba: todavía no se validan ni se envían credenciales.</p>
        <form className="login-form" onSubmit={submit}>
          <label>Correo electrónico
            <input type="email" autoComplete="username" required />
          </label>
          <label>Contraseña
            <input type="password" autoComplete="current-password" required />
          </label>
          <button type="submit">Continuar a la vista de prueba</button>
        </form>
        <button className="back-link" type="button" onClick={onBack}>Volver a la página pública</button>
      </section>
    </main>
  );
}

function NavButton({
  label,
  active,
  onClick,
  mark,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  mark: string;
}) {
  return (
    <button className={"navigation-item" + (active ? " active" : "")} type="button" onClick={onClick}>
      <span className="navigation-mark" aria-hidden="true">{mark}</span>
      <span>{label}</span>
    </button>
  );
}

function Dashboard() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [organizationId, setOrganizationId] = useState("");
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void fetch("/api/organizations")
      .then(async (response) => {
        if (!response.ok) throw new Error("No se pudieron cargar las organizaciones.");
        return (await response.json()) as Organization[];
      })
      .then((items) => {
        if (!active) return;
        setOrganizations(items);
        if (items.length) setOrganizationId(items[0].id);
        else setLoading(false);
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "No se pudo cargar el dashboard.");
          setLoading(false);
        }
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!organizationId) return;
    let active = true;
    setLoading(true);
    setMetrics(null);
    setError("");
    void (async () => {
      try {
        const [unitsResponse, membersResponse] = await Promise.all([
          fetch(`/api/organizations/${organizationId}/care-units`),
          fetch(`/api/organizations/${organizationId}/memberships`),
        ]);
        if (!unitsResponse.ok || !membersResponse.ok) throw new Error("No se pudieron cargar los indicadores.");
        const units = (await unitsResponse.json()) as CareUnit[];
        const members = (await membersResponse.json()) as Membership[];
        const recipientResponses = await Promise.all(
          units.map((unit) => fetch(`/api/care-units/${unit.id}/care-recipients`)),
        );
        if (recipientResponses.some((response) => !response.ok)) throw new Error("No se pudieron cargar las fichas.");
        const recipients = await Promise.all(recipientResponses.map((response) => response.json() as Promise<unknown[]>));
        if (active) {
          setMetrics({
            services: units.length,
            residents: recipients.reduce((total, list) => total + list.length, 0),
            caregivers: members.filter((member) => member.user_group === "staff" && /cuidador|cuidadora/i.test(member.role_label ?? "")).length,
            physicians: members.filter((member) => member.user_group === "staff" && /m[eé]dico|doctor/i.test(member.role_label ?? "")).length,
            families: members.filter((member) => member.user_group === "family").length,
            olderAdults: members.filter((member) => member.user_group === "older_adult").length,
          });
        }
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "No se pudieron cargar los indicadores.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, [organizationId]);

  return (
    <section className="dashboard-view">
      <div className="dashboard-heading-row">
        <div>
          <p className="eyebrow">Resumen de gestión</p>
          <h2>El estado de tu organización, en un solo lugar.</h2>
          <p>Los indicadores se calculan con los registros actuales de la organización seleccionada.</p>
        </div>
        {organizations.length > 0 && (
          <label className="organization-selector">
            Organización
            <select value={organizationId} onChange={(event) => setOrganizationId(event.target.value)}>
              {organizations.map((organization) => <option value={organization.id} key={organization.id}>{organization.name}</option>)}
            </select>
          </label>
        )}
      </div>

      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {organizations.length === 0 && !loading ? (
        <div className="empty-panel">
          <h3>No hay organizaciones cargadas</h3>
          <p>Creá una organización y sus servicios para empezar a ver sus indicadores.</p>
        </div>
      ) : (
        <>
          <div className="metric-grid">
            <MetricCard label="Personas cuidadas" value={loading ? "—" : metrics?.residents ?? 0} detail="Fichas activas en los servicios" />
            <MetricCard label="Servicios" value={loading ? "—" : metrics?.services ?? 0} detail="Residencias y equipos domiciliarios" />
            <MetricCard label="Cuidadores" value={loading ? "—" : metrics?.caregivers ?? 0} detail="Según la función registrada" />
            <MetricCard label="Médicos asociados" value={loading ? "—" : metrics?.physicians ?? 0} detail="No indica quién está de guardia" />
            <MetricCard label="Familias vinculadas" value={loading ? "—" : metrics?.families ?? 0} detail="Cuentas del grupo familiar" />
          </div>
          <div className="dashboard-lower-grid">
            <section className="dashboard-info-card">
              <div className="dashboard-card-heading">
                <div><span className="card-kicker">OPERACIÓN</span><h3>Guardias médicas</h3></div>
                <span className="module-status">Sin configurar</span>
              </div>
              <p>El sistema todavía no tiene una agenda de guardias. Este indicador se activará al construir ese módulo.</p>
            </section>
            <section className="dashboard-info-card">
              <div className="dashboard-card-heading">
                <div><span className="card-kicker">PRÓXIMAMENTE</span><h3>Bandeja de solicitudes</h3></div>
                <span className="module-status">En desarrollo</span>
              </div>
              <p>Las solicitudes de familiares se mostrarán aquí cuando esté implementada la bandeja de atención.</p>
            </section>
          </div>
          <p className="dashboard-preview-note">Vista de prueba sin autenticación. No usar datos reales.</p>
        </>
      )}
    </section>
  );
}

function MetricCard({ label, value, detail }: { label: string; value: number | string; detail: string }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

function EmptyModule({
  title,
  description,
  status,
}: {
  title: string;
  description: string;
  status: string;
}) {
  return (
    <section className="module-placeholder">
      <span className="module-status">{status}</span>
      <h2>{title}</h2>
      <p>{description}</p>
    </section>
  );
}
