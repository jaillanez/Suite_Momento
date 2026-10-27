import { type FormEvent, useEffect, useState } from "react";
import OrganizationsPanel, { type OrganizationView } from "./OrganizationsPanel";

type Page = OrganizationView | "dashboard" | "inbox" | "settings" | "login";
type ApiState = "checking" | "available" | "unavailable";

const pageTitles: Record<Page, string> = {
  dashboard: "Inicio",
  organizations: "Organizaciones y servicios",
  people: "Personas cuidadas",
  users: "Usuarios y vínculos",
  inbox: "Bandeja de solicitudes",
  settings: "Configuración",
  login: "Acceso a Momento",
};

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [apiState, setApiState] = useState<ApiState>("checking");

  async function checkApi() {
    setApiState("checking");
    try {
      const response = await fetch("/api/health");
      setApiState(response.ok ? "available" : "unavailable");
    } catch {
      setApiState("unavailable");
    }
  }

  useEffect(() => {
    void checkApi();
  }, []);

  if (page === "login") {
    return <LoginScreen onBack={() => setPage("dashboard")} />;
  }

  return (
    <div className="app-layout">
      <aside className="app-sidebar">
        <a className="app-brand" href="#" onClick={(event) => { event.preventDefault(); setPage("dashboard"); }}>
          <img src="/brand/iso-momento.png" alt="" />
          <span>Momento</span>
        </a>
        <p className="sidebar-caption">GESTIÓN DEL CUIDADO</p>
        <nav className="main-navigation" aria-label="Navegación principal">
          <NavButton label="Inicio" active={page === "dashboard"} onClick={() => setPage("dashboard")} mark="IN" />
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
          <button className="login-button" type="button" onClick={() => setPage("login")}>
            Iniciar sesión
          </button>
        </header>

        <div className="app-content">
          {page === "dashboard" && <Dashboard onNavigate={setPage} />}
          {(page === "organizations" || page === "people" || page === "users") && (
            <OrganizationsPanel view={page} />
          )}
          {page === "inbox" && (
            <EmptyModule
              title="Bandeja de solicitudes"
              description="Este espacio recibirá las solicitudes de familiares y permitirá que el encargado las asigne al personal designado."
              status="En desarrollo"
            />
          )}
          {page === "settings" && (
            <EmptyModule
              title="Configuración"
              description="Aquí se reunirán los parámetros de cada organización y servicio."
              status="Disponible por etapas"
            />
          )}
        </div>
      </main>
    </div>
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

function Dashboard({ onNavigate }: { onNavigate: (page: Page) => void }) {
  return (
    <section className="dashboard-view">
      <div className="dashboard-welcome">
        <div>
          <p className="eyebrow">Panel de gestión</p>
          <h2>Un espacio de trabajo para organizar el cuidado.</h2>
          <p>Seleccioná una sección del menú para administrar organizaciones, personas y usuarios.</p>
        </div>
        <div className="dashboard-mark" aria-hidden="true">M</div>
      </div>
      <div className="dashboard-shortcuts">
        <button type="button" onClick={() => onNavigate("organizations")}>
          <span className="shortcut-mark">01</span>
          <strong>Organizaciones y servicios</strong>
          <span>Gestioná prestadores, residencias y atención domiciliaria.</span>
        </button>
        <button type="button" onClick={() => onNavigate("people")}>
          <span className="shortcut-mark">02</span>
          <strong>Personas cuidadas</strong>
          <span>Consultá las fichas asociadas a cada servicio.</span>
        </button>
        <button type="button" onClick={() => onNavigate("users")}>
          <span className="shortcut-mark">03</span>
          <strong>Usuarios y vínculos</strong>
          <span>Registrá cuentas de prueba y su alcance organizativo.</span>
        </button>
      </div>
      <div className="development-note">
        <strong>Entorno local de desarrollo</strong>
        <span>Usá información ficticia. El inicio de sesión y los permisos todavía no están habilitados.</span>
      </div>
    </section>
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

function LoginScreen({ onBack }: { onBack: () => void }) {
  const [notice, setNotice] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("El acceso todavía no está conectado a autenticación. No se envió la contraseña.");
  }

  return (
    <main className="login-shell">
      <section className="login-card">
        <a className="login-brand" href="#" onClick={(event) => { event.preventDefault(); onBack(); }}>
          <img src="/brand/iso-momento.png" alt="" />
          <span>Momento</span>
        </a>
        <p className="eyebrow">Acceso al sistema</p>
        <h1>Iniciar sesión</h1>
        <p className="login-intro">Ingresá con tu cuenta de la organización.</p>
        <form className="login-form" onSubmit={submit}>
          <label>
            Correo electrónico
            <input type="email" autoComplete="username" required />
          </label>
          <label>
            Contraseña
            <input type="password" autoComplete="current-password" required />
          </label>
          <button type="submit">Continuar</button>
        </form>
        {notice && <p className="login-notice" role="status">{notice}</p>}
        <button className="back-link" type="button" onClick={onBack}>Volver al entorno local</button>
        <p className="login-footnote">Prototipo visual. La autenticación real se incorporará antes de habilitar cuentas o datos reales.</p>
      </section>
    </main>
  );
}
