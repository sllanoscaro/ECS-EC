# Regresión local y límites de cierre

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
