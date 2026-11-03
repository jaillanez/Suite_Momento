import { type FormEvent, useEffect, useState } from "react";
import CareShiftPanel from "./CareLog";
import FamilyPortal from "./FamilyPortal";
import { ForgotPasswordForm, ResetPasswordScreen } from "./PasswordScreens";
import { AuditPanel, SettingsPanel } from "./ManagerPanels";
import InboxPanel, { categoryClass, formatDate, type InboxRequest, loadInboxes } from "./InboxPanel";
import OrganizationsPanel, { categoryLabels, type OrganizationView, type StaffRole, staffRoleLabels } from "./OrganizationsPanel";

type Page = OrganizationView | "landing" | "login" | "family" | "dashboard" | "shift" | "inbox" | "audit" | "settings";
type SessionMembership = { user_group: "staff" | "family" | "older_adult"; staff_role: StaffRole | null; handles_inbox: boolean };
type Portal = "staff" | "family";
type Access = { role: StaffRole | null; inbox: boolean };

const rolePriority: StaffRole[] = ["manager", "administrative", "physician", "caregiver"];

/** El puesto más amplio de la cuenta define el menú; la API vuelve a validar cada acción. */
function accessFrom(memberships: SessionMembership[]): Access {
  const roles = memberships.map((item) => item.staff_role).filter((role): role is StaffRole => role !== null);
  const role = rolePriority.find((candidate) => roles.includes(candidate)) ?? null;
  return { role, inbox: role === "manager" || memberships.some((item) => item.handles_inbox) };
}
type ApiState = "checking" | "available" | "unavailable";
type Organization = { id: string; name: string };
type CareUnit = { id: string; name: string };
type Member = { user_group: "staff" | "family" | "older_adult"; staff_role: StaffRole | null };
type DashboardData = { organization: string; services: number; residents: number; caregivers: number; physicians: number; families: number; recent: InboxRequest[] };

const pageTitles: Record<Exclude<Page, "landing" | "login" | "family">, string> = {
  dashboard: "Panel de gestión",
  organizations: "Organizaciones y servicios",
  people: "Personas cuidadas",
  users: "Usuarios y vínculos",
  shift: "Turno y registros",
  inbox: "Bandeja de solicitudes",
  audit: "Registro de control",
  settings: "Configuración",
};

