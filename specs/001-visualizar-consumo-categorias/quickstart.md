# Quickstart y validación: Consumo por categorías

[Plan](plan.md), [modelo](data-model.md), [HTTP](contracts/http.md),
[integraciones](contracts/integrations.md), [arquitectura](../../docs/architecture.md).
Implementación parcial: catálogo/configuración, reglas puras y componentes aislados
disponibles; recepción 002, consultas/rutas y aceptación de las cuatro historias pendientes.
Resultados observados en [aceptación parcial](validation/acceptance.md). Los escenarios
de extremo a extremo siguientes conservan su carácter previsto hasta contar con esos proveedores.

## Comandos disponibles ahora

Con Python 3.14, uv y Node>=20.9 de plataforma, desde la raíz:

```sh
uv sync --locked --group dev
npm --prefix frontend ci
uv run --locked pytest backend/tests/unit/consumption backend/tests/contract/consumption -q
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
uv run --locked python scripts/generate_consumption_types.py
```

`decimal.js`10.6.0, licencia MIT, quedó fijado en `frontend/package.json` y lockfile
mediante `npm --prefix frontend install --save-exact decimal.js@10.6.0`. Solo se usa con
un contexto local de precisión 50 para geometría SVG. Energía de negocio y fechas conservan
cadenas exactas; no se altera el contexto global de otras bibliotecas.

`scripts/generate_consumption_types.py` regenera
`frontend/src/lib/api/consumption-types.ts` desde `contracts/openapi.json`. Produce tipos
readonly de transporte; restricciones semánticas/condicionales siguen siendo verificaciones
del servidor, no supuestas validaciones TypeScript. El cliente `consumption.ts` reutiliza
sesión/CSRF/no-store 006 y excluye campos derivados del PUT. No hay rutas 001 montadas todavía.

Para repetir la integración propia con una base **desechable y separada**, se usó este
contenedor local. La contraseña mostrada es únicamente sintética de pruebas:

```sh
docker run -d --name ecs-consumption-spec 001-test \
  -e POSTGRES_USER=ecs_test -e POSTGRES_PASSWORD=synthetic-spec 001-only \
  -e POSTGRES_DB=ecs_consumption_test -p 127.0.0.1:55449:5432 \
  postgres:18.3-bookworm@sha256:80630f83606d8db77d30b3851b16a9f78be2d0d4dda6f7b82a1fdca5ebe3acba
docker exec ecs-consumption-spec 001-test pg_isready -U ecs_test -d ecs_consumption_test
export TEST_DATABASE_URL='postgresql+psycopg://ecs_test:synthetic-spec 001-only@127.0.0.1:55449/ecs_consumption_test'
uv run --locked pytest --cov=ecs_ec --cov-report=term-missing -q
```

Esperar `accepting connections` antes de pytest. El harness exige PostgreSQL, nombre
terminado en `_test` y una base distinta de la aplicación antes de migrarla. Las pruebas
de configuración usan DB/auditoría reales y un doble **explícito** de límites 002;
cinco escenarios de recepción quedan omitidos hasta instalar su proveedor real.
No usar los fixtures ni la limpieza de pruebas sobre datos de una instalación.

Al terminar la reproducción se puede retirar exclusivamente este contenedor desechable:

```sh
docker rm -f ecs-consumption-spec 001-test
```

## Provisión controlada de contexto y primera configuración

El comando interno disponible usa DATABASE_URL/Settings 009, sin rutas seed ni reloj
público. Contexto JSON con `id`, `name`, `timezone`; configuración JSON con
`expected_revision`, `effective_from`, `timezone` y las siete entradas SourceEntry del
[contrato HTTP](contracts/http.md). UUID/zona/fuentes son explícitos por entorno; la
identidad del edificio debe coincidir con la configurada en 006 antes de integrar la web.
No copiar un ejemplo sintético a una instalación real.

```sh
uv run --locked alembic -c backend/alembic.ini upgrade head
uv run --locked python scripts/bootstrap_consumption.py \
  --context-file /ruta/privada/context.json \
  --configuration-file /ruta/privada/consumption-configuration.json
```

