# Hoja de ruta de implementación

Estado: plataforma 009 e identidad 006 propia implementadas localmente; integraciones, personas y VPS pendientes. Esta hoja coordina las
funcionalidades; las tareas ejecutables se mantienen en sus archivos nativos `tasks.md`.
La [arquitectura](architecture.md) es la referencia compartida, no el plan de la spec-008.

## Propiedad y estado documental

| Funcionalidad | Responsabilidad | Estado del plan y tareas |
| --- | --- | --- |
| [009 Plataforma](../specs/009-fundaciones-plataforma/spec.md) | Scaffold, herramientas, DB/UoW, reloj, retención común, auditoría/eventos, ciclo de vida y operación común. | Implementación y validación local realizadas; [aceptación](../specs/009-fundaciones-plataforma/validation/acceptance.md). [Tareas](../specs/009-fundaciones-plataforma/tasks.md): T022 pendiente de VPS real por decisión del usuario. |
| [006 Acceso](../specs/006-acceso-usuarios-rbac/spec.md) | Cuentas, sesiones, CSRF, permisos, UI de acceso/administración y participante de coordinación de identidad. | 69/87 tareas implementadas y verificadas localmente; [aceptación parcial](../specs/006-acceso-usuarios-rbac/validation/acceptance.md).18 tareas esperan proveedores 001–005/007, personas/VPS y cierre integral; no se declara aceptación completa. |
| [001 Consumo](../specs/001-visualizar-consumo-categorias/spec.md) | Catálogo/fuentes, validación de mediciones, detalle, CAT-01 y visualización. | 48/61 tareas completas: consulta/API y administración web integradas con almacenamiento/recepción 002 e identidad 006 reales; validación local física/calculada y persistencia tras reinicio. [Evidencia vigente](../specs/001-visualizar-consumo-categorias/validation/increment-2026-11-02.md). Proveedores002 de diagnósticos cruzados/retirada disponibles; aceptación ampliada001, emisor 007, integración 003/008, personas y VPS pendientes. |
| [002 Historial](../specs/002-registro-retencion-consumo/spec.md) | Límite de recepción, persistencia, agregaciones, cobertura y conservación de consumo. | 68/71 [tareas](../specs/002-registro-retencion-consumo/tasks.md) completas: US1–US4 integradas con001/006 reales; consulta/API/UI de cuatro agrupaciones, proveedores, resumen funcional y retirada protegida. [Evidencia](../specs/002-registro-retencion-consumo/validation/acceptance.md):319 backend/47 frontend y recorridos físicos/calculados/estados. T064/adaptador003, T065/emisor007 y T068/personas pendientes; no aceptación integral. Se conserva el traslado. |
| [003 Simulador PAS600/SFTP](../specs/003-simulador-pas600-sftp/spec.md) | Fuente e integración de archivos según su spec. | 28/76 [tareas](../specs/003-simulador-pas600-sftp/tasks.md) completas: paquete independiente, generación CSV/JSON normal y anómala, históricos de doce meses y control local; 40 pruebas locales pasan. [US1 parcial](../specs/003-simulador-pas600-sftp/validation/us1.md) y [US3 parcial](../specs/003-simulador-pas600-sftp/validation/us3.md). T003 (referencia DOCA0172EN-19) diferida por el usuario; conformidad documental, SFTP, contraste y aceptación integrada pendientes. Consultas/cobertura de 001/002 y emisor 007 aún requieren sus proveedores reales; ver [prerrequisitos](../specs/003-simulador-pas600-sftp/validation/prerequisites.md). |
| [004 Costos](../specs/004-costos-tarifa-bt43/spec.md) | Cálculos BT4.3, boletas, resultados persistidos, snapshot y `cost.failed`. | 66/67 [tareas](../specs/004-costos-tarifa-bt43/tasks.md) completas sobre001/002/006/009 reales: US1–US4, API/UI, calendario completo, revisiones/capturas reproducibles y eventos atómicos. [Validación local](../specs/004-costos-tarifa-bt43/validation/acceptance.md); T064/personas pendiente, tarifas reales por configurar. Productores005/008 disponibles; sus integraciones pertenecen a esas specs. |
| [005 PDF](../specs/005-generar-reportes-pdf/spec.md) | Generación, persistencia, descarga y `pdf.failed`. | [Plan](../specs/005-generar-reportes-pdf/plan.md) y [tareas](../specs/005-generar-reportes-pdf/tasks.md), pendientes de implementación. |
| [007 Observabilidad](../specs/007-observabilidad-externa/spec.md) | Logging/tracing comunes, recolectores/visores, acceso Programador y política técnica. | [Plan y diseño integral](../specs/007-observabilidad-externa/plan.md) y [tareas integrales](../specs/007-observabilidad-externa/tasks.md) generados, conservando el traslado; `$speckit-analyze` completado sin hallazgos. Pendientes de implementación y aceptación funcional. |
| [008 Notificaciones](../specs/008-notificaciones-programables/spec.md) | Reglas, calendario, evaluación, entregas, SMTP, historial e instrumentación propia. | [Plan](../specs/008-notificaciones-programables/plan.md) y [tareas](../specs/008-notificaciones-programables/tasks.md), pendientes de implementación. |

La spec-009 es una funcionalidad técnica de soporte: conserva el formato nativo de Spec Kit
para que la infraestructura tenga tareas ejecutables propias. El número no determina el
orden de implementación. No se han renumerado las ocho funcionalidades existentes.

Los borradores de traslado NO cubren todas las historias de sus specs. 006 ya tiene plan,
diseño y tareas integrales que incorporan el trabajo trasladado; `$speckit-analyze` revisó
la consistencia y se resolvieron sus tres hallazgos documentales. 001 y 002 también cuentan
con revisión de consistencia tras incorporar sus aclaraciones aprobadas. Para 007 ya existen
plan, diseño y tareas integrales; `$speckit-analyze` completó la revisión de consistencia
sin hallazgos. Su implementación y aceptación funcional siguen pendientes, sujetas a los
prerrequisitos por capacidad; encontrar archivos o generar documentos no acredita aceptación.

## Dependencias por capacidad

1. **Plataforma base**: herramientas, persistencia, reloj, auditoría y composición de la
   spec-009. No requiere cuentas implementadas, SMTP ni módulos de negocio; auditoría
   admite actor/proceso opaco sin FK obligatoria a tablas de identidad aún inexistentes.
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
sin hallazgos. Implementación y aceptación funcional siguen pendientes.
001 tiene detalle/API y administración web integrados sobre002;002 incorpora consulta
agrupada/UI, proveedores internos y retirada protegida, con validación automatizada local.
La aceptación conjunta externa y con personas permanece pendiente. 006 ya tiene
implementación y validación local propias; sus integraciones y aceptación integral siguen pendientes. La selección persistida
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
