# Instrumentación propia003 — 2026-11-24

T072 utiliza007 para recepción SFTP, claim/parseo/validación de correspondencias y deltas,
recepción002, publicación, esperas y recuperación. Archivo ilegible y fallos usan códigos
cerrados; nombres, identificadores nativos, mediciones y texto de errores no se emiten.

`PublicationEvaluation.technical_context` persiste contexto antes de adaptar, bajo el
lock de binding. Reenvíos de la publicación confiable comparten UUID opaco de publicación;
recuperación mantiene operación/intento y crea execution_ref nuevo. Entradas históricas
con input congelado y sin contexto se reconocen como unavailable. La migración
`acquisition_003_context` no modifica bytes, hashes ni resultados funcionales.

`test_telemetry.py` usa listener/emisor reales, interrumpe antes de002 y reconstruye el
servicio. Comprueba dos ejecuciones relacionadas, recuperación, parentesco/publicación
compartidos con el terminal002 y ninguna nueva señal por leer un resultado completado.
El supervisor observa fallos anteriores a cargar contexto con referencias unavailable,
sin inventar una publicación; conserva la cancelación del loop.
Un fallo del adaptador técnico permite incorporar otra publicación válida; nunca revierte
consumo ni añade eventos funcionales. El lifespan inyecta007 también en Reception002.

[Recepción002](../../002-registro-retencion-consumo/validation/telemetry.md),
[regresión](../../006-acceso-usuarios-rbac/validation/regression.md).003 queda70/76:
T003/T008/T009/T021 siguen sujetos a la referencia19, T070 a otra persona y T076 a
aceptación integral. Esto no cierra cobertura transversal, visores ni políticas007.
