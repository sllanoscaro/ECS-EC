# Revisión documental del incremento 002

Fecha: 2026-11-02. Alcance: archivos Python nuevos/modificados, migración, fixtures,
contratos y guías de este incremento; no constituye cierre integral T069.

Revisión AST: **26 archivos Python, 231 clases/funciones/métodos, cero docstrings
ausentes**, incluidos privados, pruebas y fixtures. Se revisaron manualmente los
contratos de UoW/locks/commit, errores y cancelación de Reception, calendario UTC/DST,
fórmulas de energía/cobertura y uso del aniversario 009. Los tipos compartidos separan
contratos de proveedores; declaraciones de consulta/consumidores no acreditan servicios.

La migración identifica origen Alembic y parent real; las adiciones manuales preparan
estados sin aceptación y protegen el manifiesto. Su downgrade rechaza borrado destructivo.
La relación auxiliar `calculation_contribution_reference` implementa las FK protegidas
de las referencias JSON de candidatos/totales; no añade un dominio ni otra API.
Los JSON de escenarios describen su origen sintético y el puerto usado para incorporarlos.

Se documentan permisos de procesos ligados al edificio, próxima fecha admisible,
reenvío distinto de recuperación, trabajo de arranque/reintento, ausencia de purga,
prerrequisitos y evidencia parcial. Quickstart distingue comandos ejecutables de API/UI
futuras y enlaza los procedimientos comunes de respaldo/restauración.

T069 seguirá pendiente para revisar el código restante al cerrar la funcionalidad.
