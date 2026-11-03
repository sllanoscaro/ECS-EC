# Quickstart: validación local PAS600/SFTP

[Plan](plan.md), [modelo](data-model.md), [CLI](contracts/cli.md),
[perfil](contracts/pas600-profile.md), [recepción](contracts/sftp-reception.md).
**Estado2026-11-03:** implementados validate/generate/test-connection/publish/resend/
report/compare y el módulo backend acquisition con mantenimiento/exportación. La
conformidad documental19, reproducción por otra persona, ampliación técnica007 y cierre
integral permanecen pendientes. [Evidencia](validation/acceptance.md).

## Prerrequisitos

- CPython 3.14 y uv; para recepción, Docker Compose y PostgreSQL 18 real con DB de pruebas
  separada. Seguir la [guía de plataforma009](../009-fundaciones-plataforma/quickstart.md).
- Generación local no requiere backend, VPS, equipos, SMTP ni observabilidad.
- Integración: capacidades reales 009 + configuración/fuentes 001 + recepción/historial
  002, ya disponibles. Sesión006 para contrastar UI/HTTP protegida, también disponible.
  Ver [prerrequisitos vigentes](validation/prerequisites.md); no completar otras specs desde003.
- Ejemplos sin secretos del [contrato CLI](contracts/cli.md), descriptores equivalentes
  CSV/JSON y fixtures sintéticos independientes; revisión documental19 aún diferida.
- Para SFTP habilitar PAS600_SFTP_ENABLED tras instalar un binding de prueba al mismo
  edificio/fuentes001. Host key/credenciales/bytes externos y known_hosts administrado;
  provisión concreta abajo. La identidad técnica no utiliza sesión humana006.

## Generación sin red

Desde la raíz del repositorio, con paquete, lock y ejemplos ya disponibles:

Pydantic2/AsyncSSH/simplejson deben estar en `project.dependencies`, y pytest/herramientas
de pruebas en `dependency-groups.dev`. Comprobar primero el uso normal sin grupo dev:

```sh
uv sync --project tools/pas600_simulator --locked --no-dev
uv run --project tools/pas600_simulator --locked --no-dev pas600-sim validate --scenario tools/pas600_simulator/examples/seven-meters.json
uv run --project tools/pas600_simulator --locked --no-dev pas600-sim generate --scenario tools/pas600_simulator/examples/seven-meters.json --format json --output /tmp/ecs-ec-pas600-runtime
```

Esperado: validación y generación completas sin instalar pytest ni el backend. Usar un
output nuevo/vacío; no ejecutar ese comando contra un directorio de evidencia existente.
Luego instalar el grupo dev para las pruebas y la comparación de formatos:

```sh
uv sync --project tools/pas600_simulator --locked --group dev
uv run --project tools/pas600_simulator --locked pas600-sim validate --scenario tools/pas600_simulator/examples/seven-meters.json
uv run --project tools/pas600_simulator --locked pas600-sim generate --scenario tools/pas600_simulator/examples/seven-meters.json --format csv --output /tmp/ecs-ec-pas600-csv
uv run --project tools/pas600_simulator --locked pas600-sim generate --scenario tools/pas600_simulator/examples/seven-meters.json --format json --output /tmp/ecs-ec-pas600-json
uv run --project tools/pas600_simulator --locked pytest tools/pas600_simulator/tests/unit tools/pas600_simulator/tests/contract
```

Usar directorios nuevos/vacíos. Esperado: solo los medidores presentes en archivos
nativos; configuración/oráculo/anomalías/journal en `control/`, nunca publicados. Los dos
formatos representan mismas mediciones/tiempos; el lector de pruebas
independiente valida los contratos locales, sin sustituir la revisión documental19.
Repetir en otro output con mismo escenario/semilla: datos y asignaciones idénticos;
UUID/tiempos reales distintos identificados. Confirmar explícitamente el caso 100/104 kWh
con un delta de 4 kWh y primera referencia sin consumo.

```sh
uv run --project tools/pas600_simulator --locked pas600-sim generate --scenario tools/pas600_simulator/examples/historical-12m.json --output /tmp/ecs-ec-pas600-history
uv run --project tools/pas600_simulator --locked pas600-sim generate --scenario tools/pas600_simulator/examples/partial-no-total.json --output /tmp/ecs-ec-pas600-partial
uv run --project tools/pas600_simulator --locked pas600-sim generate --scenario tools/pas600_simulator/examples/anomalies-100.json --output /tmp/ecs-ec-pas600-anomalies
```

Histórico: extremos explícitos de doce meses calendario, siete categorías, generación
local sin esperas/red. Registrar conteos, tamaño y tiempo sin inventar un SLO. El ejemplo
parcial usa CAT-03/CAT-05 y ninguna lectura CAT-01; su resultado integrado debe obtener
CAT-01 solo por 001/002. El caso de anomalías debe mostrar 100 previstas = 10 omitidas +
10 formato + 10 fuera de rango + 70 sin alterar, sin solaparse. Para acumulados hay
referencia extra y el informe enumera consecuencias de extremos inválidos por separado.

