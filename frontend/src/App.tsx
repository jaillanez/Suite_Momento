import { type FormEvent, useEffect, useState } from "react";
import OrganizationsPanel, { type OrganizationView } from "./OrganizationsPanel";

type Page = OrganizationView | "landing" | "login" | "dashboard" | "inbox" | "settings";
type ApiState = "checking" | "available" | "unavailable";
type Organization = { id: string; name: string };
type CareUnit = { id: string; name: string };
type Member = { user_group: "staff" | "family" | "older_adult"; role_label: string | null };
type DashboardData = { organization: string; services: number; residents: number; caregivers: number; physicians: number; families: number };

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
  const [userName, setUserName] = useState("");
  const [logoutError, setLogoutError] = useState("");

  useEffect(() => {
    let active = true;
    void fetch("/api/health")
      .then((response) => { if (active) setApiState(response.ok ? "available" : "unavailable"); })
      .catch(() => { if (active) setApiState("unavailable"); });
    void fetch("/api/auth/session")
      .then(async (response) => {
        if (!active || !response.ok) return;
        const data = (await response.json()) as { user: { display_name: string } };
        setUserName(data.user.display_name);
        setPage("dashboard");
      })
      .catch(() => undefined);
    return () => { active = false; };
  }, []);

  async function logout() {
    setLogoutError("");
    try {
      const response = await fetch("/api/auth/logout", { method: "POST" });
      if (!response.ok) {
        setLogoutError("No se pudo cerrar la sesión. Comprobá la conexión e intentá nuevamente.");
        return;
      }
      setUserName("");
      setPage("landing");
    } catch {
      setLogoutError("No se pudo cerrar la sesión. Comprobá la conexión e intentá nuevamente.");
    }
  }

  if (page === "landing") return <PublicLanding onLogin={() => setPage("login")} />;
  if (page === "login") {
    return <LoginScreen onBack={() => setPage("landing")} onAuthenticated={(name) => { setUserName(name); setPage("dashboard"); }} />;
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
            {logoutError && <span className="form-message error-message" role="alert">{logoutError}</span>}<span className="demo-user-badge">{userName}</span>
            <button className="login-button" type="button" onClick={() => void logout()}>Salir</button>
          </div>
        </header>

        <div className="app-content">
          {page === "dashboard" && <Dashboard userName={userName} />}
          {(page === "organizations" || page === "people" || page === "users") && <OrganizationsPanel view={page} />}
          {page === "inbox" && <InboxPanel />}
          {page === "settings" && <SettingsPanel />}
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
      </section>
      <footer className="public-footer">Plataforma de cuidado para residencias y atención domiciliaria</footer>
    </main>
  );
}

