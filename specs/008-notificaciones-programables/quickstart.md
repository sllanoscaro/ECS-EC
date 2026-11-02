# Quickstart y guía de validación

Esta guía define los comandos y escenarios que deberá ofrecer la implementación.
Actualmente solo existen especificaciones y artefactos de diseño: los comandos de app,
migración y pruebas siguientes no son ejecutables todavía. [tasks.md](tasks.md) recoge
el trabajo propio pendiente; no se afirma una validación funcional ya realizada.

Referencias: [plan](plan.md), [modelo](data-model.md), [API](contracts/openapi.json),
[integraciones](contracts/integrations.md) e [interfaz](contracts/ui.md).
Los ejemplos usan datos sintéticos y una base local desechable, nunca el relay de producción.

## Prerrequisitos y configuración

Preparar la base según [plataforma009](../009-fundaciones-plataforma/quickstart.md),
identidad según [spec-006](../006-acceso-usuarios-rbac/tasks.md), series según
[spec-001](../001-visualizar-consumo-categorias/tasks.md)/[spec-002](../002-registro-retencion-consumo/tasks.md)
y emisores/visores según [spec-007](../007-observabilidad-externa/tasks.md).
Su planificación pendiente no se ejecuta dentro de notificaciones. Contexto:
[arquitectura](../../docs/architecture.md) y [hoja de ruta](../../docs/implementation-roadmap.md).

- Docker Engine con Compose v2, uv con soporte Python 3.14 y Node >=20.9/npm para pruebas
  fuera del contenedor. Las versiones exactas proceden de lockfiles e imágenes del proyecto.
- Implementados los módulos de identidad/sesión de spec-006 y datos/calidad de specs-001/002,
  además de auditoría funcional común. Los productores reales de costos/PDF se entregan con
  [plan004](../004-costos-tarifa-bt43/plan.md), [tareas004](../004-costos-tarifa-bt43/tasks.md),
  [plan005](../005-generar-reportes-pdf/plan.md) y [tareas005](../005-generar-reportes-pdf/tasks.md),
  e integran `cost.failed`/`pdf.failed` mediante `audit/events.py` sin depender del consumidor de la spec-008.
  Solo sus alertas de sistema y aceptación integral esperan esos productores; otros incrementos
  con dependencias reales disponibles pueden validarse. Dobles no acreditan integración final.
- `.env.example`, Dockerfile multietapa, Compose, Alembic y comandos de la aplicación
  deben existir después de implementar. `.env` y secretos no se confirman en Git.

Configuración local prevista:

| Variable | Valor/propósito |
| --- | --- |
| `APP_ENV` | `local` |
| `APP_PUBLIC_BASE_URL` | `http://localhost:8000` |
| `BUILDING_TIMEZONE` | `America/Santiago`, dato sintético de prueba |
| `DATABASE_URL` | URL PostgreSQL del servicio `db`, credenciales locales propias |
| `MAIL_TRANSPORT` | `local_prueba` |
| `SMTP_HOST`, `SMTP_PORT` | `mailpit`, `1025` |
| `SMTP_STARTTLS_REQUIRED` | `false` solo para capturador local |
| `SMTP_FROM` | Remitente de prueba `ecs-ec@example.test` |
| `NOTIFICATION_POLL_SECONDS` | `5` |
| `NOTIFICATION_SEND_CONCURRENCY` | `4` |
| `PYTHONTZPATH` | Vacío para usar `tzdata` fijado |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Endpoint interno Jaeger del perfil técnico |
| `OTEL_TRACES_SAMPLER` | `always_on` en casos de referencia |

El perfil técnico configura credenciales Programador independientes, puerta de acceso
y visores de solo lectura según `deploy/README.md`. Ninguna cuenta funcional los habilita.
Pruebas y retención usan un reloj inyectable en el proceso de test, sin API pública para
cambiar la hora ni generar fallos. SMTP determinista es un adaptador exclusivo de tests.

