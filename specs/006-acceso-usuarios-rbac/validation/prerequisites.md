# Prerrequisitos comprobados

2026-11-02. La selección explícita es spec-006; repositorio limpio al comenzar.
`requirements.md`: 16/16 revisados, sin cambios de marcadores. No hay extensions.yml.

G0 disponible: Settings, reloj UTC/monotónico, Database/UoW, errores seguros, Alembic,
FunctionalAudit/EventWriter y composición de plataforma009 existen con pruebas reales
registradas en su aceptación. Identidad utiliza estos componentes, sin recrearlos.

| Gate | Resultado y propietario |
| --- | --- |
| G1 consultas | Faltan `consumption/router.py` y `costs/api.py`; contratos HTTP de specs001/002/004. |
| G2 PDF | Falta `reports/api.py`; contrato HTTP de spec005. |
| G3 mantenimiento | Faltan configuración001, suministro/perfiles004 y validadores002. |
| G4 SFTP | Falta receptor/publicador003; [contrato](../../003-simulador-pas600-sftp/contracts/sftp-reception.md). |
| G5 emisión técnica | Faltan `observability/logging.py` y `tracing.py`, propiedad007. |
| G6 personas/VPS | Sin vista real ni personas; VPS sigue no disponible conforme a decisión previa del usuario. |

Las tareas que necesitan estos gates permanecen pendientes; no se crean proveedores
ficticios ni se presenta una prueba omitida como aprobación. US1/US3, política, protocolo
neutral e historial propio pueden avanzar sobre G0. El participante concreto/SMTP es de008.