function LoginScreen({
  onBack,
  onAuthenticated,
}: {
  onBack: () => void;
  onAuthenticated: (name: string) => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const result = (await response.json()) as { detail?: string; user?: { display_name: string } };
      if (!response.ok || !result.user) {
        setError(result.detail ?? "No se pudo iniciar sesión. Revisá el correo y la contraseña.");
        return;
      }
      onAuthenticated(result.user.display_name);
    } catch {
      setError("No se pudo conectar con Momento. Comprobá que la API esté iniciada.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="login-brand"><img src="/brand/iso-momento.png" alt="" /><span>Momento</span></div>
        <p className="eyebrow">Acceso al sistema</p>
        <h1>Iniciar sesión</h1>
        <p className="login-intro">Ingresá con la cuenta configurada para tu organización.</p>
        <form className="login-form" onSubmit={submit}>
          <label>Correo electrónico<input type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
          <label>Contraseña<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
          {error && <p className="form-message error-message" role="alert">{error}</p>}
          <button type="submit" disabled={submitting}>{submitting ? "Validando acceso…" : "Ingresar a Momento"}</button>
        </form>
        <button className="back-link" type="button" onClick={onBack}>Volver a la página pública</button>
      </section>
    </main>
  );
}

function InboxPanel() {
  const [items, setItems] = useState([
    { id: 1, category: "Dieta", title: "Consulta sobre menú de esta semana", person: "Elena Suárez", family: "Lucía Ferreyra", time: "09:12", assignee: "Sofía Pereyra", status: "Pendiente" },
    { id: 2, category: "Actividad", title: "Confirmar participación en musicoterapia", person: "Ricardo Molina", family: "Andrés Molina", time: "08:26", assignee: "Mariana López", status: "En seguimiento" },
    { id: 3, category: "Medicación", title: "Aviso: acercar receta actualizada", person: "Beatriz Acosta", family: "Nicolás Acosta", time: "07:48", assignee: "Sin asignar", status: "Pendiente" },
    { id: 4, category: "Actividad", title: "Agradecimiento por la celebración", person: "Elena Suárez", family: "Lucía Ferreyra", time: "Ayer", assignee: "Sofía Pereyra", status: "Resuelta" },
  ]);
  function assign(id: number, assignee: string) {
    setItems((current) => current.map((item) => item.id === id ? { ...item, assignee, status: "En seguimiento" } : item));
  }
  function resolve(id: number) {
    setItems((current) => current.map((item) => item.id === id ? { ...item, status: "Resuelta" } : item));
  }
  return <section className="inbox-view">
    <div className="dashboard-heading-row"><div><p className="eyebrow">Comunicación con familias</p><h2>Bandeja de solicitudes</h2><p>El encargado organiza y asigna cada solicitud al personal designado.</p></div><span className="module-status">{items.filter((item) => item.status !== "Resuelta").length} abiertas</span></div>
    <div className="inbox-filters"><span className="filter-chip selected">Todas</span><span className="filter-chip">Pendientes</span><span className="filter-chip">En seguimiento</span><span className="filter-chip">Resueltas</span></div>
    <div className="inbox-list">{items.map((item) => <article className="inbox-item" key={item.id}>
      <div className="inbox-item-top"><span className={"request-type " + (item.category === "Dieta" ? "type-diet" : item.category === "Actividad" ? "type-activity" : "type-medication")}>{item.category}</span><span className="request-date">{item.time}</span></div>
      <h3>{item.title}</h3><p>{item.family} · familiar de <strong>{item.person}</strong></p>
      <div className="inbox-item-actions"><label>Responsable<select value={item.assignee} onChange={(event) => assign(item.id, event.target.value)}><option>Sin asignar</option><option>Mariana López</option><option>Sofía Pereyra</option><option>Ramiro Costa</option><option>Dra. Laura Méndez</option></select></label><span className={"status-pill " + (item.status === "Resuelta" ? "status-green" : item.status === "En seguimiento" ? "status-blue" : "status-amber")}>{item.status}</span>{item.status !== "Resuelta" && <button className="resolve-button" type="button" onClick={() => resolve(item.id)}>Marcar resuelta</button>}</div>
    </article>)}</div>
    <p className="dashboard-preview-note">Solicitudes y nombres ficticios; las acciones de asignación y resolución se reflejan en esta demostración.</p>
  </section>;
}

function SettingsPanel() {
  return <section className="settings-view"><p className="eyebrow">Datos del espacio de trabajo</p><h2>Residencia Los Aromos</h2><p className="settings-intro">Información de ejemplo para mostrar cómo se identifican los servicios de la organización.</p>
    <div className="settings-grid"><article><span>Organización</span><strong>Los Aromos Cuidados S.R.L.</strong><small>Prestador · Argentina</small></article><article><span>Servicio</span><strong>Residencia Los Aromos</strong><small>Residencia para personas mayores</small></article><article><span>Ubicación</span><strong>Palermo, Buenos Aires</strong><small>Argentina · UTC−3</small></article><article><span>Responsable del espacio</span><strong>Mariana López</strong><small>Encargada de residencia</small></article><article><span>Contacto</span><strong>administracion@losaromos.demo</strong><small>Cuenta de demostración</small></article><article><span>Preferencias</span><strong>Español · formato 24 h</strong><small>Configuración visible del espacio</small></article></div>
    <div className="settings-note"><strong>Entorno de demostración</strong><p>Estos datos describen una organización inventada. En la aplicación, cada organización administra su propio espacio y sus miembros autorizados.</p></div>
  </section>;
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

function Dashboard({ userName }: { userName: string }) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const orgResponse = await fetch("/api/organizations");
        if (!orgResponse.ok) throw new Error("No se pudo cargar la organización de esta cuenta.");
        const organizations = (await orgResponse.json()) as Organization[];
        if (!organizations.length) {
          if (active) setData({ organization: "", services: 0, residents: 0, caregivers: 0, physicians: 0, families: 0 });
          return;
        }
        const unitsByOrganization = await Promise.all(organizations.map(async (org) => {
          const response = await fetch(`/api/organizations/${org.id}/care-units`);
          if (!response.ok) throw new Error("No se pudieron cargar los servicios.");
          return (await response.json()) as CareUnit[];
        }));
        const membersByOrganization = await Promise.all(organizations.map(async (org) => {
          const response = await fetch(`/api/organizations/${org.id}/memberships`);
          if (!response.ok) throw new Error("No se pudo cargar el equipo.");
          return (await response.json()) as Member[];
        }));
        const units = unitsByOrganization.flat();
        const recipientsByUnit = await Promise.all(units.map(async (unit) => {
          const response = await fetch(`/api/care-units/${unit.id}/care-recipients`);
          if (!response.ok) throw new Error("No se pudieron cargar las personas cuidadas.");
          return (await response.json()) as unknown[];
        }));
        const members = membersByOrganization.flat();
        if (active) setData({
          organization: organizations.length === 1 ? organizations[0].name : `${organizations.length} organizaciones`,
          services: units.length,
          residents: recipientsByUnit.reduce((sum, list) => sum + list.length, 0),
          caregivers: members.filter((member) => member.user_group === "staff" && /cuidador|cuidadora/i.test(member.role_label ?? "")).length,
          physicians: members.filter((member) => member.user_group === "staff" && /m[eé]dico|doctor/i.test(member.role_label ?? "")).length,
          families: members.filter((member) => member.user_group === "family").length,
        });
      } catch (caught) {
        if (active) setError(caught instanceof Error ? caught.message : "No se pudo cargar el resumen.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => { active = false; };
  }, []);

  return (
    <section className="dashboard-view">
      <div className="demo-banner"><span>ESCENARIO DE DEMOSTRACIÓN</span><p>Los registros del escenario son ficticios. Los indicadores se consultan desde la base local.</p></div>
      <div className="dashboard-heading-row">
        <div><p className="eyebrow">Resumen del día · turno mañana</p><h2>Buen día, {userName.split(" ")[0] || "equipo"}.</h2><p>{data?.organization || "Cargando organización…"} · Argentina</p></div>
        <span className="live-status"><i /> Operación en curso</span>
      </div>
      {error && <p className="form-message error-message" role="alert">{error}</p>}
      {data && !data.organization ? <div className="empty-panel"><h3>La cuenta todavía no tiene una organización</h3><p>Creá la organización y el servicio desde “Organizaciones” para completar el panel.</p></div> : (
        <>
          <div className="metric-grid">
            <MetricCard label="Personas cuidadas" value={loading ? "—" : data?.residents ?? 0} detail="Fichas activas en sus servicios" />
            <MetricCard label="Cuidadores" value={loading ? "—" : data?.caregivers ?? 0} detail="Personal vinculado a la organización" />
            <MetricCard label="Médicos asociados" value={loading ? "—" : data?.physicians ?? 0} detail="Profesionales vinculados al equipo" />
            <MetricCard label="Familias vinculadas" value={loading ? "—" : data?.families ?? 0} detail="Cuentas del grupo familiar" />
            <MetricCard label="Servicios" value={loading ? "—" : data?.services ?? 0} detail="Residencias y equipos domiciliarios" />
          </div>
          <div className="dashboard-lower-grid">
            <section className="dashboard-info-card">
              <div className="dashboard-card-heading"><div><span className="card-kicker">AGENDA DE EJEMPLO</span><h3>Actividades de hoy</h3></div><span className="module-status">Muestra</span></div>
              <ul className="activity-list">
                <li><span className="activity-time">09:30</span><span><strong>Control médico</strong><small>Elena Suárez · consultorio</small></span><b className="status-pill status-blue">Agendado</b></li>
                <li><span className="activity-time">10:00</span><span><strong>Taller de música</strong><small>Salón principal · grupo A</small></span><b className="status-pill status-green">En curso</b></li>
                <li><span className="activity-time">12:30</span><span><strong>Almuerzo</strong><small>Menú adaptado · comedor</small></span><b className="status-pill status-gray">Programado</b></li>
              </ul>
            </section>
            <section className="dashboard-info-card">
              <div className="dashboard-card-heading"><div><span className="card-kicker">EQUIPO DE EJEMPLO</span><h3>Referentes del turno</h3></div><span className="module-status">Muestra</span></div>
              <ul className="team-list">
                <li><span className="avatar avatar-lilac">LM</span><span><strong>Dra. Laura Méndez</strong><small>Profesional médica · referencia del día</small></span><i className="team-indicator">Disponible</i></li>
                <li><span className="avatar avatar-peach">SP</span><span><strong>Sofía Pereyra</strong><small>Cuidadora · coordinación de planta</small></span><i className="team-indicator">En servicio</i></li>
                <li><span className="avatar avatar-mint">RC</span><span><strong>Ramiro Costa</strong><small>Encargado · turno mañana</small></span><i className="team-indicator">En servicio</i></li>
              </ul>
            </section>
          </div>
          <section className="dashboard-info-card recent-requests">
            <div className="dashboard-card-heading"><div><span className="card-kicker">SOLICITUDES DE EJEMPLO</span><h3>Actividad reciente</h3></div><span className="module-status">Muestra</span></div>
            <div className="request-preview"><span className="request-type type-diet">DIETA</span><span><strong>Consulta sobre menú de esta semana</strong><small>Lucía Ferreyra · familiar de Elena Suárez</small></span><span className="request-date">09:12</span></div>
            <div className="request-preview"><span className="request-type type-activity">ACTIVIDAD</span><span><strong>Confirmar participación en musicoterapia</strong><small>Andrés Molina · familiar de Ricardo Molina</small></span><span className="request-date">08:26</span></div>
          </section>
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