function readResetToken(): string {
  const match = window.location.hash.match(/^#restablecer=([\w-]+)$/);
  if (match) window.history.replaceState(null, "", window.location.pathname + window.location.search);
  return match?.[1] ?? "";
}

export default function App() {
  const [page, setPage] = useState<Page>("landing");
  const [apiState, setApiState] = useState<ApiState>("checking");
  const [userName, setUserName] = useState("");
  const [access, setAccess] = useState<Access>({ role: null, inbox: false });
  const [logoutError, setLogoutError] = useState("");
  // Enlace del correo (#restablecer=…); se quita de la barra de direcciones al leerlo.
  const [resetToken, setResetToken] = useState(readResetToken);
  useEffect(() => {
    const onHashChange = () => { const token = readResetToken(); if (token) setResetToken(token); };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    let active = true;
    void fetch("/api/health")
      .then((response) => { if (active) setApiState(response.ok ? "available" : "unavailable"); })
      .catch(() => { if (active) setApiState("unavailable"); });
    void fetch("/api/auth/session")
      .then(async (response) => {
        if (!active || !response.ok) return;
        const data = (await response.json()) as {
          authenticated: boolean;
          user: { display_name: string } | null;
          memberships: SessionMembership[];
        };
        if (!data.authenticated || !data.user) return;
        setUserName(data.user.display_name);
        setAccess(accessFrom(data.memberships));
        setPage(data.memberships.some((item) => item.user_group === "staff") ? "dashboard" : "family");
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

  if (resetToken) return <ResetPasswordScreen token={resetToken} onDone={() => { setResetToken(""); setPage("login"); }} />;
  if (page === "landing") return <PublicLanding onLogin={() => setPage("login")} />;
  if (page === "login") {
    return <LoginScreen onBack={() => setPage("landing")} onAuthenticated={(name, portal, memberships) => { setUserName(name); setAccess(accessFrom(memberships)); setPage(portal === "family" ? "family" : "dashboard"); }} />;
  }
  if (page === "family") return <FamilyPortal userName={userName} onLogout={() => void logout()} />;

  const isManager = access.role === "manager";
  const canAuthorize = isManager || access.role === "administrative" || access.role === "physician";

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
          {isManager && <NavButton label="Organizaciones" active={page === "organizations"} onClick={() => setPage("organizations")} mark="OR" />}
          <NavButton label="Turno y registros" active={page === "shift"} onClick={() => setPage("shift")} mark="TR" />
          <NavButton label="Personas cuidadas" active={page === "people"} onClick={() => setPage("people")} mark="PC" />
          {canAuthorize && <NavButton label={isManager ? "Usuarios y vínculos" : "Familias"} active={page === "users"} onClick={() => setPage("users")} mark="UV" />}
          {access.inbox && <NavButton label="Bandeja de solicitudes" active={page === "inbox"} onClick={() => setPage("inbox")} mark="BD" />}
          {isManager && <NavButton label="Registro de control" active={page === "audit"} onClick={() => setPage("audit")} mark="RC" />}
          {isManager && <NavButton label="Configuración" active={page === "settings"} onClick={() => setPage("settings")} mark="CO" />}
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
            {logoutError && <span className="form-message error-message" role="alert">{logoutError}</span>}<span className="demo-user-badge">{userName}{access.role ? ` · ${staffRoleLabels[access.role]}` : ""}</span>
            <button className="login-button" type="button" onClick={() => void logout()}>Salir</button>
          </div>
        </header>

        <div className="app-content">
          {page === "dashboard" && <Dashboard userName={userName} isManager={isManager} canAuthorize={canAuthorize} hasInbox={access.inbox} />}
          {(page === "organizations" || page === "people" || page === "users") && <OrganizationsPanel view={page} canManage={isManager} canCreatePeople={isManager || access.role === "administrative"} />}
          {page === "shift" && <CareShiftPanel />}
          {page === "inbox" && <InboxPanel isManager={isManager} />}
          {page === "audit" && <AuditPanel />}
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
  onAuthenticated: (name: string, portal: Portal, memberships: SessionMembership[]) => void;
}) {
  const [portal, setPortal] = useState<Portal>("staff");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [forgot, setForgot] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const response = await fetch(portal === "family" ? "/api/auth/family-login" : "/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const result = (await response.json()) as { detail?: string; user?: { display_name: string }; memberships?: SessionMembership[] };
      if (!response.ok || !result.user) {
        setError(result.detail ?? "No se pudo iniciar sesión. Revisá el correo y la contraseña.");
        return;
      }
      onAuthenticated(result.user.display_name, portal, result.memberships ?? []);
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
        <h1>{forgot ? "Recuperar contraseña" : "Iniciar sesión"}</h1>
        {forgot ? <ForgotPasswordForm onBack={() => setForgot(false)} /> : <>
        <div className="login-switch" role="tablist" aria-label="Tipo de acceso">
          <button type="button" role="tab" aria-selected={portal === "staff"} className={portal === "staff" ? "active" : ""} onClick={() => { setPortal("staff"); setError(""); }}>Equipo de la residencia</button>
          <button type="button" role="tab" aria-selected={portal === "family"} className={portal === "family" ? "active" : ""} onClick={() => { setPortal("family"); setError(""); }}>Familias</button>
        </div>
        <p className="login-intro">{portal === "staff" ? "Ingresá con la cuenta configurada para tu organización." : "Ingresá con la cuenta que te dio la residencia."}</p>
        <form className="login-form" onSubmit={submit}>
          <label>Correo electrónico<input type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
          <label>Contraseña<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
          {error && <p className="form-message error-message" role="alert">{error}</p>}
          <button type="submit" disabled={submitting}>{submitting ? "Validando acceso…" : "Ingresar a Momento"}</button>
        </form>
        <button className="back-link" type="button" onClick={() => { setForgot(true); setError(""); }}>¿Olvidaste tu contraseña?</button>
        <button className="back-link" type="button" onClick={onBack}>Volver a la página pública</button>
        </>}
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

function Dashboard({ userName, isManager, canAuthorize, hasInbox }: { userName: string; isManager: boolean; canAuthorize: boolean; hasInbox: boolean }) {
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
          if (active) setData({ organization: "", services: 0, residents: 0, caregivers: 0, physicians: 0, families: 0, recent: [] });
          return;
        }
        const unitsByOrganization = await Promise.all(organizations.map(async (org) => {
          const response = await fetch(`/api/organizations/${org.id}/care-units`);
          if (!response.ok) throw new Error("No se pudieron cargar los servicios.");
          return (await response.json()) as CareUnit[];
        }));
        // Los cuidadores no consultan usuarios; administrativo y médico reciben solo familias.
        const membersByOrganization = await Promise.all(organizations.map(async (org) => {
          if (!canAuthorize) return [] as Member[];
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
        const inboxes = hasInbox ? await loadInboxes({ isManager }).catch(() => []) : [];
        const recent = inboxes
          .flatMap((inbox) => inbox.requests)
          .sort((a, b) => b.created_at.localeCompare(a.created_at))
          .slice(0, 3);
        if (active) setData({
          organization: organizations.length === 1 ? organizations[0].name : `${organizations.length} organizaciones`,
          services: units.length,
          residents: recipientsByUnit.reduce((sum, list) => sum + list.length, 0),
          caregivers: members.filter((member) => member.staff_role === "caregiver").length,
          physicians: members.filter((member) => member.staff_role === "physician").length,
          families: members.filter((member) => member.user_group === "family").length,
          recent,
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
            {isManager && <MetricCard label="Cuidadores" value={loading ? "—" : data?.caregivers ?? 0} detail="Personal vinculado a la organización" />}
            {isManager && <MetricCard label="Médicos asociados" value={loading ? "—" : data?.physicians ?? 0} detail="Profesionales vinculados al equipo" />}
            {canAuthorize && <MetricCard label="Familias vinculadas" value={loading ? "—" : data?.families ?? 0} detail="Cuentas del grupo familiar" />}
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
          {hasInbox && <section className="dashboard-info-card recent-requests">
            <div className="dashboard-card-heading"><div><span className="card-kicker">BANDEJA</span><h3>Solicitudes recientes</h3></div></div>
            {!loading && (data?.recent.length ?? 0) === 0 && <p className="list-empty">No hay solicitudes de familias.</p>}
            {data?.recent.map((item) => (
              <div className="request-preview" key={item.id}><span className={"request-type " + categoryClass[item.category]}>{categoryLabels[item.category]}</span><span><strong>{item.subject}</strong><small>{item.family_name} · familiar de {item.care_recipient_name} · {item.status_label}</small></span><span className="request-date">{formatDate(item.created_at)}</span></div>
            ))}
          </section>}
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

