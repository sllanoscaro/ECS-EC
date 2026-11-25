# Operación común

La plataforma es una imagen con un proceso Uvicorn y PostgreSQL 18 externo.
Identidad006 y observabilidad007 están incorporadas desde sus propietarios;
SMTP008 y urgencias/historial están verificados con Mailpit local; relay de producción
y enlaces externos008:T091 siguen pendientes.

Consumo 001 entrega contexto/fuentes, configuración versionada, reglas puras y consulta
web de detalle sobre recepción/almacenamiento 002 real. Para migración `cb63a76198be`, bootstrap
controlado, pruebas PostgreSQL aisladas y limitaciones, seguir su
[quickstart](../specs/001-visualizar-consumo-categorias/quickstart.md). El CLI usa archivos
locales y Settings 009, sin endpoints seed ni cuentas nuevas. Cambios posteriores al
bootstrap requieren límites históricos 002; no habilitar un sustituto que suponga historia vacía.

Historial 002 aporta ahora recepción/almacenamiento internos, agregados sincrónicos y
recuperación CAT-01 en el lifespan común. Migración `47457bdabdfa` y procedimientos de
próxima aceptación, reenvío/recuperación y reconciliación de calendario están en su
[quickstart](../specs/002-registro-retencion-consumo/quickstart.md).
La fachada/UI001, consulta agrupada y retirada protegida002 están integradas y verificadas
localmente; la integración consumidora003 también está verificada. La instrumentación ampliada007 está verificada; faltan personas. Consultar la
[aceptación parcial](../specs/002-registro-retencion-consumo/validation/acceptance.md).
Los procesos de recepción requieren bindings confiables por edificio, vacíos por defecto.
Respaldo/restauración incluyen estas tablas junto con el resto de PostgreSQL; no restaurar
solo el detalle omitiendo ledger, aportes, solicitudes, estados o auditoría.

La consulta está en `/consumption/` y la configuración de fuentes en
`/administracion/consumo/`, con permisos/sesión/CSRF de 006. `IDENTITY_BUILDING_ID`
debe coincidir con el contexto provisionado. No habilitar una configuración que suponga
historia vacía si falla el proveedor 002. Los límites de diagnósticos cruzados y gates
restantes se describen en [la evidencia vigente001](../specs/001-visualizar-consumo-categorias/validation/acceptance.md).

## Configuración local y construcción

Seguir el [README](../README.md) y el [quickstart](../specs/009-fundaciones-plataforma/quickstart.md).
`cp .env.example .env` crea solo valores sintéticos locales; configurar secretos reales
fuera del repositorio. Compose espera PostgreSQL sano y finalización de `migrate`.
La imagen ejecuta Uvicorn como usuario 10001, sin Node en runtime. `PUBLIC_URL`,
`BUILDING_TIMEZONE` y `ENVIRONMENT` se inyectan al arrancar. No usar `NEXT_PUBLIC_*` para
datos privados. La zona de ejemplo no confirma la del edificio. El build usa Webpack
explícitamente tras observar un fallo nativo de Turbopack.

Los servicios `db`, `migrate` y `app` representan infraestructura/migración y una aplicación.
PostgreSQL 18 monta `/var/lib/postgresql`, con `PGDATA=/var/lib/postgresql/18/docker`.
No aplicar upgrades mayores automáticos.

```sh
docker compose build app
docker compose up -d --wait app
docker compose logs app migrate
docker compose restart app
docker compose stop
```

`stop` y `down` sin `--volumes` conservan datos. La aplicación comprueba el head de Alembic
incluso cuando arranca directamente. `/api/v1/health/live` indica proceso vivo;
`/api/v1/health/ready` comprueba DB, esquema y exportación, con 503 seguro ante fallo.

