# US2: boletas y contraste persistido

Validación local, 2026-11-02; PostgreSQL18.3 e identidad006 reales, datos exclusivamente
sintéticos. Las boletas se introducen manualmente y nunca modifican mediciones ni tarifas.

- `backend/tests/unit/costs/test_comparison.py`:105 frente100→+5CLP/+5%; denominador
  cero→porcentaje null; crédito negativo conserva signo; impuestos incluidos solo se
  alinean a neto cuando consta su importe; conceptos ajenos quedan excluidos con causa.
  Un suministro/ciclo incompatible o límites efectivos inciertos no producen contraste.
- `backend/tests/contract/costs/test_bills_comparisons_api.py`: operaciones HTTP reales,
  revisión inmutable, precondición428/412 y selección pendiente tras corregir boleta.
- `backend/tests/integration/costs/test_bill_revisions.py`: dos registros simultáneos
  idénticos producen una sola boleta/revisión (201/200); dos correcciones de igual ETag
  tienen un ganador (200/412); la revisión original mantiene100000CLP.
- `frontend/tests/e2e/cost-comparisons.spec.ts`:3 recorridos aprobados. Registro web de
  energía100000 y abono externo−50, total a pagar99950; contraste comparable0CLP/0%.
  Corrección a90000: par pendiente, confirmación explícita→10000CLP/11.111111%; K1
  sigue disponible. Corrección a cero conserva diferencia y muestra porcentaje No aplica.
  Operador sin controles ni permiso de mutación. Una respuesta perdida después del commit
  conserva campos/clave: reintento devuelve la única revisión1 persistida.

Las consultas no crean comparaciones. La tabla distingue subtotal comparable, total a
pagar y exclusiones; no presenta una comparación histórica como el par actual.
