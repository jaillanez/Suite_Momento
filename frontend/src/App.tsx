import { useEffect, useState } from "react";

type ServiceState = "checking" | "available" | "unavailable";

async function isServiceAvailable(path: string): Promise<boolean> {
  try {
    const response = await fetch(path);
    if (!response.ok) return false;

    const body = (await response.json()) as { status?: string };
    return body.status === "ok";
  } catch {
    return false;
  }
}

export default function App() {
  const [apiState, setApiState] = useState<ServiceState>("checking");
  const [databaseState, setDatabaseState] =
    useState<ServiceState>("checking");

  async function checkServices() {
    setApiState("checking");
    setDatabaseState("checking");

    const [apiAvailable, databaseAvailable] = await Promise.all([
      isServiceAvailable("/api/health"),
      isServiceAvailable("/api/health/database"),
    ]);

    setApiState(apiAvailable ? "available" : "unavailable");
    setDatabaseState(databaseAvailable ? "available" : "unavailable");
  }

  useEffect(() => {
    void checkServices();
  }, []);

  return (
    <main className="page-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Momento, inicio">
          <img className="brand-logo" src="/brand/iso-momento.png" alt="" />
          <span>momento</span>
        </a>
        <span className="environment-tag">
          <span className="environment-dot" aria-hidden="true" />
          Entorno de desarrollo
        </span>
      </header>

      <section className="hero" aria-labelledby="welcome-title">
        <div className="hero-copy">
          <p className="eyebrow">Una base nueva para cuidar mejor</p>
          <h1 id="welcome-title">El cuidado se construye en red, con la persona en el centro.</h1>
          <p className="hero-description">
            Momento nace para acompañar el cuidado de personas mayores en
            residencias y domicilios, conectando a quienes forman parte de su
            vida cotidiana.
          </p>
          <div className="hero-note">
            <span className="note-symbol" aria-hidden="true">i</span>
            <p>
              Esta es una base de desarrollo. Los antecedentes de Momento orientan el descubrimiento; el alcance nuevo todavía se está definiendo.
            </p>
          </div>
        </div>

        <aside className="service-panel" aria-labelledby="service-title">
          <div className="panel-heading">
            <p className="eyebrow">Estado del sistema</p>
            <h2 id="service-title">Servicios locales</h2>
          </div>
          <ServiceRow label="API de Momento" state={apiState} />
          <ServiceRow label="Base PostgreSQL" state={databaseState} />
          <button className="check-button" onClick={() => void checkServices()}>
            Volver a comprobar
          </button>
          <p className="panel-footnote">
            La API puede funcionar aunque la base todavía no esté configurada.
          </p>
        </aside>
      </section>

      <section className="foundation" aria-labelledby="foundation-title">
        <div className="section-heading">
          <p className="eyebrow">De la experiencia de Momento</p>
          <h2 id="foundation-title">Temas que vamos a validar con el piloto</h2>
        </div>

        <p className="section-intro">
          Son líneas surgidas de los materiales compartidos, no funciones ya implementadas.
        </p>
        <div className="foundation-grid">
          <article className="foundation-card">
            <span className="card-number">01</span>
            <h3>La persona y su historia</h3>
            <p>
              Preferencias, apoyos y aspectos de su vida que pueden ayudar a personalizar el cuidado.
            </p>
          </article>
          <article className="foundation-card">
            <span className="card-number">02</span>
            <h3>Continuidad entre quienes cuidan</h3>
            <p>
              Novedades, actividades y asuntos pendientes que podrían facilitar la coordinación.
            </p>
          </article>
          <article className="foundation-card">
            <span className="card-number">03</span>
            <h3>Comunicación con la familia</h3>
            <p>
              Información clara y autorizada, diferenciada de los registros profesionales privados.
            </p>
          </article>
          <article className="foundation-card">
            <span className="card-number">04</span>
            <h3>Apoyo a cuidadores</h3>
            <p>
              Herramientas de trabajo junto con capacitación y recursos de acompañamiento.
            </p>
          </article>
        </div>
      </section>

      <footer className="page-footer">
        <span>Momento · producto en descubrimiento</span>
        <span>Sin datos reales de residentes</span>
      </footer>
    </main>
  );
}

function ServiceRow({
  label,
  state,
}: {
  label: string;
  state: ServiceState;
}) {
  const stateText = {
    checking: "Comprobando",
    available: "Disponible",
    unavailable: "Pendiente",
  }[state];

  return (
    <div className="service-row" aria-live="polite">
      <span className={"service-indicator " + state} aria-hidden="true" />
      <span className="service-label">{label}</span>
      <span className={"service-state " + state}>{stateText}</span>
    </div>
  );
}
