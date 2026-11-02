# Quickstart: validación local PAS600/SFTP

[Plan](plan.md), [modelo](data-model.md), [CLI](contracts/cli.md),
[perfil](contracts/pas600-profile.md), [recepción](contracts/sftp-reception.md).
Guía prevista para después de implementar; los comandos/módulos/fixtures de aplicación
todavía no existen. Esta planificación no ejecuta pruebas ni acredita sus resultados.

## Prerrequisitos

- CPython 3.14 y uv; para recepción, Docker Compose y PostgreSQL 18 real con DB de pruebas
  separada. Seguir la [guía de plataforma009](../009-fundaciones-plataforma/quickstart.md).
- Generación local no requiere backend, VPS, equipos, SMTP ni observabilidad.
- Integración: capacidades reales 009 + configuración/fuentes 001 + recepción/historial
  002. Sesión 006 para contrastar UI/HTTP protegida. No completar otras specs desde 003.
- Ejemplos sin secretos del [contrato CLI](contracts/cli.md), dos descriptores equivalentes
  CSV/JSON y fixtures independientes revisados contra la revisión documental fija.
- Receptor habilitado por `PAS600_SFTP_ENABLED=true`, binding de prueba al mismo edificio/
  fuentes que 001, puerto `127.0.0.1:2222`, host key persistida y volúmenes de adquisición.
  Variables/rutas concretas y procedimiento de carga del binding se documentan al implementar.
  Contraseña/clave privada fuera de escenarios/informes. Verificar clave pública local
  del servidor por canal administrado antes de crear `known_hosts` de prueba.

## Generación sin red

Desde la raíz del repositorio, una vez disponibles paquete, lock y ejemplos:

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
formatos representan mismas mediciones/tiempos; fixtures documentales y lector de pruebas
independiente validan conformidad, sin usar únicamente el parser ECS-EC como oráculo.
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

Preparar `.env` y binding local; las fuentes 001 se crean mediante su contrato de
configuración, sin insertar categorías desde el simulador. Habilitar listener y montar
host key/credenciales de prueba/volumen en la app de plataforma. En este diseño no hay
contenedor `sftp` separado. Con base y configuración reales:

```sh
docker compose up -d db
docker compose run --rm app uv run --locked alembic -c backend/alembic.ini upgrade head
docker compose up -d app
uv run --project tools/pas600_simulator --locked pas600-sim test-connection --transport tools/pas600_simulator/examples/transport.local.json
uv run --project tools/pas600_simulator --locked pas600-sim publish --run /tmp/ecs-ec-pas600-csv --transport tools/pas600_simulator/examples/transport.local.json
uv run --locked pytest backend/tests/unit/acquisition backend/tests/contract/acquisition backend/tests/integration/acquisition
```

Esperado: CLOSE confirmado por archivo; lote sellado únicamente tras EOF limpio; bytes/
manifiesto preservados; adaptador entrega una publicación lógica a 002; su resultado
indica aceptados/duplicados/rechazados por categoría y nunca se infiere de SFTP. Si el
último EOF se pierde, archivos transferidos pueden seguir sin lote sellado: reenviar todo.

La suite de integración usa PostgreSQL y transporte locales reales, no SQLite. Las pruebas
de aceptación de cadencia con red usan **900 segundos reales** después del fin de cada
intento; deben ser seleccionables como pruebas largas por el marcador `real_time` a
implementar, sin reducir el intervalo por variables de pruebas. Las pruebas unitarias
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

Comando técnico previsto, ejecutado por proceso de mantenimiento autorizado del entorno.
La selección es obligatoria: el ejemplo usa CAT-03, una hora y zona Etc/UTC; ajustar
fechas/zona/categorías al escenario y binding reales. Esa selección no revela anomalías.

```sh
uv run --locked python -m ecs_ec.acquisition.cli export-results --publication-ref PUBLICATION_REF --start 2026-01-01T00:00:00Z --end 2026-01-01T01:00:00Z --timezone Etc/UTC --categories CAT-03 --view hour --output /tmp/ecs-ec-pas600-reception.json
uv run --project tools/pas600_simulator --locked pas600-sim compare --run /tmp/ecs-ec-pas600-csv --reception /tmp/ecs-ec-pas600-reception.json --output /tmp/ecs-ec-pas600-comparison.json
uv run --project tools/pas600_simulator --locked pas600-sim report --run /tmp/ecs-ec-pas600-csv --output /tmp/ecs-ec-pas600-control.json
```

Sustituir `PUBLICATION_REF` por la referencia obtenida del resultado durable del receptor;
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


## Estado ejecutable local (2026-11-02)

Disponibles validate/generate y los ejemplos normales/anómalos; ver
[README del paquete](../../tools/pas600_simulator/README.md),
[validación US1 parcial](validation/us1.md) y [US3 parcial](validation/us3.md).
Los comandos de publicación/exportación/contraste de esta guía siguen siendo diseño
pendiente de implementación; no se han ejecutado. T003 fue diferida por el usuario;
los contratos locales permiten desarrollo, sin acreditar revisión documental19.
