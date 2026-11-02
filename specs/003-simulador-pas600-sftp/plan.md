# Implementation Plan: Simulador PAS600 con publicación SFTP

**Branch**: `003-simulador-pas600-sftp` (identificador devuelto por Spec Kit);
rama Git actual `develop`, sin creación de rama.
**Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)
**Input**: `specs/003-simulador-pas600-sftp/spec.md`.
**Estado**: fases 0 y 1 de diseño y [tareas](tasks.md) generadas; revisión de consistencia, implementación y aceptación pendientes.
Al iniciar la planificación no existía `tasks.md` ni borrador de traslado para esta funcionalidad.

## Contexto compartido del proyecto (ECS-EC)

Aplican [AGENTS.md](../../AGENTS.md), [arquitectura](../../docs/architecture.md),
[hoja de ruta](../../docs/implementation-roadmap.md) y la
[constitución v1.0.0](../../.specify/memory/constitution.md).
009 posee plataforma/auditoría; 006, cuentas/sesiones/autorización; 001/002,
configuración, validación, recepción normalizada, historial y consultas de consumo;
003, fuente de pruebas y adquisición PAS600/SFTP; 007, emisor técnico común;
008, notificaciones. No existe todavía código de aplicación.

## Summary

Crear un simulador independiente y opcional que genere energía de medidores iEM3150
concentrada por un PAS600, en CSV/JSON del perfil documental DOCA0172EN-19. Reproducir
valores/anomalías con algoritmo y semilla fijos, conservar un oráculo local separado y
permitir generación histórica sin red. Las categorías configuradas, incluido un total
medido opcional, determinan qué medidores se serializan; el simulador no calcula CAT-01.

Incorporar un receptor SFTP y adaptador dentro del monolito, con staging, evidencia,
normalización exacta de contadores y llamada al puerto real 002. La convención de
integración es una sesión SFTP por publicación y un EOF limpio después de todos los
CLOSE explícitos confirmados. No se procesan archivos aislados mientras se escribe
el lote. La guía fija formatos, pero no demuestra esa frontera de sesión del firmware;
se requiere verificarla antes de habilitar un PAS600 físico. Se distingue compatibilidad
documental, entrega SFTP y aceptación funcional de mediciones.

## Technical Context

**Language/Version**: CPython 3.14 convencional con GIL, `>=3.14,<3.15`; no cambia
la pila común. El simulador no necesita Node ni frontend/backend para generar localmente.

**Primary Dependencies**: simulador: Pydantic 2, AsyncSSH, simplejson, stdlib csv/Decimal/
SHA-256/zoneinfo/argparse; receptor: AsyncSSH, SQLAlchemy 2/Psycopg 3/Alembic y puertos
009/001/002 del monolito FastAPI 0.162.0. AsyncSSH ofrece cliente y servidor asíncronos;
simplejson evita float al serializar números nativos. Versiones exactas/locks y soporte
instalable se verifican al implementar; este plan no certifica dependencias ejecutadas.
El paquete independiente declara Pydantic2/AsyncSSH/simplejson en `project.dependencies`;
pytest y herramientas de pruebas pertenecen a `dependency-groups.dev`. La validación
US1 incluye instalación y generación con `--no-dev`, después de existir CLI/ejemplos.

**Storage**: simulador: datos nativos inmutables y control/journal locales, sin DB.
Receptor: PostgreSQL 18 y volumen persistente de staging/bytes, manifiestos/lecturas/pares/
resultados propios 003; no recrear tablas ni política de conservación 001/002/009.

**Testing**: pytest para generador, anomalías y CLI; fixtures independientes revisados
contra fabricante; PostgreSQL real para concurrencia/reinicio/resultados; SFTP real
local con host key verificada, errores de canal/CLOSE/EOF y reloj real en aceptación.
Dobles y reloj inyectado solo para reglas/tiempos unitarios, sin acreditar transporte real.
UI/Playwright se consume de 001/002 para comprobar cobertura/total cuando corresponda;
no se crea interfaz web del simulador ni nueva vista de consumo.

