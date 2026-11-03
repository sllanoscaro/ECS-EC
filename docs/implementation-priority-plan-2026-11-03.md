# Revisión y plan de implementación priorizado

Fecha: 2026-11-03. Base inspeccionada: `30eca06`, árbol limpio al iniciar.
Referencias: [arquitectura](architecture.md), [roadmap](implementation-roadmap.md)
y [constitución](../.specify/memory/constitution.md).

Este documento propone el orden de trabajo entre funcionalidades. No reemplaza los
planes, contratos ni tareas de cada spec, ni marca aceptación. Se contrastaron los nueve
`tasks.md`, evidencias de validación y código de composición/proveedores. Los porcentajes
cuentan tareas marcadas; no estiman esfuerzo, cobertura funcional ni aceptación integral.

## Estado observado

| Spec | Completas / total | Avance | Pendientes y condición de cierre |
| --- | ---: | ---: | --- |
| [004 Costos](../specs/004-costos-tarifa-bt43/tasks.md) | 66/67 | 98,5 % | Una: T064, evaluación humana SC-006. Cálculo/API/UI y evidencia automatizada local disponibles; tarifas y suministro de referencia son sintéticos. |
| [002 Historial](../specs/002-registro-retencion-consumo/tasks.md) | 68/71 | 95,8 % | Tres: T064 integración real003, T065 instrumentación con007 y T068 evaluación humana. Recepción, agrupaciones, conservación y UI implementadas localmente. |
| [009 Plataforma](../specs/009-fundaciones-plataforma/tasks.md) | 22/23 | 95,7 % | Una: T022, validación VPS real, diferida expresamente por el usuario. Plataforma local disponible. |
| [006 Acceso](../specs/006-acceso-usuarios-rbac/tasks.md) | 69/87 | 79,3 % | Dieciocho: integraciones funcionales, PDF/SFTP, instrumentación, regresión y aceptación humana/VPS. Identidad propia implementada localmente. |
| [001 Consumo](../specs/001-visualizar-consumo-categorias/tasks.md) | 48/61 | 78,7 % | Trece: ampliaciones de integración/estados/períodos, telemetría, integración003/008, personas/VPS y cierre. Catálogo/configuración/detalle/API/UI disponibles. |
| [007 Observabilidad](../specs/007-observabilidad-externa/tasks.md) | 26/65 | 40,0 % | Treinta y nueve: matriz completa de acceso, semántica/correlación/cobertura, métricas, cuotas/retención real y aceptación. Emisor básico y acceso técnico parcial disponibles. |
| [003 PAS600/SFTP](../specs/003-simulador-pas600-sftp/tasks.md) | 28/76 | 36,8 % | Cuarenta y ocho: conformidad independiente, transporte/receptor/adaptación, reproducibilidad integrada y aceptación. Generación local implementada; no existe `backend/src/ecs_ec/acquisition/`. |
| [005 PDF](../specs/005-generar-reportes-pdf/tasks.md) | 5/63 | 7,9 % | Cincuenta y ocho: generación durable, render/preflight, API/UI e integración. Hay puertos, fuentes y adaptador parcial de captura; no existe generación/descarga funcional. |
| [008 Notificaciones](../specs/008-notificaciones-programables/tasks.md) | 0/92 | 0 % | Implementación pendiente. Plan y tareas disponibles; módulo funcional aún ausente. |

La evidencia histórica incluye regresiones PostgreSQL y navegador en
[002](../specs/002-registro-retencion-consumo/validation/acceptance.md),
[004](../specs/004-costos-tarifa-bt43/validation/acceptance.md) y
[007](../specs/007-observabilidad-externa/validation/acceptance.md).
Sus cifras corresponden a distintos cortes y no deben sumarse como pruebas actuales.

## Hallazgos que afectan el orden

1. El roadmap describe005 como pendiente de implementación, pero sus tareas ya registran
   cinco preparatorias completas. Sigue pendiente el producto PDF, no todo su setup.
2. Los registros de prerrequisitos de003 y005 todavía declaran ausentes proveedores que
   ahora existen: consultas/cobertura001/002 y emisor007. La evidencia anterior de001
   también conserva bloqueos de diagnósticos/retirada ya entregados por002. Corresponde
   renovar la comprobación y ejecutar los casos pendientes, sin marcar tareas por inspección.
3. Existe `Telemetry` en `backend/src/ecs_ec/observability/lifecycle.py`, registrado en
   `backend/src/ecs_ec/main.py`. Sin embargo, `complete` admite únicamente
   `operation.completed`: descarta los eventos especiales de recepción/PDF. El soporte
   requerido por002/005 aún necesita trabajo de007, con contratos y pruebas propios.
