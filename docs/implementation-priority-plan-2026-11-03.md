# Plan de implementación pendiente

Creado: 2026-11-03. Revisado: **2026-11-25** tras los pasos1–5 y el recorrido documental
por las nueve specs. El nombre conserva la fecha original para mantener enlaces.
Referencias: [arquitectura](architecture.md), [hoja de ruta](implementation-roadmap.md),
[revisión documental](documentation-review-2026-11-25.md) y
[constitución](../.specify/memory/constitution.md).

**Punto6.1 completado:001:T056.** Los recorridos CSV/JSON verifican SFTP003,consulta
001/002,Mailpit008 yLoki/Jaeger/Grafana007 reales;209 pruebas de regresión aprobadas.
[Evidencia](../specs/001-visualizar-consumo-categorias/validation/local-integrations.md).
La siguiente continuación técnica es6.2,007:T059 en su plazo real,y6.3 después de su
verificación. Los estados proceden de las tareas y evidencia de cada propietario;
esta entrega marca únicamente001:T056 yconserva las checklists de revisión.

## Estado contrastado

| Spec | Completas / total | Pendientes exactas | Evidencia |
| --- | ---: | --- | --- |
| [001 Consumo](../specs/001-visualizar-consumo-categorias/tasks.md) | 58/61 | 001:T059,001:T060,001:T061 | [Aceptación parcial](../specs/001-visualizar-consumo-categorias/validation/acceptance.md) |
| [002 Historial](../specs/002-registro-retencion-consumo/tasks.md) | 70/71 | 002:T068 | [Aceptación local](../specs/002-registro-retencion-consumo/validation/acceptance.md) |
| [003 PAS600/SFTP](../specs/003-simulador-pas600-sftp/tasks.md) | 70/76 | 003:T003,003:T008,003:T009,003:T021,003:T070,003:T076 | [Estado y referencia19](../specs/003-simulador-pas600-sftp/validation/implementation-status.md) |
| [004 Costos](../specs/004-costos-tarifa-bt43/tasks.md) | 66/67 | 004:T064 | [Validación local](../specs/004-costos-tarifa-bt43/validation/acceptance.md) |
| [005 PDF](../specs/005-generar-reportes-pdf/tasks.md) | 60/63 | 005:T037,005:T058,005:T059 | [Entrega técnica](../specs/005-generar-reportes-pdf/validation/acceptance.md) |
| [006 Acceso](../specs/006-acceso-usuarios-rbac/tasks.md) | 84/87 | 006:T085,006:T086,006:T087 | [Aceptación parcial](../specs/006-acceso-usuarios-rbac/validation/acceptance.md) |
| [007 Observabilidad](../specs/007-observabilidad-externa/tasks.md) | 58/65 | 007:T059–007:T065 | [Paso4 y límites](../specs/007-observabilidad-externa/validation/step4.md) |
| [008 Notificaciones](../specs/008-notificaciones-programables/tasks.md) | 90/92 | 008:T090,008:T091 | [Aceptación local](../specs/008-notificaciones-programables/validation/acceptance.md) |
| [009 Plataforma](../specs/009-fundaciones-plataforma/tasks.md) | 22/23 | 009:T022 | [Base local](../specs/009-fundaciones-plataforma/validation/acceptance.md) |
| **Total** | **578/605 (95,5 %)** | **27 pendientes** | Casillas, no esfuerzo ni aceptación integral. |

Los pasos1–3 verificaron integraciones SFTP consumidoras, el productorPDF y el acceso/
recepción instrumentados. El paso4 entregó cobertura001–006, métricas, aislamiento y
cuotas reales, con su continuación007 aún abierta. El paso5 completó el alcance técnico
local de008: US1–US4, productores reales, correo, historial/reenvíos y conservación.
No volver a programarlos como módulos ausentes. Las evidencias anteriores tienen cortes
diferentes; sus conteos de pruebas no se suman como si fueran una ejecución actual.

## Orden restante y dependencias

### 6. Verificar integraciones transversales y cerrar validación local

#### 6.1.001:T056 completada —2026-11-25

Resultado:dos recorridos CSV/JSON,dos escenarios de navegador y209 pruebas de consumo
aprobadas,sin omisiones. Cuatro correos aceptados por Mailpit,datos yperíodos idénticos
en API/gráfico/tabla,yseñales correlacionadas consultables mediante Programador.
[Resultados,recursos ycomandos](../specs/001-visualizar-consumo-categorias/validation/local-integrations.md).
La secuencia siguiente queda como procedimiento de reproducción; no es otra tarea pendiente.

