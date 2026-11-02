# Recepción interna y fundaciones verificadas

Fecha: 2026-11-02. Base Git `cb5134494bd9032ab50bd47f085b052518e04bbb` más
cambios locales de este incremento, sin commit. [Prerrequisitos](prerequisites.md),
[aceptación parcial](acceptance.md). Fixtures internos, sin PAS600/SFTP.

## Resultado observado

La regresión final completa pasó: **261 pruebas backend**, incluidas las pruebas de
001 que antes esperaban `consumption_reception_environment`. PostgreSQL 18.3 real,
CPython 3.14.4, tzdata 2026.6; zona sintética America/Santiago y casos de calendario
America/New_York/Australia/Lord_Howe/UTC. No SQLite ni dobles de almacenamiento.

| Tareas 002 / requisito | Evidencia y resultado |
| --- | --- |
| T003/T015, FR-001..005, SC-001 | Siete fuentes físicas aceptadas en el mismo instante; rechazo a899s, aceptación a900s, lotes históricos, independencia por categoría y retroceso de reloj detectado. `test_reception_limits.py`. |
| T014/T020/T021, FR-004..006 | Mismo intento devuelve accepted/too_early originales; nueva entrada da attempt_payload_conflict, nuevo intento reevalúa. Lookup autorizado, readonly, inexistencia distinta de DB caída; tipos numéricos/textuales no se confunden. `test_reception_contract.py`. |
| T016/T019, FR-005/006 | Equivalencias Wh/kWh/MWh, primer original conservado, conflicto, cruce y contigüidad. Dos novedades concurrentes y dos recuperaciones de un intento; prueba con pool de una conexión y cancelación. `test_reception_concurrency.py`. |
| T016/T024 parcial | Carreras recepción/configuración en ambos órdenes usando locks/servicios 001 y máximos 002 reales. Revisión propia/ajena en las cinco pruebas `test_measurement_semantics.py` de 001. |
| T017/T022/T023, FR-002/006/014 | Faltantes/desalineación, firma cambiante, revisión global de etiquetas, total físico100 frente a parciales60 y base vacía sin sustitución; seis máximos dan exactamente `6*(10^45-1)` quanta. `test_pending_totals.py`. |
| T017/T018, FR-014 | Caída tras commit de parciales y antes del candidato deja solicitud pending. Nuevo trabajador/lifespan recupera sin reenvío; fallo entre flush de total y processed revierte ambos. Recepción concurrente incluida o reactiva solicitud. |
| T017/T023/T026 | CAT-01 con límite distinto de sus parciales: candidatos sin fila numérica anticipada, sondeo sin cambiar revisión/plazo y varios intervalos incorporados juntos al límite exacto. Dos trabajadores simultáneos no duplican. Segundo arranque de aplicación tampoco duplica. |
| T018/T025 parcial, FR-006/014 | Fallo de EventWriter revierte medición/estado/agregados/evento/resultados; fallo entre categorías conserva lo confirmado; pérdida de respuesta tras commit recupera originales. `test_reception_durability.py`. |
| T005..T013 | DTO, claves/FK/estados/exclusión reales, manifiesto protegido por trigger; q/máximos/suma >precisión50, DST/bisiesto, transición30min, agregados sincrónicos y aniversarios iniciales. `test_history_ports.py`, `test_history_schema.py`, `test_history_primitives.py`, `test_history_store.py`. |
| T003/T013 | 91 lecturas de siete categorías durante trece meses entran solo por Reception. Cero aporta duración; suma máximo+q exacta. Una lectura cruzada de hora sigue aportando a día/mes/año. Retención inicial bisiesta y extensión solo con novedades; límites incompatibles requieren reconciliación. |
| T024 parcial | Extensión global del detalle, cruces, diagnósticos CAT-01 y máximos permanentes; siete estados iniciales sin aceptación fabricada; capturas readonly no crean filas ni cambian plazos. `test_history_store.py`. |

Las pruebas usan `Reception.accept/read_attempt`, servicios 001 y escritor 009 reales.
Los fallos deliberados representan puntos concretos de caída; no reemplazan esos
proveedores por implementaciones en memoria. Los DELETE/TRUNCATE de fixtures sirven
solo para aislar la DB desechable, no acreditan retirada de detalle.

## Límites pendientes

T024 conserva pendiente inyectar el proveedor en la fachada `queries.py` de 001, aún
ausente. T025 confirma eventos atómicos; falta el proveedor de resumen/cobertura
funcional y su composición. Por ello **el checkpoint integral de US1 sigue pendiente**,
aunque la recepción y recuperación internas descritas están verificadas.
No se acreditan consulta agrupada HTTP, UI, retirada, consumidores, emisor 007 ni SFTP.

## Cierre del gate de lectura US1, 2026-11-02

T024/T025 completas: proveedores reales002 inyectados en fachada001; límites permanentes
verificados también después de retirada autorizada. `crossing_diagnostic_ids` diferencia
candidatos excluidos y cuenta uno aunque cruce ambos extremos. El resumen funcional propio
`FunctionalSummary.read` está compuesto y probado con permisos, conteo observado/cero,
cobertura desde registro, huecos y contenido desconocido. No consulta logs ni SMTP.
