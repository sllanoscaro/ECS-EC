# Hoja de ruta de implementación

Estado revisado el 2026-11-25: 578/605 tareas completas y27 pendientes. Plataforma009,
identidad006, consumo001/002, costos004 y receptor003 tienen implementación local;
007 es parcial;005 tiene entrega técnica real con pendientes físicos/humanos;008 tiene
entrega técnica local verificada,90/92 tareas. El punto6.1/001:T056 está verificado;
retención/GC007,recorrido/cierre007,personas,impresión,referencia19 yVPS siguen pendientes. Esta hoja coordina las
funcionalidades; las tareas ejecutables se mantienen en sus archivos nativos `tasks.md`.
El [plan priorizado actualizado](implementation-priority-plan-2026-11-03.md) detalla el
orden restante. Las cifras cuentan tareas, no esfuerzo ni aceptación integral.
La [arquitectura](architecture.md) es la referencia compartida, no el plan de la spec-008.

001:T056 ya verificó la integración con003/007/008 en [dos recorridos reales](../specs/001-visualizar-consumo-categorias/validation/local-integrations.md).
La continuación es conservar/revisar el ensayo007:T059 en su plazo real. Después sigue
007:T060 y su cadena final. La [secuencia pendiente](implementation-priority-plan-2026-11-03.md)
enumera las27 tareas y sus condiciones; la [revisión documental](documentation-review-2026-11-25.md)
registra el recorrido por las nueve specs, sin cambiar marcas ni acreditar suites nuevas.

## Propiedad y estado documental

| Funcionalidad | Responsabilidad | Estado del plan y tareas |
| --- | --- | --- |
| [009 Plataforma](../specs/009-fundaciones-plataforma/spec.md) | Scaffold, herramientas, DB/UoW, reloj, retención común, auditoría/eventos, ciclo de vida y operación común. | Implementación y validación local realizadas; [aceptación](../specs/009-fundaciones-plataforma/validation/acceptance.md). [Tareas](../specs/009-fundaciones-plataforma/tasks.md): T022 pendiente de VPS real por decisión del usuario. |
| [006 Acceso](../specs/006-acceso-usuarios-rbac/spec.md) | Cuentas, sesiones, CSRF, permisos, UI de acceso/administración y participante de coordinación de identidad. | 84/87 [tareas](../specs/006-acceso-usuarios-rbac/tasks.md) completas: integración de PDF real005, matrices de ambos perfiles, actividad/limpieza, administración y auditoría con001/002/004, e instrumentación propia verificadas. [Regresión](../specs/006-acceso-usuarios-rbac/validation/regression.md):672 backend/91 frontend y recorridos reales. Solo T085/personas, T086/VPS y T087/aceptación integral pendientes. |
| [001 Consumo](../specs/001-visualizar-consumo-categorias/spec.md) | Catálogo/fuentes, validación de mediciones, detalle, CAT-01 y visualización. | 58/61 tareas completas: consulta/API y administración web integradas con almacenamiento/recepción 002 e identidad 006 reales; validación local física/calculada y persistencia tras reinicio. [Evidencia vigente](../specs/001-visualizar-consumo-categorias/validation/acceptance.md). Casos ampliados de períodos/estados e instrumentación propia con emisor007 verificados localmente; integración transversal003/007/008 verificada en001:T056; personas,VPS ycierre integral pendientes. |
| [002 Historial](../specs/002-registro-retencion-consumo/spec.md) | Límite de recepción, persistencia, agregaciones, cobertura y conservación de consumo. | 70/71 [tareas](../specs/002-registro-retencion-consumo/tasks.md) completas: US1–US4 integradas con001/006 reales; consulta/API/UI de cuatro agrupaciones, proveedores, resumen funcional y retirada protegida. [Evidencia](../specs/002-registro-retencion-consumo/validation/acceptance.md):recorridos físicos/calculados/estados e instrumentación durable verificada. T064/verificación consumidora SFTP003 completada; T065/instrumentación propia con007 verificada; T068/personas pendiente; no aceptación integral. Se conserva el traslado. |
| [003 Simulador PAS600/SFTP](../specs/003-simulador-pas600-sftp/spec.md) | Fuente e integración de archivos según su spec. | 70/76 [tareas](../specs/003-simulador-pas600-sftp/tasks.md) completas: generador y transporte independientes, receptor en el monolito, staging/evidencia/recuperación, recepción real001/002 y exportación/contraste coherentes. Ensayos SFTP con900s reales y restauración local comprobados; [evidencia](../specs/003-simulador-pas600-sftp/validation/acceptance.md). Quedan referencia19 diferida (T003/T008/T009/T021), otra persona (T070) y aceptación integral (T076); T072/instrumentación propia verificada. No se cierran verificaciones de otras specs automáticamente. |
| [004 Costos](../specs/004-costos-tarifa-bt43/spec.md) | Cálculos BT4.3, boletas, resultados persistidos, snapshot y `cost.failed`. | 66/67 [tareas](../specs/004-costos-tarifa-bt43/tasks.md) completas sobre001/002/006/009 reales: US1–US4, API/UI, calendario completo, revisiones/capturas reproducibles y eventos atómicos. [Validación local](../specs/004-costos-tarifa-bt43/validation/acceptance.md); T064/personas pendiente, tarifas reales por configurar. Puertos productores para consumidores005/008 disponibles; sus integraciones pertenecen a esas specs. |
| [005 PDF](../specs/005-generar-reportes-pdf/spec.md) | Generación, persistencia, descarga y `pdf.failed`. | 60/63 [tareas](../specs/005-generar-reportes-pdf/tasks.md) verificadas técnicamente. [Resultados](../specs/005-generar-reportes-pdf/validation/acceptance.md): generación real, API/UI, geometría, costo/contraste, calidad y offline. T037/T058/T059 conservan impresión/personas y revisión física pendientes. |
| [007 Observabilidad](../specs/007-observabilidad-externa/spec.md) | Logging/tracing comunes, recolectores/visores, acceso Programador y política técnica. | 58/65 [tareas](../specs/007-observabilidad-externa/tasks.md) completas: acceso/PDF, productores001–006, métricas/continuidad, privacidad y cuotas físicas verificadas. [Paso4](../specs/007-observabilidad-externa/validation/step4.md). T059/TTL24h y GC, T060/recorrido final y T061–T065/personas/revisión/aceptación pendientes. Ensayo real reanudable documentado, sin cierre anticipado. |
| [008 Notificaciones](../specs/008-notificaciones-programables/spec.md) | Reglas, calendario, evaluación, entregas, SMTP, historial e instrumentación propia. | 90/92 [tareas](../specs/008-notificaciones-programables/tasks.md) completas: US1–US4, Mailpit, productores reales001/002/004/005, historial/reenvíos, conservación e instrumentación verificados localmente. T090/personas y T091/VPS pendientes. [Aceptación local](../specs/008-notificaciones-programables/validation/acceptance.md). |

