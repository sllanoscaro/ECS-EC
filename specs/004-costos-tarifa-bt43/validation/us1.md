# US1: productor real y consulta local

2026-11-02, base23c26d0. T001–T027 implementadas; configuración y precios exclusivamente
sintéticos. PostgreSQL18.3 desechable en `ecs-spec004-test`, loopback55452, bases separadas
`ecs_costs_test` y `ecs_costs_browser_test`. No se usó la base de aplicación.

- Contratos productores001/002:4/4 aprobados. CAT-01 calculada es limitación; datos horarios
  no prueban quince minutos. La captura financiera comparte REPEATABLE READ y corte único.
- Suite004 inicial:16 aprobadas (unitarias/fundaciones/HTTP/eventos), incluidas1000×100=100000,
 10kWh/0.25h=40kW, máximos60/50→55, punta30/20→25 y referencia abril→30. Los máximos
  se verifican sobre trece meses de bloques completos, no solo valores aislados; retirar
  un cuarto invalida el máximo del mes afectado.
- Ausencia, precio faltante y total calculado no inventan cero/costo completo. Un fijo
  disponible se conserva como subtotal. Impuesto sintético19% explícito produce19000
  y no se aplica nuevamente a bases con impuesto incluido.
- HTTP actual006: sesiones/permisos/CSRF/origen/no-store, idempotencia y revisión/motivo de
  recálculo; lecturas recuperan recursos persistidos. Esquemas y tipos monetarios textuales.
- Fallo controlado del motor persiste resultado fallido y `cost.failed`009 en nueva UoW.
  Fallo de escritura del evento revierte resultado/snapshot/auditoría; devuelve503 y no
  afirma persistencia. Datos insuficientes esperados no emiten `cost.failed`.
- Playwright inicial:2/2 perfiles, cálculo/recálculo, recarga,100000CLP en tabla y gráfico;
  Operador consulta y no muta. Se reiniciaron proceso Uvicorn y PostgreSQL y se repite el
  recorrido con las mismas cuentas/datos. Consumidor008 y SMTP ausentes.

Migraciones propias: `costs_004_initial` sobre `47457bdabdfa`, luego
`costs_004_calculations`; auditoría009 reutilizada, sin tablas comunes duplicadas.
Alembic check de la fundación sin diferencias. La validación de fases posteriores y
los conteos finales se consolidan en aceptación al cerrar la ejecución.

Referencia adicional de todos los cargos sintéticos con cobertura física de quince minutos:
energía400, transmisión8, servicio12, fijo50, suministrada550 (55kW×10), punta600
(30kW×20), otro5; neto1625, impuesto sintético19% redondeado309, total1934CLP.
El histórico completo demuestra las bases, sin deducir potencia de intervalos horarios.
Un importe fuera de precisión documentada conserva limitación funcional en lugar de
producir un resultado numérico o evento técnico incorrecto.
