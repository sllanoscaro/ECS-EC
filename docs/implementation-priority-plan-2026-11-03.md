# Revisión y plan de implementación priorizado

Creado: 2026-11-03. Actualizado: 2026-11-24 por inspección documental y de código.
El nombre del archivo conserva la fecha original para mantener los enlaces existentes.
Referencias: [arquitectura](architecture.md), [hoja de ruta](implementation-roadmap.md)
y [constitución](../.specify/memory/constitution.md).

Este documento coordina el orden de trabajo. No reemplaza planes, contratos ni tareas
de cada spec. Los porcentajes cuentan casillas; no estiman esfuerzo ni aceptación.
La actualización documental inicial no ejecutó suites. La continuación del paso1
añade pruebas reales y completa tres tareas; conserva los marcadores de checklists.
El paso3 está completado en su alcance técnico; once tareas cerradas con pruebas reales.
El paso2 se reanudó:005 tiene entrega técnica verificada60/63 y007 completa T031/T032.
[Resultados y pendientes](../specs/005-generar-reportes-pdf/validation/acceptance.md).
El [registro de interrupción005](../specs/005-generar-reportes-pdf/validation/implementation-checkpoint-2026-11-23.md)
conserva el corte anterior. No se acreditan impresión física, personas ni todo007.

## Estado observado

| Spec | Completas / total | Avance | Pendientes |
| --- | ---: | ---: | --- |
| [001 Consumo](../specs/001-visualizar-consumo-categorias/tasks.md) | 57/61 | 93,4 % | 4: integración transversal003/007/008, personas, VPS y aceptación integral. Períodos/estados ampliados y telemetría propia ya verificados localmente. |
| [002 Historial](../specs/002-registro-retencion-consumo/tasks.md) | 70/71 | 98,6 % | 1: T068 personas. T064/SFTP y T065/instrumentación durable verificadas. |
| [003 PAS600/SFTP](../specs/003-simulador-pas600-sftp/tasks.md) | 70/76 | 92,1 % | 6: T003/T008/T009/T021 referencia independiente19, T070 otra persona y T076 aceptación. T072 instrumentación propia verificada. Receptor/publicador y recorrido local reales disponibles. |
| [004 Costos](../specs/004-costos-tarifa-bt43/tasks.md) | 66/67 | 98,5 % | 1: T064 evaluación humana. Tarifas y suministro reales siguen por configurar; los casos probados son sintéticos. |
| [005 PDF](../specs/005-generar-reportes-pdf/tasks.md) | 60/63 | 95,2 % | 3:T037/T058/T059 (impresión física/personas y revisión enlazada). Productor/API/UI, eventos, A4/preflight, fuentes reales, instrumentación propia y apertura offline verificados. |
| [006 Acceso](../specs/006-acceso-usuarios-rbac/tasks.md) | 84/87 | 96,6 % | 3: T085 personas, T086 VPS y T087 aceptación integral. Matrices/PDF, actividad, administración y regresión verificadas. T069/T077 de separación SFTP verificadas. |
| [007 Observabilidad](../specs/007-observabilidad-externa/tasks.md) | 28/65 | 43,1 % | 37: acceso integral, terminales/correlación/cobertura, métricas, cuotas, retención real y aceptación. Emisor/acceso local y capacidad común para005 disponibles; T031/T032 verificadas, cierre transversal pendiente. |
| [008 Notificaciones](../specs/008-notificaciones-programables/tasks.md) | 0/92 | 0 % | 92: módulo completo; plan/tareas disponibles, sin implementación. |
| [009 Plataforma](../specs/009-fundaciones-plataforma/tasks.md) | 22/23 | 95,7 % | 1: T022 VPS real, diferida expresamente. Plataforma local disponible. |
| **Total** | **457/605** | **75,5 %** | **148**;005/007/008 concentran132 pendientes. |

Evidencia por propietario: [001](../specs/001-visualizar-consumo-categorias/validation/acceptance.md),
[002](../specs/002-registro-retencion-consumo/validation/acceptance.md),
[003](../specs/003-simulador-pas600-sftp/validation/acceptance.md),
[004](../specs/004-costos-tarifa-bt43/validation/acceptance.md),
[005](../specs/005-generar-reportes-pdf/validation/dependencies.md),
[006](../specs/006-acceso-usuarios-rbac/validation/acceptance.md),
[007](../specs/007-observabilidad-externa/validation/acceptance.md) y
[009](../specs/009-fundaciones-plataforma/validation/acceptance.md).
Son resultados de distintos cortes; no se suman ni se presentan como ejecución actual.

