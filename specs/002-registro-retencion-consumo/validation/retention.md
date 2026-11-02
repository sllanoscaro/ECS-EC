# Conservación y retirada verificadas

Fecha: 2026-11-02. [Aceptación](acceptance.md); tareas T045–T053, FR-015..019/SC-004.

`retention.py` reutiliza el aniversario009, conserva plazos no decrecientes y centraliza
la protección de contribuciones usada por `pending_totals.py`. La retirada interna exige
proceso autorizado por edificio, motivo acotado y contexto→categorías→registros. La
previsualización no escribe; ejecución revalida vencimiento/payload/dependientes y confirma
retirada/auditoría juntas. No existe endpoint público ni purga automática.

| Escenarios US3 | Evidencia |
| --- | --- |
| 1/2/3: primera aceptación, frontera y dato antiguo | `test_retention.py`: originales históricos y91 lecturas de13 meses/siete categorías conservados antes/en aniversario; consulta posterior no obliga a retirar. |
| 4: última incorporación y consultas/duplicados | Escritor común/extensión no decreciente, `test_history_store.py`, `test_retention.py`, `test_aggregates.py`; duplicados no cambian revisión/plazo. |
| 5: año parcial | Proyecciones de cuatro niveles y13 meses: cobertura real incompleta, sin fabricar historia anterior. |
| 6/8: bisiesto/hora inexistente/repetida | Aceptación2028-02-29T12Z→2029-02-28T12Z;2026-09-05T04:30Z→2027-09-05T04Z;2026-04-04T02:30Z→2027-04-04T03:30Z. Zona America/Santiago, tzdata2026.6. Helper009 y límite persistido; nunca365 días. |
| 7: agregado protegido tras retirada | `test_detail_withdrawal.py`: extensión del día antes de retirar un original vencido; energía/cobertura/revisión/plazo del agregado intactos, payload eliminado por operación real y máximos001 conservados. |
| 9: novedad y reenvío tras retirada | `test_history_late_data.py`: duplicado/conflicto/superposición no suman; nueva lectura contigua aporta una vez y extiende plazo. |
| Dependencias | `test_retention_references.py`: solicitud pending sin candidato bloquea retirada incluso tras el mínimo; recuperación completa sin perder evidencia. Total incorporado más tarde extiende la protección de sus originales. Configuración/fuentes/ledger/aportes permanecen con FK protegidas. |

Playwright `consumption-history-states.spec.ts` retira mediante el CLI interno de pruebas,
consulta el agregado preservado y alterna a detalle vacío con aviso. El mismo recorrido
expira sesión y exige autenticación006 nuevamente. Reloj ISO privado0600 y DB separada;
no se alteró el host ni se usaron DELETE directos para acreditar retirada.
La aplicación y PostgreSQL se reiniciaron y el recorrido de agrupaciones volvió a pasar.