## Arranque previsto

Desde la raíz del proyecto, después de completar la implementación:

```sh
cp .env.example .env
docker compose --profile local build app
docker compose --profile local up -d db mailpit
docker compose --profile local run --rm app uv run --locked alembic -c backend/alembic.ini upgrade head
docker compose --profile local run --rm app uv run --locked python -m ecs_ec.cli bootstrap-admin
docker compose --profile local --profile observability up -d
docker compose ps
```

Editar `.env` antes de arrancar. Bootstrap solicita la credencial de forma interactiva,
sin pasarla en argumentos ni imprimirla, y mantiene el cambio obligatorio de contraseña
de spec-006. Ingresar en `http://localhost:8000`, renovarla y crear desde administración
un segundo Administrador técnico y un Operador con correos `example.test` distintos.

Esperado: una única imagen/proceso de aplicación sirve UI y API; PostgreSQL está sano,
migraciones aplicadas y scheduler iniciado una sola vez. Mailpit muestra correos locales
en `http://localhost:8025`, publicado solo en loopback. UI técnica se alcanza a través de
su puerta de acceso; Loki, Jaeger query e ingestas no tienen acceso público directo.

La base monta `/var/lib/postgresql` para PG18. Reiniciar app conserva reglas e historial.
SMTP/observabilidad pueden caer sin retirar la disponibilidad funcional de la aplicación.

## Comprobaciones automatizadas previstas

