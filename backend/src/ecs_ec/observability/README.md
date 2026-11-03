# Emisor técnico007

`Telemetry` es un puerto interno best effort, compuesto desde `main.py` mediante
el lifecycle existente de009. Por defecto está deshabilitado. Ninguna operación
adquiere DB/locks de dominio ni espera red/disco para admitir señales. `begin`
entrega un handle interno; `stage` registra etapas y `complete` lo termina una vez.
`continue_operation` implementa el puerto conceptual `Telemetry.continue` del
contrato (palabra reservada de Python): conserva intento y crea ejecución/traza nueva.
`bind`/`current` ofrecen contextvars explícitos; nunca se propagan cabeceras públicas.

Los productores siguen siendo dueños de sus llamadas y transiciones durables. Esta
fase fundamental solo habilita terminales `operation.completed`; la semántica de
recepción/PDF y links de recuperación tiene tareas posteriores de007. No usar el
emisor como deduplicador, bus FunctionalEvent o evidencia contable. Un commit puede
sobrevivir sin señal si hay caída entre confirmación y admisión.

Para activar mediante variables de proceso, definir `OBS_ENABLED=true`,
`OBS_ENVIRONMENT=local|test|vps`, `OBS_SPOOL` (directorio exclusivo),
`OBS_CA`, `OBS_APP_CERT`, `OBS_APP_KEY`, `OBS_HEALTH_CERT`, `OBS_HEALTH_KEY`
(rutas absolutas a archivos externos). Certificados de aplicación y salud distintos.
Opcionales: `OBS_SERVICE_VERSION`, `OBS_POLICY_REVISION` (1–128caracteres),
`OBS_RETENTION_HOURS=168` (24 solo en test), `OBS_TRACE_RATIO=1.0`,
`OBS_OTLP_ENDPOINT=https://technical-gateway:8444/v1/traces`,
`OBS_HEALTH_ENDPOINT=https://technical-gateway:8446/collector-health`.
Configuración inválida imprime solo un diagnóstico fijo y deshabilita telemetría.
El perfil Compose/acceso humano todavía requiere las tareas US1 correspondientes.

El esquema empaquetado se copia del contrato normativo de007 con el comando de
`events.py`; pruebas comparan ambos. No editarlo independientemente. Solo el sobre
cerrado pasa al logger privado, colas y SDK. Código desconocido se convierte en
`unclassified`; otros campos/tipos libres se rechazan sin conservar su contenido.
No usar instrumentación automática de HTTP/SQL ni registrar objetos/excepciones.

Cola1023+control1 reemplazable, evento<=16KiB, spool8x16MiB con TTL y pérdidas
conservadoras por rotación. SDK privado<=256 spans activos/2048 pendientes,
atributos<=32/128caracteres, <=16KiB/span exportable y lotes<=512. OTLP usa
hasta3 intentos bajo deadline real total5s; respuestas parciales son fallo de lote.
Heartbeat15s: estado y fecha de logs/trazas independientes. Ausencia>45s implica
continuidad desconocida; falta de actividad no inventa fallo de transporte.
Una confirmación OTLP no certifica persistencia consultable. Shutdown comparte5s
entre salud/logs/trazas; residuo en cola/en curso cuenta como pérdida conservadora.

Verificación: `uv run pytest backend/tests/unit/observability backend/tests/contract/observability`.
Estos tests no acreditan cobertura de productores, acceso humano ni retención real.
