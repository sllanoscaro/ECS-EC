/** Small consistent stroke icons; decorative by default because controls carry text labels. */
export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, string> = {
    dashboard: 'M4 20V12h3v8M11 20V7h3v13M18 20V3h3v17',
    consumption: 'M13 2 4 14h7l-1 8 10-13h-7l1-7Z',
    costs: 'M4 6c0-4 16-4 16 0s-16 4-16 0Zm0 0v12c0 4 16 4 16 0V6M4 12c0 4 16 4 16 0',
    users: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M16 4a4 4 0 0 1 0 8M22 21v-2a4 4 0 0 0-3-4M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
    history: 'M3 11a9 9 0 1 1 3 8M3 4v7h7M12 7v5l3 2',
    settings: 'M4 4h6v6H4zM14 14h6v6h-6zM14 4h6v6h-6zM4 14h6v6H4z',
    report: 'M5 3h9l5 5v13H5V3Zm9 0v6h5M8 13h8M8 17h6',
    account: 'M20 21a8 8 0 0 0-16 0M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
    logout: 'M9 3H3v18h6M9 12h13m-5-5 5 5-5 5',
    collapse: 'm14 5-7 7 7 7', menu: 'M3 6h18M3 12h18M3 18h18',
    refresh: 'M20 7a9 9 0 0 0-15-2L2 8m0-6v6h6M4 17a9 9 0 0 0 15 2l3-3m0 6v-6h-6',
    warning: 'M12 3 1 21h22L12 3Zm0 6v5m0 3v1',
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] ?? paths.settings} /></svg>;
}
