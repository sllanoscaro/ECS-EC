# Revisión documental de las nueve specs — 2026-11-25

**Corte anterior a la ejecución de6.1.** Después se completó001:T056 con evidencia real;
el estado vigente pasa a578/605 y27 pendientes. [Resultados](../specs/001-visualizar-consumo-categorias/validation/local-integrations.md)
y[plan vigente](implementation-priority-plan-2026-11-03.md). Los recuentos ycontroles
siguientes conservan el corte de esta revisión documental previa,no el cierre posterior.

Se contrastó el estado del **árbol de trabajo actual**, incluidos los cambios locales
de los pasos anteriores, con las nueve listas nativas de tareas y su evidencia fechada.
Resultado: **577/605 completas;28 pendientes**. El [plan pendiente](implementation-priority-plan-2026-11-03.md)
ordena el trabajo que resta; la [hoja de ruta](implementation-roadmap.md) conserva la
propiedad. Esta revisión modifica documentación, sin implementar tareas ni declarar
actualizados los contenedores funcionales del usuario.

## Alcance y resultados por spec

El inventario comprende **195 documentos Markdown en `specs/`**: especificaciones,
planes, tareas, investigación, modelos, contratos, guías, checklists y validaciones.
Se revisaron además los documentos comunes/operativos relacionados. Los contratos y
resultados JSON se comprobaron estructuralmente; los artefactos de ejecuciones anteriores
conservan sus bytes, fechas y resultados. No se alteraron requisitos de `spec.md` ni
se convirtieron estados Draft en aprobaciones.

| Spec / documentos Markdown | Estado contrastado | Correcciones y conclusión |
| --- | --- | --- |
| [001](../specs/001-visualizar-consumo-categorias/plan.md) /20 |57/61 | Se retiró la afirmación de que008 no existe;003/007/008 ya permiten la integración consumidora001:T056. Se corrigieron proveedores002 supuestamente pendientes, trazabilidad de alcance ya implementado y rutas del formulario/shell reales. Los cortes antiguos de aceptación permanecen identificados. T059/personas,T060/VPS,T061/aceptación siguen abiertos. |
| [002](../specs/002-registro-retencion-consumo/plan.md) /19 |70/71 | Investigación, prerrequisitos y contrato ya reflejan fachada/UI001, consumidores008 e instrumentación007 disponibles. T064/SFTP y T065/emisión están verificadas; soloT068/personas pendiente. Se precisó la ruta real de migración y la fecha de los resultados históricos. |
| [003](../specs/003-simulador-pas600-sftp/plan.md) /23 |70/76 | Se reconciliaron las menciones69/76, «todas pendientes» y «rutas futuras» del plan con la implementación actual. Modelo y guía reflejan recepción/integración e instrumentaciónT072 verificadas. Referencia19/T003/T008/T009/T021, otra persona/T070 y aceptación/T076 permanecen pendientes. |
| [004](../specs/004-costos-tarifa-bt43/plan.md) /22 |66/67 | Plan y modelo reflejan el productor implementado;008 ya consume `cost.failed` en pruebas reales y007 tiene instrumentación propietaria. Los resultados antiguos mantienen su corte; no se acreditan tarifas/suministro reales niT064/personas. |
| [005](../specs/005-generar-reportes-pdf/plan.md) /22 |60/63 | Se eliminó la contradicción de la guía entre5/63/no generación y60/63/entrega real. Se actualizaron modelo, dependencia de terminales007 y estado de tareas. Los comandos de navegador incluyen la habilitación optativa, fixture y sesión requeridas. T037/impresión,T058/personas yT059/componente físico siguen pendientes; apertura offline digital ya verificada. |
| [006](../specs/006-acceso-usuarios-rbac/plan.md) /30 |84/87 | Se conservó la evidencia propia vigente y se identificó como histórico el corte75/87. Se añadió el estado de las integraciones007/008 posteriores, sin trasladar propiedad de SMTP. T085/personas,T086/VPS,T087/aceptación pendientes. |
| [007](../specs/007-observabilidad-externa/plan.md) /25 |58/65 | Investigación, plan, guía y aceptación incorporan el trabajo propio008 ya verificado. El contrato de acceso documenta ambos UID autorizados. T059–T065 conservan su grafo:TTL/GC, recorrido final, personas y cadena de documentación/quickstart/aceptación. Esta revisión no cierraT062/T063 antes deT060. |
| [008](../specs/008-notificaciones-programables/plan.md) /22 |90/92 | Plan, investigación y modelo ya no presentan la implementación como futura. Se corrigió la ruta real de las pruebas deterministas SMTP. El cierre del paso5 conserva los resultados y las incidencias de runtime documentadas. SoloT090/personas yT091/VPS pendientes; checklist adicional0/36 intacta. |
| [009](../specs/009-fundaciones-plataforma/plan.md) /12 |22/23 | Plan/modelo identifican la base implementada; la guía sirve la aplicación actual, con módulos privados y perfiles opcionales. La aceptación original se distingue del estado posterior de sus consumidores. Workflow configurado no equivale a CI remoto ejecutado. T022/VPS continúa diferida. |