Cada propietario registra rutas y context managers mediante
`create_app(modules=(Module(...),))` y detiene/espera sus tareas al salir. El cierre ocurre
en orden inverso, seguido del pool DB. Las migraciones enlazan el head real sin recrear
tablas compartidas. Los contratos de escritores están en [plataforma](../docs/platform.md).

## Respaldo y restauración

Se requieren clientes PostgreSQL 18. `PG_CONTAINER` permite usar los clientes del
contenedor PostgreSQL existente. Usar variables libpq o `PGPASSFILE` con permisos 0600
(ruta dentro del contenedor si corresponde), sin URLs con claves como argumentos.
`PGHOST`/`PGPORT` corresponden al espacio donde ejecuta el cliente; omitirlos para usar
el socket local del contenedor. No guardar respaldos en Git ni en la imagen.

```sh
# Consultar primero el nombre exacto con docker compose ps.
export PG_CONTAINER=ecs-ec-db-1
export PGUSER=ecs_local
export PGDATABASE=ecs_local
./deploy/backup.sh /tmp/ecs-ec-local.dump
docker compose exec db createdb -U ecs_local ecs_restore
export SOURCE_DATABASE=ecs_local
export PGDATABASE=ecs_restore
./deploy/restore.sh /tmp/ecs-ec-local.dump
```

El respaldo usa snapshot consistente de `pg_dump`, formato custom, permisos 0600 y
publicación atómica sin sobrescribir. Un fallo no publica archivos incompletos.
La restauración exige destino vacío distinto terminado en `_restore`, host local y nombre
sin connection strings. No usa `--clean`, aplica todo en una transacción y rechaza una
segunda restauración. La aplicación de origen no debe apuntar al destino de verificación.

Comparar filas completas, restricciones, fechas de conservación y `alembic_version`;
contar filas no basta. Ejecutar suites en otra base `_test`, nunca en respaldos reales.
La [evidencia local](../specs/009-fundaciones-plataforma/validation/restore.md) usa datos
sintéticos. Cifrar respaldos fuera del host, restringir acceso y comprobar restauración
periódicamente. Roles/ACL se provisionan externamente: `--no-owner --no-acl` conserva
filas/restricciones, no privilegios. No hay borrado automático ni downgrade destructivo.

## Preparación VPS

Configurar dominio/DNS reales, URL pública HTTPS, zona IANA real, credenciales externas y
volumen persistente. `ENVIRONMENT=production` valida HTTPS y rechaza la contraseña sintética.
Si la contraseña contiene caracteres reservados de URL, codificarlos en `DATABASE_URL`;
en Compose, adaptar explícitamente ese valor manteniendo la contraseña original de DB.
No exponer PostgreSQL a Internet.

Un proxy TLS de infraestructura del operador termina HTTPS y reenvía a `127.0.0.1:8000`.
Configurar certificado/renovación, redirección HTTP→HTTPS y firewall 80/443. Aceptar
cabeceras proxy solo desde el proxy confiable, con límites/timeouts. El acceso a la red
técnica de spec-007 no otorga acceso funcional; SMTP se verifica en spec-008.

Registrar CPU, RAM, disco libre, tamaño de volumen/respaldo y duración de construcción y
restauración en el entorno real antes de dimensionar; no hay SLO ni mínimo de recursos
aprobado. Reservar disco para DB, imagen y respaldo separados. Antes de publicar, comprobar
salud desde HTTPS, puertos internos cerrados, persistencia tras reinicio, secretos externos,
permisos del volumen y restauración independiente. No registrar claves ni filas personales.

La [validación VPS](../specs/009-fundaciones-plataforma/validation/vps.md) permanece pendiente
por falta de entorno real, según la decisión del usuario. La ejecución local no la acredita.

## Identidad humana (spec-006)

