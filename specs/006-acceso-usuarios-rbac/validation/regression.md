# Regresión local y límites de cierre

## Paso3 — 2026-11-24

006:T084 completa. Backend final: **672 aprobadas,31 omitidas,3 deseleccionadas en232,09s**.
[JUnit de la ejecución](artifacts/step3-backend.xml). Después se amplió la clasificación de rechazos técnicos002 y la observación de fallos
del supervisor003; regresión focal final: **54 aprobadas,3 deseleccionadas en74,05s**
(adquisición completa, telemetría002 y contrato de permisos/OpenAPI006).
Frontend: **91 pruebas/30 archivos**, typecheck y exportación estática aprobados.
Playwright: **3 escenarios identity.spec.ts** pasan juntos desde una base nueva (16,2s),
**2 costos**, **4 boletas/perfiles**, **1 historial financiero**. Los recorridos propietarios
se ejecutaron separadamente según sus prerrequisitos; no requieren respuestas simuladas.

Comandos desde raíz, con `TEST_DATABASE_URL` apuntando a PostgreSQL18.3 privado y diferente
de la base configurada de la aplicación:

```sh
.venv/bin/pytest -q --tb=short --junitxml=/tmp/ecs-step3-final-backend.xml
.venv/bin/pytest -q backend/tests/integration/acquisition backend/tests/integration/consumption/test_history_telemetry.py backend/tests/contract/identity/test_permission_matrix.py
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
.venv/bin/python scripts/check_identity_documentation.py
```

Browser: preparar base vacía separada `*_test`, migrar y usar
`scripts/seed_costs_reference.py --password-file /ruta/privada0600`; servidor
`backend.tests.run_identity_browser:create_test_app` con `ENVIRONMENT=test`, identidad
habilitada, edificio99, origen loopback y `WEB_DIRECTORY=frontend/out`. El archivo
`IDENTITY_E2E_CLOCK_FILE` privado empieza en0. Ejecutar con `IDENTITY_E2E_STEP3=1`,
`IDENTITY_E2E_PASSWORD_FILE`, `E2E_BASE_URL` y Playwright `identity.spec.ts --workers=1`.
Los escenarios financieros requieren las cuentas renovadas, `COSTS_E2E=1`,
`COSTS_E2E_RENEWED=1`, y orden costos→boletas/perfiles→historial; los dos primeros
escenarios006 crean su cálculo de referencia por UI. No se añaden rutas de fixture públicas.

Revisión006: **49 archivos Python** sin módulos/clases/funciones sin docstring; imports
no usados eliminados, fachada de permisos preservada. El chequeo documental se añadió
al workflow existente, limitado a006; CI remoto no ejecutado. Contrato contra OpenAPI
real verifica rutas, campos públicos y dependencias de autorización mediante los contextos
de ruta de la versión instalada de FastAPI. Se revisaron TSDoc, contratos de actividad,
retorno PDF y la normalización de resultados004 en [HTTP006](../contracts/http.md).

Migraciones: upgrade desde vacío, check sin diferencias; downgrade de las dos columnas
nuevas hasta `reports_005_initial`, upgrade a head y nuevo check aprobados. El intento de
bajar hasta base se rechaza por la protección destructiva existente de004 y revierte
atómicamente; no se modificó esa protección ni la base de aplicación.

Las31 omisiones son007:30 exigen su stack externo explícito `OBS_TEST_ROOT`; una conserva
la matriz gateway/PDF007:T022 pendiente del paso4. Su mensaje anterior afirmaba que005
no existía; se corrigió porque el proveedor real y la matriz006 ya están comprobados.
Las3 deseleccionadas son los ensayos opt-in003 de cadencia real900s y restauración.
Ninguna sustituye pruebas de este paso ni acredita personas/VPS/aceptación integral.

Hubo interrupciones nativas de CPython3.14.4/Node24.22.0 en ejecuciones iniciales; esas
corridas no se contaron. La regresión backend final pasó completa con el runtime normal.
Para aislar las interrupciones del runner de navegador se ejecutó directamente
`node --jitless node_modules/@playwright/test/cli.js test ... --workers=1` desde frontend;
los tres escenarios finales pasan desde base nueva. No se alteró la aplicación para ello.
Contenedor/bases/servidor temporales retirados al terminar; servicios previos preservados.

## Cortes históricos

## Continuación paso1 — 2026-11-23

Estado75/87. Nuevas verificaciones006:T069/T077 con SFTP003 real, dentro de las15
pruebas focales aprobadas de este incremento. [Regresión y alcance](technical-separation.md).
T084 sigue pendiente de historias/integraciones completas; no se reejecutan frontend,
PDF, personas ni VPS. Los resultados siguientes conservan sus cortes anteriores.

## Continuación local — 2026-11-03

Identidad006 ampliada con lecturas reales001/002/004, autorización administrativa
explícita e instrumentación propia con emisor007. Estado73/87;006:T084 permanece
pendiente de sus historias/integraciones completas (PDF/SFTP), no por ausencia del emisor.
No se añadieron checks redundantes a CI: el workflow existente descubre las nuevas
pruebas006 dentro de su ejecución general de pytest. No se ejecutó CI remoto.

