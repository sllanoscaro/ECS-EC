# Continuación del paso5 —2026-11-24

Este documento conserva el corte histórico de US1/US2. La continuación del25 de
noviembre implementa US3/US4 e instrumentación; consultar el
[estado vigente](acceptance.md) y el [nuevo punto de continuación](implementation-checkpoint-2026-11-25.md).

Se conserva la selección explícita de Spec Kit en003.008 se inspeccionó mediante las
variables oficiales sin persistir otra selección. El usuario autorizó continuar sin
marcar los36 criterios de la checklist adicional y aprobó la excepción del primer
corte periódico vacío. Ninguna checklist fue modificada.

Configuración/fundaciones/US1 verificadas: [resultados](us1.md). Núcleo de US2 y correo
local: [resultados](us2.md). Migraciones propias: instalación limpia, rollback vacío y
reinstalación aprobados; rollback con historia rechazado atómicamente conservando
head e historial, incluida la migración de slot futuro y evidencia tipada.

Últimas verificaciones independientes:70 pruebas008 sin navegador;97 Vitest; exportación
Next; tres escenarios Playwright mediante el arnés real; perfil periódico20/20.
Otra ejecución de29 casos de calendario/transporte/configuración/coordinación aprobó
el cambio de perfil y el aislamiento de configuración SMTP inválida.

Queda implementar/verificar US3, completar decisiones de reenvío/conservación de US4,
aislamiento con productores reales, instrumentación008 y aceptación transversal.
El perfil mixto40, personas008:T090 y VPS008:T091 permanecen pendientes. La existencia
de modelos y clientes para esas capacidades no acredita que ya funcionen.

Entorno desechable exclusivo de este paso: contenedores `ecs008-step5-db` (PostgreSQL,
loopback55565) y `ecs008-step5-mailpit` (SMTP11025/interfaz18025). Las credenciales solo
existen en un archivo temporal privado; no se registran aquí. Estos recursos no se
comparten con los contenedores originales del usuario.

Se preservan los cambios previos del paso4 y su ensayo físico24h/GC: proyecto
`ecs007-step4-quotas`, trabajador y volúmenes exclusivos. No se hicieron reinicios,
llenados de disco ni alteraciones de ese ensayo desde008. Su aceptación sigue en007.
No hay commits ni despliegue de producción implícitos.
