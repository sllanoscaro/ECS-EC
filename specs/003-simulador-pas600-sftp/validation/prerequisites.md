# Prerrequisitos003 verificados

2026-11-03. Revisión de código y pruebas reales del incremento; [evidencia](acceptance.md).
La situación anterior (acquisition ausente) queda superada por esta integración.

| Propietario | Disponibilidad y verificación003 |
| --- | --- |
| 009 | Database/UoW, reloj/aniversario, auditoría, lifecycle, Alembic/Compose y backup/restore reutilizados. App conserva una unidad de despliegue. |
| 001 | Catálogo/fuentes existentes y reglas de validación consumidos por bindings/adaptación. Correspondencia explícita de medidores; sin fuentes ni categorías creadas desde archivos. |
| 002 | Reception.accept/read_attempt reales: ID/entrada congelados, pérdida de respuesta, recuperación concurrente, duplicate/too_early y reenvío nuevo. Total calculado11 de4+7 y medido20 por SFTP real. |
| 001/002 consulta | read_report_snapshot con UoW/corte del exportador. Captura concurrente demuestra aislamiento REPEATABLE READ; detalle y agregados reales,2700s/75%. No usa detail en transacción separada. |
| 006 | Lecturas protegidas/permisos conservados en regresión. Identidad SFTP técnica separada, sin cookies o autorización humana. Las verificaciones integrales pendientes006 pertenecen a006. |
| 007 | Emisor real consumido para operation.completed de acquisition.receive/acquisition.process y etapas ordinarias; fallo de adapter no altera commit. Semántica ampliada/continuación durable completas siguen en007:T037/T038; T072 permanece parcial. |

No son prerrequisitos del recorrido sintético local PDF005, correo008, VPS ni hardware.
T003 sigue diferida explícitamente por el usuario: permite desarrollo con contratos locales,
sin acreditar conformidad DOCA0172EN-19 en T008/T009/T021. T070 espera otra persona;
T076 conserva los criterios no ejecutados. La verificación física exige IDs/topología y
captura CLOSE/EOF del firmware antes de habilitarlo; no se deriva de ejemplos sintéticos.

Las cifras antiguas y proveedores ausentes de los registros2026-11-02 describen ese corte,
no bloqueos vigentes.003 no modifica marcas de verificación de001/002/006/007.