| Comprobación actual | Resultado |
| --- | --- |
| Suite focal de identidad y contratos001/002/004 |143 aprobadas en32,60s antes de los dos últimos casos; nueva ejecución focal de los tres archivos de integración:12 aprobadas en7,01s. |
| Frontend |53 pruebas en23 archivos; typecheck y exportación estática aprobados. |
| Playwright `identity.spec.ts` |Un recorrido conjunto aprobado en4,2s: ambos perfiles, renovación, cuentas, historial, cierre entre pestañas y expiración por reloj privado. HTTP loopback explícito; no acredita VPS ni la matriz PDF. |
| Documentación Python006 |AST de45 archivos propios/backend de identidad, fachada de seguridad, CLI y pruebas:sin módulos/clases/funciones sin docstring. Nuevas funciones documentadas. |
| Contratos/OpenAPI |Las suites contract006 y proveedores reales pasan con las dependencias actuales; no cambian DTO, errores ni rutas públicas. El snapshot inferior conserva su corte original. |
| Dependencias/setup |Locks y migraciones sin cambios. Ignores Python/npm/Docker/secretos/salidas existentes comprobados; frontend privado, sin ESLint/Prettier/Terraform/Helm que requieran ignores adicionales. |

La regresión amplia inicial tuvo427 aprobadas y un fallo: la prueba de telemetría001
contaba terminales de todos los productores del emisor compartido. Ahora filtra
`source_module=consumption` para conservar el contrato de su operación, sin suprimir las
nuevas señales006. La repetición final pasa428/428 en69,01s, sin omisiones; comando y alcance en [aceptación](acceptance.md).

PostgreSQL18.3 desechable `ecs006-completion`, loopback55449. Base de suites
`ecs006_completion_test` y de navegador `ecs006_browser_test`, distintas de aplicación;
credenciales sintéticas efímeras y archivos0600. CLI real con pseudo-TTY forma parte de
la regresión de identidad. No hay aceptación SFTP/PDF/personas/VPS.

## Registro histórico — 2026-11-02

Lo siguiente conserva herramientas y resultados originales; prevalece el estado anterior.

2026-11-02. La regresión local de plataforma+006 se ejecutó contra PostgreSQL18.3 real,
DB `ecs_identity_test` en55446. Solo datos sintéticos; ningún destino de producción.

| Comprobación | Resultado |
| --- | --- |
| `uv sync --locked --group dev` | Correcto, 52 paquetes resueltos en lock. |
| `pytest backend/tests --cov=ecs_ec --cov-report=term-missing` | Suite completa aprobada; resumen final en aceptación. |
| `alembic ... check` | Sin nuevas operaciones; modelos coinciden con el esquema real. |
| `npm ci`, Vitest | Correctos;12 pruebas en8 archivos. |
| `next build --webpack`, `tsc --noEmit` | Correctos; incluyen tests/configuración TypeScript y exportación estática. |
| Playwright/Chromium con TLS local |2 escenarios conjuntos pasan en4.9s, incluyendo acceso, cuentas e historial. |
| `docker compose ... build/up --wait app` | Correcto desde volumen nuevo; DB→migración→salud de app. |
| Imagen final | `sha256:29f908a071982431481ddbdc291784e415fca161e027d7ca8c234f964abc587e`. |
| Runtime | CPython3.14.4, UID10001, Argon2 real correcto, sin Node ni módulos de test. |
| Export/secretos | No contiene claves HMAC reales de prueba; los campos privados se obtienen por API. |
| OpenAPI | [Generado](openapi.json):9 rutas, contratos DTO/Problem, cookie/presesión y CSRF documentados. |
| Documentación | AST de módulos/clases/funciones Python y revisión de TSDoc; sin imports a notificaciones. |

El workflow existente agrega solo checks/fixtures006, con claves efímeras y contraseña por
archivo0600. Se separaron puertos de Compose de la base de pytest. No se ejecutó un job
remoto ni se publicó código. En CI el navegador usa reloj normal y HTTP loopback explícito;
la validación local adicional usa TLS y reloj por archivo protegido fuera de la aplicación
normal, sin endpoint público para modificar hora/cuentas.

T084 permanece pendiente por su prerrequisito de instrumentación007 real: lo anterior
acredita regresión local de las capacidades disponibles, no la integración G5. Las
pruebas de proveedores ausentes no se reemplazaron por stubs ni skips aprobados.

Las pruebas de reactivación de cuentas e historial verifican que las recargas automáticas
usan `background`. Solo la navegación inicial y acciones explícitas como filtros/Consultar
usan `interactive`, evitando prolongar la inactividad por cadenas de revalidación.

Al finalizar se detuvieron el servidor TLS y los contenedores creados para esta validación.
Los volúmenes y bases sintéticas se conservaron; no se modificaron otros proyectos.
