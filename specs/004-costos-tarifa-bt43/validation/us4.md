# US4: historia, reproducción y captura

Validación local, 2026-11-02, con proveedores001/002/006/009 reales.

- `test_history_pagination.py`: doce ciclos mensuales reales004, páginas5/5/2, IDs
  únicos/corte fijo, cursor firmado incompatible con otros filtros rechazado422;
  lecturas no incrementan revisiones ni extienden conservación.
- `test_history_snapshots.py`: C1/B1/K1 al corte A; B2 sin comparación deja el par actual
  pendiente, diferencias null y fuera del contraste agregado. K2 exacta incorpora
 10000CLP al agregado. C2 vuelve a dejarlo pendiente; corte A mantiene K1.
- `test_snapshot_consistency.py`: UoW real REPEATABLE READ compartida con consumo físico;
  cambios concurrentes B2/C2 son visibles en captura nueva, mientras el llamador mantiene
  B1/C1. Lecturas no crean comparaciones ni distribuyen cargos para PDF.
- `test_reproduction_retention.py`: retirada real002 del original al cumplir su mínimo,
  mientras la captura004 sigue protegida; reproducción pura conserva100000CLP. Alterar
  energía/hash o solicitar versión de motor desconocida falla explícitamente.
- `test_retention.py`: doce meses calendario, 29-febrero→28-febrero y plazo ya extendido
  nunca acortado; se reutiliza el helper009 para horas repetidas/inexistentes.
- `frontend/tests/e2e/cost-history.spec.ts`: recálculo deja par pendiente; comparación
  anterior aparece solo histórica; horario no demuestra demanda de15min, conserva
  subtotal100000 y total completo ausente. Punto de medición distinto figura sin ajuste
  implícito. Período en curso identificado y captura histórica estable recuperable.
- Gráfico y tabla usan la misma página/corte. Disponible/completo y pares comparables
  calculado/facturado/diferencia conservan cadenas exactas; un par pendiente no genera
  barras o diferencias cero ficticias.

`CostsSnapshot` v1 y motor `bt43-v1`; salida tipada inmutable y agregados separados por
moneda/concepto/base tributaria. El productor está listo para integración005; no se ha
implementado ni validado generación PDF como parte de004.
