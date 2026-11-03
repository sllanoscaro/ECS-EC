# Integraciones pendientes por capacidad

Actualización2026-11-03 tras implementación y pruebas locales. Estado73/87;14 pendientes.
Lectores001/002/004 e integración administrativaG3 verificados; instrumentación006 con
emisor007 real disponible. Ver [matriz](operator-matrix.md), [administración](system-administration.md)
y [telemetría](observability.md). No hay aceptación integral ni modificaciones de checklists.

| Tareas006 pendientes | Capacidad y condición restante |
| --- | --- |
| T043 | G2: generación/descarga/replay005 real, aún sin `backend/src/ecs_ec/reports/api.py`; [HTTP005](../../005-generar-reportes-pdf/contracts/http.md). |
| T046/T048 | Integración completa con G1/G2; rutas001/004 están protegidas, falta PDF y completar limpieza/actividad/retorno seguro en todas las vistas según sus tareas. |
| T049/T050 | Matriz y UI integrales esperan T046/T048 y PDF real. Consultas locales y límites de actividad con proveedores reales tienen evidencia, sin sustituir descarga/replay. |
| T068/T076/T078 | G1/G3 disponibles y ensayos administrativos parciales; cierre integral exige G2, prerrequisitos de US2 y toda la evidencia prevista. No se aceptan por existir sus archivos. |
| T069/T077 | G4: receptor/publicador003 reales aún ausentes en `backend/src/ecs_ec/acquisition/`; [SFTP003](../../003-simulador-pas600-sftp/contracts/sftp-reception.md). |
| T084 | Regresión local actualizada después de T083; cierre integral todavía exige historias e integraciones completas. |
| T085 | Personas reales, diferidas por instrucción del usuario. [Usabilidad](usability.md). |
| T086 | VPS real009 y capacidades de consulta/descarga; diferida por instrucción del usuario. [VPS](vps.md). |
| T087 | Consolidación/aceptación integral condicionada a las evidencias anteriores. |

El participante concreto008 y SMTP permanecen en su propietario, sin dependencia inversa.
No se ejecutaron tareas de proveedores ausentes desde006 ni se aprobaron integraciones con
skips, dobles o generación documental. Las14 tareas conservan sus casillas pendientes.
