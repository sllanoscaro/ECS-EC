# Aceptación parcial de spec-001

## Continuación vigente — 2026-11-03

**57/61 tareas completas.** Completadas001:T018/T038/T041/T043/T044/T045/T052/T053/T054.
No hay aceptación integral: T056 espera receptor/adaptador003 y correo008 reales;
T059/personas y T060/VPS se difieren por instrucción del usuario; T061 depende de esos
resultados. No se modificaron checklists ni tareas ajenas. requirements16/16, sin hooks
registrados antes/después (`.specify/extensions.yml` ausente). Selección explícita001.

| Verificación | Resultado observado |
| --- | --- |
| `.venv/bin/pytest backend/tests/unit/consumption backend/tests/contract/consumption backend/tests/integration/consumption -q` |188 aprobadas en39,42s. Incluye pruebas compartidas002, carreras recepción/configuración en ambas órdenes, recuperación, retiro real y límites conservados; sin omisiones. |
| `npm --prefix frontend test -- --maxWorkers=1 --no-file-parallelism` |53 pruebas aprobadas en23 archivos. |
| TypeScript / exportación Next |Ambos aprobados; datos privados se obtienen por API. |
| Playwright `consumption.spec.ts` |Dos perfiles en modo físico y dos en calculado; períodos antes/dentro/después, cruce excluido, offsets y estados/API/gráfico/tabla. |
| Playwright `consumption-detail-states.spec.ts` |Recorrido ampliado real en fixture físico de siete fuentes: incompleto→20, M/6*M, cambios de base/fuente, A→B y error/reintento. |
| Documentación / enlaces / espacios |Docstrings de archivos nuevos comprobados mediante AST; enlaces locales y `git diff --check` verificados. |

PostgreSQL18.3, contenedor exclusivo `ecs001-completion`, loopback55449, bases desechables
terminadas `_test` distintas de aplicación; no se usaron datos reales. La publicación de
fixtures se hace mediante Reception002 y la configuración mediante ConfigurationService001.
Sin nuevas migraciones, dependencias ni modificaciones del emisor007.

El adaptador `consumption/telemetry.py` instrumenta catálogo, detalle y configuración,
correlacionando el UUID generado por el servidor; nunca entradas/correos/cookies ni kWh.
La prueba de terminales falló inicialmente por ausencia de instrumentación y pasó después.
Verificados rechazo de selección, cola007 saturada con pérdidas visibles y fallo técnico
sin afectar consulta/mutación. No emite terminales de recepción/agregados/retención002.
La autorización previa sigue siendo de006; no se duplica su operación de autorización.

Evidencia por historia: [US3](us3.md), [US4](us4.md). Reglas de recepción/configuración
FR-002..006/010 y SC-003 verificadas sobre002 real junto con retirada y límites permanentes;
períodos FR-011..013 y estados FR-014..016/SC-004 cubiertos localmente. Las pruebas previas
US1/US2 y construcción se conservan en [incremento anterior](increment-2026-11-02.md).
FR-019/SC-006 transversal, SC-005 humano y FR-017/018/SC-007 VPS permanecen pendientes.
No se sustituyen con este ensayo local. Ningún resultado certifica PAS600/SFTP ni SMTP.

## Registro histórico anterior

La disponibilidad y cifras siguientes corresponden a sus cortes originales; prevalece
la actualización vigente anterior.

Fecha: 2026-11-02. Base Git `c9f336c14372b6fe8f82a0a66038f55c0fb1122a`;
cambios de esta ejecución sin commit. **23/61 tareas completas; aceptación funcional
integral pendiente.** [Prerrequisitos](prerequisites.md), [base/reglas](foundations.md).

## Resultados observados

| Comprobación | Resultado y alcance |
| --- | --- |
| Backend completo | `uv run --locked pytest --cov=ecs_ec --cov-report=term-missing -q`: 214 aprobadas, 5 omitidas; cobertura global90%. PostgreSQL real y TEST_DATABASE_URL explícita separada. |
| Omisiones | Cinco escenarios de `test_measurement_semantics.py` esperan fixture/proveedor real 002. No son aceptación de recepción ni sustitutos ejecutados satisfactoriamente. T015 queda pendiente. |
| Frontend completo | `npm --prefix frontend test`: 30 aprobadas en 15 archivos; 18 de consumo, 12 de identidad/plataforma. Componentes de consumo aislados, sin rutas de consumo montadas. |
| TypeScript | `npm --prefix frontend run typecheck`:aprobado. Tipos de consumo generados desde OpenAPI; cadenas exactas, revisiones y cuerpos PUT separados de salidas. |
| Export Next | `npm --prefix frontend run build`:aprobado, páginas estáticas existentes. No se declara MVP de consumo ni prueba de volumen; T057 pendiente. |
| Migraciones | Upgrade desde cero a `cb63a76198be` y `alembic check` sin diferencias. Solo tablas 001 y catálogo fijo; sin almacenamiento 002. |
| Bootstrap real por CLI | `scripts/bootstrap_consumption.py` sobre `ecs_consumption_bootstrap_test`:primera configuración revisión 1; repetición con expected_revision1 conserva revisión 1. No endpoint público ni reloj configurable. |
| Verificaciones de cambios | `git diff --check`, documentación de código y sincronía de tipos generados comprobadas. Ningún checklist marcado. |

