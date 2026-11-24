# Administración y auditoría reales — 2026-11-24

006:T068/T076 ejecutadas con001/002/004/005 disponibles. La matriz y los cambios se
prueban mediante HTTP real y PostgreSQL18.3 en `test_system_administration.py`.
Los recorridos de [navegador](administration-ui.md) complementan sus verificaciones.

- Administrador conserva lecturas y mantiene configuración001, suministro, calendarios
  BT4.3, boletas y recálculo004. Operador es rechazado incluso en GET administrativo.
- Asignar una fuente a dos categorías se rechaza sin nueva revisión ni persistencia parcial.
  Entradas inválidas y conflictos conservan el último estado válido.
- Recepción002 admite inicialmente, rechaza un intervalo nuevo a899s y admite al900.
  Retention002 rechaza retirada antes de su aniversario de12meses calendario. Estos
  mínimos no se exponen como ajustes ni mediante una nueva API de mantenimiento.
- Denegaciones GET/POST/PUT por sesión ausente/inválida, perfil, CSRF u origen generan
  exactamente una fila por operation_ref. El actor procede de la sesión vigente o es
  unauthenticated; su protección es al menos12meses calendario.
- Fallar EventWriter después de escribir el primer evento y la auditoría001 revierte
  configuración, eventos y auditoría permitida juntos. Un destino de auditoría que falla
  devuelve503 saneado, sin afirmar que la denegación quedó persistida.

Se corrigió006/history:004 guarda `recorded`/`failed`; la proyección y los filtros006
los presentan como `allowed`/`rejected`. Se preservan acción, actor y resultado originales
009. Pruebas con cálculo, boleta y fallo de motor004 reales comprueban la normalización,
los filtros y ausencia de detalles internos. SC-006 tiene evidencia local; permanecen
personas, VPS y aceptación integral006:T085–T087.
