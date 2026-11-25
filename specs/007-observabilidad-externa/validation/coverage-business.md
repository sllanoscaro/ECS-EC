# Cobertura real004/005/006 y configuración — paso4

Corte2026-11-24. Integración de costos004 autorizada expresamente por el usuario:
«Sí, integrar costos004». No se transfieren propiedad de costos, cuentas ni auditoría.
Pruebas: `backend/tests/integration/observability/test_costs_reports.py`,
`test_identity_administration.py` y casos propietarios importados allí. [Resultados](step4.md).

| Operación | Resultado y contraste |
| --- | --- |
| cost.calculate | Cálculo completo y fallo durable real: ambos pueden responder201; execution_state=fallido determina ERROR/calculation_failed. Capture/calculate/commit se observan donde ocurren, no por interpretar HTTP como éxito. |
| cost.compare / cost.query | Boleta y cálculo reales, contraste y consultas/listados; payload financiero queda solo en004. Replay no repite trabajo ni etapa calculate. |
| report.generate | Admisión durable, captura/espera/render/preflight/publicación y descarga real. Tres fallos controlados comparan report.completed con evento funcional005/009 confirmado; rechazo previo no inventa generación. |
| report.query / report.download | Consulta y PDF real con permisos; un terminal de lectura/entrega, nunca nueva generación. |
| identity.authenticate / authorize / session | Ingreso válido/inválido, decisiones de acceso, sesiones, cambio/recuperación, concurrencia y falla segura en006 real. Decisión authorize separada del objetivo. |
| administration.change | Catálogo001, suministro/calendario/boleta004 y cuentas006 reales. Diez peticiones de suministro/perfil producen diez terminales objetivo con UUID distintos. Rechazos framework/permisos anteriores al propietario también son visibles una vez. |
| administration.query | Historial006: administrador200/operador403, un terminal objetivo y autorización separada. Ningún permiso Programador en006. |

La frontera ASGI usa un registro cerrado de rutas existentes y presta el contexto una
vez a la instrumentación propietaria. No crea otra API ni interpreta cuerpos/cabeceras
públicas como parentesco confiable. Al leer historial006→costos004 comparte la operación
administrativa, evitando doble terminal. Denegaciones previas tienen resultado esperado.
Rollback después de escribir evidencia004 comprueba cero cálculo/cero auditoría huérfana
y un terminal técnico inesperado, sin etapa commit exitosa. FunctionalAudit/Event009
conservan finalidad/transacción; la telemetría no los sustituye.

E2E `frontend/tests/e2e/observability-diagnosis.spec.ts`: agregado observado→terminal→
traza Jaeger realmente consultable→filtro de otras ejecuciones. La traza abre pestaña
propia por el router de Grafana. E2E es validación técnica, no SC-008 con personas.