**Target Platform**: Linux local, Docker Compose común y futura VPS configurada.
Una imagen/proceso inicial Uvicorn contiene receptor y trabajos en lifespan; listener SFTP
opcional al habilitar adquisición. Herramienta externa ejecutable por separado, nunca
necesaria para que la aplicación funcione. Puerto local 2222, configurable en despliegue.

**Project Type**: herramienta CLI externa de pruebas + módulo de adquisición de
aplicación web monolítica. No worker ni receptor de aplicación desplegado por separado.

**Performance Goals**: la spec no aprueba SLO de latencia/caudal. Probar generación local
de >=12 meses simulados sin esperar tiempo equivalente; medir duración/volumen sin
inventar umbral. Toda publicación/reintento respeta >=900 s reales desde fin anterior.

**Constraints**: perfil fijo, correspondencias explícitas y sin campos ECS-EC en datos
nativos; CSV/JSON lógicamente equivalentes; anomalías exactas/excluyentes con denominador
original; sin ceros implícitos, deltas sobre huecos ni aceptación inferida por SFTP.
Secretos fuera de informes/mediciones. Tres intentos totales iniciales; identidad estable
en reenvíos. Proceso técnico SFTP no equivale a rol humano. Cuotas y timeouts explícitos
según [modelo](data-model.md)/[CLI](contracts/cli.md), sin purga silenciosa de pendientes.

**Scale/Scope**: un publicador PAS600, subconjuntos de siete categorías, una serie por
categoría medida, 15 minutos de muestreo inicial. Historias US1–US4 completas.
N intervalos acumulados requieren N+1 lecturas; la referencia no es consumo. Alcance de
fidelidad: archivos/publicación, sin emular RS485, Modbus ni firmware completo. Generar
doce meses localmente no afirma que el buffer del PAS600 Universal conserve doce meses.

## Constitution Check

Puerta previa a investigación y reevaluación posterior a fase 1:

| Principio / restricción | Antes de fase 0 | Después de fase 1 / evidencia |
| --- | --- | --- |
| I. Monitoreo/fuentes explícitas | PASS: iEM3150/RS485/PAS600 y muestreo identificados por la spec. | PASS de diseño: descriptores/orígenes explícitos, siete categorías opcionales, [perfil](contracts/pas600-profile.md). |
| II. Monolito modular | PASS: herramienta externa de pruebas permitida por alcance; recepción dentro de app. | PASS: adquisición en lifespan 009; no depende del simulador ni de un worker externo. |
| III. Documentación integral | PASS: documentación de archivos, funciones, clases, pruebas y contratos en su cambio de código. | PASS de diseño: [CLI](contracts/cli.md), [recepción](contracts/sftp-reception.md), [guía](quickstart.md), fuentes/algoritmos; revisión de código pendiente. |
| IV. Integridad/trazabilidad | PASS: origen, unidad, zona y anomalías explícitos. | PASS: [modelo](data-model.md), evidencia nativa, contadores/huecos, tasas exactas, idempotencia y retención protegida. |
| V. Visualización verificable | PASS: esta spec no añade vistas de consumo; conserva contratos 001/002. | PASS: contraste prueba origen, cero/ausencia/cobertura y CAT-01 de 001/002, sin totales ficticios del generador. |
| Pila, pruebas y garantías | PASS: adopta arquitectura y criterios SC-001..006, sin garantías nuevas. | PASS de diseño: conformidad independiente y aceptación de red real previstas; ninguna ejecución declarada desde documentación. |

No hay desviaciones constitucionales ni aclaraciones técnicas pendientes para el diseño
local. El gate de instalación física exige identidades y comportamiento de sesión reales;
no se presenta como prueba ya superada. Si el dispositivo no satisface esa frontera,
se debe revisar el contrato antes de habilitar su integración, conservando la spec.

## Project Structure

### Documentation (this feature)

