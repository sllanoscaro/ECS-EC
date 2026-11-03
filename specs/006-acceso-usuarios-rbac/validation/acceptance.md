# Aceptación parcial de spec-006

## Estado vigente — continuación2026-11-03

**73/87 tareas completas;14 pendientes.** Completadas006:T042/T075/T082/T083 con
consultas reales001/002/004, dependencias administrativas e instrumentación propia007.
Hay pruebas parciales de006:T068/T076 y actividad de lectura, sin declarar cerradas esas
tareas ni la aceptación de US2/US4. Personas/VPS se difieren por instrucción del usuario.

| Verificación del incremento | Resultado |
| --- | --- |
| Regresión backend local de plataforma, identidad, consumo, costos, preparación PDF y unidades del emisor |428 aprobadas en69,01s, sin omisiones. No incluye integración del stack externo007 ni generación PDF todavía inexistente. |
| Vitest / TypeScript / export Next |53 pruebas aprobadas en23 archivos; typecheck y build aprobados. |
| Playwright identidad |Un recorrido conjunto pasa: ambos perfiles, renovación, cuentas, historial, cierre entre pestañas y expiración. HTTP loopback con claves sintéticas y reloj privado. |
| Documentación / contratos |AST de45 archivos Python006 y pruebas sin docstrings ausentes; contratos API y espacios/enlaces comprobados. |

Comando de regresión final:

```sh
.venv/bin/pytest backend/tests/unit backend/tests/integration/identity backend/tests/integration/consumption backend/tests/integration/costs backend/tests/integration/core backend/tests/integration/audit backend/tests/integration/reports backend/tests/contract/identity backend/tests/contract/consumption backend/tests/contract/costs -q
```

Se usó `TEST_DATABASE_URL` hacia `ecs006_completion_test`, PostgreSQL18.3 desechable
`ecs006-completion`, loopback55449. Navegador en otra base `ecs006_browser_test`; sin datos
reales, secretos en Git ni endpoints de fixture. Contenedor/volumen exclusivos retirados
al finalizar. No se modificaron dependencias, migraciones o checklists; requirements16/16.
Selección persistida006 mediante script oficial; `.specify/extensions.yml` ausente antes
y después, sin hooks que ejecutar. No se hizo commit ni despliegue.

[Lecturas y límites de actividad](operator-matrix.md),
[administración disponible y parcial](system-administration.md),
[telemetría006](observability.md) y [regresión](regression.md) detallan evidencia y límites.
La regresión detectó una prueba001 que contaba señales de todos los módulos; se corrigió
el filtro de productor sin suprimir señales de identidad. Repetición final428/428.

Permanecen pendientes006:T043/T046/T048/T049/T050/T068/T069/T076/T077/T078/T084/T085/T086/T087.
PDF005 y SFTP003 deben entregar sus proveedores reales en sus propias specs. También
faltan la integración completa de vistas/actividad, matrices y evidencias asociadas,
personas, VPS y consolidación. No se implementan otros módulos desde006 ni se usa la
preparación PDF existente como generación/descarga funcional. T084 tiene regresión local
actualizada, pero conserva el prerrequisito de historias/integraciones completas.

## Registro histórico — 2026-11-02

Las cifras y estados siguientes corresponden al corte original; prevalece la actualización
vigente anterior, sin reatribuir pruebas históricas al incremento actual.

2026-11-02. **69/87 tareas completadas;18 pendientes por capacidades externas.** No se
declara aceptación integral. Checklist de requisitos conservada16/16; no se modificaron
sus marcadores por implementar. El repositorio estaba limpio al comenzar y no se hizo commit.

Implementados: cinco tablas propias/migración, Argon2/correo, sesiones/presesión/espera,
transporte/CSRF, política fija, protocolo neutral, cuentas/revisiones/revocación concurrente,
auditoría009 e historial, páginas/cliente runtime, bootstrap/recuperación y limpieza.
Las capacidades ajenas no se recrearon. Los detalles de los18 pendientes y sus propietarios
están en [integraciones pendientes](integrations-pending.md) y [prerrequisitos](prerequisites.md).

**Verificación final:**142 pruebas backend pasan, cobertura Python total89%;12 pruebas
Vitest pasan; TypeScript (incluidos tests/configuración), export Next y dos escenarios de
Chromium con TLS local pasan. Compose final arranca desde volumen vacío con migraciones,
CPython3.14.4/Argon2 reales, UID10001, sin Node ni fixtures en runtime. No hay umbral de
cobertura adicional definido en la spec. Los procesosCLI reales se probaron con pseudo-TTY,
incluidos dos bootstraps concurrentes; su ejecución como subprocess no se suma íntegramente
a la cobertura del proceso pytest padre. OpenAPI fue generado/revisado fuera de esa medición.