## Hallazgos que afectan el orden

1. **003 ya proporciona receptor y publicador:** `backend/src/ecs_ec/acquisition/` y
`tools/pas600_simulator/`, con recepción001/002, recuperación, contraste y restauración
local.002:T064 y006:T069/T077 se completaron en el paso1 con evidencia consumidora
propia; la existencia del proveedor003 por sí sola no acreditaba esas tareas.

2. **Ampliaciones ya completadas:**001:T018/T038/T041/T043/T044/T045/T052/T053/T054 y006:T042/T075/T082/T083
ya están completas. No se programan otra vez como trabajo de implementación pendiente.

3. El emisor007 está registrado en `main.py`. Durante el paso2 se añadió código de
terminales especiales y continuación durable; queda sin cierre y con regresión final
pendiente. [Estado de la ampliación007](../specs/007-observabilidad-externa/validation/step2.md).
002:T065/003:T072 integran esa capacidad y están verificadas en sus propietarios;
la cobertura transversal007 permanece en el paso4.

4. El acceso integral007 espera PDF005 y la aceptación US1 de005 exige instrumentación
real007. La coordinación debe hacerse por capacidad: desarrollar las fundaciones/PDF
independientes y preparar las pruebas comunes007 desde sus fundaciones; concretar la
secuencia de007:T031–T035/T037/T038 antes de ampliar el emisor, respetando sus
prerrequisitos. No exigir cerrar toda007 ni aceptar005 para comenzar el otro módulo.
Las verificaciones integradas finales sí requieren productores reales.

## Secuencia propuesta

### 1. Verificar las integraciones SFTP consumidoras disponibles

**Verificaciones técnicas completadas el2026-11-23:**002:T064 y006:T069/T077 sobre
receptor/publicador003 reales. [Evidencia002](../specs/002-registro-retencion-consumo/validation/source-integration.md)
y [evidencia006](../specs/006-acceso-usuarios-rbac/validation/technical-separation.md).
Se preparó el [protocolo de diez tareas004](../specs/004-costos-tarifa-bt43/validation/usability.md);
su ejecución sigue pendiente de participantes.009:T022 permanece diferida hasta VPS real.

### 2. Desarrollar PDF005 y la ampliación común007 coordinadamente

**Entrega técnica disponible; aceptación integral pendiente.**005 pasó a60/63 tareas:
627 pruebas backend/31 omisiones técnicas,65 de la suite propia/coordinación,91 frontend,
E2E de las tres escalas y fallos, imagen, migraciones y apertura sin red. Los conteos
se solapan y sus alcances figuran en [aceptación005](../specs/005-generar-reportes-pdf/validation/acceptance.md).

La capacidad común de terminales/continuación007 usada por005 está implementada y
probada; T031/T032 se completaron. T033–T035 y el cierre transversal T037/T038 siguen
sujetos a sus matrices/prerrequisitos completos, como indica [el registro007](../specs/007-observabilidad-externa/validation/step2.md).
No se exige completar visores007 ni008/SMTP para usar el productor.

Quedan005:T037/T058/T059 en su alcance físico/humano. Se pueden preparar las
integraciones del paso3 con el PDF real disponible; eso no cierra esas validaciones
ni sustituye la cobertura transversal007 del paso4.

### 3. Completar acceso006 y la instrumentación de recepción

**Completado2026-11-24:**006:T043/T046/T048–T050/T068/T076/T078/T084,
002:T065 y003:T072. [Regresión/evidencias](../specs/006-acceso-usuarios-rbac/validation/regression.md):
672 backend,91 frontend, matrices/UI reales; contexto durable y terminales de recepción
separan ejecución parcial, recuperación y cierre lógico. El historial006 ya incluye los
resultados originales004 mediante una proyección coherente de sus filtros.

Quedan006:T085/T086/T087 (personas/VPS/aceptación),002:T068 (personas) y los seis
gates documentales/humanos/integrales003. Continuar con el paso4; no acreditar esos
criterios ni las tareas transversales007 por el cierre técnico de este paso.