## Receptor local y publicación

Preparar `.env` y fuentes001 siguiendo su [provisión controlada](../001-visualizar-consumo-categorias/quickstart.md).
El binding003 usa esos UUID existentes; no crea fuentes ni cuentas. Tomar un escenario
con timezone/offsets y medidores compatibles con esa configuración. Preparar un directorio
externo con bytes/ y secrets/, propietario del UID efectivo de app (10001 por defecto).
PAS600_RESOURCE_ROOT apunta a él; secrets se monta readonly y sus privadas son0600.

Provisión local administrada con claves externas (no ejecutar sobre material existente):

```sh
export PAS600_RESOURCE_ROOT=/ruta/privada/pas600-local
uv run --locked python - <<'PYKEYS'
import json, os
from pathlib import Path
import asyncssh
root=Path(os.environ['PAS600_RESOURCE_ROOT'])
(root/'bytes').mkdir(parents=True, mode=0o700, exist_ok=False)
(root/'secrets').mkdir(mode=0o700)
host=asyncssh.generate_private_key('ssh-ed25519')
client=asyncssh.generate_private_key('ssh-ed25519')
host.write_private_key(root/'secrets/host_key')
client.write_private_key(root/'client_key')
for path in (root/'secrets/host_key',root/'client_key'):path.chmod(0o600)
auth=root/'secrets/auth.json'
auth.write_text(json.dumps({'pas600': {'public_keys':[client.export_public_key().decode()]}}))
auth.chmod(0o600)
(root/'known_hosts').write_bytes(b'[127.0.0.1]:2222 '+host.export_public_key())
PYKEYS
```

El known_hosts se deriva de la clave administrada, no de una conexión sin verificar.
Mantener client_key solo en el cliente; ajustar propiedad de secrets/bytes al UID app
antes de montar. Para contraseña, auth.json admite password_hash Argon2 generado con
getpass/PasswordHasher; el cliente usa password_env. Nunca copiar texto claro al archivo.

Crear /ruta/privada/binding.json validando contra BindingInput de acquisition/schemas.py.
Ejemplo sintético de un canal (cambiar UUID/zona/medidores según001 y escenario):

```json
{
  "id":"00000000-0000-0000-0000-000000000bbb", "revision":1,
  "building_id":"00000000-0000-0000-0000-000000000063",
  "username":"pas600", "directory":"/", "timezone":"America/Santiago",
  "publisher_serial":"SYNTHETIC-PAS600", "publisher_remote_id":"synthetic-pas600",
  "channels":[{
    "source_id":"00000000-0000-0000-0000-000000000003", "category_id":"CAT-03",
    "device_local_id":"3", "reduced_id":"3_mb", "device_name":"iEM3150 CAT03",
    "csv_topic_id":"SYNTHETIC.3.energy", "json_value_item_id":"synthetic/3/energy",
    "unit":"kWh", "sampling_minutes":15, "semantics":"cumulative",
    "timestamp_role":"reading_instant", "provenance":"synthetic",
    "evidence_ref":"synthetic:local-guide"
  }]
}
```

Añadir un canal por cada medidor realmente seleccionado, con fuente001 existente.
No incluir CAT-01 si no tiene medidor. Revisiones nuevas incrementan revision y conservan
historia; requieren no tener sesiones receiving. Reiniciar app tras cambiar bindings para
recargar la lista de procesos002 autorizados. Los descriptores no se deducen de etiquetas.

Configurar PAS600_MAINTENANCE_PROCESSES=process:pas600-maintenance. Con app deshabilitada
para SFTP instalar primero el binding por CLI host con DATABASE_URL del despliegue:

```sh
export PAS600_MAINTENANCE_PROCESSES=process:pas600-maintenance
export PAS600_MAINTENANCE_PROCESS=process:pas600-maintenance
uv run --locked alembic -c backend/alembic.ini upgrade head
uv run --locked python -m ecs_ec.acquisition.cli install-binding --file /ruta/privada/binding.json
```

Luego PAS600_SFTP_ENABLED=true y reconstruir/arrancar app. En Compose también se puede
copiar el binding sin secretos con docker compose cp y ejecutar el mismo módulo mediante
/app/.venv/bin/python con -e PAS600_MAINTENANCE_PROCESS=process:pas600-maintenance.
No hay endpoint público de mantenimiento ni autorización derivada de Programador.
Copiar transport.local.json fuera del repositorio y ajustar known_hosts_file,
auth.private_key_file, alias estable, puerto y directorio; quitar auth.password_env al usar clave.
Con base y configuración reales:

```sh
docker compose up -d db
docker compose run --rm migrate
docker compose up -d app
uv run --project tools/pas600_simulator --locked pas600-sim test-connection --transport /ruta/privada/transport.json
uv run --project tools/pas600_simulator --locked pas600-sim publish --run /tmp/ecs-ec-pas600-csv --transport /ruta/privada/transport.json
uv run --locked pytest backend/tests/unit/acquisition backend/tests/contract/acquisition backend/tests/integration/acquisition
```

Esperado: CLOSE confirmado por archivo; lote sellado únicamente tras EOF limpio; bytes/
manifiesto preservados; adaptador entrega una publicación lógica a 002; su resultado
indica aceptados/duplicados/rechazados por categoría y nunca se infiere de SFTP. Si el
último EOF se pierde, archivos transferidos pueden seguir sin lote sellado: reenviar todo.

La suite de integración usa PostgreSQL y transporte locales reales, no SQLite. Las pruebas
de aceptación de cadencia con red usan **900 segundos reales** después del fin de cada
intento; son seleccionables por el marcador `real_time`, sin reducir el intervalo por variables de pruebas. Las pruebas unitarias
usan reloj inyectado para 899/900 s y no acreditan por ello SC-004 en red.

## Casos de aceptación y resultados esperados

| Caso / criterio | Preparación y evidencia que conservar |
| --- | --- |
| Formatos normales, US1/SC-001 | Siete medidores y anomalías desactivadas; conformidad contra referencia independiente; equivalencia de valores/instantes y nombres/cortes por dispositivo/frecuencia/24 h/256000 bytes. |
| Categorías opcionales, US1/SC-001 | CAT-03/CAT-05 sin medidor total; solo dos medidores publicados, base calculada correcta en 001/002. Categorías ausentes no cuentan como omitidas; con CAT-01 medida conserva su valor aunque difiera de parciales. |
| Acumulados, US1/FR-006 | Inicial, igualdad/cero, hueco, inválida, descenso/reset, tardía y cambio de descriptor/fuente. Ningún puente de hueco, reparto ni consumo anterior a referencia; pares/intervalos trazables. |
| Cadencia, US2/SC-004 | Intento lento, siguiente envío/reintento desde fin +900 s, categorías juntas y publicación fragmentada; timestamps monotónicos/UTC reales y resultados 002; una actualización lógica por categoría. |
| Seguridad/errores, US2 | Host desconocido/cambiado, clave/contraseña inválida, directorio sin permiso y prueba de conexión: fallo claro, ninguna medición publicada y ningún secreto en salidas. Probar password y clave. |
| Completitud, US2/SC-004 | Interrumpir escritura, perder conexión después de CLOSE y antes de EOF, cerrar por limpieza, excepción del cliente tras primer archivo: ninguno sella lote parcial. Archivo cerrado con EOF limpio sí permite sellar; comprobar volúmenes tras reinicio. |
| Reenvío, US2/SC-004 | Persistir ID/entrada antes de llamar002 y perder respuesta tras commit: read_attempt encuentra resultados originales; accept con mismo ID/entrada completa solo lo no confirmado, incluso ante dos recuperaciones. Otra entrada con igual ID falla attempt_payload_conflict. Reenvío completo nuevo conserva bytes/identidad y usa ID nuevo; too_early confirmado no se reevalúa en recuperación. DB fallida nunca se interpreta not_found. |
| Agotamiento/parada, US2/US4 | Tres intentos totales, espera real, archivos pendientes conservados; señales sin nuevo ciclo; timeout aborta sin EOF y journal recuperable. Reenvío manual conserva historial/cadencia. |
| Tasas, US3/SC-002 | 100 con 10/10/10; 0/100 % por clase, suma >100 rechazada, posiciones disjuntas, categorías no elegidas intactas, rango/duración/unidad inválidos rechazados antes de generar. |
| Corrupción, US3 | Tipos/fechas por registro y archivo estructuralmente roto seleccionado: conteo por archivo separado. Otros archivos se interpretan; una corrupción transferida figura transferida y parseo fallido, no fallo de transporte. |
| Bandas, US3/FR-014 | Rango 0..10 kWh/15 min: outlier >10 o <0. Contrastarlo con reglas reales 001; un positivo elevado puede aceptarse, sin agregar una regla de limpieza desde el simulador. |
| Reproducción, US4/SC-003 | Misma semilla/configuración/período/algoritmo en carpetas distintas: 100 % de valores/instantes/posiciones iguales. CSV/JSON equivalentes, tiempos de transferencia separados. |
| Contraste, US4/SC-005 | Exportación con selección/snapshot_id/corte y recepción+consumo en la misma captura: tres intervalos de15min dentro de una hora dan2700s cubiertos/75%; detectar si la cobertura observada figura completa. Snapshot indisponible permite contraste parcial de recepción, pero nunca éxito global sin diferencias; no subir el oráculo al receptor. |
| Historial, US1/SC-006 | >=12 meses simulados, siete categorías sin hardware/espera histórica. Preparar consultas hora/día/mes/año y retención 002; publicar ciclos a cadencia real o cargar fixtures por puerto interno en pruebas 002, sin llamar SFTP a esa inyección. |
| Reinicio/protección, transversal | Crash antes/después de fsync/sellado/commit/copia de resultado; solo estados demostrables, idempotencia de pares/candidatos, evidencia protegida y manifiestos pendientes conservados. |