4. La aceptación de acceso007 espera PDF005; a su vez005 exige instrumentación real007
   antes del checkpoint US1. Si se exige cerrar toda US1 de007 antes de ampliar su emisor,
   aparece un bloqueo de secuencia. El grafo de007 permite preparar pruebas/puertos comunes
   de US2 desde fundaciones. Hay que concretar ese incremento por capacidad y reflejar
   sus prerrequisitos en el plan/tareas antes de ejecutarlo; no saltar las dependencias
   actuales de007:T037/T038 ni exigir aceptación completa de los consumidores para diseñar
   el emisor. Las pruebas integradas finales sí requieren productores reales.
5. Los archivos de pruebas de períodos/estados001 y las rutas/guías técnicas007 ya existen
   parcialmente. Su existencia no basta para cerrar sus tareas ampliadas.

## Secuencia propuesta

### 1. Preparar cierres y actualizar las dependencias verificadas

- Revalidar los gates obsoletos indicados arriba y actualizar los registros vigentes,
  conservando la evidencia histórica. Mantener propietarios y trazabilidad del traslado.
- Programar004:T064 con personas representativas: diez tareas, al menos nueve sin ayuda
  en un máximo de dos minutos cada una. Registrar resultados y corregir obstáculos antes
  de cerrar. Es la spec con menor trabajo restante; no necesita005/008 para esta evaluación.
- Mantener009:T022 pendiente mientras no exista VPS, conforme al diferimiento registrado.
  No dedicar implementación adicional de infraestructura local a simular este cierre.

Salida: gates actuales y protocolo de cierre004 listos;004 solo llega a67/67 si la
evaluación se ejecuta y cumple. Este plan no acredita uso de tarifas reales.

### 2. Terminar las ampliaciones disponibles de001 y avanzar006

- En001, abordar T018 y T038/T041/T043/T044 con proveedores002 actuales: carreras,
  retirada permitida, diagnósticos cruzados, contención exacta y horas repetidas/DST.
- Completar001:T045/T052/T053: estados, llegada tardía, CAT-01 calculada y recorridos
  ampliados de navegador, comparando tabla/gráfico con datos conocidos.
- En006, avanzar T042 y T068/T075/T076 sobre consultas/configuración/costos reales.
  Completar los segmentos disponibles de T046/T048; conservar pendientes las tareas que
  también requieren PDF. No declarar terminadas T049/T050/T078 sin todos sus gates.
- Preparar las sesiones humanas de002:T068 y001:T059 con sus criterios propios;002 exige
  al menos nueve de diez tareas sin ayuda en un máximo de60 segundos cada una.

Salida: menos trabajo local pendiente en001/006 y pruebas reales sobre módulos disponibles;
sin esperar SFTP/PDF para todo el incremento y sin cerrar tareas multiproveedor parcialmente.

### 3. Entregar desde007 la capacidad común que falta

- Preparar007:T031/T032 y las pruebas aplicables de productores; concretar el alcance y
  secuencia de T037/T038 para terminales de recepción/PDF y continuación durable. Resolver
  primero los prerrequisitos del plan mencionados en los hallazgos.
- Cada propietario añade su instrumentación:002:T065,001:T054 y006:T082/T083.
  Recepción debe distinguir fallo parcial recuperable de terminal confirmado; ningún
  log sustituye el resultado/evento transaccional.
- Verificar correlación, saneamiento, conteos y continuidad funcional con transporte
  caído/colas saturadas. No exigir visores activos para commits funcionales.
- Ejecutar006:T084 cuando sus prerrequisitos estén cumplidos y registrar regresión.

Salida:002 puede alcanzar70/71 si T065 y la evaluación humana T068 se completan;
solo quedaría su integración003. El emisor básico existente por sí solo no permite esa marca.

### 4. Implementar003 hasta disponer de recepción SFTP real

- Revalidar las referencias independientes CSV/JSON.003:T003 sigue diferida por decisión
  del usuario: registrar el límite y mantener pendiente conformidad/aceptación que dependa
  de ella. Avanzar únicamente trabajo independiente; no producir el oráculo con el writer.
- Seguir US2 en su orden: almacenamiento/bindings, staging y cierre limpio, listener,
  lectores/mapeo/contadores, transporte/journal, procesamiento durable y recuperación,
  lifecycle/Compose y pruebas reales. No tratar estas48 tareas como un desbloqueo pequeño.
- El adaptador debe persistir entrada e intento antes de llamar002, recuperar el mismo
  intento y usar otro al reenviar después de rechazo por cadencia.