```sh
uv sync --locked --group dev
uv run --locked pytest backend/tests/unit/notifications backend/tests/contract/notifications backend/tests/integration/notifications
npm --prefix frontend ci
npm --prefix frontend run test -- --run
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Las suites de integración usan PostgreSQL 18 y un esquema/base de prueba independiente
configurado en `TEST_DATABASE_URL`; se niegan a ejecutarse contra la base de producción.
La suite de contratos compara API implementada con `contracts/openapi.json`, valida
errores y permisos y no depende solo de snapshots. El build debe producir `frontend/out/`
sin funciones Node requeridas en ejecución. Playwright usa `APP_PUBLIC_BASE_URL` local.

Ejecutar estas suites una vez con Mailpit y los adaptadores funcionales reales. Los tests
de fallo usan transporte controlado para comprobar momentos que Mailpit no simula por sí solo.

## Escenarios y resultados esperados

### 1. Permisos, activación y cambios (SC-001, SC-006)

1. Administrador crea resumen de recepción/calidad; queda desactivado. Selecciona cuenta
   activa, programación diaria 06:00 y zona, revisa próximas fechas y activa.
2. Operador, Programador y sesión ausente intentan los mismos POST/PUT directamente:
   denegación, ningún cambio de versión/estado. Operador no consulta objetos de otra cuenta.
3. Añadir auditoría administrativa y seleccionar un Operador: no permite activar.
4. Probar sin destinatario, correo libre no registrado, NaN/infinito, umbral negativo,
   silencio <15 min y campos calendario incompatibles: 422 con razón de campo saneada.
5. Editar desde dos sesiones usando la misma revisión: una gana, la otra recibe 412.
   Repetir misma acción/clave idempotente devuelve recurso original sin nueva revisión.
6. Pausar/revisar cancela pendientes anteriores. No modifica intentos ya iniciados ni
   aceptados. El token de preview vencido/configuración cambiada exige nueva vista previa.

### 2. Calendario y ventanas (SC-002)

Con reloj controlado y tzdata fijado, probar cada intervalo y recurrencia permitida.
Diaria 06:00 produce una ocurrencia y ventana `[06:00 anterior,06:00 actual)`. Probar
hora inexistente -> primer instante válido posterior; repetida -> primera ocurrencia;
31 de enero -> último de febrero -> 31 de marzo; anual 29 de febrero -> último válido.
Los tests incluyen fechas DST reales de la versión tzdata fijada y expectativas explícitas.
Con dos versiones controladas de reglas horarias, iniciar una versión nueva con una fecha
futura afectada: antes de habilitar planificación, cambia solo el futuro no materializado,
conserva ocurrencias existentes y sus versiones/cortes e invalida preview afectado. Repetir
reinicio a mitad de reconciliación y demostrar reanudación sin duplicados ni scheduler prematuro.

Activar después de varias fechas históricas no reproduce esos envíos. Solo con todos los contenidos completos y conteo cero se envía «Sin novedades», sin afirmar
consumo cero. Probar primera ventana anterior al registro íntegro, conservación vencida,
fuente no consultable y mezcla de recepción completa con cambios administrativos desconocidos:
conservar conteos observados y períodos/huecos, mostrar NULL como no disponible y estado global
información insuficiente. La disponibilidad de logs técnicos no cambia esa cobertura. Cada
destinatario obtiene su entrega separada y no ve direcciones ajenas.

### 3. Urgencias y evidencia (SC-004)

Datos de referencia con ventanas completas posteriores a activación:

| Entrada/regla | Resultado |
| --- | --- |
| 100 kWh, `gt 100` | No abre episodio |
| 100 kWh, `gte 100` | Abre uno |
| 101 kWh, `gt 100`, reevaluado varias veces | Una sola urgencia |
| 99 kWh válido tras episodio, luego 101 | Cierra y permite nuevo episodio |
| Ventana incompleta tras episodio abierto | No evaluable, no cierra ni crea cero |
| CAT-01 calculada 20, base CAT-03/CAT-05, `gt 15` | Una urgencia, base/alcance visibles; no suma de nuevo |
| Falta una contribución del total calculado | No evaluable |
| Categoría parcial sin fuente | Sin alerta de ausencia ni consumo cero |
| Silencio configurado >=15 min desde última novedad/activación | Abre por reloj, sin nueva recepción |
| Duplicado o rechazo durante silencio | No reinicia el plazo |
| Lote histórico con muchas ventanas | Solo última admisible; período/retraso reales visibles |
| Mismo evento puntual reintentado | Una ocurrencia lógica |

Probar las cuatro comparaciones y todas las ventanas, sin promedios ni estimaciones para
completar huecos. Fuente CAT-01 calculada usa disponibilidad de totales válidos, no supuesto
medidor físico. Eventos funcionales PDF/costo/rechazo no adjuntan detalles técnicos.

### 4. Tiempo del primer intento (SC-003)

Perfil aprobado y obligatorio con reloj real: diez destinatarios elegibles, dos reglas
periódicas y dos urgentes coincidentes, cada una dirigida a las diez cuentas, 40 entregas
iniciales, cola vacía, cuatro plazas de envío y transporte local que confirma cada aceptación
en <=1 s. Mantener app/PostgreSQL/correo operativos y conservar la evidencia de ese límite
del transporte; si no se cumple, el ensayo no acredita este perfil y debe repetirse en sus
condiciones, sin ocultar los resultados observados.

Medir los 40 valores `attempt.started_at - scheduled_at` o `attempt.started_at - detected_at`:
cada uno <=60 s desde la referencia real correspondiente. El caso periódico aislado es una
comprobación adicional; no sustituye este caso mixto ni la equidad entre modalidades.
No sustituir reloj real por adelantar solo el falso ni medir únicamente inserción en cola.
Registrar recursos CPU/memoria, versiones/tzdata, carga y las cuarenta referencias/resultados;
el resultado no constituye una promesa para cualquier volumen de producción.

### 5. SMTP, reintentos y correo vigente (SC-005, SC-009)

En Mailpit revisar un único To, contenido/unidades/corte, URL local y etiqueta de transporte
de prueba. `aceptada` dice «por el servicio»; no afirma bandeja externa ni lectura.
Cambiar el correo de una cuenta antes del intento: llega a la dirección vigente y el
intento conserva esa dirección efectiva en historial funcional, nunca en telemetría.

Con adaptador determinista:

- Rechazo transitorio confirmado: tres intentos máximos, segundo >=1 min desde final del
  primero y tercero >=5 min desde final del segundo; misma entrega y Message-ID.
- Rechazo definitivo/configuración: un intento, estado fallida y causa funcional visible.
- Pérdida de confirmación tras DATA: indeterminada sin reintento. DATA confirmado seguido
  de fallo QUIT conserva aceptada si la confirmación pudo registrarse.
- Administrador autoriza reenvío de indeterminada con advertencia: nueva entrega vinculada;
  repetir petición con misma clave no crea otra. Operador no reenvía.
- Desactivar cuenta, retirar permisos o pausar regla antes de inicio cancela solo pendientes
  afectados. Un administrador degradado no conserva contenido administrativo por historial.

### 6. Reinicios y consolidación (SC-002, SC-005)

Detener app con varias ocurrencias periódicas todavía nunca intentadas y reiniciarla.
Esperado: un resumen recuperado por versión/cuenta con períodos originales identificados.
No incluir aceptadas, indeterminadas ni ya intentadas; los reintentos mantienen su identidad.
Repetir reinicio no recrea los mismos miembros de recuperación.

Detener durante SMTP y antes de persistir resultado. Sin evidencia inequívoca del relay,
el intento abierto se vuelve indeterminado, no pendiente automático. Ejecutar dos
consumidores de prueba sobre la misma base: cada clave lógica produce una sola entrega.

### 7. Aislamiento y observabilidad (SC-006, SC-009)

```sh
docker compose stop mailpit loki jaeger
```

Con correo/telemetría caídos, recibir datos válidos, consultar consumo/costos y generar
PDF: mantienen reglas y datos. No nace una cadena de alertas por el fallo de correo.
Colas técnicas no exceden límites definidos; pérdida/cobertura desconocida queda visible
al recuperar. Reanudar con `docker compose --profile local --profile observability up -d`.

Programador consulta logs, métricas LogQL y trazas correlacionadas; Operador/Administrador
no acceden por UI ni URL técnica directa. Revocar Programador deniega siguiente consulta.
Diez operaciones, ocho correctas y dos fallos inesperados -> conteo 10 y 20 % con cobertura
completa. Ausencia de heartbeat/pérdida no se presenta como cero. Inspeccionar señales con
datos sensibles sintéticos: sin correos, secretos, consumos individuales ni cuerpos.

### 8. Retención y enlaces (SC-007, SC-009)

Avanzar reloj de test al aniversario de 12 meses desde registro/revisión. Registros y sus
referencias siguen disponibles hasta ese límite; incluir 29 de febrero, hora inexistente
y hora repetida usando la ocurrencia posterior para retención (distinta del scheduler).
Consulta/duplicado no reinicia el plazo; telemetría expirada no elimina historia funcional.

En VPS, configurar `MAIL_TRANSPORT=smtp_produccion`, relay autenticado con STARTTLS
obligatorio, remitente y `APP_PUBLIC_BASE_URL` HTTPS real. Verificar enlaces desde otra red:
usan dominio público y exigen sesión/permisos, incluidos PDF. Credenciales/relay/URL real
se suministran al desplegar; no se realiza un envío remoto como parte de este plan.

### 9. Usabilidad (SC-008)

Medir diez tareas con Administradores técnicos representativos: configurar resumen diario
06:00 para una cuenta elegible e identificar siguiente envío, sin ayuda. Al menos nueve
terminan en <=3 min. Conservar resultados y obstáculos; una suite E2E no prueba este criterio.

## Evidencia de aceptación

Registrar versiones/lockfiles, tzdata, entorno, comandos, conteos, duraciones reales y
referencias de entregas/episodios de prueba. No guardar secretos ni cuerpos personales
en reportes técnicos. La finalización funcional requiere todos los escenarios aplicables;
las comprobaciones documentales del plan no sustituyen esas pruebas.
