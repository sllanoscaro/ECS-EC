# Research: Análisis de costos eléctricos con tarifa BT4.3

**Date**: 2026-11-01. Alcance: diseño técnico y productor real U1; cifras de aceptación sintéticas.

## R1. Stack compartido

**Decision**: Reutilizar Python 3.14/FastAPI, PostgreSQL 18/SQLAlchemy/Psycopg y React/Next exportados del [arquitectura compartida](../../docs/architecture.md); mismos lockfiles, parches fijados al implementar.
**Rationale**: Un módulo adicional del monolito no requiere otro runtime ni gestor.
**Alternatives considered**: Servicio financiero separado o cálculo autoritativo en navegador; añaden límites innecesarios respecto de los datos validados.

## R2. Decimal y redondeo

**Decision**: Cadenas decimales/NUMERIC; construir Decimal desde cadenas y rechazar no finitos/float. Cada perfil declara precisión, quantum, modo y etapa de redondeo por concepto/impuesto. Perfil sintético: precisión 50, quantum CLP `1`, `ROUND_HALF_UP`; no es una norma legal universal. Totales reconcilian conceptos presentados conforme a esa política versionada.
**Rationale**: Precisión y redondeo explícitos permiten repetir importes sin mezcla binaria. [Decimal de Python 3.14](https://docs.python.org/3.14/library/decimal.html).
**Alternatives considered**: float o redondeo solo cosmético; no ofrecen el contrato requerido.

## R3. Perfil BT4.3

**Decision**: Fórmulas de spec-004 y catálogo cerrado de reglas. Registrar fuente normativa/pliego específico y vigencias antes de declarar completo un cálculo real; sin descarga ni interpretación automática de tarifas.
**Rationale**: El [Decreto 5T, secciones 3.4 y 4.8](https://www.cne.cl/wp-content/uploads/2025/08/Decreto-5T-2024-Toma-de-razon.pdf) es el marco citado en la especificación. No determina por sí solo precios, impuestos ni condiciones del suministro concreto; el motor conserva esas referencias y limita el resultado cuando faltan.
**Alternatives considered**: Fijar distribuidora/tasa o ejecutar expresiones libres; no están autorizados.

**Refinamiento I1**: Cada revisión es un calendario completo de segmentos sin solapamientos internos. V1 abierta se sustituye para cálculos nuevos por V2 con tramos antes/después de un cambio; una corrección retroactiva crea V3. Revisiones anteriores y capturas no se modifican; el solapamiento entre revisiones históricas es válido. Resolver una sola revisión publicada al corte. Borradores se guardan sin cambiar selección y publicarlos crea otra revisión. `expected_previous_version_id` se compara con la última guardada bajo bloqueo para impedir publicaciones concurrentes basadas en un estado anterior. Se descarta editar `valid_to` de una revisión ya utilizada o escoger precios de distintas revisiones por fecha.

## R4. Demanda, calendario y ausencias

**Decision**: Bloques completos de 15 minutos usan kWh/0,25 h; dividir únicamente con evidencia exacta. Conservar máximos y cobertura por mes, incluidos máximos iguales de meses diferentes. Historial, punta y vigencias siguen reglas versionadas en zona IANA.
**Rationale**: Frecuencia de recepción no demuestra resolución de medición suficiente.
**Alternatives considered**: Medias horarias, repartir costos entre categorías o rellenar vacíos; contradicen la especificación.

**Refinamiento A1**: El mes de demanda no se deduce por defecto del ciclo o emisión. Usar política versionada/documentada del perfil: regla cerrada parametrizada o evidencia explícita del suministro/ciclo/mes validada contra datos estructurados de referencia, sin interpretar documentos automáticamente. Capturar mes, fuente y versión por revisión del cálculo; contradicción/ausencia limita los cargos dependientes. El caso sintético de la guía fija mes, calendario y ventana histórica para distinguir elecciones de meses diferentes; no prescribe condiciones reales.

## R5. Captura y revisiones

**Decision**: Captura REPEATABLE READ a corte único, cálculo puro y revisión optimista; consultas no mutan el negocio. Preservar valores/versiones para reproducción y aplicar idempotencia por actor/operación/clave.
**Rationale**: Una captura estable durante la transacción no reemplaza la evidencia duradera necesaria después. [Aislamiento PostgreSQL 18](https://www.postgresql.org/docs/18/transaction-iso.html).
**Alternatives considered**: Consultas READ COMMITTED independientes o precios actuales al reproducir; pueden mezclar revisiones.

**Refinamientos U1/C1**: Suministro con revisión positiva y ETag fuerte, GET administrativo para recuperar configuración y PUT condicionado: alta `If-None-Match: *`, edición `If-Match`. Autorizar/reproducir una operación idempotente confirmada antes de comprobar precondiciones de una mutación nueva. Su revisión/datos se copian en la captura. Formularios web explícitos confirman cálculo/recálculo con motivo y comparación de IDs/revisiones elegidos, conservan entradas y reutilizan la clave al reintentar la misma operación. Las consultas y las correcciones de boleta no crean comparaciones automáticamente.

## R6. Evento sin ciclo de dependencias

**Decision**: Resultado fallido y `cost.failed` juntos mediante `audit/events.py`; tras rollback usar transacción nueva válida. Base indisponible no acredita durabilidad. Una insuficiencia prevista no es un fallo técnico.
**Rationale**: El productor funciona sin consumidor 008; el evento es parte de su resultado funcional persistido.
**Alternatives considered**: Callback después de commit, importación de notifications o broker externo; permiten pérdida de identidad o añaden dependencias innecesarias.

## R7. Retención y PDF

**Decision**: 12 meses calendario según spec-002, segunda hora repetida al conservar; extender padres/evidencia hasta el último dependiente protegido. `Costs.read_snapshot` selecciona ciclos cerrados por fin efectivo y conserva comparaciones sobre los mismos pares.
**Rationale**: Una referencia a datos eliminados no basta para reproducir un importe o reporte.
**Alternatives considered**: 365 días, cascadas destructivas o prorrateo de ciclos; no cumplen el dominio.

**Refinamiento A2**: Seleccionar últimas revisiones de cálculo/boleta al corte antes de buscar comparación del par exacto. Si hay ambos recursos sin ella, `missing_for_selected_revisions`, diferencias null y exclusión del contraste agregado; los importes disponibles se conservan. Comparaciones anteriores siguen siendo históricas, sin retroceder recursos ni generar una nueva al leer. Cortes anteriores conservan su selección; el contrato consumidor de 005 adopta la misma regla.

## Resultado

Decisiones técnicas resueltas. Condiciones reales del suministro siguen siendo entradas administrativas obligatorias. El núcleo y el productor requieren implementación; los documentos no acreditan ejecución ni cálculos reales ya validados.