La spec-009 es una funcionalidad técnica de soporte: conserva el formato nativo de Spec Kit
para que la infraestructura tenga tareas ejecutables propias. El número no determina el
orden de implementación. No se han renumerado las ocho funcionalidades existentes.

Los borradores de traslado NO cubren todas las historias de sus specs. 006 ya tiene plan,
diseño y tareas integrales que incorporan el trabajo trasladado; `$speckit-analyze` revisó
la consistencia y se resolvieron sus tres hallazgos documentales. 001 y 002 también cuentan
con revisión de consistencia tras incorporar sus aclaraciones aprobadas. Para 007 ya existen
plan, diseño y tareas integrales; `$speckit-analyze` completó la revisión de consistencia
sin hallazgos. Su implementación técnica cubre productores, acceso, métricas y cuotas; retención real/GC
y aceptación integral siguen pendientes, sujetas a los prerrequisitos por capacidad; encontrar archivos o generar documentos no acredita aceptación.

## Dependencias por capacidad

1. **Plataforma base**: herramientas, persistencia, reloj, auditoría y composición de la
   spec-009. No requiere cuentas implementadas, SMTP ni módulos de negocio; auditoría
   admite actor/proceso opaco sin requerir identidad habilitada para registrar evidencia.
2. **Identidad y consumo**: planificar 006 y 001/002; implementar sus capacidades reales
   sobre la base común. Definir interfaces de consumo conjuntamente, sin exigir la
   aceptación completa de 001 para comenzar 002 ni crear un ciclo entre ambas.
   La recepción física/SFTP se concreta con 003; las pruebas locales pueden inyectar
   registros en el puerto de recepción, sin acreditar por ello integración PAS600/SFTP.
3. **Instrumentación común**: planificar e implementar el emisor de 007 sobre plataforma.
   Su emisor puede existir antes que los visores. Cada funcionalidad instrumenta sus
   operaciones cuando se incorpora; la cobertura completa de 007 espera esos productores,
   sin bloquear su implementación por visores o red técnica caídos.
4. **Costos y PDF**: 004 consume identidad, series y auditoría; 005 añade el snapshot real
   de 004. Ninguna depende de completar 008 ni de su transporte de correo.
5. **Notificaciones**: US1 necesita plataforma, identidad y fuentes/consultas reales;
   US2 añade correo local, despacho y recuperación; urgencias de consumo usan las mismas
   series. El puente de fallos de sistema espera resultados/eventos reales de 004/005.
   La coordinación de identidad y el participante de notificaciones preceden al primer envío.