Zona/tzdata y versiones en [prerrequisitos](prerequisites.md). Los comandos PostgreSQL
usan las bases y contenedor sintéticos de la ejecución, no credenciales de instalación.
El90% es una medición global observada, no un umbral nuevo de aceptación.

## Evidencia por requisito

| Requisito | Alcance comprobado | Pendiente para aceptación |
| --- | --- | --- |
| FR-001 | Catálogo, instalación versionada, no-op, revisiones locales y fallo cerrado; selector/formulario aislados | Límites reales 002, carrera recepción/configuración, configuración web autorizada |
| FR-002 | DTO/originales y fixtures por subconjunto | Recepción y conservación reales 002 |
| FR-003 | Validación pura completa, unidades/fronteras/revisiones | Resultados durables por registro y lotes mixtos 002 |
| FR-004/005 | Contratos y escenarios de integración redactados | Duplicados/conflictos/exclusión concurrente/eventos con 002 |
| FR-006 | Cálculo candidato exacto/base/segmentos, ausencia de sustitución física | Incorporación temporal, pendientes, recuperación y consulta de datos incorporados 002 |
| FR-007/008/009 | SVG/tabla/selector aislados; misma cifra/intervalo q/M/6*M y procedencia | Una respuesta real, encabezado/período y navegación de consulta |
| FR-010 | Conversión exacta, originales y formato compartido verificados | Comparación desde recepción real hasta UI |
| FR-011/012 | No implementados | Selección temporal, contención, cruces y preservación de rango |
| FR-013 | Validación UTC/microsegundos y etiquetas textuales con zona/offset | Formulario DST, offsets correspondientes a zona y consulta completa |
| FR-014 | Formulario administrativo retiene borrador ante503/conflicto | Estados de detalle, reintento y recuperación del total |
| FR-015 | Gráfico aislado mantiene huecos y distingue cero/positivo; tabla no fabrica filas | Consulta real sin datos/diagnósticos y mismo resultado en ambas vistas |
| FR-016 | No implementado | Hook de clave/generación/abort y flujos A→B con sesión real |
| FR-017/018 | Herramientas y build reutilizados; consumo mantiene módulos internos | Montaje/API/UI real y VPS/HTTPS/red externa con perfiles 006 |
| FR-019 | Configuración PostgreSQL local y pruebas aisladas reproducibles | Integraciones locales 003/007/008 sin sustituirlas por fixtures |

| Criterio | Estado |
| --- | --- |
| SC-001/002 | Componentes y valores conocidos verificados aisladamente; aceptación de extremo a extremo pendiente. |
| SC-003 | Reglas puras aprobadas; recepción/deduplicación/concurrencia durable pendiente de 002. |
| SC-004 | Casos numéricos/vacíos puros cubiertos; estados, fechas y carreras de la aplicación pendientes. |
| SC-005 | Personas no disponibles; T059 pendiente. |
| SC-006 | Proveedores 003/007/008 ausentes; T056 pendiente. |
| SC-007 | VPS no provista; T060 pendiente. |

## Próxima capacidad necesaria

Implementar las tareas propias de [spec-002](../../002-registro-retencion-consumo/tasks.md)
mediante una selección explícita posterior: recepción, estado temporal, almacenamiento,
máximos históricos e incorporación calculada.001 ya entrega el dominio/configuración
que necesita 002, sin exigir completar la aceptación 001. No se ejecutó esa spec aquí.

Después se podrán completar T015/T018..T020, consultas/API y montaje de los componentes,
US3/US4 y pruebas reales de las cuatro historias. T035 debe coordinar el shell
administrativo real de 006. T054/T056 requieren proveedores específicos; personas/VPS
permanecen separados. T058/T061 tienen documentación parcial y **no** se marcan completos.

No hay `.specify/extensions.yml`; no se registraron hooks previos ni posteriores.