El actor es `process:consumption_bootstrap`. Inicialmente expected_revision=0;
`effective_from` puede ser histórica y nunca futura. `created_at` lo fija el reloj interno.
Repetir con la revisión actual y sin cambios devuelve la misma revisión/eventos. Cambios
posteriores necesitan MeasurementStore 002; este CLI sin proveedor los rechaza, sin una
opción para eludir límites. La CLI confirma solo el número de revisión o un código seguro.
El bootstrap aislado real produjo revisión 1 y un no-op revisión 1; no creó mediciones.

Los modelos y helpers de configuración están en `consumption/catalog_storage.py`;
`lock_configuration` debe compartirse con recepción 002, seguido de lectura de estado en
READ COMMITTED. `configuration_segments` deriva fin de vigencia desde la siguiente revisión;
las revisiones anteriores no se actualizan. La migración es `cb63a76198be`, sobre
`identity_initial`; `alembic check` comprueba la sincronía del esquema.

## Prerrequisitos y preparación

Esta sección y las consultas HTTP posteriores describen el flujo **pendiente de integración**;
no presentar esos comandos como una aplicación de consumo ya disponible.

Reutilizar plataforma 009 real: herramientas/build, PostgreSQL 18, UoW/reloj/auditoría y
migraciones. Identidad 006 real para aceptación web: Administrador y Operador activos,
con contraseña renovada; Programador no obtiene acceso funcional. Integrar recepción y
almacenamiento reales de 002 con reglas 001. Los dobles de estos puertos solo acreditan
pruebas aisladas, no aceptación funcional. PAS600/SFTP requiere el adaptador de 003.

Proveer contexto del edificio, zona y configuración de fuentes por entorno, sin copiar
identidades reales a fixtures. Secretos en `.env` local ignorado/secretos de VPS; no en
documentos, imágenes, pruebas ni archivos PAS600. Orígenes/revisiones mediante PUT
administrativo o fixture controlado; datos mediante `Reception.accept`, nunca INSERT que
eluda validaciones. Correo/visores no son prerrequisitos para consultar consumo.

Después de implementar, desde la raíz del repositorio:

```sh
cp .env.example .env
uv sync --locked --group dev
npm --prefix frontend ci
npm --prefix frontend run build
docker compose build app
docker compose up -d db
docker compose run --rm app uv run --locked alembic -c backend/alembic.ini upgrade head
docker compose up -d app
uv run --locked pytest backend/tests/unit/consumption backend/tests/integration/consumption backend/tests/contract/consumption
npm --prefix frontend test -- --run
npm --prefix frontend exec -- playwright test tests/e2e/consumption.spec.ts
```

Completar `.env` antes de arrancar según plataforma: base local, contexto/zona, URL pública
local y sesión. Pruebas PostgreSQL usan `TEST_DATABASE_URL` a una base separada y comprobada
como desechable, no la base de la aplicación ni producción. Los fixtures de pytest y la
preparación de Playwright crean configuraciones/usuarios de prueba mediante los servicios
reales; Playwright levanta una instancia sobre su propia base. El reloj inyectable pertenece
al harness de pruebas; no hay endpoint ni bandera pública para alterar tiempo o inyectar datos.

Para una consulta manual tras iniciar sesión por el flujo de 006 y guardar su cookie en
un archivo local de prueba protegido (no se versiona), usando el puerto local documentado
por plataforma en `APP_PUBLIC_BASE_URL`:

```sh
curl --fail-with-body --cookie /tmp/ecs-ec-consumption-session.cookies "$APP_PUBLIC_BASE_URL/api/v1/consumption/catalog"
curl --fail-with-body --cookie /tmp/ecs-ec-consumption-session.cookies --get "$APP_PUBLIC_BASE_URL/api/v1/consumption/categories/CAT-03/detail" --data-urlencode 'start=2026-10-01T00:00:00-03:00' --data-urlencode 'end=2026-10-02T00:00:00-03:00' --data-urlencode 'timezone=America/Santiago'
```