```text
specs/003-simulador-pas600-sftp/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── pas600-profile.md
│   ├── sftp-reception.md
│   └── examples/               # CSV/JSON sintéticos y oráculo documental
└── checklists/requirements.md   # conservar su estado
```

[tasks.md](tasks.md) contiene la lista integral generada con `$speckit-tasks`; todas las
tareas siguen pendientes y su generación no acredita implementación ni aceptación.

### Source Code (repository root, this feature)

Rutas futuras, no archivos existentes ni revisiones de migración reservadas:

```text
tools/pas600_simulator/
├── pyproject.toml, uv.lock, README.md
├── src/pas600_simulator/
│   ├── cli.py, scenario.py, calendar.py, identity.py, generator.py, anomalies.py
│   ├── csv_writer.py, json_writer.py, publication.py
│   └── transport.py, journal.py, report.py, compare.py
├── examples/
└── tests/{unit,contract,fixtures/reference}/
backend/src/ecs_ec/acquisition/
├── config.py, models.py, schemas.py
├── sftp_server.py, staging.py, lifecycle.py
├── csv_reader.py, json_reader.py, mapping.py, counters.py
├── store.py, service.py, evidence.py
└── cli.py                     # mantenimiento/exportación técnica propia
backend/migrations/versions/acquisition_003_initial.py
backend/tests/{unit,integration,contract}/acquisition/
backend/tests/fixtures/pas600/reference/
```

**Structure Decision**: paquete independiente del simulador y módulo `acquisition` con
responsabilidad de transporte/adaptación; no duplicar `consumption`, `core`, identidad
ni auditoría. Registrar listener/trabajo en composición 009 y extender Compose/env/locks
secuencialmente cuando la capacidad propietaria exista. No se modifica el CLI de identidad
006 para poseer funciones de adquisición; el mantenimiento usa módulo propio.

## Phase 0 — Investigación

[research.md](research.md) resuelve perfil/canales, dependencias, sellado, identidad,
reloj/reintentos, acumulados, anomalías y evidencia. Incluye fuentes primarias y
alternativas. La investigación de contratos 001/002/009 fue delegada, como indica la skill,
y se consolidó con la lectura directa de DOCA0172EN-19 y documentación de bibliotecas.

La decisión de frontera SFTP está expresamente limitada al cliente que cumple el contrato;
no atribuir al fabricante garantía de EOF, número total de fragmentos o rename atómico
que no se documenta. IDs sintéticos permiten pruebas; la aceptación de identidades físicas
requiere su descriptor/topología con procedencia.

## Phase 1 — Diseño

1. [data-model.md](data-model.md): entidades locales y persistidas 003, estados, tasas,
   calendario, deltas, idempotencia, durabilidad y plazos.
2. [contracts/pas600-profile.md](contracts/pas600-profile.md): estructuras, nombres,
   tiempos, división, metadatos y casos de conformidad independientes.
3. [contracts/cli.md](contracts/cli.md): comandos/configuración, salida, errores,
   ejemplos a implementar e informe de contraste con estados completo/parcial/no evaluable.
4. [contracts/sftp-reception.md](contracts/sftp-reception.md): identidad técnica,
   sesión/lote, reintentos, `attempt_id`/entrada congelados antes de `Reception.accept`,
   recuperación mediante `Reception.read_attempt`002 y evidencia autorizada. La exportación
   recibe categorías/período/zona/vista e incluye snapshot_id/cutoff_at/selection y resultados
   reales001/002 de cobertura en la misma captura REPEATABLE READ que recepción.
   Cobertura indisponible no se transforma en cero ni en comparación global exitosa.
5. [quickstart.md](quickstart.md): guía reproducible de validación local, escenarios,
   resultados esperados y evidencias por criterio, sin código de implementación.

## Dependencias y secuencia para tareas

