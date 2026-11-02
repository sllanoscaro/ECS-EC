# Investigación: Simulador PAS600 y recepción SFTP

Fecha: 2026-11-01. Diseño, sin implementación ni pruebas ejecutadas.
[Spec](spec.md), [plan](plan.md), [arquitectura](../../docs/architecture.md),
[hoja de ruta](../../docs/implementation-roadmap.md).

## Fuentes primarias y evidencia disponible

- **S1**: [Schneider Electric, DOCA0172EN-19](https://www.productinfo.schneider-electric.com/ecostruxurepanelserverguide/doca0172-ecostruxure-panel-server-user-guide/English/Panel-Server-User-Guide-DOCA0172EN-19.pdf),
  publicación SFTP pp. 118–120, formatos pp. 126–127, apéndice D pp. 274–276 y
  apéndice E p. 277. Se consultó la revisión fijada, no se sustituyó por la actual.
- **S2**: [ficha A9MEM3150](https://iportal.se.com/Contents/docs/SQD-A9MEM3150_DATASHEET.PDF),
  2020-03-20: energía activa y comunicación Modbus RTU/RS485.
- **S3**: [AsyncSSH, documentación oficial](https://asyncssh.readthedocs.io/en/latest/),
  [API de sesiones/SFTP](https://asyncssh.readthedocs.io/en/latest/api.html) y
  [cambios](https://asyncssh.readthedocs.io/en/latest/changes.html).
- **S4**: [simplejson, documentación oficial](https://simplejson.readthedocs.io/en/latest/),
  codificación/lectura Decimal sin float.
- Contratos locales: [001](../001-visualizar-consumo-categorias/contracts/integrations.md),
  [002](../002-registro-retencion-consumo/contracts/integrations.md) y
  [009](../009-fundaciones-plataforma/contracts/integrations.md).

Las páginas web vivas no fijan firmware. En implementación se conservarán procedencia,
revisión y SHA-256 del material de referencia utilizado y resultados esperados revisados
independientemente. El apéndice contiene ejemplos de tensión e IO: prueba la estructura,
no acredita por sí solo un identificador de energía específico del iEM3150.

## R1 — Perfil y correspondencias nativas

**Decisión**: fijar `pas600-doca0172en19-energy-v1`, con contrato en
[perfil PAS600](contracts/pas600-profile.md). Separar identidad del publicador, identidad
local del medidor, canal nativo, unidad y semántica. Las correspondencias son entradas
explícitas del escenario y de la configuración del adaptador, nunca columnas CAT añadidas
al archivo. Se admite energía activa acumulada y canales de intervalo solo si su descriptor
identifica esa semántica. No inferirla del tamaño del valor o del nombre traducido.

**Razón**: S1 describe CSV por dispositivo y JSON por series de varios dispositivos;
S2 identifica el origen físico, pero no fija los IDs internos asignados por un PAS600.
La identidad JSON requiere correspondencia de topología, no derivación desde el modelo.
Un descriptor local sintético debe declararse como tal; no equivale a captura del equipo.
La compatibilidad documental y la aceptación del dispositivo físico son evidencias distintas.

**Alternativas**: CSV/JSON propios con `category_id` descartados por FR-003/004;
IDs de tópico supuestos o copia de ejemplos de otro medidor descartados por falta de evidencia.

## R2 — Herramienta independiente y receptor dentro del monolito

**Decisión**: paquete CLI independiente en `tools/pas600_simulator/`, Python 3.14,
Pydantic 2, stdlib `csv`, `decimal`, `hashlib`, `zoneinfo`, AsyncSSH y simplejson.
Su propio manifiesto/lock permite ejecutar generación sin instalar el backend.
Pydantic2/AsyncSSH/simplejson se declaran como dependencias de ejecución en
`project.dependencies`; pytest y herramientas de pruebas en `dependency-groups.dev`.
La aceptación local comprueba validate/generate con instalación bloqueada `--no-dev`.
El receptor AsyncSSH y el adaptador viven en `backend/src/ecs_ec/acquisition/`,
registrados en el `lifespan` común 009, en el proceso Uvicorn inicial. Un listener SSH
adicional no es otro servicio de aplicación. El simulador no importa `ecs_ec`.
Versiones exactas y compatibilidad de instalación se verifican y bloquean al implementar.

**Razón**: S3 ofrece cliente/servidor asíncronos, host keys y callbacks de sesión;
S4 conserva números JSON exactos. El puerto de recepción debe conocer el cierre explícito
de los handles, algo que un directorio compartido vigilado por mtime no demuestra.

**Alternativas**: receptor/worker propios en otro contenedor incumplirían el monolito;
OpenSSH externo con polling no proporciona por sí solo la frontera de lote necesaria.
Paramiko con hilo dedicado añade coordinación respecto al ciclo asíncrono ya elegido.

## R3 — Fin de archivo y de publicación

**Decisión**: convención de integración `sftp-session-batch-v1`: una sesión del subsistema
SFTP exclusiva por publicación, escritura secuencial de todos sus archivos con nombres
nativos, CLOSE explícito confirmado de cada uno y SSH CHANNEL_EOF limpio al concluir.
El receptor escribe a staging y sella un conjunto inmutable solo al recibir ese EOF,
sin handles abiertos ni errores de escritura/cierre. Una pérdida de conexión, un cierre
implícito de limpieza o el cierre genérico del canal no sellan nada. Un cliente que falla
aborta el canal sin emitir EOF; un context manager no puede cerrarlo normalmente en
esa ruta. Probar estas diferencias en transporte real es requisito de implementación.

**Razón**: S1 documenta índices de archivo, pero no un total explícito ni un marcador de
commit. El EOF es una afirmación del cliente conforme al contrato, no una comprobación
mágica del número de archivos. La sesión es la frontera adicional; los bytes PAS600 no
cambian. El receptor conserva también archivos estructuralmente defectuosos sellados.

**Alternativas**: estabilidad de tamaño, timeout, parser exitoso o último índice observado
no prueban completitud; un manifest privado requerido al PAS600 carece de respaldo documental.
La sesión resuelve el camino del simulador. **S1 no garantiza esta conducta del firmware**:
antes de habilitar un PAS600 real se debe comprobar en captura que una publicación cumple
la convención. Si no la cumple, se necesita diseñar una frontera verificable del receptor;
no se habilita una heurística silenciosa ni se declara esa compatibilidad desde este plan.
No se requiere hardware para aceptar los escenarios locales especificados.

## R4 — Identidad, intentos y reloj

**Decisión**: contenido y nombres se congelan al generar. `publication_ref` del receptor
identifica binding/revisión semántica/perfil/publicador, ciclo nativo y lista ordenada de nombres, tamaños y hashes;
la comparación comprueba además el manifiesto completo. Intento SFTP e intento 002 tienen
UUID internos nuevos por reenvío; recuperación de un intento existente conserva su UUID.
003 fija y persiste ese UUID y toda la entrada ordenada antes de `Reception.accept`002.
El contrato propietario define `read_attempt` para consultar resultados sin efectos y
`accept` con el mismo ID/entrada para continuar solo lo no confirmado. Un mismo ID con
otra entrada produce `attempt_payload_conflict`; un intento completado conserva su
resultado original, incluso `too_early`. DB fallida no equivale a intento inexistente.
La identidad de medición final sigue siendo la de 001/002, independiente del archivo/formato.
No descartar permanentemente una publicación por haberla visto: un `too_early` puede
aceptarse en otro intento. El cliente reenvía el conjunto completo original.

**Razón**: 002 compara duplicados antes del límite; no autoacepta novedades físicas
rechazadas. 003 conserva candidatos y resultados; nunca presenta un envío como aceptación.
Separar tiempo simulado, monotónico y UTC real. Un candado por destino/publicador en el
cliente impide publicaciones concurrentes. Se aplica conservadoramente una espera global
por publicador de >=900 s desde fin del intento anterior, incluidos fallos y reintentos.
Al reiniciar, esperar de nuevo el intervalo completo; una caída/reloj UTC cambiado no
acorta el plazo. Son tres intentos totales iniciales, no tres reintentos adicionales.

**Alternativas**: deduplicar por hash todo el lote impediría recuperar rechazos temporales;
usar el timestamp de medición o avanzar reloj de prueba en red incumple FR-008.

## R5 — Contadores y huecos

**Decisión**: persistir lecturas nativas y candidatos en 003. Para lecturas C(t),
`E([t0,t1)) = C(t1)-C(t0)` solo con extremos válidos consecutivos del calendario de
muestreo, misma fuente/unidad/descriptor y `t1=t0+sampling`. Primera lectura es referencia.
No puentear omisiones, valores inválidos, resets ni cambios de configuración. El valor
inferior tras un reset puede iniciar un segmento nuevo; no produce energía hasta tener
el siguiente extremo válido consecutivo. No extrapolar. Los datos tardíos completan
pares antes ausentes sin cambiar intervalos ya incorporados.

**Razón**: conserva evidencia exacta para 001/002 y evita inventar cobertura. Un registro
no debe desaparecer del backlog por avanzar un cursor antes de su aceptación durable.
Los candidatos rechazados temporalmente permanecen reconstruibles y reenvíables.

**Alternativas**: restar el último valor disponible tras un hueco o distribuir el delta
sobre períodos ausentes ocultaría pérdidas. Tratar el contador absoluto como kWh de
intervalo inventaría consumo inicial.

## R6 — Reproducción y anomalías

**Decisión**: algoritmo versionado, enteros/Decimal y orden canónico. Usar SHA-256 de
semilla + versión + identidad lógica + índice + dominio para valores/selecciones, sin
`hash()` de Python ni azar global. Las tasas usan `floor(N*p/100)` por categoría sobre
N intervalos previstos; selección por ranking determinista en conjuntos disjuntos.
La referencia inicial de acumulados no entra en N. La corrupción estructural se aplica
al final a archivos seleccionados y se cuenta aparte.

**Razón**: igualdad lógica entre CSV/JSON y ejecuciones, incluso al cambiar el orden de
serialización. El reporte distingue muestras alteradas de consecuencias derivadas: una
lectura inválida puede impedir dos deltas. Un outlier acumulado se introduce cambiando
el incremento elegido y desplazando los contadores posteriores, conservando los demás
incrementos. Si es imposible bajo el descriptor/configuración, rechazar antes de generar.

**Alternativas**: tasas probabilísticas no garantizan conteos exactos; reclasificar como
anómalas todas las muestras de un archivo roto inflaría los conteos.

## R7 — Evidencia y responsabilidades

**Decisión**: informe local inmutable de generación más journal de intentos. El backend
conserva manifiesto, lecturas, pares/candidatos, errores de archivo/registro y referencias
al `ReceptionOutcome` real. Exportación técnica local de resultados para comparación;
incluye selección/corte/snapshot_id y un snapshot real de detalle o agregados001/002 en
la misma captura REPEATABLE READ que recepción. `compare` usa esa cobertura exportada;
su indisponibilidad produce evaluación parcial/no evaluable, nunca éxito global vacío.
El contraste manual puede usar GET identificando su propio corte. No se envía el oráculo
ni se añade endpoint público de inyección/confirmación o UI nueva. Las bandas del escenario
no se envían al receptor ni se convierten en reglas de limpieza. Un outlier positivo
aceptado por 001, que no define bandas físicas del edificio, es un hallazgo esperado de
contraste; no autoriza alterar 001 desde 003.

**Razón**: FR-018 permite contraste humano. 009 aporta auditoría común, 007 señales cuando
exista; los resultados funcionales no se reconstruyen desde logs. La evidencia backend
usa el mínimo de 12 meses calendario de 009 desde registro/revisión sustantiva y protege
sus dependencias. No se introduce purga automática de staging o resultados.

**Alternativas**: acoplar simulador a base/backend, importar notificaciones, o revelar el
oráculo al receptor rompería independencia y límites de propiedad.

## Cierre de investigación

Las decisiones técnicas quedan resueltas para el diseño local. R3 registra explícitamente
el límite de compatibilidad del dispositivo físico; R1 exige descriptores con procedencia,
no IDs inventados presentados como oficiales. Locks, fixtures independientes, captura
física futura y pruebas locales reales son entregables de implementación/validación,
no resultados obtenidos al crear estos documentos. No se modifica la spec ni su checklist.
