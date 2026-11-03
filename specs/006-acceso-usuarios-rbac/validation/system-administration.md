# Administración disponible y límites pendientes — 2026-11-03

006:T075 completada: rutas administrativas001 y004 usan las dependencias explícitas de
`backend/src/ecs_ec/core/security.py`, además del middleware previo al cuerpo. Los enlaces
actuales de la composición web llevan a configuración de fuentes001 y costos004, filtrados
por permisos actuales. No se añadieron formularios ni ajustes para los mínimos obligatorios002.

La dependencia no renueva actividad por admitir una mutación: el servicio propietario
la renueva cuando confirma éxito. `test_invalid_mutation_does_not_extend_activity` verifica
que un cuerpo inválido al minuto29 no modifica actividad/vencimiento. GET interactivo
sigue siendo una acción explícita distinta de un sondeo.

`test_system_administration.py` prepara suministro/perfil/consumo reales y prueba ausencia
  de sesión, Operador denegado incluso GET de configuración y cuerpos inválidos, rechazo
  de fuente duplicada sin revisión ni persistencia parcial, y retirada protegida mediante
Retention002 real. `test_read_integrations.py` contrasta todas las filas de tablas propias
001/002/004 antes/después de consultas; no solo compara contadores.

006:T068/T076 siguen pendientes: estos ensayos son parciales respecto de su gate G2/PDF,
matriz integral, restricciones completas y evidencia final de auditoría. Los contratos
existentes de004 y001 forman parte de la regresión, pero no sustituyen PDF005 ni una
aceptación integral de US4. No hay skips ni dobles usados como aprobación en las nuevas
pruebas.006:T078 sigue pendiente de sus prerrequisitos y del recorrido ampliado integral.