- Con el proveedor real disponible, ejecutar002:T064; si T065/T068 ya están satisfechas,
  cerrar002 en71/71. Ejecutar006:T069/T077 y la cobertura de adquisición007 que corresponda.

Salida: cierre posible de002 y eliminación del bloqueo técnico SFTP para006/007/001.
Sin resolver la referencia diferida, no prometer aceptación documental integral003.

### 5. Completar005 y cerrar las integraciones restantes de006

- Continuar desde005:T006 con modelos/migración, captura durable REPEATABLE READ,
  idempotencia y supervisor; el adaptador parcial actual no sustituye estas tareas.
- Implementar las historias completas: generación/descarga real, siete categorías en
  una página A4, costos/contraste y calidad/procedencia. Integrar005:T061–T063 con007 real
  antes del checkpoint US1, incluido `pdf.failed` atómico e interrupciones recuperadas.
- Con generación/descarga reales, cerrar las verificaciones PDF de006:T043/T046/T048/
  T049/T050 y las dependientes T078; completar007:T022 y su cadena T028–T030 mediante
  verificación de lo ya preparado, sin reconstruir innecesariamente Compose/gateway.

Salida: PDF funcional e integraciones locales de acceso verificadas.006 conserva personas,
VPS y consolidación hasta que existan sus evidencias.

### 6. Completar007 y después008

- Retomar cobertura real, métricas, aislamiento, cuotas y retención de007. Reservar
  una ventana para su prueba real de TTL24h y verificación posterior; no equivale a
  probar solo configuración o reloj controlado.
- Implementar008 por US1 configuración → US2 calendario/despacho/recuperación → US3
  urgencias → US4 historial/reenvío/conservación. Coordinación006 precede al primer envío.
  Configuración, correo periódico y urgencias de consumo no exigen cierre integral005;
  las alertas `pdf.failed` sí necesitan el productor real. Se pospone008 aquí para
  concentrar el esfuerzo en las specs avanzadas y sus desbloqueos.
- Con003/007/008 disponibles, ejecutar001:T056 con SFTP, visores y Mailpit reales.

Salida: integraciones locales transversales completas, pendientes solo los criterios
humanos/externos que no hayan sido ejecutados y sus consolidaciones correspondientes.

### 7. Cierre humano y VPS cuando estén disponibles

Completar las evaluaciones humanas restantes respetando el protocolo de cada spec.
Cuando se provea VPS real, ejecutar009:T022 primero y después las verificaciones de
cada propietario: HTTPS/permisos/descargas, aislamiento técnico007 y SMTP/enlaces008.
Registrar criterios cumplidos y fallidos individualmente; el despliegue común no acredita
automáticamente aceptación de los módulos.

## Reglas de ejecución y seguimiento

- Prioridad por dos criterios: proximidad al cierre y capacidad para desbloquear una spec
  avanzada.004 tiene el primer cierre humano;003 sube antes de005/008 para cerrar002.
 009 permanece prioritaria para cierre cuando exista VPS, sin bloquear trabajo local.
- Ejecutar una spec explícitamente seleccionada por incremento. La selección persistida
  observada es007; esta revisión no la cambia. Inspecciones ajenas usan
  `SPECIFY_FEATURE_DIRECTORY` y `SPECIFY_FEATURE_NO_PERSIST=1` con scripts oficiales.
- Mantener tareas y checklists originales sin cambios hasta ejecutar trabajo real.
  Secuenciar escrituras de composición, manifiestos, Compose y archivos compartidos.
- Para cada incremento: pruebas de contrato/integración PostgreSQL cuando corresponda,
  pruebas UI afectadas, typecheck/build si cambia frontend y evidencia en la spec dueña.
- Actualizar roadmap y aceptación después de verificar, separando implementación local,
  integración, personas y VPS. No comprometer fechas basadas en porcentajes de tareas:
  no representan duración y faltan disponibilidad humana y configuración externa.

## Comprobaciones de esta revisión

- `.venv/bin/pytest backend/tests/unit/costs backend/tests/unit/consumption -q`:
  **98 pruebas aprobadas en3,37s** sobre el checkout actual.
- La ejecución general de `backend/tests/unit` se interrumpió tras dejar de mostrar
  progreso; no se contabiliza como aprobada ni se atribuye una causa sin diagnóstico.
- Enlaces Markdown del documento comprobados contra archivos existentes; comprobación
  de espacios realizada. No se reejecutaron integración PostgreSQL, navegador, build,
  infraestructura, sesiones humanas ni VPS durante esta revisión.
- Único archivo añadido: este plan. Tareas, checklists, roadmap original, código y
  selección persistida de Spec Kit se mantienen sin cambios.
