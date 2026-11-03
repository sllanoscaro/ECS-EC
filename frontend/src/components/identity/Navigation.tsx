/** Shared permission-filtered sidebar; visual state never grants server permissions. */
"use client";
import { useState, type MouseEvent } from 'react';
import { usePathname } from 'next/navigation';
import { useSession } from './SessionProvider';
import { Icon } from './Icon';
export type NavigationLink = { href: string; label: string; permission: string };
/** Render registered destinations, own account and durable logout with the current verified session. */
export function Navigation({ links = [], collapsed = false, toggle, close }: { links?: NavigationLink[]; collapsed?: boolean; toggle?: () => void; close?: () => void }) {
  const { status, session, logout } = useSession();
  const pathname = usePathname();
  const [error, setError] = useState('');
  const allowed = session && !session.must_change_password ? links.filter(link => session.permissions.includes(link.permission)) : [];
  /** Resolve consistent decorative icons from installed paths. */
  function icon(href: string) { return href === '/' ? 'dashboard' : href.includes('usuarios') ? 'users' : href.includes('historial') ? 'history' : href.includes('administracion') ? 'settings' : href.includes('consumption') ? 'consumption' : href.includes('reportes') ? 'report' : 'costs'; }
  /** Expand the desktop icon rail on its first activation; open the destination from the expanded panel. */
  function activate(event: MouseEvent<HTMLAnchorElement>) {
    if (collapsed && toggle && window.matchMedia('(min-width:901px)').matches) {
      event.preventDefault(); toggle();
    } else close?.();
  }
  /** Confirm durable revocation; the provider clears private state even on a network failure. */
  async function leave() {
    try { await logout(); window.location.assign('/ingreso/'); }
    catch { setError('No se pudo confirmar el cierre. Ingrese de nuevo para comprobarlo.'); }
  }
  return <nav aria-label="Principal" className="sidebar">
    <div className="brand-row"><a href="/" aria-label="Electro Conforma · inicio"><img src={collapsed ? '/brand/electro-conforma-icon.svg' : '/brand/electro-conforma.svg'} alt="Electro Conforma" className="brand-logo" /></a>{toggle && !collapsed && <button type="button" className="icon-button collapse-button" onClick={toggle} aria-label="Plegar panel lateral" aria-expanded={!collapsed}><Icon name="collapse" /></button>}</div>
    <p className="brand-caption">ECS-EC · Monitoreo eléctrico</p>
    {status === 'loading' ? <p role="status">Comprobando sesión…</p> : !session ? <a className="nav-item" href="/ingreso/"><Icon name="account" /><span>Ingresar</span></a> : <>
      {['Monitoreo', 'Administración'].map(group => {
        const entries = allowed.filter(link => link.href.startsWith('/administracion') === (group === 'Administración'));
        return entries.length ? <div className="nav-group" key={group}><p className="nav-group-label">{group}</p>{entries.map(link => <a key={link.href} href={link.href} title={link.label} onClick={activate} className={`nav-item ${pathname?.replace(/\/$/, '') === link.href.replace(/\/$/, '') ? 'is-active' : ''}`} aria-current={pathname?.replace(/\/$/, '') === link.href.replace(/\/$/, '') ? 'page' : undefined}><Icon name={icon(link.href)} /><span>{link.label}{link.href === "/reportes/" && <small className="upcoming">Próximamente</small>}</span></a>)}</div> : null;
      })}
      <div className="sidebar-account"><a className={`nav-item account-link ${pathname?.replace(/\/$/, '') === '/cuenta' ? 'is-active' : ''}`} href="/cuenta/" aria-label="Mi cuenta" title={session.account?.email} aria-current={pathname?.replace(/\/$/, '') === '/cuenta' ? 'page' : undefined} onClick={activate}><Icon name="account" /><span className="account-details"><strong>{session.account?.email}</strong><small>{session.account?.role === 'operador' ? 'Operador' : 'Administrador técnico'}</small></span></a><button type="button" className="logout-button" aria-label="Salir" title="Cerrar sesión" onClick={leave}><Icon name="logout" /></button></div>
    </>}
    {error && <p role="alert" className="notice notice--error">{error}</p>}
  </nav>;
}