La [guía 006](../specs/006-acceso-usuarios-rbac/quickstart.md) configura `IDENTITY_ENABLED`,
claves HMAC externas y bootstrap. No hay contraseñas operativas predeterminadas ni alta
pública. La imagen ejecuta `--no-proxy-headers`: identidad verifica el peer real y confía
solo en `IDENTITY_TRUSTED_PROXIES`, con IP/CIDR explícitos y sin confianza universal.
Mantener el backend detrás del proxy previsto y el listener local publicado en loopback.
En HTTP local se exige development explícito/origen loopback y se rechaza un peer público,
incluso con Host falsificado. `X-Forwarded-Proto` de otro peer no habilita HTTPS efectivo.

```sh
docker compose exec app /app/.venv/bin/ecs-ec identity bootstrap-admin --email admin@example.test
docker compose exec app /app/.venv/bin/ecs-ec identity recover-admin --email admin@example.test --reason 'Recuperación operativa autorizada'
```

Ambos comandos requierenTTY, leen dos veces sin eco y no admiten password como argumento.
Bootstrap solo con cero cuentas. Recuperación solo sobre admin ya activo: no crea,
promueve ni reactiva. Captura revisión antes de Argon2 y la revalida bajo locks; revoca
sesiones, exige renovación y escribe actor `process:recovery`/código operativo en audit 009.
El motivo se valida (obligatorio, <=500 caracteres, sin controles); no se copia texto
libre al payload aprobado ni a logs. Entregar la contraseña inicial por canal operativo
protegido, fuera de esta aplicación, y el titular debe renovarla antes del acceso normal.

Mantener secretos/IDs estables entre reinicios. Para rotar CSRF, generar nueva clave/ID
único fuera del repositorio; contextos con el ID retirado exigen nuevo ingreso. No reutilizar
IDs ni retroceder configuración a claves retiradas. Para bucket, desplegar nueva clave/ID
y configurar `IDENTITY_PREVIOUS_LOGIN_BUCKET_KEY`/`..._ID` con los anteriores durante **al
menos30min**, sin procesos viejos escribiendo. El siguiente acceso migra la pareja bajo
locks, incluidos bloqueos activos, sin añadir fallos ni extender la espera. El arranque
falla cerrado si falta una clave de búsqueda para estado reciente/esperas aún activas.
Retirar después la anterior; conservar secreto/IDs según política externa de respaldo.

El hashing usa64MiB por trabajo, máximo inicial dos; mediciones locales en
[dependencias](../specs/006-acceso-usuarios-rbac/validation/dependencies.md). Medir recursos
en VPS antes de aumentar concurrencia. La limpieza interna cada60 s elimina lotes acotados
de sesiones/presesiones inválidas tras24h y buckets inactivos, conservando cuentas/audit.
La validez no depende del job; un fallo fija `identity_maintenance_failed` sin exponer SQL
ni secretos. No se ha implementado un emisor técnico paralelo a 007.

Un503 puede representar confirmación incierta. Recargar estado/revisión o ingresar de
nuevo antes de repetir; no afirmar rollback ni reenviar automáticamente una mutación.
La evidencia de la misma operación no se duplica cuando el commit ya se confirmó en DB.

Los respaldos 009 contienen PHC y estado de acceso; protegerlos y conservar claves externas
en almacén separado. Antes de servir un DB restaurado, con aplicación detenida, invalidar
sesiones/presesiones restauradas para no revivir cookies que se cerraron después del backup:

```sql
BEGIN;
UPDATE identity_session SET revoked_at=clock_timestamp(), revocation_code='account_changed' WHERE revoked_at IS NULL;
UPDATE identity_preauth SET consumed_at=clock_timestamp() WHERE consumed_at IS NULL;
COMMIT;
```

Comparar primero el snapshot según 009; después aplicar la invalidación técnica. Revisar
la antigüedad de credenciales del snapshot y recuperar/restablecer cuentas según operación
autorizada. Nunca borrar auditoría/cuentas ni limpiar esperas activas para resolver claves
perdidas. Las comprobaciones reales de VPS/personas siguen pendientes; los proveedores locales
de negocio se verifican en la regresión del paso4.