### 4. Completar observabilidad007 sobre productores reales

Cerrar007:T022 y su cadena T028–T030, verificando el código/configuración ya preparado.
Continuar cobertura/correlación US2, métricas/cobertura US3 y políticas, cuotas, retención
y aislamiento US4. Reservar ventana real para TTL24h/GC y comprobación posterior;
una configuración o reloj controlado no acredita esa retención.

### 5. Implementar notificaciones008

Fundaciones y coordinación006 → US1 reglas → US2 programación/correo/recuperación →
US3 urgencias → US4 historial/reenvíos/conservación → instrumentación/aceptación.
La coordinación de identidad008:T014 y sus pruebas preceden al primer envío.
US1/US2 y urgencias de consumo pueden avanzar con sus proveedores ya disponibles,
en paralelo con trabajo independiente005/007. El puente `pdf.failed` requiere005 real;
no se crea ese productor desde008 ni se exige aceptación integral005 para todo008.

### 6. Verificar integraciones transversales y cerrar validación local

Con003/007/008 reales, ejecutar001:T056 con SFTP, visores y Mailpit. Completar las
suites, recorridos, matrices y documentación finales de cada propietario, manteniendo
abiertos los criterios humanos/externos pendientes. Los archivos compartidos se editan
secuencialmente, aunque existan tareas independientes con marcador `[P]`.

### 7. Completar personas, VPS y aceptación integral

Ejecutar evaluaciones humanas001:T059,002:T068,003:T070,004:T064,005:T058,
006:T085,007:T061 y008:T090 con los protocolos y prerrequisitos de cada una.
Pueden organizarse antes cuando sus capacidades estén listas; no se sustituyen por E2E.
Con VPS real, verificar009:T022 y después HTTPS/permisos/descargas de001/006,
aislamiento técnico007 y SMTP/enlaces008 según sus contratos. Consolidar aceptación
de cada spec solo al reunir su evidencia; un despliegue común no acepta los módulos.

## Referencia PAS600: aclarar el alcance ahora y mantener diferido el cotejo

No hay ambigüedad sobre la revisión exigida:003:T003 fija DOCA0172EN-19,
procedencia/hash y revisión visual independiente. El impedimento es obtener y revisar
esa fuente; el usuario autorizó continuar con contratos locales. La búsqueda acotada
actual no obtuvo una copia19 verificable. Ver [registro de referencias y decisión](../tools/pas600_simulator/tests/fixtures/reference/README.md).

Se mantiene diferido el cotejo T003/T008/T009/T021 y su aceptación asociada; no bloquea
las integraciones sintéticas disponibles ni cambia el perfil normativo. Retomarlo al
obtener la revisión19 y antes de cerrar conformidad/aceptación integral003. Si se propone
adoptar otra revisión, tramitar entonces una aclaración de alcance con comparación de
contratos, ejemplos y pruebas; no sustituir19 silenciosamente ni afirmar compatibilidad
física sin descriptor/topología y evidencia del firmware.

## Reglas de seguimiento y comprobación documental

- La selección activa se consulta en `.specify/feature.json`; al revisar se conserva003.
  Para inspeccionar otra spec usar `SPECIFY_FEATURE_DIRECTORY` y
  `SPECIFY_FEATURE_NO_PERSIST=1` con scripts oficiales. No persistir otra selección
  como efecto de actualizar documentación.
- Cada tarea permanece en su propietario y sus IDs son locales. El paso1 verifica
  únicamente002:T064 y006:T069/T077; no cambia checklists ni acepta specs completas.
- Los registros históricos conservan sus resultados y condiciones originales. Los
  avisos de estado vigente remiten a la evidencia posterior y distinguen disponibilidad
  de proveedores de aceptación consumidora.
- Las98 pruebas unitarias de costos/consumo registradas en la revisión original del
  2026-11-03 fueron un resultado de ese corte, no de esta actualización. No se reutiliza
  esa cifra como validación actual ni se declara aprobada su ejecución general interrumpida.
- La continuación del paso1 ejecuta integración PostgreSQL/SFTP y contratos de consumo,
  identidad y adquisición. No reejecuta navegador, build, TTL, personas ni VPS. Resultados
  y comandos en la evidencia enlazada; también se comprueban recuentos/enlaces/espacios.
