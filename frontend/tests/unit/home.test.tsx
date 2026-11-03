/** The landing page exposes its title but never mounts daily private reads without a session. */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';
import Home from '../../src/app/page';
vi.mock('../../src/components/identity/SessionProvider', () => ({
  SessionGuard: () => <p>Debe <a href="/ingreso/">iniciar sesión</a>.</p>,
}));
test('offers login instead of embedding daily measurements in the landing page', () => {
  /** Anonymous static rendering contains no fake or installation-specific energy value. */
  render(<Home />);
  expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Resumen del edificio');
  expect(screen.getByRole('link', { name: 'iniciar sesión' }).getAttribute('href')).toBe('/ingreso/');
  expect(screen.queryByText(/kWh/)).toBeNull();
});
