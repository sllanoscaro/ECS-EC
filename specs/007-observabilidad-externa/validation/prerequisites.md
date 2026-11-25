# Prerrequisitos verificados007 —2026-11-24

| Capacidad / propietario | Estado comprobado |
| --- | --- |
|009 core/DB/reloj/auditoría/lifecycle | Disponible; regresión PostgreSQL real, commits/rollback bajo fallos007. |
|001/002 consultas/validación/recepción/agregación/retirada | Productores instalados e instrumentados; [cobertura](coverage-acquisition.md). |
|003 SFTP/publicación/adaptación | Receptor real, EOF/abortos/contexto durable/recuperación consultables; no hay bloqueo por inexistencia. |
|004 costos/boletas/calendarios | Integración propietaria007 autorizada expresamente; [evidencia004](../../004-costos-tarifa-bt43/validation/observability.md). |
|005 PDF | Generación durable, render/preflight/publicación/descarga reales; matriz007 sin omisión PDF. |
|006 identidad/permisos/historial | Matriz funcional y denegaciones reales, independientes del Basic Programador. |
|007 terminales/continuación/métricas/cuotas | Capacidad transversal verificada en el paso4; [resultados](step4.md). |
|TTL24h/GC / personas / VPS | Permanecen pendientes por evidencia real o participantes; no se simulan. |

Cada propietario conserva su módulo, contratos y tareas. Las pruebas007 consumen sus
proveedores y no reemplazan aceptación humana/documental externa. Selección Spec Kit
persistida003 intacta; se inspeccionó007 sin persistir. Checklists16/16 de revisión,
sin modificación; no hooks before/after porque extensions.yml está ausente.