## Historial de consumo002

La consulta agrupada y la retirada interna usan los proveedores reales001/002/006 del
mismo monolito. Véanse [operación y pruebas002](../specs/002-registro-retencion-consumo/quickstart.md)
y [aceptación local](../specs/002-registro-retencion-consumo/validation/acceptance.md).
Mantener reloj UTC sincronizado y zona IANA/tzdata fijadas; next_admissible_at es un
límite de recepción de900 segundos, no una garantía de llegada. Reenvío explícito crea
otro attempt_id; recuperación usa el mismo. El lifespan recupera solicitudes/candidatos.
Respaldo/restauración incluyen ledger, payloads, agregados/aportes, configuración y auditoría.
La retirada no es una purga programada: exige proceso autorizado, motivo, vencimiento y
comprobación transaccional de dependientes. La validación local no acredita VPS.

## Costos BT4.3 (spec-004)

El mismo monolito incorpora `/costos/`, `/administracion/costos/` y `/api/v1/costs` cuando
identidad006 está habilitada. Aplicar las migraciones comunes hasta `costs_004_bills`;
no existe servicio adicional ni variable de precio predeterminada. Solo Administrador
configura suministro/perfil y confirma cálculos, boletas o contrastes; Operador consulta.

Antes de operar con importes reales, registrar CAT-01 física001, documentos/condiciones
del suministro y calendario completo BT4.3 con fuentes, precios, tributación, regla mensual
 y redondeo. Los fixtures exclusivamente sintéticos rechazan bases de aplicación y no
son datos de producción. Ver [procedimiento004](../specs/004-costos-tarifa-bt43/quickstart.md).

Respaldar toda la base: capturas, revisiones financieras, auditoría y eventos son evidencia
con conservación mínima por aniversario. Consultar no recalcula ni extiende plazos.
No ejecutar downgrade destructivo de costos; restaurar respaldo verificado ante reversión.
`cost.failed` se registra atómicamente en009; su productor no espera a008/SMTP. La captura
interna para005 está documentada en [contrato004](../specs/004-costos-tarifa-bt43/contracts/integrations.md).

## Reportes PDF (005)

Generación real de una páginaA4 mediante ReportLab, captura inmutable002/004,
preflight>=10pt, persistencia BYTEA/hash, supervisor con dos plazas, API y descarga
protegidas e interfaz `/reportes/`. Funciona sin008/SMTP ni visores técnicos activos.

**60/63 tareas verificadas técnicamente**. Quedan impresión física y evaluación con
personas (T037/T058/T059); no hay aceptación integral ni despliegue VPS acreditado.
[Resultados, comandos y cobertura](../specs/005-generar-reportes-pdf/validation/acceptance.md).
Las fixtures requieren PostgreSQL independiente `_test` y datos sintéticos. Nunca usar
la base de la aplicación para las limpiezas de pruebas. Los binarios no son archivos
públicos de la exportación estática.

## Observabilidad opcional (007)

[Stack, señales y limitaciones](observability/README.md) y
[frontera Programador, TLS/mTLS y revocación](technical-gateway/README.md).
El emisor no condiciona readiness, permisos, DB ni commits. El perfil técnico está
separado de SMTP008 y de identidad006. Cobertura001–006, métricas/continuidad y cuotas
físicas/corte90% están verificadas localmente en el [paso4](../specs/007-observabilidad-externa/validation/step4.md).
Retención24h/GC, recorrido final, aceptación humana y VPS continúan pendientes.

## Adquisición PAS600/SFTP (003)

La imagen incorpora AsyncSSH2.24.1 y la migración `f68f086ee8a7`, posterior a costos004.
El listener es opcional en el mismo Uvicorn; no hay servicio SFTP/worker separado.
Seguir la [provisión concreta003](../specs/003-simulador-pas600-sftp/quickstart.md) para
fuentes001 existentes, binding inmutable, host key administrada, auth.json privado y
known_hosts verificado. No usar una cuenta006 como identidad técnica SFTP.

