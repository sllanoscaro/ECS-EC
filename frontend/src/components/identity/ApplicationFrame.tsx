/** Responsive application shell and actual building-time context, populated after hydration. */
"use client";
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import { Navigation, type NavigationLink } from './Navigation';
import { Icon } from './Icon';
import { useSession } from './SessionProvider';
const BuildingTime = createContext<(timezone: string) => void>(() => {});
/** Publish the API-provided timezone to the shared clock without inventing an installation default. */
export function useBuildingTimezone(timezone?: string) {
  const publish = useContext(BuildingTime);
  useEffect(() => { if (timezone) publish(timezone); }, [timezone, publish]);
}
/** Show one grey clock, keeping today's offset separate from historical measurement offsets. */
function FooterClock({ timezone }: { timezone: string | null }) {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => { setNow(new Date()); const timer = setInterval(() => setNow(new Date()), 1000); return () => clearInterval(timer); }, []);
  if (!timezone || !now) return null;
  const time = new Intl.DateTimeFormat('es-CL', { timeZone: timezone, hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' }).format(now);
  const offset = new Intl.DateTimeFormat('en', { timeZone: timezone, timeZoneName: 'longOffset' }).formatToParts(now).find(p => p.type === 'timeZoneName')?.value.replace('GMT', 'UTC');
  return <span>Hora actual <time dateTime={now.toISOString()}>{time}</time><span className="clock-zone"> · {timezone} · {offset}</span></span>;
}
/** Keep desktop collapse and keyboard-dismissable mobile navigation distinct, with one shared footer. */
export function ApplicationFrame({ children, links }: { children: ReactNode; links: NavigationLink[] }) {
  const { status } = useSession();
  const pathname = usePathname();
  const isLogin = pathname?.replace(/\/$/, '') === '/ingreso';
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [timezone, setTimezone] = useState<string | null>(null);
  const menu = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (status !== 'authenticated') { setTimezone(null); setMobileOpen(false); } }, [status]);
  /** Restore focus to the mobile disclosure after keyboard dismissal. */
  function closeMenu() { setMobileOpen(false); menu.current?.focus(); }
  // The public login owns a centered canvas at every session state, including hydration.
  if (isLogin) return <div className="login-frame"><a className="skip-link" href="#login-content">Ir al contenido</a>{children}<footer className="login-footer">ECS-EC · Electro Conforma</footer></div>;
  return <BuildingTime.Provider value={setTimezone}><div className={`app-frame ${collapsed ? 'shell--collapsed' : ''}`} data-mobile-open={mobileOpen} onKeyDown={event => { if (event.key === 'Escape' && mobileOpen) closeMenu(); }}>
    <a className="skip-link" href="#page-content">Ir al contenido</a>
    <header className="mobile-header"><button ref={menu} type="button" className="icon-button" aria-label={mobileOpen ? 'Cerrar menú' : 'Abrir menú'} aria-expanded={mobileOpen} aria-controls="app-navigation" onClick={() => setMobileOpen(value => !value)}><Icon name="menu" /></button><span>Electro Conforma</span></header>
    {mobileOpen && <button className="menu-backdrop" aria-label="Cerrar menú" onClick={closeMenu} tabIndex={-1} />}
    <aside id="app-navigation"><Navigation links={links} collapsed={collapsed} toggle={() => setCollapsed(value => !value)} close={() => setMobileOpen(false)} /></aside>
    <div className="page-column"><div id="page-content" tabIndex={-1}>{children}</div><footer className="app-footer"><span>ECS-EC · Electro Conforma</span>{status === 'authenticated' && <FooterClock timezone={timezone} />}</footer></div>
  </div></BuildingTime.Provider>;
}
