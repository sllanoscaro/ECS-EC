# Contrato CLI y configuración del simulador

[Modelo](../data-model.md), [perfil](pas600-profile.md), [SFTP](sftp-reception.md).
Herramienta de pruebas externa opcional; no es la interfaz de usuarios de ECS-EC.
Comandos y archivos ejecutables siguientes se implementarán en la siguiente fase.

## Comandos

Instalación independiente prevista: `uv sync --project tools/pas600_simulator --locked`.
Pydantic2, AsyncSSH y simplejson son dependencias de ejecución en `project.dependencies`;
pytest y herramientas de pruebas van en `dependency-groups.dev`. La instalación con
`--no-dev` debe permitir validar/generar y publicar con las capacidades implementadas.
Ejecutable `pas600-sim` del paquete `pas600_simulator`:

| Comando | Entradas / salida y efectos |
| --- | --- |
| `validate --scenario FILE` | Valida estructura, descriptor, rangos, tasas/calendario; no escribe mediciones ni conecta. |
| `generate --scenario FILE --output DIR [--format csv\|json]` | Genera localmente archivos nativos, manifiesto/reporte separados y journal inicial. No red. Formato opcional prevalece sobre el escenario, conservando igual identidad lógica de muestras. |
| `test-connection --transport FILE` | Resuelve secretos, verifica host/autenticación/permisos con probe excluido de recepción; sin mediciones. |
| `publish --run DIR --transport FILE [--resume]` | Verifica hashes, valida cadencia y publica ciclos pendientes secuencialmente; puede detenerse con señal. Reanudación conserva journal/espera. |
| `resend --run DIR --publication KEY --transport FILE` | Presupuesto de intentos nuevo explícito, conjunto original completo; conserva ordinales/historial y cadencia. |
| `report --run DIR --output FILE` | Compone informe saneado con generación y transferencias, sin llamar al backend. |
| `compare --run DIR --reception FILE --output FILE` | Lee exportación técnica autorizada y reporta diferencias; solo archivos locales, sin mutar originales. |

`generate` rechaza output ya existente salvo carpeta vacía; no sobrescribe un escenario.
`publish` verifica que el directorio de datos contiene exactamente el manifiesto esperado,
no envía archivos de informe/configuración. El formato se elige en generación; cambiarlo
requiere nueva ejecución, no reserializar en un reintento.

Salidas: resumen humano y resultado JSON local versionado por comando; diagnósticos
saneados a stderr. Códigos: 0 operación completada (incluido `compare` sin diferencias),
2 configuración/argumentos, 3 identidad/autenticación/permisos, 4 transporte agotado,
5 evidencia ilegible/insuficiente o conflicto de estado local, 6 diferencias encontradas por `compare`,
130 parada solicitada. La señal guarda estados antes de salir cuando el proceso pueda
hacerlo; tras caída abrupta se recupera desde journal, nunca se presupone envío exitoso.
Una comparación distinta no significa fallo del generador: puede mostrar reglas legítimas
del receptor (por ejemplo, banda del escenario no aplicada por 001).

## Escenario (`schema_version=1`)

JSON validado estrictamente; campos desconocidos se rechazan. Categorías CAT-01..07
siempre aparecen una vez con `has_meter`; una sin medidor no incluye canal/rangos/tasas.
Cada presente incluye `meter`, descriptor del [perfil](pas600-profile.md), rango esperado
por duración/unidad y tasas `missing`, `format`, `out_of_range` (por defecto 0).

Campos raíz: versión del algoritmo/perfil, semilla (cadena), PAS600 publicador, zona IANA,
`start`, `end`, `sampling_minutes` (15 inicial), `publication_time` fijo, formato,
`categories`, `structural_corruptions` (lista de selectores de archivo y operación).
El calendario define ciclos lógicos por `samples_per_publication` entero >=1; en cada
ciclo se serializan todos los medidores presentes. El modo histórico permite muchos ciclos
sin esperas durante generación; publicación siempre respeta 900 segundos reales.

`start/end` y `publication_time` llevan offset; JSON nativo normaliza UTC y CSV preserva
fecha local/offset. Un período de doce meses usa extremos calendario explícitos, nunca
`365 days` como sustituto general. Las cadenas decimales del escenario se leen como
Decimal. Rango finito, quantum y contador inicial representables se comprueban antes
de cualquier escritura/publicación.

