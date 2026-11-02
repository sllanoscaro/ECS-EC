# Implementation Plan: Reportes PDF de una página por período

**Contexto compartido**: [arquitectura](../../docs/architecture.md) y
[hoja de ruta](../../docs/implementation-roadmap.md). La infraestructura común pertenece
a [plataforma009](../009-fundaciones-plataforma/plan.md); esta funcionalidad consume sus capacidades.

**Branch/contexto**: `005-generar-reportes-pdf` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)
**Input**: Spec-005 y decisión U1 de construir el productor real en su propia funcionalidad; el puente de integración de spec-008 solo conecta sus eventos.
**Note**: Diseño previo a implementación; no acredita generación ni pruebas funcionales ejecutadas. La edición documental no modifica la selección persistida de funcionalidad.

## Summary

Generar a solicitud un PDF completo de exactamente una página A4 vertical, con todo el texto >=10 puntos, las siete categorías, evolución de CAT-01, costos por cierre de ciclo, comparación pareada y calidad/procedencia. El documento conserva un corte único y se interpreta sin conexión.

`reports` captura datos reales de consumo y `Costs.read_snapshot`, compone vectores/texto con ReportLab, valida estructura/geometría y publica los bytes solo tras superar verificaciones. PostgreSQL conserva solicitud, captura, resultado, hash y estado. Un executor acotado del monolito realiza la generación sin servicio de PDF separado.

Una operación fallida conserva su resultado funcional y `pdf.failed` en la misma transacción mediante `audit`. La generación no depende del consumidor ni del transporte de notificaciones.

## Technical Context

**Language/Version**: CPython 3.14 convencional y TypeScript; React 19.x/Next.js 16.x exportado estáticamente, Node >=20.9 solo en construcción. Reutilizar el stack/lockfiles de la [arquitectura común](../../docs/architecture.md), implementados por plataforma009.

**Primary Dependencies**: FastAPI 0.162.0, Pydantic 2, SQLAlchemy 2/Psycopg 3 asíncronos y Alembic; ReportLab 5.1.0 y pypdf 6.21.4. Canvas/gráficos vectoriales, fuente TTF Unicode incrustada con licencia redistribuible registrada. Fijar transitivas/fuentes/imagen y comprobar instalación real bajo Python 3.14 en implementación.

**Storage**: PostgreSQL 18; captura JSONB tipada y bytes PDF en BYTEA interno, SHA-256 y fechas UTC con zona IANA. Política de diseño: solicitud, captura y resultado se conservan al menos 12 meses calendario, sin eliminar evidencia todavía referenciada por registros protegidos.

**Testing**: pytest/HTTPX y PostgreSQL real; pypdf para parseo, página, MediaBox, texto y fuentes; manifiesto geométrico propio para tamaños/colisiones, más revisión visual de impresión al 100 %. Vitest/Testing Library/Playwright. Extraer texto no prueba por sí solo ausencia de recortes/solapamientos.

**Target Platform**: Linux Docker Compose local y VPS HTTPS posterior; una imagen FastAPI con exportación Next y sin navegador ni Node en ejecución.

**Project Type**: Módulo web monolítico con generación interna y resultados durables.

**Performance Goals**: No hay SLO de renderizado/volumen en la spec. Medir tiempo/memoria en casos de referencia sin inventar garantías. SC-006 exige nueve de diez tareas con personas representativas en <=2 minutos.

**Constraints**: Exactamente una página A4 vertical 210×297 mm; texto >=10 pt en tablas/ejes/notas/leyendas; sin anexos, omisiones esenciales ni interpolación. Corte único y fuentes versionadas. kWh/Decimal; moneda/impuestos/redondeo de spec-004. CAT-01 calculada no habilita costo energético completo del suministro.

**Scale/Scope**: Un edificio, siete categorías, tres escalas. Gráfico diario por horas reales/desfases, mensual por días y anual por meses. No se exportan todas las mediciones ni rangos arbitrarios. Síntesis financiera agrupada por moneda/base compatible, con alcance de ciclos/pares.