6. **Aceptación y VPS**: cada spec valida sus criterios con dependencias reales. Plataforma
   verifica infraestructura/restauración; 007 verifica acceso técnico y aislamiento;
   008 verifica SMTP y enlaces. Usabilidad con personas y verificaciones externas siguen
   pendientes hasta contar con resultados reales.

Compartir archivos como `compose.yaml`, manifiestos o el registro de rutas requiere cambios
secuenciales. Los marcadores `[P]` solo permiten trabajo independiente después de satisfacer
sus prerrequisitos. No se ejecutan automáticamente otras specs desde `tasks.md` de la activa.

## Uso con Spec Kit

Leer [AGENTS.md](../AGENTS.md). Las plantillas de proyecto de especificación, plan y tareas
en `.specify/templates/overrides/` incluyen referencias a estos documentos. Los scripts y
las skills oficiales conservan sus rutas y comportamiento. `docs/` se carga como contexto
por esas instrucciones y enlaces; no se presenta como otro directorio de funcionalidades
ni se presupone que `AVAILABLE_DOCS` enumere documentos externos a la feature.

Para seleccionar una funcionalidad en una sesión, usar el identificador de carpeta completo
al invocar la skill correspondiente. Para que los scripts usen inequívocamente ese contexto,
configurar el entorno de la sesión donde se ejecuta Spec Kit, por ejemplo:

```sh
export SPECIFY_FEATURE_DIRECTORY=specs/009-fundaciones-plataforma
```

Al ejecutar setup, Spec Kit puede persistir esa selección en `.specify/feature.json`.
Los scripts de esta instalación priorizan `SPECIFY_FEATURE_DIRECTORY` sobre ese archivo;
el nombre de la rama Git no selecciona por sí solo una funcionalidad.

Inspección de otra funcionalidad sin alterar la selección persistida:

```sh
SPECIFY_FEATURE_DIRECTORY=specs/009-fundaciones-plataforma SPECIFY_FEATURE_NO_PERSIST=1 bash .specify/scripts/bash/check-prerequisites.sh --json --require-spec --require-tasks --include-tasks
```

Para 007, la comprobación encuentra `plan.md`, sus artefactos de diseño y las tareas
integrales que conservan el traslado; `$speckit-analyze` completó la revisión de consistencia
sin hallazgos. Acceso, cobertura001–006, métricas, aislamiento y cuotas están verificados;
retención real/GC y aceptación integral siguen pendientes con evidencia por capacidad.
001 tiene detalle/API y administración web integrados sobre002;002 incorpora consulta
agrupada/UI, proveedores internos y retirada protegida, con validación automatizada local.
La aceptación conjunta externa y con personas permanece pendiente. 006 ya tiene
implementación e integraciones locales verificadas; personas, VPS y aceptación integral siguen pendientes. La selección persistida
se consulta en `.specify/feature.json` y cambia al seleccionar explícitamente otra spec.
El software local de Spec Kit debe estar instalado;
los overrides se versionan y su infraestructura generada sigue ignorada por Git.

## Trazabilidad del traslado

Los números de tarea son locales a cada spec y pueden cambiar al regenerar tareas. Las
referencias siguientes registran los IDs anteriores de 008 como procedencia histórica,
sin establecer dependencias de ejecución por esos números:

| Trabajo anterior en 008 | Propietario actual |
| --- | --- |
| T001–T008; T012–T013; T022; composición general de T030; respaldo/TLS general de T104 | [Plataforma 009](../specs/009-fundaciones-plataforma/tasks.md) |
| Parte de identidad de T009; T019; T024; autenticación/CSRF de T027; lado identidad de T028 | [Acceso 006](../specs/006-acceso-usuarios-rbac/tasks.md) |
| Parte de validación/origen de T010; semántica de categorías/mediciones de T020 | [Consumo 001](../specs/001-visualizar-consumo-categorias/tasks.md) |
| Persistencia/límite de recepción de T020; agregados/cobertura de T021 y sus pruebas T010 | [Historial 002](../specs/002-registro-retencion-consumo/tasks.md) |
| T029; T100–T101; infraestructura técnica de T102; pruebas comunes de T103 | [Observabilidad 007](../specs/007-observabilidad-externa/tasks.md) |
| Adaptadores, pruebas de integración de identidad/consumo, lado notificaciones de T028, instrumentación propia y SMTP/VPS del módulo | [Notificaciones 008](../specs/008-notificaciones-programables/tasks.md) |

La propiedad de los requisitos funcionales originales y los marcadores de checklists se
conserva. Ninguna fila acredita aceptación funcional o implementación realizada.