La semilla no contiene secretos. IDs, valores y selección se calculan con algoritmo
versionado SHA-256, dominios separados y orden canónico. El hash lógico ignora el formato,
output y tiempos reales; un hash de configuración completa adicional sí identifica el
formato. Un mismo caso en CSV/JSON conserva muestras, no promete archivos byte a byte
iguales entre formatos. Misma configuración completa y versión sí reproduce los bytes.

## Transporte (archivo separado)

Campos: `destination_alias`, `host`, `port`, `directory`, `username`, `known_hosts_file`,
`auth` (`password_env` o `private_key_file`, con `passphrase_env` opcional),
`publication_gap_seconds` (900 inicial), `max_attempts` (3 inicial),
`connect_timeout_seconds` (30), `operation_timeout_seconds` (60),
`attempt_timeout_seconds` (300). Valores positivos; intervalo >=900 y máximo >=1.
Timeouts acotan parada/recuperación y no son garantía de rendimiento.
El usuario corrige configuración si un lote necesita mayor timeout antes de reenviarlo.
No se aceptan password inline ni parámetros de línea de comandos con el secreto.
El informe solo registra alias/puerto, modo de autenticación sin credencial y resultado
saneado; no copia claves, valores del entorno ni transport file completo.

## Informe y contraste

Directorio de ejecución:

```text
RUN/
├── data/<publication-key>/<native-name>.csv|json
├── control/scenario.safe.json
├── control/expected.jsonl
├── control/anomalies.jsonl
├── control/manifest.json
├── control/run.json
└── control/transfers.jsonl
```

El plan exige configuraciones de ejemplo sin secretos en
`tools/pas600_simulator/examples/`: `seven-meters.json`, `partial-no-total.json`,
`anomalies-100.json`, `historical-12m.json`, `transport.local.json` y descriptores
marcados sintéticos. El fixture de anomalías tiene 100 intervalos por categoría objetivo,
10 % por clase y cero en las demás. La referencia acumulada extra no entra en esos 100.
La configuración por defecto representa siete medidores y cero anomalías; no impone
esa topología a una instalación. Las correspondencias backend se cargan separadamente,
con fuentes reales 001 creadas por su propietario, nunca desde los archivos publicados.

La exportación técnica del backend, distinta de `pas600-sim`, usa el proceso autorizado
de mantenimiento y exige selección explícita:

```text
python -m ecs_ec.acquisition.cli export-results
  --publication-ref REF --start INSTANT --end INSTANT --timezone IANA
  --categories CAT-03,CAT-05 --view detail|hour|day|month|year --output FILE
```

`--categories` es lista no vacía de categorías únicas CAT-01..07; `--start/--end` llevan
offset y son crecientes, `--timezone` debe coincidir con la zona del edificio resuelto
desde la publicación y `--view` selecciona detalle o una agrupación existente001/002.
Estos filtros no contienen datos esperados ni marcas de anomalía. La selección y los
resultados reales quedan incluidos en el snapshot del [contrato de exportación](sftp-reception.md).

`compare` correlaciona manifiesto/hash/nombre/posición o extremos de un delta; informa
aceptaciones esperadas/inesperadas, rechazos, duplicados, datos no evaluables y huecos
esperados frente a cobertura de `consumption_snapshot`. Requiere `snapshot_id`,
`cutoff_at` y `selection` coherentes con la ejecución; compara solo el alcance declarado
y señala intervalos/categorías o bloques excluidos que no puede evaluar. No asume que
todas las anomalías deban ser rechazadas: identifica el criterio de aceptación aplicado.
No necesita red ni otro archivo de cobertura, pues recibe los resultados001/002 en la
misma exportación de recepción. El contraste manual mediante GET sigue siendo posible,
pero una respuesta obtenida después no sustituye silenciosamente ese snapshot.

La salida incluye `comparison_status: complete|partial|not_evaluable`, selección,
snapshot_id/cutoff_at, diferencias observadas y limitaciones. `complete` exige evidencia
suficiente para todo el alcance declarado. Si `consumption_snapshot.status=unavailable`
o faltan evidencias protegidas, puede completar la parte de recepción pero debe marcar
la evaluación global como partial o not_evaluable. Código0 solo cuando complete y sin
diferencias; código6 si detecta diferencias, incluso con limitaciones declaradas;
código5 si falta evidencia para concluir y no hay diferencias ya demostradas.
Exportación ausente/ilegible/ajena también produce código5, no una lista vacía de éxito.