## Constitution Check

*Evaluación previa y posterior; PASS acredita diseño, no código ejecutado.*

| Principio | Previo | Posterior y evidencia |
| --- | --- | --- |
| I. Monitoreo eléctrico | PASS | Consumo, costos/calidad ya definidos; fuentes/frecuencias no se inventan. |
| II. Monolito modular | PASS | Puertos internos y executor dentro de una unidad de aplicación. |
| III. Documentación integral | PASS | Cada archivo/contrato/cálculo/componente/prueba se documenta junto al cambio; guía reproducible prevista. |
| IV. Integridad y trazabilidad | PASS | Captura coherente, revisiones/corte, ausencia explícita, historial inmutable y evento transaccional. |
| V. Visualización verificable | PASS | Magnitud/unidad/período, calidad/origen visibles; comparación con consultas y preflight independiente. |
| Verificación de cálculos | PASS | Valores conocidos y ausencias para selección, agregación financiera y presentación. |

Sin excepciones constitucionales. Las bibliotecas PDF son dependencias del monolito.

## Project Structure

### Documentation (this feature)

```text
specs/005-generar-reportes-pdf/
  plan.md research.md data-model.md quickstart.md tasks.md
  contracts/http.md contracts/integrations.md contracts/ui.md
```

### Source Code (repository root, estructura propuesta)

```text
backend/src/ecs_ec/reports/
  api.py schemas.py models.py repository.py services.py calendar.py ports.py
  snapshots.py content.py renderer.py layout.py charts.py preflight.py worker.py
  energy_table.py financial_summary.py formatting.py quality.py fonts/README.md
backend/src/ecs_ec/audit/{models.py,events.py}
backend/migrations/versions/reports_initial.py
backend/tests/{unit,integration,contract}/reports/
frontend/src/app/reportes/page.tsx
frontend/src/components/reports/
frontend/src/lib/api/reports.ts
frontend/tests/{unit,e2e}/
```

**Structure Decision**: Reutilizar `core`, `identity`, `consumption`, `costs`, `audit` y el emisor común de `observability` de spec-007; `reports` no reproduce recepción ni fórmulas tarifarias. Los directorios son propuestos, no implementación existente.

## Phase 0: Research

[research.md](research.md) resuelve motor PDF, validación, captura coherente y persistencia. Los hechos técnicos nuevos se contrastan con documentación primaria; no se afirma validación de ejecución. Las decisiones funcionales proceden de la spec y no quedan decisiones técnicas bloqueantes.

## Phase 1: Design & Contracts

1. Validar sesión/permisos actuales y selección. Una transacción REPEATABLE READ captura consumo, calidad y costos mediante la misma unidad de trabajo y corte fijado al inicio; persistir captura inmutable antes de responder.
2. Un supervisor interno reclama pendientes exclusivamente, marca `generando` y renderiza fuera del event loop/transacción. Dos plazas iniciales son configuración operativa, no garantía de volumen.
3. Componer seis bandas dentro de márgenes de 10 mm: identificación, tabla de siete categorías, evolución CAT-01, costos por cierres, contraste pareado y calidad/procedencia. Usar presupuesto geométrico/reflujo y agrupación semántica; jamás bajar de 10 pt, omitir advertencias o añadir página. Si no cabe, fallar con motivo funcional.
4. Preflight sobre bytes reales: una página A4, texto obligatorio, fuentes/tamaños y manifiesto geométrico. Conservar todos los bloques del gráfico y vacíos; seleccionar etiquetas legibles no elimina datos. Desambiguar horas repetidas con desfase.
5. Publicar binario íntegro, longitud/hash y estado `generado` en una transacción. Ante fallo descartar bytes parciales y persistir `fallido` + `pdf.failed` juntos. Un error técnico no se confunde con reporte válido sin datos.
6. Reconciliar `generando` interrumpidos a fallo durable al iniciar; pendientes conservan captura. Nueva petición de reintento crea otra identificación; misma clave HTTP devuelve la petición original.
7. Descarga con permiso actual, binario interno y sin URL pública. Valores iguales al mismo corte producen contenido funcional igual aunque emisión/identidad difieran. La generación no modifica las fuentes.
8. Capturar en filas y bloques `source_mode` y `provenance_segments` del productor 001/002, incluidos modo mixto, límites, fuentes, revisiones y bases. Sintetizar su alcance visible sin recalcular el total ni tratar todo CAT-01 como medición física. Conservar `comparison_status` financiero: revisión de cálculo/boleta sin comparación exacta muestra contraste pendiente, diferencias nulas y exclusión del agregado, manteniendo intactas capturas anteriores.
9. Instrumentar solicitud y executor con el emisor común de spec-007: captura, espera, render, preflight, publicación y descarga. Propagar correlación técnica fuera del contenido/hash funcional; emitir logs saneados y trazas con resultados distinguibles. Definir conteos y duración mediante LogQL según [integrations.md](contracts/integrations.md), con dimensiones acotadas y emisión desacoplada de red/commits funcionales.