| Capacidad propietaria / documento | Uso en 003 / condición |
| --- | --- |
| Plataforma009: [plan](../009-fundaciones-plataforma/plan.md), [contrato](../009-fundaciones-plataforma/contracts/integrations.md) | Scaffold app, DB/UoW/reloj/aniversario/auditoría/lifespan y Compose. Reales antes de migración/receptor integrado; 003 no los implementa como setup propio. |
| Consumo001: [modelo](../001-visualizar-consumo-categorias/data-model.md), [contrato](../001-visualizar-consumo-categorias/contracts/integrations.md) | Catálogo/fuentes/revisiones y validación pura; configurar correspondencias reales. No crear catálogo, bandas de limpieza ni CAT-01 en 003. |
| Historial002: [modelo](../002-registro-retencion-consumo/data-model.md), [recepción](../002-registro-retencion-consumo/contracts/integrations.md) | Puertos Reception.accept/read_attempt con identidad/entrada fija y recuperación exclusiva por intento; límite, dedup y lectura de cobertura con UoW/corte del exportador. Contratos definidos; verificar proveedor real antes de adaptar/aceptar E2E. |
| Acceso006: [spec](../006-acceso-usuarios-rbac/spec.md) | Necesaria para validar vistas/consultas de consumo protegidas; no para generar o transportar desde proceso técnico SFTP. |
| Observabilidad007: [spec](../007-observabilidad-externa/spec.md) | Emisor común al instrumentar adquisición; no exige visores disponibles para procesar. |

Secuencia: descriptores/fixtures independientes y contratos → generador/serializadores
sin red US1 → receptor con staging/sellado, transporte/cadencia y adaptación integrada
US2 → anomalías exactas y defectos por archivo/registro US3 → informe/contraste/parada y
reproducción US4 → validación transversal, documentación y evidencia de criterios.
Las bases del reporte/oráculo y de las anomalías se diseñan desde el generador, aunque
la validación completa esté en US3/US4. Reglas de conversión, selección, calendario y
anomalías requieren pruebas de resultados conocidos antes de su implementación.

Generación local puede avanzar sin capacidades app. Fixtures/dobles de 002 permiten
probar el adaptador, pero no acreditan recepción durable ni SFTP E2E. Las modificaciones
de `backend/src/ecs_ec/main.py`, manifiestos, Compose, migraciones y puertos comunes se
hacen secuencialmente y no transfieren su propiedad.

## Trazabilidad de alcance y aceptación

| Historia / requisitos | Diseño y verificación prevista |
| --- | --- |
| US1; FR-001..006,019,020,022; SC-001/003/006 | Perfil/documentación, descriptor, dos formatos, acumulados 100/104, subconjuntos sin total, >=12 meses local, comparación con fixtures independientes. |
| US2; FR-007..011,020,021; SC-004 | Sesión/lote, CLOSE/EOF, host key/autenticación, 900 s reales desde fin, lento/fallo/reintento/agotamiento, PostgreSQL/consumo real y destino local. |
| US3; FR-012..015,019; SC-002 | Tasas floor sobre N, 100=10+10+10+70, extremos 0/100, rango/duración/unidad, categorías aisladas, archivos ilegibles independientes y efectos de pares acumulados. |
| US4; FR-016..018,020,022; SC-003/005 | Oráculo separado, journal reproducible, correlación de manifiesto/posiciones/pares y resultado 002/cobertura, parada/reanudación y repetición por otra persona sin secretos. |
| Transversal; FR-009/021 y SC-001/004/005 | Idempotencia tras reintento/crash, conflictos/cambios de fuente y timestamp/offset, cero/ausencia, un único lote por categoría, evidencia protegida. |

No se han ejecutado escenarios ni marcado checklists de revisión. La generación de
artefactos no acredita compatibilidad física, limpieza correcta ni aceptación funcional.

## Complexity Tracking

Sin infracciones que justificar. El listener SFTP integrado evita un servicio de aplicación
adicional; staging y ledger son necesarios para demostrar fronteras de entrega y deltas.
La herramienta externa es fuente opcional de pruebas prevista explícitamente por la spec.
