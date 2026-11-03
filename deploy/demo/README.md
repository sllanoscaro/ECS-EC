# Demostración local con publicaciones por cuarto de hora

Desde la raíz, con `.env` e identidad preparados:

```sh
docker compose up -d --build --wait
```

Compose carga `compose.override.yaml`: PostgreSQL, migraciones, provisión sintética,
aplicación y simulador. Solo admite ENVIRONMENT=local. Las cuentas, claves, configuración
administrativa e historial se conservan. Una instalación ajena se rechaza.

## Arranque y actualización

Al iniciar a las18:20 en BUILDING_TIMEZONE, el simulador genera/publica inmediatamente
los intervalos completos desde00:00 hasta18:15. A las18:30 publica solo18:15–18:30;
luego18:30–18:45, etc. El instante de arranque no desplaza las publicaciones. No hay
lecturas futuras. Antes de00:15 se espera al primer intervalo completo. Los horarios
se calculan con instantes UTC y la zona IANA del edificio, incluidos cambios de día/offset.

La generación conserva su referencia diaria determinista: el envío incremental filtra
las muestras ya emitidas sin cambiar sus energías. Al reiniciar se reenvía el prefijo
completo del día; la recepción reconoce duplicados sin duplicar filas ni energía.
Los archivos y el journal previos permanecen en `demo_data`.

La demo usa una política explícita de calendario: transport.local_calendar=true y
DEMO_CALENDAR=true en el receptor. Permite carga inicial inmediata y admisión al siguiente
cuarto de hora aunque hayan transcurrido menos de900s desde la carga inicial. Ambas
opciones rechazan producción. La política normal sigue exigiendo900s reales desde el
fin del intento y recuperación conservadora tras reinicio. La base registra la política
de admisión; la migración `demo_calendar_admission` conserva el modo estricto por defecto.

El backend entrega por archivo compartido privado únicamente la configuración de fuentes
vigente. El simulador publica solo canales sintéticos activos: CAT-01 se omite cuando
el total es calculado; lo incorpora exclusivamente002 a partir de contribuciones aceptadas.
Los totales calculados se evalúan en la misma recepción, sin una segunda espera.
La interfaz consulta una sola vez por cuarto de hora, cinco segundos después del cierre
(:00:05, :15:05, :30:05 y :45:05), conservando el gráfico visible durante la consulta.
Si la lectura no está disponible, el botón Actualizar permite consultarla manualmente;
no hay sondeos ni reintentos automáticos entre cierres. La llegada y procesamiento tienen una latencia breve,
no una garantía instantánea. Verificar aceptación funcional además del transporte.

## Total calculado o medido

El valor inicial es el total calculado de CAT-02 a CAT-07. Las barras del dashboard
representan la energía de cada categoría dividida por la energía total del mismo día;
la categoría de mayor consumo no se usa como escala. En
`/administracion/consumo/`, elegir «Origen de la energía total»: total calculado o
medidor propio. Para el segundo, elegir «Demo CAT-01» y guardar. Su canal independiente
no tiene por qué coincidir con la suma de categorías. Las elecciones sobreviven reinicios.
Los cambios son prospectivos: el historial conserva su origen y un intervalo que cruza
el cambio puede quedar excluido. Reiniciar servicios no reescribe ese historial.

La cobertura diaria evalúa desde medianoche hasta el último cuarto de hora cerrado,
indicado en la interfaz. Con todos esos intervalos válidos muestra100%; el intervalo
abierto no reduce el porcentaje. Un intervalo cerrado ausente sí reduce la cobertura,
aunque la última lectura disponible sea anterior. Antes del primer cierre muestra «—».

## Operación y diagnóstico

```sh
docker compose logs -f --timestamps --tail=100 simulator app
docker compose stop
docker compose up -d --wait
```

Los logs del simulador muestran el rango enviado y la próxima publicación. Las claves,
bytes y evidencia persisten en `demo_data`; no borrar journals para cambiar la cadencia.
La evidencia crece mientras se utiliza la demo. Los servicios db/app/simulator se
reinician automáticamente con Docker (`restart: unless-stopped`).

Para instalaciones reales excluir la extensión local en todos los comandos:

```sh
docker compose -f compose.yaml up -d --build --wait app
```

## Reinicio explícito del consumo sintético

Con app y simulador detenidos, realizar un respaldo PostgreSQL completo en formato custom,
comprobar su lista con pg_restore y conservarlo fuera del repositorio. `reset.py` requiere
ese archivo, contexto sintético y ausencia de configuración de costos. Conserva cuentas
y auditoría; reinicia consumo/adquisición y reprovisiona las fuentes elegidas con vigencia
histórica, para poblar el día completo. Es una acción explícita, nunca parte del arranque.

```sh
docker compose stop simulator app
# Respaldar y validar primero según deploy/README.md.
docker compose run --rm --no-deps -v /ruta/backup.dump:/backup.dump:ro demo-setup \
  /app/.venv/bin/python /runner/reset.py --backup-file /backup.dump
docker compose up -d --wait
```

## Verificación

```sh
uv run --project tools/pas600_simulator --locked --group dev python -m pytest -c tools/pas600_simulator/pyproject.toml deploy/demo/tests -q
```

Las pruebas PostgreSQL de `test_pending_totals.py` verifican18:20→18:30 con persistencia,
rechazo antes del límite, total exacto y una nueva instancia del receptor. Requieren una
base aislada `_test`, distinta de la aplicación, configurada con TEST_DATABASE_URL.
