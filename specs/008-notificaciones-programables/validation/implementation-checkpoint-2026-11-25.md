# Continuación del paso5 —2026-11-25

US1–US4 están implementadas y verificadas localmente: configuración, calendario,
resúmenes periódicos, urgencias, historial protegido, recuperación, decisiones de
reenvío, conservación e instrumentación. El [informe de aceptación](acceptance.md)
es la referencia de resultados y tareas pendientes; sustituye el corte parcial del
[24 de noviembre](implementation-checkpoint-2026-11-24.md).

Las alertas consumen las ventanas reales001/002 y los eventos confirmados009 de
costos004/PDF005. Los acuses por identidad de evento cubren commits fuera de orden;
ocho evaluadores concurrentes conservan una sola apertura. La evidencia distingue
medido, calculado, agregado mixto e insuficiente. El primer corte vacío autorizado
queda identificado y conserva conteos desconocidos.

El supervisor y SMTP usan plazas acotadas. La confirmación perdida queda indeterminada
sin otro envío automático; un Administrador decide explícitamente el reenvío vinculado.
Intentos y decisiones extienden el grafo protegido por doce meses calendario. Las
consultas no renuevan conservación y no existe purga automática.

La integración técnica empleó Alloy/Loki/Jaeger/Grafana reales en un proyecto008
exclusivo. El generador de dashboards conserva ambas vistas con la misma política;
la puerta limita lectura a sus UID conocidos. Los resultados se describen en
[observabilidad](observability.md), sin acreditar cuotas ni TTL24h de007.

Pendientes de008: T090 requiere diez tareas observadas con participantes representativos;
T091 requiere VPS, dominio y relay de producción disponibles. Consultar los protocolos
de [usabilidad](usability.md) y [VPS](vps.md). Las pruebas automatizadas no sustituyen
esas validaciones. El siguiente trabajo técnico del plan es el paso6, integración
transversal bajo las listas de cada propietario.

Se conserva la selección Spec Kit003, las dos checklists y los cambios previos del
paso4. El ensayo físico007 de24h/GC, sus mounts, trabajador y contenedores originales
del usuario no se reiniciaron ni reutilizaron desde008. No hay commits ni despliegue
de producción implícitos. Credenciales y material TLS permanecen fuera del repositorio.

PostgreSQL y Mailpit temporales008 fueron retirados al acabar las verificaciones;
su stack técnico exclusivo también quedó retirado. Para reproducir, preparar recursos
test nuevos según el quickstart. El ensayo007 y los servicios originales siguen activos.
