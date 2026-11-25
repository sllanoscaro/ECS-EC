# Aceptación local008 —2026-11-25

Alcance técnico local completado: **90/92 tareas**. US1–US4, integración de productores
reales, SMTP local, historial/reenvíos, conservación e instrumentación están verificadas.
008:T090/personas y008:T091/VPS permanecen pendientes. La checklist adicional conserva
sus36 marcadores sin revisar, conforme a la autorización expresa del usuario.

Resultados observados, sin sumar ejecuciones repetidas como pruebas distintas:

- Regresión backend: **844 aprobadas,52 omitidas,5 deseleccionadas y1 fallo de arranque
 de Playwright**,377,94s. El trabajador Node24.22 terminó con SIGSEGV antes de iniciar
 el escenario periódico. Ambos arneses de navegador pasaron después con Node24.21:
 **2 aprobados en91,75s**, cubriendo los cinco escenarios reales. Hay845 casos únicos
 con ejecución aprobada entre esos cortes; no se presenta la regresión como una sola
 ejecución sin fallos. Los128 casos008 tienen ejecución aprobada; su prueba optativa
 del stack se verifica separadamente.
- Las52 omisiones pertenecen a007:47 requieren `OBS_TEST_ROOT` explícito y5 requieren
 sus filesystems físicos/trabajador. No se reutilizó el ensayo de retención activo.
 La integración008 sí se ejecutó por separado con Alloy/Loki/Jaeger/Grafana reales,
 TLS/Basic, revocación y denegación de escritura/UID ajeno.
- 101 Vitest aprobadas,34 archivos,28,39s con un worker; typecheck y exportación Next
 aprobados. Un arranque paralelo previo produjo SIGSEGV del worker; la ejecución
 serial completó sin error. No se atribuyó ese fallo a una prueba aprobada.
- Cinco escenarios Playwright reales: configuración, denegación, dos cortes periódicos,
 total calculado urgente y recuperación/reenvío/ámbito propio. El arnés periódico mide
 dos cortes reales de un minuto; el urgente usa reloj privado controlado.
- Perfiles de20 periódicas y40 mixtas con SystemClock/Mailpit. En la última medición
 mixta supervisada: **40/40 aceptadas**, primer intento máximo3,718829s, duración
 máxima0,059385s. El supervisor usa ciclos5s y cuatro plazas; la prueba de equidad
 coencolada se registra separada. Consultar los valores completos en los artefactos.
- Migración limpia/rollback vacío/reinstalación y rechazo atómico de pérdida de evidencia;
 comprobados hasta el head `notifications_008_consumed`. El rechazo conserva head,
 esquema y evidencia. No se aplicó rollback sobre datos del usuario.
- Los13 casos JavaScript del conciliador aprobaron. Ruff F/I y formato aprobaron;
 76 archivos Python propios tienen docstrings de módulo/clase/función. Los contratos
 empaquetados007/008 coinciden byte a byte y los tipos008 se regeneran sin diferencias.
 Los enlaces Markdown locales y `git diff --check` aprobaron.

Dos expectativas antiguas de pruebas se corrigieron: identidad comprueba sus cinco
tablas junto a otros propietarios y la prueba de configuración recibe explícitamente
su URL sintética. Un corte intermedio falló en una publicación SFTP del simulador;
su repetición seleccionada8/8 y el caso en la regresión posterior aprobaron, sin
añadir reintentos ni cambiar el simulador. Su causa no quedó determinada. El cambio
de Node es una alternativa de ejecución comprobada; no demuestra la causa del SIGSEGV.

Comandos de las ejecuciones, sobre basePostgreSQL18 exclusiva cuyo nombre termina en
`_test`, distinta de la aplicación y con capturador Mailpit exclusivo:

Subcomandos ejecutados con configuración test privada; las credenciales no se incluyen.
Los arneses Playwright se ejecutaron con la exportación ya construida y Mailpit activo:

```sh
uv sync --locked --group dev
.venv/bin/pytest backend/tests -q
.venv/bin/pytest backend/tests/integration/notifications/test_browser.py backend/tests/integration/notifications/test_urgent_browser.py -q
npm --prefix frontend run typecheck
npm --prefix frontend test -- --maxWorkers=1
npm --prefix frontend run build
node --test deploy/observability/grafana/plugins/ecsec-coverage-panel/reconcile.test.mjs
```

Los arneses `test_browser.py`/`test_urgent_browser.py` arrancan la aplicación real y
Playwright sobre la exportación indicada explícitamente. La prueba del stack exige
su raíz test privada/puerto/proyecto propios; no selecciona un entorno implícito.
Credenciales y material TLS permanecen fuera del repositorio.

Versiones verificadas: CPython3.14.4, PostgreSQL18.3, Mailpit1.33.1, tzdata2026.6,
FastAPI0.162.0, SQLAlchemy2.0.55, Psycopg3.3.6, pytest9.2.0 y HTTPX0.28.1.
Frontend usa Next16.4.5/React19.3.1; construcción y Vitest con Node24.22.0,
repetición de navegador con Node24.21.0. El procedimiento reproducible y las variables
de habilitación están en el [quickstart](../quickstart.md).

[Resultados saneados](artifacts/acceptance-results.json),
[perfil mixto supervisado](artifacts/mixed40-supervised.json) y
[equidad](artifacts/mixed40-fairness.json) conservan referencias, tiempos y recursos.
Los datos eléctricos/cuentas son sintéticos; su incorporación y los productores son
reales. El perfil usa el host compartido sin CPU/memoria reservadas. La aceptación
SMTP local no acredita buzón, lectura ni relay externo. La automatización no acredita
usabilidad con participantes.

[US1](us1.md),[US2](us2.md),[US3](us3.md),[US4](us4.md),
[observabilidad](observability.md),[trazabilidad](coverage.md),
[usabilidad pendiente](usability.md) y[VPS pendiente](vps.md).

Se preservan la selección Spec Kit003, los cambios anteriores, contenedores originales
y el ensayo físico007 de24h/GC. No se ejecuta automáticamente el paso6, no se marcan
checklists y no hay commit o despliegue de producción implícito.

Al terminar se retiraron únicamente los contenedores de prueba `ecs008-step5-db`
y `ecs008-step5-mailpit`, tras verificar su etiqueta de propiedad. El stack temporal
`ecs008-step5-observe` ya estaba detenido y retirado. El trabajador de retención007
y los contenedores originales siguen activos. Los artefactos saneados permanecen aquí;
repetir pruebas requiere preparar otra vez sus recursos test exclusivos.