### Dependencias reales y entregables U1

- Prerrequisitos: capacidades reales de `core`, identidad/sesiones spec-006, consumo/calidad specs-001/002 y `audit`/EventWriter. Resolverlas por capacidad con plataforma009 y specs-001/002/006, sin depender del planificador, consumidor o SMTP de spec-008. No crear un ciclo 005 → consumidor008 → 005.
- La instrumentación de reports consume el emisor común de [spec-007](../007-observabilidad-externa/spec.md), previsto en `backend/src/ecs_ec/observability/logging.py` y `tracing.py`; su [investigación trasladada](../007-observabilidad-externa/research.md) conserva la decisión Loguru/OTel y métricas LogQL. El emisor real es prerrequisito de esta integración y del checkpoint US1; registrar su ausencia en la spec propietaria sin implementarlo dentro de PDF. Los visores y recolectores pueden estar caídos sin impedir generación, descarga ni confirmaciones funcionales; no se requiere completar toda spec-007.
- Spec-004 entrega `Costs.read_snapshot(building_id,start,end,cutoff_at,principal)` con ciclos cerrados por fin efectivo, revisiones vigentes, desglose/moneda/base, limitaciones y pares comparables. [Contrato productor](../004-costos-tarifa-bt43/contracts/integrations.md). Se ejecuta en la misma unidad de trabajo de la captura energética.
- Esta spec entrega generación real, resultado/binario persistido y evento independiente `pdf.failed`, según [integrations.md](contracts/integrations.md). Los dobles solo acreditan pruebas aisladas; aceptación integral exige productores reales.
- [http.md](contracts/http.md), [ui.md](contracts/ui.md) y [quickstart.md](quickstart.md) definen acceso y validación, sin exigir notificaciones instaladas.

### Cobertura y fases

| Historia | Requisitos | Diseño |
| --- | --- | --- |
| US1, P1 | FR-001..003, 017, 020..022 | Selección, captura, generación/descarga y fallo durable; instrumentación propia conforme a la hoja de ruta y spec-007. |
| US2, P1 | FR-004..009, 018, 021 | Composición una página con tabla y gráfico, incluida procedencia mixta por segmentos. |
| US3, P1 | FR-010..015 | Ciclos/costos, subtotal disponible, comparación pareada y contraste pendiente de las revisiones seleccionadas. |
| US4, P2 | FR-008..009, 016..019, 022 | Calidad, procedencia, detalle retirado y coherencia concurrente. |

El primer incremento incorpora desde el principio todas las secciones obligatorias y estados básicos; las historias posteriores profundizan sus casos. Ningún MVP publica un documento que suprima secciones o incumpla página/tamaño. SC-001..005 necesitan PDFs reales; SC-006 necesita participantes.

## Complexity Tracking

Sin violaciones. Captura y binario en una base evitan confirmación distribuida entre almacenamiento y estado funcional.