| Requisito | Resultado y alcance |
| --- | --- |
| FR-001 | Local: dos perfiles y estados fijos, matriz exhaustiva, roles técnicos/acciones/edificios desconocidos denegados. |
| FR-002 | Local: ingreso real de ambos perfiles y renovación restringida. |
| FR-003 | Local: canónico IDNA/casefold, unicidad incluso inactivo; Unicode/espacios de contraseña exactos. |
| FR-004 | Local: rechazo general y espera durable, cinco fallos/concurrencia/bordes/rotación. |
| FR-005 | Identidad: comprobación vigente por petición y bajo locks. Integración en rutas de negocio pendiente G1/G2/G3. |
| FR-006 | Rutas propias protegidas; archivos/reportes reales pendientes005. |
| FR-007 | Política de lectura/PDF implementada; consumo/costos/PDF reales pendientes. |
| FR-008 | Operador denegado en cuentas/historial; configuración/boletas ajenas pendientes. |
| FR-009 | Herencia probada en catálogo fijo; aceptación de consultas/PDF espera proveedores. |
| FR-010 | Navegación runtime por permiso, enlaces solo a páginas instaladas; datos privados se limpian. |
| FR-011 | Alta/listado/detalle/edición/reset reales, sin registro público ni DELETE. |
| FR-012 | Desactivar/reactivar conserva UUID y no restaura sesiones. |
| FR-013 | Guardia real, dos procesosCLI y carreras de retiro; al menos un admin activo. |
| FR-014 | Cambio propio/reset y recuperación sin obtener credencial anterior. |
| FR-015 | Renovación requerida; solo introspección mínima/cambio/cierre hasta nuevo ingreso. |
| FR-016 | Cierre, igualdad de bordes30min/8h, actividad29→59 y no renovación por introspección. |
| FR-017 | Cambios efectivos invalidan dos dispositivos; original del actor se revalida después de esperas. |
| FR-018 | PHC irreversible, proyecciones aprobadas, secretos ausentes de errores/audit/export. |
| FR-019 | Configuración001/004 y validadores002 pendientes; no se inventó edición de mínimos002. |
| FR-020 | Boletas/recálculos reales pendientes004; catálogo de permisos ya deniega al Operador. |
| FR-021 | Cambios/denegaciones propios en audit009, actor confiable/no autenticado e historial; productores ajenos pendientes. |
| FR-022 | Atomicidad/revisiones/rollback y deduplicación del intento ante confirmación incierta probados; integraciones ajenas pendientes. |
| FR-023 | Política humana rechaza Programador/SFTP; publicación técnica real espera003/007. |
| FR-024 | TLS local, proxy falsificado/origen/CSRF/HTTP público probados. HTTPS público pendiente VPS. |

| Criterio | Resultado |
| --- | --- |
| SC-001 | Casos locales de cuentas/perfiles/credenciales/renovación aprobados. |
| SC-002 | Matriz aislada y rutas propias aprobadas; combinaciones de rutas propietarias pendientes. |
| SC-003 | Política común aprobada; consultas/generaciones PDF reales pendientes. |
| SC-004 | Invalidaciones y límites propios aprobados; entrega/replay PDF real pendiente005. |
| SC-005 | Cuentas y carreras PostgreSQL aprobadas; UUID/referencias y unicidad conservados. |
| SC-006 | Auditoría/historial propios aprobados; cambios administrativos de otros módulos pendientes. |
| SC-007 | [Personas/vista real pendientes](usability.md), sin tiempos humanos inventados. |
| SC-008 | [VPS pendiente](vps.md); TLS local no se presenta como prueba externa. |

Escenarios: US1.1–7/9 y US3.1–8 tienen evidencia local; US1.8 espera VPS. US2.3/4/6
se comprobaron en navegación/política/rutas propias; US2.1/2/5/7 e integración completa
esperan001/002/004/005. US4.5/6 están comprobados para identidad e historial propio;
US4.1–4 y4.7 esperan mantenimiento/PDF/SFTP reales, conservando el alcance original.

Evidencia: [dependencias](dependencies.md), [fundamentos](foundations.md),
[autenticación](authentication.md), [UI de acceso](access-ui.md), [cuentas](accounts.md),
[UI de cuentas](accounts-ui.md), [historial/operación](history.md), [regresión](regression.md)
y [OpenAPI](openapi.json). La [guía](../quickstart.md) y [operación](../../../deploy/README.md)
incluyen comandos reales, claves, TTY, rotación, recuperación y restauración segura.

T084 permanece parcialmente ejecutada por falta de instrumentación007; T087 no se cierra
con esta consolidación parcial. El workflow se amplió pero no se ejecutó un job remoto,
ni se publicó o desplegó una VPS. No hay excepciones constitucionales ni nuevos servicios
de aplicación. `.specify/extensions.yml` no existe: no hay hooks antes/después que ejecutar.
