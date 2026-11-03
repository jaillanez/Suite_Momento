import { useEffect, useRef, useState } from "react";

export type Item = { id: string; kind: string; title: string; body: string | null; created_at: string; read: boolean };

const when = (value: string) => new Date(value).toLocaleString("es-AR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });

/** Campana de avisos. Consulta cada minuto; la app móvil usará las mismas rutas.
 *  El personal usa /api/notifications y las familias /api/family/notifications. */
export default function NotificationBell({ basePath = "/api/notifications", onOpen }: { basePath?: string; onOpen: (item: Item) => void }) {
  const [items, setItems] = useState<Item[]>([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const wrapper = useRef<HTMLDivElement>(null);

  async function load() {
    try {
      const response = await fetch(basePath);
      if (!response.ok) return;
      const data = (await response.json()) as { unread: number; items: Item[] };
      setItems(data.items);
      setUnread(data.unread);
    } catch {
      // Sin conexión: se reintenta en la próxima consulta.
    }
  }

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 60000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent) => { if (!wrapper.current?.contains(event.target as Node)) setOpen(false); };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", escape); };
  }, [open]);

  async function select(item: Item) {
    if (!item.read) await fetch(`${basePath}/${item.id}/read`, { method: "POST" });
    setOpen(false);
    await load();
    onOpen(item);
  }

  async function readAll() {
    await fetch(`${basePath}/read-all`, { method: "POST" });
    await load();
  }

  return (
    <div className="notification-wrapper" ref={wrapper}>
      <button className="notification-bell" type="button" aria-expanded={open} aria-label={unread ? `Avisos: ${unread} sin leer` : "Avisos"} onClick={() => { setOpen(!open); if (!open) void load(); }}>
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path d="M12 3a6 6 0 0 0-6 6v3.6L4.3 15.4A1 1 0 0 0 5.1 17h13.8a1 1 0 0 0 .8-1.6L18 12.6V9a6 6 0 0 0-6-6Zm0 18a2.5 2.5 0 0 0 2.4-2h-4.8A2.5 2.5 0 0 0 12 21Z" fill="currentColor" /></svg>
        {unread > 0 && <span className="notification-count">{unread > 9 ? "9+" : unread}</span>}
      </button>
      {open && (
        <div className="notification-panel" role="dialog" aria-label="Avisos">
          <div className="notification-panel-heading">
            <strong>Avisos</strong>
            {unread > 0 && <button className="link-action" type="button" onClick={() => void readAll()}>Marcar todo como leído</button>}
          </div>
          {items.length === 0 ? <p className="list-empty">No tenés avisos.</p> : (
            <ul>
              {items.map((item) => (
                <li key={item.id}>
                  <button type="button" className={item.read ? "" : "unread"} onClick={() => void select(item)}>
                    <strong>{item.title}</strong>
                    {item.body && <span>{item.body}</span>}
                    <small>{when(item.created_at)}</small>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