## Plan restante reconciliado

1. Ejecutar001:T056 ahora con SFTP,visores y Mailpit reales y recursos test nuevos.
2. Conservar el ensayo007:T059 hasta sus verificaciones previas/posteriores al TTL y
   GC físico; luego007:T060 y las ramas007:T061/personas y007:T062→T063→T064.
3. Retomar003:T003→T008/T009→T021 cuando exista DOCA0172EN-19 verificable. No cambia
   la revisión normativa ni bloquea integraciones sintéticas existentes.
4. Organizar personas y la impresión/revisión física005 en paralelo cuando se cuente
   con sus recursos, respetando los prerrequisitos propios.
5. Cuando haya VPS real:009:T022→006:T086; después001:T060 y008:T091.
6. Cerrar001:T061,003:T076,006:T087 y007:T065 solo tras reunir sus evidencias.

Los puntos anteriores distribuyen las28 tareas existentes; no crean tareas ocultas
ni duplican la implementación ya realizada. Las verificaciones humanas mantienen
sus umbrales originales; una reorganización documental no las completa.

## Comprobaciones de esta revisión

- Scripts oficiales de prerrequisitos: **9/9** reconocen spec,plan,tareas,investigación,
  modelo,contratos y quickstart, usando `SPECIFY_FEATURE_NO_PERSIST=1`.
- Recuento e identificadores de las nueve listas nativas contrastados con la tabla
  global y el plan. Estados de todas las casillas de tareas/checklists preservados;
  selección persistida003 intacta.
- Enlaces Markdown locales y anclas revisados en el inventario completo. Se corrigieron
  **seis enlaces a artefactos temporales ausentes** de ingreso/costos en documentos
  comunes: se explicita su indisponibilidad, sin inventar ni reconstruir resultados.
  Comprobación final: **1.386 enlaces locales en217 documentos Markdown**, sin destinos
  ni anclas rotos. Se actualizaron44 documentos existentes y se añadió este informe.
- Rutas de código citadas contrastadas con el checkout. Tres tareas completadas
  citaban destinos previstos distintos de los reales:001:T035,002:T011,008:T044.
  Las rutas futuras de tareas pendientes y las ausencias de los cortes históricos
  no se presentan como implementación actual.
- **93 bloques shell** comprobados con `bash -n`, sin ejecutarlos. Esta comprobación
  valida sintaxis; no acredita disponibilidad de recursos, credenciales ni éxito de CLI.
- **16 documentos JSON** de specs legibles; referencias JSON locales resolubles.
  Sus307 referencias locales resuelven. Esquema de eventos007 válido y copias
  normativas/empaquetadas007/008 idénticas.
- `git diff --check` sin errores. Código,contratos JSON,lockfiles,artefactos previos y
  selección Spec Kit no cambiaron respecto al inicio de esta revisión.

Los resultados de las suites anteriores conservan su alcance y corte. No se repitieron
pytest,Vitest,Playwright,build,migraciones ni CI remoto en este trabajo documental.
La regresión del paso5 y sus repeticiones se consultan en
[aceptación008](../specs/008-notificaciones-programables/validation/acceptance.md);
no se convierten en una única ejecución sin fallos ni se suman como pruebas distintas.
No se comprobaron enlaces externos ni se obtuvo una referencia PAS600 nueva.

## Recursos y límites que permanecen

El estado privado del ensayo007 sigue en `waiting_real_ttl`. Se observaron los plazos
originales del25 de noviembre: preconsulta18:29:33,TTL18:39:45 y límite19:39:33,
hora de Santiago. El monitor y los contenedores siguen activos; no se reiniciaron ni
se tocaron cuotas,volúmenes o reloj. Consultar el
[checkpoint007](../specs/007-observabilidad-externa/validation/implementation-checkpoint-2026-11-24.md)
antes de continuar o limpiar recursos. No se atribuye cumplimiento de TTL/GC a su
mera actividad.

Los contenedores originales del usuario se conservaron. No hubo commit,despliegue,
aprovisionamiento de VPS ni correo externo. La documentación queda reconciliada con
las evidencias disponibles; personas,impresión,referencia19 y VPS permanecen condiciones
reales pendientes y no se reemplazan por esta revisión.
