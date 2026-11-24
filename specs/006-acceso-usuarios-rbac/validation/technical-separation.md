# Separación de identidades técnica y funcional

2026-11-23.006:T069/T077, escenarioUS4.7 y FR-023 sobre003 real.
Checklists de002/006:16/16 cada uno, leídos sin modificar. No existe
`.specify/extensions.yml`: sin hooks de implementación que ejecutar.

## Entorno y comando

PostgreSQL18.3 y base desechable `ecs_step1_test`, contenedor exclusivo
`ecs-step1-test`, loopback55461. La selección persistida003 se conserva; los scripts
oficiales inspeccionaron002/006 con `SPECIFY_FEATURE_NO_PERSIST=1`.
Versiones y salvaguardas en la [evidencia002](../../002-registro-retencion-consumo/validation/source-integration.md).

Con `TEST_DATABASE_URL` apuntando explícitamente a esa base separada:

```sh
.venv/bin/pytest backend/tests/integration/acquisition/test_lifecycle.py backend/tests/integration/acquisition/test_schema.py backend/tests/integration/consumption/test_source_reception.py backend/tests/integration/identity/test_technical_identity_separation.py -q --tb=short
```

**15 aprobadas en10,13s**: seis de002, siete de006 y dos de regresión003.
Las pruebas se escribieron para comprobar capacidades ya existentes; no se atribuye
un fallo inicial de comportamiento de producción a problemas de infraestructura/harness.

## Resultados por frontera

| Caso | Evidencia observada |
| --- | --- |
| Publicador sin cuenta humana | CLI003 real genera/publica por SFTP;002 incorpora dos intervalos de4kWh. Cero cuentas y sesiones006 antes/después; no se emite sesión web. |
| Contraseña/cookie de Operador y Administrador | Login006 real y catálogo001 autorizado; contraseña humana y bearer web usados como credencial SSH se deniegan, tanto con correo humano como con username del binding. Ningún intento abre un subsistema/publicación; la sesión web permanece válida. |
| Credencial SFTP frente a HTTP | Password003 autentica realmente SSH; Basic con esa credencial y cabeceras de rol/usuario no entrega sesión, catálogo001, ciclos004, cuentas ni historial administrativo. Respuestas401 no-store y sin cookie de sesión. |
| Credencial Programador frente a HTTP | Se genera un registro externo habilitado con el aprovisionador007 existente y se verifica su bcrypt. Basic/cabeceras no conceden acceso a las mismas rutas reales ni crean cuentas/sesiones006. |

El listener de pruebas es real y usa host key verificada, puerto efímero y credenciales
protegidas temporales. HTTP usa el monolito compuesto con HTTPX/ASGI y PostgreSQL reales;
no hay endpoint público de fixture, suplantación de principal ni sesión ficticia.
El helper externo de aprovisionamiento007 se consume sin cambiar sus permisos o crear
un rol Programador funcional. La aceptación del gateway/visores007 sigue en su propietaria;
esta suite comprueba específicamente la denegación por006.

## Regresión y correcciones del harness

La primera regresión amplia obtuvo251 aprobadas, dos fallos y tres casos largos
deseleccionados. Los fallos eran dos suposiciones antiguas de pruebas003: faltaba
`app.state.settings` para la opción demo y se fijaba un head Alembic anterior.
Se suministró Settings real de prueba con demo desactivada y se comprobó el head actual
antes/después del downgrade rechazado, conservando además el binding protegido.
No se modificó código de producción, migraciones, formatos, autenticación ni dependencias.

Comando de regresión de los tres módulos afectados:

```sh
.venv/bin/pytest backend/tests/integration/consumption backend/tests/integration/identity backend/tests/integration/acquisition backend/tests/contract/consumption backend/tests/contract/identity backend/tests/contract/acquisition -q --tb=short
```

**Regresión final:253 aprobadas,3 deseleccionadas en133,66s**, sin omisiones dentro
del conjunto seleccionado. Las tres excluidas son dos mediciones largas de cadencia
real_time y una restauración, excluidas por la configuración pytest del proyecto.
Documentación Python nueva/modificada comprobada mediante AST y `git diff --check`.
Se retiró únicamente el contenedor/volumen desechable creado para estas pruebas;
la aplicación, simulador y PostgreSQL locales existentes permanecen en ejecución.

No se ejecutan frontend/build
porque no se modifica interfaz. No se certifican las pruebas largas real_time/restore,
gateway007, PDF005, personas o VPS.006:T084 conserva sus prerrequisitos de historias
e integraciones completas; esta regresión acotada no cierra la aceptación integral006.
