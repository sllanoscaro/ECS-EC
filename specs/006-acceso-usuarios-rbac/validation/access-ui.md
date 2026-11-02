# Acceso web local

2026-11-02. Playwright/Chromium real contra el monolito, PostgreSQL18 y TLS local
autofirmado en `https://localhost:58446`. US1 de identidad pasa: ambos perfiles renuevan
su contraseña inicial, vuelven a ingresar, usan cookie HttpOnly/Lax/host-only/Secure,
cierran sesión en dos pestañas y ya no pueden reutilizarla. Operador recibe403 en cuentas.
Vencimiento al minuto30 comprobado con reloj inyectado internamente por archivo protegido,
sin endpoint público de reloj/fixtures. La fábrica de pruebas rechaza entornos/base ajenos.

La primera verificación de acceso pasó cinco pruebas Vitest (incluido scaffold) para
proveedor, error de red, limpieza de contraseña, mensaje general, helper de actividad y
retorno seguro. La regresión final pasa12 pruebas en8 archivos, incluidas recargas
automáticas de cuentas/historial con actividad background y acciones explícitas interactive. `next build --webpack`
exporta ingreso/cuenta y `tsc` pasa. El layout monta SessionProvider antes de Navigation.

El primer run conjunto tuvo un fallo de confianza del certificado en el smoke de plataforma;
el escenario de identidad sí pasó. Se configuró confianza de prueba únicamente cuando
hay un reloj local protegido. Este TLS local no acredita US1.8/SC-008 público ni personas.