PAS600_SFTP_ENABLED=false por defecto. Para habilitar, PAS600_RESOURCE_ROOT contiene
bytes/ y secrets/{host_key,auth.json}; dar propiedad al UID efectivo de app, privadas0600
y directorios0700. Compose monta bytes en /acquisition y secretos readonly; el puerto
host PAS600_PORT=2222 se publica en PAS600_BIND_ADDRESS=127.0.0.1 por defecto.
PAS600_STORAGE/HOST_KEY_FILE/AUTH_FILE permiten usar el CLI host con las rutas reales.
Montar material existente: una clave regenerada exige revalidación administrada del pin.

install-binding/export-results requieren un proceso incluido explícitamente en
PAS600_MAINTENANCE_PROCESSES y PAS600_MAINTENANCE_PROCESS en el entorno del comando.
Ejecutar cambios de binding sin sesiones receiving y reiniciar app para recargar los
procesos autorizados002. No hay endpoints públicos de seed/exportación. El mantenimiento
usa el edificio del binding y registra auditoría saneada; SFTP no crea fuentes ni usuarios.

Solo CLOSE explícito de todos los archivos seguido de CHANNEL_EOF limpio sella un lote.
La exclusión de listener es PostgreSQL; un segundo listener activo falla al iniciar.
Al reiniciar, sesiones receiving se abortan sin promover bytes y se recuperan evaluaciones
selladas conservando attempt_id/entrada002. Archivo ilegible, entrega uncertain y rechazo
002 son estados distintos. No editar manifests/bytes ni usar logs como evidencia durable.

El cliente comparte PAS600_SIM_STATE_DIRECTORY por alias/publicador entre procesos,
espera900s monotónicos desde fin y900s completos tras reinicio. Conservar ese directorio
y el control de cada run. Resend crea presupuesto nuevo, sin resetear cadencia/historial.

Para respaldar003 detener app y esperar cierre de canales/tareas; ejecutar backup009 y
copiar el volumen bytes completo con sus rutas relativas (incluidos abortados/pendientes)
antes de reanudar. Restaurar DB completa y ese volumen en un destino aislado; comparar
manifiestos/hashes, lecturas/pares/resultados002, estados y plazos. No purgar originales.
export-results detecta bytes faltantes/alterados y conserva una exportación anterior si
la captura falla. La [restauración local](../specs/003-simulador-pas600-sftp/validation/restore.md)
usa los scripts009 sin reescribirlos. Guardar secretos externos por separado y proteger
los respaldos completos que también contienen identidad/auditoría.

El emisor007 recibe operaciones ordinarias acquisition.receive/acquisition.process y
etapas authenticate/transfer/seal/claim/parse/validate/receive/publish; sus fallos no revierten commits. No certifica entrega al visor
por sí solo; continuación durable/cobertura transversal se verifican en el paso4. El journal externo conserva esperas/
reintentos sin depender del backend. Evidencia y limitaciones en
[aceptación003](../specs/003-simulador-pas600-sftp/validation/acceptance.md).
No se ejecutó VPS ni se certifica firmware físico: antes de habilitarlo comprobar IDs,
topología y la convención de sesión con captura real.


## Instrumentación instalada002/003 — paso3,2026-11-24

El mismo lifespan inyecta el emisor007 en recepción002, pendientes/agregados y
adquisición003. Las migraciones `consumption_002_context` y `acquisition_003_context`
requieren el procedimiento009 normal antes de iniciar la aplicación; agregan columnas
JSONB técnicas fuera de manifiestos/mediciones, sin nuevos servicios ni secretos requeridos.
Registros antiguos sin contexto se reconocen como unavailable y no inventan parentesco.

