# US3: suministro y calendarios completos

Validación local, 2026-11-02, con PostgreSQL18.3 y permisos006 reales. Fuentes/condiciones
son referencias sintéticas; faltan el pliego, precios y documentos reales del edificio.

- Pruebas unitarias de vigencias: solapamiento interno rechazado; huecos, fuentes o
  estrategias no soportadas limitan el cargo. Dos intervalos físicos de500kWh a100/110
  producen105000CLP; no se prorratea un fijo que cambia a mitad del ciclo. Calendario
  Santiago distingue ambas ocurrencias UTC de la hora repetida; mes documental
  contradictorio queda sin resolver.
- HTTP de suministro:404 inicial,428 sin precondición,422 con cabeceras incompatibles,
 201 con If-None-Match:*,200 con If-Match,412 ante creación/edición obsoleta. Replay
  autorizado precede nuevas precondiciones. POST perfil exige antecesor explícito y
  devuelve409 cuando cambió; lectura distingue última guardada/publicada.
- Concurrencia PostgreSQL: un ganador al crear suministro ausente, al editar igual ETag
  y al publicar dos calendarios contra la misma revisión. No hay calendarios parciales.
- V1 abierta100; V2 completa con cambio julio a110; V3 retroactiva105. Un recálculo del
  primer tramo pasa100000→105000; GET original conserva captura V1. Borrador120 no
  sustituye la publicación V3. Publicación inválida conserva última revisión válida.
- `frontend/tests/e2e/cost-profiles.spec.ts`: conflicto412 conserva borrador, revisión
  explícita y recarga recuperan suministro; copia/edición web del calendario completo,
  cierre de vigencia abierta, corrección retroactiva y recálculo105000; borrador distinto
  de publicación, carrera201/409 y formulario409 conserva120 hasta revisar estado actual.
- `frontend/tests/e2e/cost-supply-initial.spec.ts`: en otra base inicialmente sin costos,
  renovación006 normal, alta web de suministro/revisión1, publicación inicial completa
  desde formularios, cálculo100000 y recuperación tras recarga. Ejecutado contra la
  imagen monolítica construida, con usuario de runtime `ecs`.

Los editores ofrecen copia de calendarios históricos y paginación de revisiones.
La configuración real requiere documentar cada cargo aplicable, política y fuente;
ninguna tasa o distribuidora se asigna universalmente por el software.
