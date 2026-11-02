# Revisión documental vigente002

Continuación2026-11-02: T069 completa para el código propio de esta funcionalidad.
AST de archivos modificados/nuevos:22 Python/157 símbolos/cero docstrings ausentes.
Revisión ampliada de módulo consumo, pruebas unitarias/integración/contrato, composición,
harness y migración real: 61 archivos/411 símbolos/cero ausencias.

Se revisaron contratos de captura/UoW/cutoff y autorización del llamador, fórmulas de
quanta y porcentaje por enteros, estados exactos antes de redondeo, fuentes/bases
históricas, recuperación de solicitudes, vencimientos/dependientes/retirada y auditoría
atómica. Tipos002 manuales citan su contrato; tipos001 identifican su generador y se
regeneraron por `detail_withdrawn`. Componentes, formateadores, hook y pruebas frontend
conservan TSDoc y evidencias exactas compartidas. No hay cambios a dependencias/locks,
scripts ni skills distribuidos de Spec Kit.

[Guía reproducible](../quickstart.md), [API](../contracts/http.md),
[puertos concretos](../contracts/integrations.md), [aceptación](acceptance.md).
Revisión de enlaces Markdown relativos y `git diff --check` sin errores al cierre.
La revisión anterior se conserva a continuación como evidencia histórica, sin convertir
sus limitaciones pasadas en gates vigentes.

---

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
