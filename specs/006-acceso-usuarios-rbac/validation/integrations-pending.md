# Integraciones pendientes por capacidad

Los proveedores no existen en el código actual. No se crearon rutas de negocio ficticias
ni se contaron pruebas omitidas como éxito. Puertos/política/navegación propios sí están
implementados y probados sin exigir estos módulos para acceso o cuentas.

| Tareas006 pendientes | Gate/propietario y contrato/ruta |
| --- | --- |
| T042/T046/T048/T049/T050 | G1: lectores001/002 y costos004; `backend/src/ecs_ec/consumption/router.py`, `costs/api.py` y sus contratos HTTP. |
| T043/T046/T048/T049/T050 | G2: generación/descarga/replay005; `backend/src/ecs_ec/reports/api.py`, [HTTP005](../../005-generar-reportes-pdf/contracts/http.md). |
| T068/T075/T076/T078 | G1/G2/G3: configuración001, suministro/perfiles/boletas/recálculo004 y validadores de recepción/retención002. No se crean paneles/API para los mínimos obligatorios002. |
| T069/T077 | G4: receptor/publicador003 y entorno técnico007; [SFTP003](../../003-simulador-pas600-sftp/contracts/sftp-reception.md). |
| T082/T083 | G5: emisor007, `backend/src/ecs_ec/observability/logging.py` y `tracing.py`. No se construyó otro emisor/cola. |
| T084 | Regresión integral espera T083; regresión local y CI disponibles documentados en [regression](regression.md). |
| T085 | G6 personas + vista real de datos. [Usabilidad](usability.md). |
| T086 | G6 VPS009 + consultas/descargas reales. [VPS](vps.md). |
| T087 | Consolidación/aceptación integral espera resultados reales de los gates anteriores; [aceptación parcial](acceptance.md). |

Son18 tareas pendientes. Las tareas propias disponibles se marcan solo por ejecución real.
El participante concreto008 y SMTP siguen perteneciendo a008, sin dependencia inversa.