Recepción emite execution.completed por ejecución efectiva y reception.completed solo
tras su transición durable a completed. Fallo parcial: counts=null, sin terminal lógico;
recuperación: mismo intento, otra ejecución, resumen completo original. Acquisición
observa transferencia/sellado, parseo/deltas, espera, publicación y recuperación con
códigos fijos y UUID opacos persistidos. Reenvíos confiables comparten publicación y
crean otro intento. Lectura/replay completado no ejecuta procesamiento nuevo.

El fallo/saturación del destino no revierte commits de negocio ni auditoría009. Una
interrupción después del commit puede perder señal: los logs no reemplazan evidencia
funcional. No se emiten CSV/JSON nativo, nombres de archivo, valores, credenciales ni
texto de excepciones. [Evidencia002](../specs/002-registro-retencion-consumo/validation/telemetry.md),
[evidencia003](../specs/003-simulador-pas600-sftp/validation/telemetry.md).
Cobertura/visores/cuotas007 se verifican en el paso4; TTL real/GC sigue pendiente y SMTP008 permanece en su propietario.

## Notificaciones008: programación, urgencias e historial local

La [guía008](../specs/008-notificaciones-programables/quickstart.md) y su
[evidencia periódica](../specs/008-notificaciones-programables/validation/us2.md)
describen el incremento verificado. Urgencias y reenvíos tienen [evidencia local](../specs/008-notificaciones-programables/validation/us4.md); usabilidad y relay externo siguen pendientes. Mailpit pertenece al perfil opcional `mail`, con
imagen/digest fijados y puertos solo loopback; no participa en readiness.

`NOTIFICATION_ENABLED=false` es el valor inicial. Al habilitarlo, el monolito ejecuta
ciclos de hasta5s y un máximo de cuatro plazas SMTP. No hay worker desplegado por
separado. Un error de configuración opcional desactiva correo y conserva el acceso
funcional; un fallo de almacenamiento deja el trabajo durable pendiente o incierto.

En local usar `MAIL_TRANSPORT=local_prueba`, `SMTP_HOST=mailpit`, `SMTP_PORT=1025`
y `MAIL_FROM=ecs@example.test`. Éxito significa aceptación por el capturador.
`APP_PUBLIC_BASE_URL` vacío hereda `PUBLIC_URL`; un valor explícito debe apuntar al
origen funcional autenticado. Enlaces del correo no eluden sesión ni permisos.

Producción requiere `MAIL_TRANSPORT=smtp_produccion`, remitente autorizado, dominio
HTTPS real, `SMTP_PORT=587`, `SMTP_STARTTLS=true` y usuario/contraseña externos.
El adaptador exige verificación estándar de certificado y hostname, sin downgrade.
Timeout de socket10s y presupuesto total30s; una llamada de envío activa conserva
su plaza hasta finalizar. No se guardan respuestas SMTP ni credenciales en historial.
La configuración/certificado del relay real y los enlaces desde otra red siguen
pendientes de008:T091; una prueba local no los acredita.

Solo no aceptación temporal confirmada permite hasta tres intentos, con esperas de
uno y cinco minutos desde el fin del anterior. DATA aceptado sigue aceptado aunque
QUIT falle. Una confirmación perdida o un proceso interrumpido queda indeterminado
y no se reintenta automáticamente. Message-ID estable no garantiza deduplicación
externa. Tras reinicio se consolidan únicamente periódicos nunca intentados,
conservando miembros, períodos y huecos; los intentos previos no se incorporan de nuevo.

`/notificaciones/` muestra historial autorizado; el Operador solo ve su propia cuenta
y todo contenido aún permitido. `/notificaciones/reglas/` requiere administración.
La ventana inicial vacía informa conteo no disponible; cero conocido con historia
íntegra permite «Sin novedades». La retención técnica007 no reemplaza los12 meses
calendario de evidencia funcional. [Pendientes008](../specs/008-notificaciones-programables/tasks.md).