Usar perfiles y adaptadores existentes de003/007/008, con proyectos, bases y volúmenes
**test exclusivos**. Publicar archivos nativos CSV/JSON por SFTP003; contrastar recepción,
datos/períodos/cobertura y consulta001/002; consultar señales mediante Programador y
observar el correo correspondiente en Mailpit mediante008. Conservar origen simulado,
ausencia distinta de cero, permisos y enlaces autenticados.

Registrar configuración saneada, comandos, valores esperados/observados y límites en
`specs/001-visualizar-consumo-categorias/validation/local-integrations.md`, como exige
001:T056. No crear recepción, telemetría ni SMTP nuevos dentro001. La prueba no necesita
conformidad documental19, personas, VPS ni aceptación integral007; sí sus proveedores
reales, que están disponibles. No cerrarla solo por las pruebas individuales de008.

#### 6.2. Continuar el paso4 en su ventana real:007:T059

El ensayo `ecs007-step4-quotas` permanece activo, fase `waiting_real_ttl`, observado
el2026-11-25. Plazos originales, en `America/Santiago` (UTC-03:00 en esa fecha):

| Hito | Fecha/hora local | UTC |
| --- | --- | --- |
| Lectura previa al TTL | 2026-11-25 18:29:33 | 21:29:33Z |
| Vencimiento de la cohorte | 2026-11-25 18:39:45 | 21:39:45Z |
| Límite de comprobación posterior | 2026-11-25 19:39:33 | 22:39:33Z |

El monitor sigue ejecutándose. Mantener UTC/BOOTTIME/bootID y cohorte originales;
no reiniciar el plazo, detener el trabajador, llenar cuotas, desmontar ni reutilizar
esos recursos para001:T056. El [checkpoint007](../specs/007-observabilidad-externa/validation/implementation-checkpoint-2026-11-24.md)
identifica raíz, procedimiento y limpieza exclusiva.

Exigir consulta previa, desaparición consultable y retirada/GC físico dentro del plazo,
además de protección funcional y política normal168h. Un404, TTL configurado o reloj
controlado no acredita liberación física. Si falta evidencia o falla el GC, investigar
la implementación propietaria007 y conservar007:T059 pendiente; no debilitar el criterio.
El punto6.1 se ejecutó durante esta espera real,con recursos exclusivos distintos.

#### 6.3. Cerrar el recorrido y la cadena técnica007 después de007:T059

Respetar el orden nativo:

1. **007:T060**: tres señales con salida a observabilidad remota bloqueada, imágenes
   ya descargadas, autorización Programador y separación funcional; repetir operaciones
   reales sin perfil `observability`. Guardar `validation/local.md` de007.
2. Tras007:T060, abrir dos ramas independientes: **007:T061/personas** y la cadena
   **007:T062 → 007:T063 → 007:T064**. Esta última completa procedimientos, revisión
   del código/documentación y ejecución del quickstart en entorno limpio.
3. **007:T065** espera ambas ramas:007:T061 y007:T064. No exige una VPS para acreditar
   el recorrido localSC-009, ni se cierra por esta actualización documental.

Las guías y contratos ya actualizados no completan007:T062/T063 mientras su prerrequisito
007:T060 esté abierto;007:T064 necesita ejecución real limpia posterior. Registrar en
su matriz cualquier criterio humano/externo todavía pendiente.

Antes de las regresiones, preparar entorno estable de herramientas y recursos optativos.
El cierre008 registró un trabajador Playwright con SIGSEGV bajo Node24.22; ambos arneses
pasaron con Node24.21. También hubo un fallo aislado SFTP cuya causa no quedó determinada
y pasó en la ejecución posterior. Conservar esas limitaciones y los resultados de cada
corte; no declarar una suite única sin fallos ni sumar repeticiones como casos distintos.

#### 6.4. Referencia003: vía independiente, diferida hasta tener la fuente

Retomar **003:T003 → 003:T008 y003:T009 → 003:T021** al disponer de
**DOCA0172EN-19** verificable. Registrar procedencia, páginas y SHA-256, revisión visual
independiente y esperados estáticos; los lectores/oráculos no deben generarse con el
serializador bajo prueba. Las pruebas locales existentes no certifican esa conformidad.