Son fechas/zona sintéticas. La preparación autenticada de cookies usa exclusivamente el
flujo existente de 006; no asumir credenciales ni un endpoint de login nuevo.

## Escenarios reproducibles y resultados esperados

Los fixtures dan nombre a cada escenario y fijan su reloj, zona/tzdata, configuraciones,
fuentes y entradas. Enviar historia de una categoría en una sola actualización o avanzar
el reloj de prueba >=15 minutos; no desactivar el límite para preparar datos.

| Caso / requisitos | Preparación | Resultado esperado |
| --- | --- | --- |
| Catálogo y tres intervalos, US1 / SC-001/002 | Siete fuentes sintéticas; tres intervalos no superpuestos conocidos por categoría, mezcla Wh/kWh/MWh y recepción fuera de orden. | Siete opciones; SVG y tabla comparten cada intervalo, valor kWh y origen; orden cronológico, mismo período inicial global. |
| Total físico, FR-006 | CAT-01 100 kWh y seis parciales de 10 kWh en el mismo intervalo. | Total medido 100, nunca 60 ni 160. Retirar otra lectura general dejando parciales no activa suma sustituta. |
| Total calculado, FR-006/009 | Sin medidor total; solo CAT-03 y CAT-05 instaladas, 12 y 8 kWh para I. | 20 kWh, base CAT-03/CAT-05, referencias a ambos datos y alcance parcial visible. Ningún medidor total ficticio. |
| Incompleto/desalineado, US4 | Omitir CAT-05 de I; repetir con dos subintervalos que no cubren exactamente I. | Sin total numérico para I; diagnóstico identifica faltante/alineación; no suma 12, no reparto. |
| Cero/base vacía/ausente, SC-004 | Ambas contribuciones cero; después sin ninguna categoría instalada; parcial sin medidor y parcial instalada sin lecturas. | Cero calculado válido con base; base vacía sin valor; "Sin medidor" distinto de "Sin datos". |
| Equivalencia y rechazo, US2 / SC-003 | Reenvío 1000 Wh frente a 1 kWh; luego 2 kWh con identidad igual; otro intervalo solapado y otro contiguo. | Duplicate, rejected/conflict, rejected/overlap, accepted; original intacto. |
| Entradas mixtas, FR-003/004 | Negativo, NaN/infinito, origen/categoría desconocidos, W en vez de energía, fechas inválidas y un registro válido independiente. | Resultado por registro con causa; el válido sigue disponible. |
| Concurrencia/tiempo, integración 002 | Dos novedades simultáneas incompatibles, duplicado anticipado, datos nuevos a 14m59s/15m; completar candidato CAT-01 antes de su elegibilidad. | Sin duplicación/superposición; duplicado no reinicia plazo; novedades anticipadas rechazadas; CAT-01 pendiente hasta incorporación permitida por trabajo interno, incluso tras reinicio. GET no adelanta nada. |
| Período, US3 | Datos antes/dentro/después y uno cruzado; rango inválido. | Solo contención completa, aviso por cruce incluso si queda sin datos; rango inválido conserva última consulta válida. Cambiar categoría conserva rango. |
| DST/zona, FR-013 | Dos instantes de hora repetida con offsets distintos; hora inexistente; navegador en otra zona. | Instantes distintos sin duplicar/omitir; corrección de fecha inexistente; etiquetas/offsets del edificio. No truncar microsegundos. |
| Gráfico, FR-007/010/015 | Una sola lectura, cero, positivo `0.000001 Wh` (= `0.000000001 kWh`), hueco entre intervalos. | Todos visibles con cifras exactas; positivo no parece cero, hueco sin línea/filas inventadas. |
| Carrera/error, FR-014/016 | Retrasar respuesta A, seleccionar B, fallar B y reintentar; alternar representación. | A nunca aparece atribuida a B; carga/error distinguibles; reintento de B y misma respuesta para ambas vistas. |
| Revisión de configuración | Cambiar fuente/presencia con revisión vigente; intentar revisión anterior, cambio de zona con datos y retroactividad. | Nueva base solo desde vigencia; historia conserva procedencia; conflicto/validación sin cambios parciales. |
| Revisión global ajena, I1 | Cambiar CAT-03 a las 10:05; recibir CAT-05 [10:00,10:15) con fuente estable y temporalmente admisible. Repetir cambiando su propia fuente dentro del intervalo. | Primera lectura aceptada con revisión global de inicio y `category_revision` estable; segunda rechazada con `source_configuration_changed`, sin división. Probar cambios exactamente en inicio/fin. |
| Cambio calculado, I1 | Cambiar modo/base/fuente contribuyente CAT-01 dentro de un intervalo observado, conservando parciales válidas. Repetir con revisión global sin cambio de firma CAT-01. | Cambio real: `calculation_configuration_changed`, sin valor, faltantes vacíos, fecha próxima null y segmentos con revisiones distintas. Cambio ajeno: cálculo permitido. |
| Límites de reconfiguración, U1 | Carrera en ambos órdenes entre recepción/cambio; retirar solo detalle permitido y consultar límites; provocar proveedor ausente/fallido y claves incompletas. | Puerto 002 conserva máximos por categoría e historia aceptada, incluida calculada; no-op sin nueva revisión y cambio incompatible/fallo sin modificación parcial. Primera configuración puede preceder a 002; revisión posterior con cambios exige proveedor real. |
| Fronteras numéricas, A1 | Cero, q=`10^-15 kWh`, `M=10^30-q`, `10^-16 kWh`, `10^30 kWh`, no múltiplo de q y representaciones equivalentes Wh/kWh/MWh. | Cero/q/M admitidos; restantes fuera del dominio rechazados con `energy_out_of_supported_range`, sin redondeo ni cero inventado. `10^-12 Wh`, `10^-15 kWh`, `10^-18 MWh` equivalen al mismo mínimo. |
| Máximo calculado, A1 | Seis contribuciones M en un intervalo, base/fuentes estables e incorporación temporal permitida; alternar gráfico/tabla. | Exactamente `6*M` kWh, incluso por encima del techo individual; hasta 31 dígitos enteros y 15 fraccionarios sin pérdida. Contexto 50 sin `Inexact`/`Rounded`; cadenas exactas en ambas vistas. |
| Seguridad, FR-018 | Acceso directo sin sesión/expirada; Operador a configuración GET/PUT; sesión restringida; CSRF inválido. | 401/403, sin datos protegidos ni cambios. Ambos perfiles funcionales consultan; identidad técnica no. |