Para cobertura, usar los GET y permisos descritos por [001](../001-visualizar-consumo-categorias/contracts/http.md)
y [002](../002-registro-retencion-consumo/contracts/http.md). No insertar SQL para simular
una aceptación funcional. Reloj inyectado solo en pruebas internas; no un endpoint público.
El caso histórico de doce meses prepara pruebas de conservación, no demuestra que haya
transcurrido el mínimo desde la aceptación real del registro.

## Exportar y comparar resultados

Comando técnico implementado, ejecutado con PAS600_MAINTENANCE_PROCESS autorizado.
La selección es obligatoria: el ejemplo usa CAT-03, una hora y zona Etc/UTC; ajustar
fechas/zona/categorías al escenario y binding reales. Esa selección no revela anomalías.

```sh
uv run --locked python -m ecs_ec.acquisition.cli export-results --publication-ref PUBLICATION_REF --start 2026-01-01T00:00:00Z --end 2026-01-01T01:00:00Z --timezone Etc/UTC --categories CAT-03 --view hour --output /tmp/ecs-ec-pas600-reception.json
uv run --project tools/pas600_simulator --locked pas600-sim compare --run /tmp/ecs-ec-pas600-csv --reception /tmp/ecs-ec-pas600-reception.json --output /tmp/ecs-ec-pas600-comparison.json
uv run --project tools/pas600_simulator --locked pas600-sim report --run /tmp/ecs-ec-pas600-csv --output /tmp/ecs-ec-pas600-control.json
```

Sustituir `PUBLICATION_REF` por acquisition_publication.publication_ref, consultado por
el proceso de mantenimiento autorizado en la DB del despliegue (no desde el clienteSFTP);
no se expone un listado público. Ajustar PAS600_STORAGE al volumen real al usar CLI host;
no por un UUID que el cliente haya declarado como identidad confiable. No otorga acceso
funcional por el rol Programador. Contrastar también períodos/energía/cobertura por los
contratos de consumo incluidos en `consumption_snapshot`: verificar snapshot_id,
cutoff_at, selection y los resultados reales de todas las categorías en la misma captura.
Con estado unavailable el contraste puede informar recepción parcial, pero código0 solo
significa comparación completa sin diferencias; código6 señala diferencias observadas y
código5 evidencia insuficiente sin diferencias ya demostradas. Mantener limitaciones en
el JSON y no fabricar cobertura cero ante un fallo. La verificación visual del gráfico
usa la UI/GET protegida y registra su corte si es distinto del snapshot exportado.

Guardar versiones/locks, revisión y hash de referencias, configuración saneada, semilla,
comandos, reportes, resultados durables y tiempos reales en
`specs/003-simulador-pas600-sftp/validation/acceptance.md` al ejecutarlos. Una segunda
persona reproduce con los ejemplos/documentación y registra el contraste US4.
Sin resultados reales no se marcan checklists ni se declara SC-001..006 cumplido.
VPS requiere destino/secretos reales y configuración de red. Un PAS600 físico requiere
además comprobar sus IDs/topología y frontera de sesión; las pruebas sintéticas no lo
acreditan y no se reetiquetan como integración física.


## Suites seleccionadas y límites

```sh
uv run --locked pytest backend/tests/integration/acquisition/test_real_time_publication.py -m real_time -q -s
PAS600_RESTORE_CONTAINER=NOMBRE_CONTENEDOR_POSTGRES uv run --locked pytest backend/tests/integration/acquisition/test_restore.py -m restore -q
```

Configurar TEST_DATABASE_URL separada terminada _test; restore usa otra DB vacía única
_restore y elimina solo ese destino. Las dos pruebas real_time tardan al menos30 minutos.
Las suites rápidas excluyen real_time/restore por defecto. [Resultados US2](validation/us2.md),
[US3](validation/us3.md), [US4](validation/us4.md) y [restauración](validation/restore.md).

No hace falta PDF005, SMTP008, VPS ni hardware para esos ensayos locales. No marcan
las verificaciones pendientes de otras specs. T003/T008/T009/T021 siguen abiertas por
referencia19 diferida; T070 por persona independiente; T072 por alcance técnico007;
T076 por aceptación integral. Los checklists de calidad no se modifican.