La revisión19 sigue siendo el alcance aprobado; no hay una ambigüedad nueva que resolver.
El [registro de referencia](../tools/pas600_simulator/tests/fixtures/reference/README.md)
conserva la búsqueda y la autorización anterior para avanzar con contratos locales.
Esta revisión documental no vuelve a buscar ni obtiene una fuente nueva. No sustituir19
silenciosamente por otra revisión. Este diferimiento no bloquea6.1 ni6.3; sí el cierre
integral003:T076.003:T070/reproducción puede organizarse sobre la capacidad local actual,
con la limitación documental explícita.

### 7. Completar personas, comprobación física, VPS y aceptación integral

#### 7.1. Personas y papel: organizar cuando estén disponibles

| Trabajo | Tareas | Condición para cerrar |
| --- | --- | --- |
| Consumo/historial | 001:T059,002:T068 | Diez tareas por protocolo;>=9 sin ayuda en<=60s cada una. |
| Reproducción SFTP | 003:T070 | Otra persona reproduce quickstart/contraste, trazabilidad y parada/reanudación con proveedores reales. |
| Costos/PDF | 004:T064,005:T058 | Diez tareas por protocolo;>=9 sin ayuda en<=2min cada una. |
| Ingreso y vista asignada | 006:T085 | Diez tareas;>=9 sin ayuda en<=1min. |
| Diagnóstico técnico | 007:T061 | Después de007:T060;>=9/10 identifican operación, resultado y etapa sin ayuda. |
| Notificaciones | 008:T090 | Diez tareas;>=9 sin ayuda en<=3min. |
| PDF impreso y revisión offline | 005:T037 → 005:T059 | Impresión A4 al100%, legibilidad y componente físico de revisión; apertura offline digital ya verificada. |

Las evaluaciones humanas disponibles pueden avanzar durante la espera24h,
respetando el prerrequisito particular de007:T061. No sustituirlas con E2E ni inventar
participantes. Registrar tiempos/ayuda/resultados y sujetos opacos. PDF005:T059 conserva
su componente físico pendiente aunque la apertura sin red ya haya aprobado.

#### 7.2. VPS: conservar el diferimiento hasta disponer del entorno real

**009:T022** valida el entorno común: dominio/HTTPS, secretos externos, zona/recursos,
red y persistencia/restauración. Luego **006:T086** verifica desde otra red la frontera
HTTPS/proxy, sesión, cookies, permisos y descargas de ambos perfiles. Sobre esa base,
**001:T060** contrasta las consultas y **008:T091** comprueba enlaces protegidos y
relay de producción autenticado587 con STARTTLS/certificado/hostname verificados.
Estas dos verificaciones consumidoras pueden prepararse en paralelo.

No contratar ni aprovisionar infraestructura desde001/006/008. Precios, suministro,
fuentes físicas y zona real requieren configuración de instalación; los ejemplos
sintéticos no los confirman. Mailpit no acredita relay externo, buzón ni lectura.
La documentación operativa007 se mantiene en su propietario; no se inventa otra tarea
VPS007 que altere los27 pendientes actuales.

#### 7.3. Consolidar cada aceptación cuando estén sus evidencias

| Cierre | Dependencias aún abiertas |
| --- | --- |
| 001:T061 | 001:T059,001:T060 yrecorrido/controles finales exigidos por su quickstart;001:T056 ya verificada. |
| 003:T076 | 003:T003/T008/T009/T021,003:T070 y suites/escenarios aplicables. |
| 006:T087 | 006:T085,006:T086 y evidencias de historias/gates reales. |
| 007:T065 | 007:T061 y007:T064, con007:T059–T063 satisfechas según su grafo. |

002,004,005,008 y009 conservan sus tareas pendientes de personas/físicas/VPS, sin
crear cierres nuevos por una revisión documental. Cada propietario actualiza su matriz
FR/SC cuando obtenga resultados reales. No cerrar tareas consumidoras por la mera
existencia del proveedor ni aceptar todo el sistema por un despliegue común.

## Seguimiento

- Mantener la selección Spec Kit003. Inspeccionar otras specs con
  `SPECIFY_FEATURE_DIRECTORY` y `SPECIFY_FEATURE_NO_PERSIST=1` en scripts oficiales.
- Los identificadores son locales: indicar siempre la spec cuando se cruza de propietario.
- Marcar tareas solo tras su ejecución y evidencia; las checklists son revisión de
  requisitos, no progreso de implementación. Conservar todos sus marcadores.
- Trabajar secuencialmente en archivos compartidos. Usar recursos test exclusivos;
  conservar los contenedores originales y el ensayo007 hasta su revisión y limpieza.
- Después de cada entrega, recalcular esta tabla desde las nueve listas nativas y
  enlazar evidencia fechada. No volver a presentar cortes históricos como estado actual.