Pruebas de rollback verifican configuración/auditoría/eventos atómicos y registros originales
intactos. Reiniciar app/DB y comprobar persistencia real; caída de correo/visores no impide
consulta. El build estático se realiza sin consultar datos privados y se sirve desde FastAPI.

## Integración local y aceptación posterior

Para SC-006, ejecutar además escenarios locales de 003 con SFTP/archivos nativos CSV y JSON,
007 con sus receptores/visores y 008 con SMTP/Mailpit, según los procedimientos de cada
propietario cuando existan. No añadir sus servicios al setup de 001. Documentar qué
sustitutos se usaron y qué contratos/resultados conservan; fixture interno no acredita SFTP.
Ningún recurso remoto o VPS es obligatorio para estas pruebas locales.

SC-005 requiere diez tareas con personas representativas: localizar categoría y verificar
valor/período en ambas vistas; al menos nueve sin ayuda en <=60 segundos. Registrar tiempo,
acierto y estado reconocido por tarea; sin participantes el criterio queda pendiente.

SC-007 se valida en VPS con dominio/HTTPS y configuración real: una cuenta activa de cada
perfil consulta desde red externa con equipo de desarrollo apagado; sin sesión no se
entregan datos. Comparar categorías, unidades y zona; comprobar permisos vigentes. Local
no acredita esta verificación ni confirma fuentes físicas reales.

Crear evidencia durante implementación en `specs/001-visualizar-consumo-categorias/validation/acceptance.md`:
commit, comandos/versiones, zona/tzdata, fixture/contratos, resultados esperados/observados
de FR-001..019 y SC-001..007, fallos y pendientes. No marcar checklists por generar estos documentos.
