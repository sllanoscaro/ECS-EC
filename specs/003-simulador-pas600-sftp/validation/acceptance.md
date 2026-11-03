# Aceptación local003 — incremento2026-11-03

**Estado: implementación local comprobada; aceptación integral pendiente.**
69/76 tareas completas (41 adicionales). No se certifican referencia documental19,
firmware físico, VPS o reproducción por otra persona. Se preservaron las actualizaciones
documentales previas al incremento. Checklists de requisitos sin cambios.

## Implementación y entorno

Herramienta externa sin dependencia runtime del backend, con validate/generate/
test-connection/publish/resend/report/compare. Receptor003 opcional en el procesoUvicorn,
staging por sesión y manifiesto sellado únicamente mediante CLOSE+EOF explícitos.
Persistencia propia, primeras lecturas válidas canónicas, pares estrictamente adyacentes,
binding/revisión históricos, intentos002 congelados y recuperación concurrente.

Exportación de mantenimiento autorizada con selección explícita y una sola UoW
REPEATABLE READ para003 y001/002; escritura atómica después de capturar. Auditoría009
en la misma UoW del cambio003;002 conserva sus eventos y resultados. Emisor007 opcional.

Python3.14.4, PostgreSQL18.3, AsyncSSH2.24.1, versiones de pyproject/uv.lock y lock
independiente del simulador. Migración `f68f086ee8a7`, padre `costs_004_bills`.
Imagen final construida `ecs003-validation-app:local`:
`sha256:05243409e5891f9b25fca34cd9b5b8bf56573dab2d5232464f4e4fbee34fe2bc`.
Se usaron contenedor/DBs temporales y credenciales sintéticas, nunca un despliegue real.

## Pruebas ejecutadas

Con TEST_DATABASE_URL explícita, distinta de la aplicación y terminada `_test`:

```sh
uv run --locked pytest backend/tests/unit backend/tests/contract/consumption backend/tests/contract/identity backend/tests/contract/costs backend/tests/contract/acquisition backend/tests/integration/core backend/tests/integration/audit backend/tests/integration/consumption backend/tests/integration/costs backend/tests/integration/identity backend/tests/integration/reports backend/tests/integration/acquisition -q
uv run --project tools/pas600_simulator --locked pytest tools/pas600_simulator/tests -q
npm --prefix frontend test -- --reporter=dot
```

Regresión general: **491 backend** (138,08s;3 excluidas real_time/restore), **53 simulador**
(13,63s), **53 frontend**. No se ejecutó el stack técnico externo007 ni una nueva suite
visual completa de aceptación. La imagen incluye build estático/TypeScript satisfactorios. Tras ampliar la instrumentación
ordinaria del listener se repitió adquisición completa: **64 aprobadas**,3 excluidas,69,45s;
un terminal por sesión sin fingir recepción002. No se repitió toda la regresión general.

Comprobaciones seleccionadas adicionales:

```sh
uv run --locked pytest backend/tests/integration/acquisition/test_real_time_publication.py -m real_time -q -s
PAS600_RESTORE_CONTAINER=NOMBRE_CONTENEDOR_POSTGRES uv run --locked pytest backend/tests/integration/acquisition/test_restore.py -m restore -q
uv run --locked alembic -c backend/alembic.ini upgrade head
uv run --locked alembic -c backend/alembic.ini check
docker build -t ecs003-validation-app:local .
```

Los ensayos real_time se ejecutaron individualmente en DBs distintas: dos ciclos,
900,004936s fin→inicio,902,07s de prueba; fallo/lento y reintento,900,015390s,
902,52s de prueba. Reloj y SSH reales, sin intervalo reducido. Esas mediciones son
anteriores a los últimos refuerzos de constraints, exclusión del journal y metadata de
estado de archivo; la regresión final cubre esos cambios, sin repetir las dos esperas.

Restore ampliado:1 prueba aprobada (3,59s), conserva IDs/estados/plazos y verifica resultado
original002/4kWh; bytes faltantes producen5 sin sustituir export previo. Upgrade/rollback
vacío/upgrade y alembic check sin diferencias; downgrade poblado rechazado atómicamente.
Paquete --no-dev realmente instalado sin pytest/ecs_ec: validate/generate/probe/publish
con contraseña y clave, duplicados comprobados. Detalle en [US2](us2.md).

## Trazabilidad de requisitos

| Requisitos | Evidencia local / límite |
| --- | --- |
| FR-001/002/019 | Paquete independiente y validación estricta; runtime --no-dev, siete estados, topología/rangos/tasas/offsets/cadencia inválidos rechazados. |
| FR-003/004 | CSV/JSON y lectores de test independientes, equivalencia y cortes nativos. Conformidad contra DOCA0172EN-19 sigue pendiente en T003/T008/T009/T021. |
| FR-005/006 | Mapping explícito por binding/revisión;100→104=4, cero válido, hueco/reset/conflicto/corrección tardía. SFTP real:4+7→11 calculado002; total medido20 conserva20. |
| FR-007/008 | Host administrado, password/key, probe sin publicación, waits900s reales en ciclos/reintentos; candados persistentes y rechazo899. VPS/hardware no ejecutados. |
| FR-009/010/011 | CLOSE/EOF versus desconexión/cleanup, multiarquivo, cuotas, tres intentos, fallo permanente, ordinales/reenvío intactos; transferred no implica aceptación. |
| FR-012/013/014/015 | Tasas exactas y exclusión de posiciones, corruptos independientes, tipo/date en CSV/JSON reales. CAT-03 conserva62 intervalos admisibles; otras seis categorías100;10 inválidas. Positivo fuera de banda sigue regla real001. [US3](us3.md). |
| FR-016/017 | Oráculo/control separado, informes saneados, reproducción integral con categorías reordenadas; hashes lógicos/completos y tiempos reales diferenciados. |
| FR-018 | Snapshot autorizado/concurrente coherente,0/5/6, unavailable,2700s/75%, cobertura falsamente completa detectada, manifiestos ajenos/archivos alterados. Revisión humana pendiente. [US4](us4.md). |
| FR-020 | Histórico >=12 meses sin red en suite del paquete; SIGINT/SIGTERM en espera/WRITE/CLOSE, reanudación durable. Medidas históricas completas conservadas en [US1](us1.md). |
| FR-021 |001/002 reales: aceptación/duplicate/too_early, lost-response y mismo intento, payload conflict, cobertura, total calculado y retención protegida. Fallos de archivo/registro/transferencia separados. |
| FR-022 | README/quickstart/despliegue y docstrings; revisión de [documentación](documentation.md) y [aislamiento](deployment.md). Sin secretos operativos versionados. |

| Criterio | Estado |
| --- | --- |
| SC-001 | Casos funcionales medidos/calculados y formatos verificados localmente; conformidad documental pendiente. |
| SC-002 | Conteos/posiciones y efectos de anomalías comprobados con receptores reales; no se transforma la banda de prueba en regla001. |
| SC-003 |100% reproducción automatizada comprobada; T070 y aceptación por otra persona pendientes. |
| SC-004 | Transporte/estados/reenvío/recuperación y900s reales comprobados en los cortes indicados. |
| SC-005 | Contraste automatizado y limitaciones comprobados; falta persona independiente y recorridos visuales restantes. |
| SC-006 | Generación histórica local de siete categorías comprobada; no acredita12 meses transcurridos de conservación real ni envío histórico acelerado. |

## Trabajo abierto

T003/T008/T009/T021: referencia19 diferida por el usuario; los contratos locales no la
sustituyen. T070: otra persona. T072: instrumentación ordinaria real parcial; cobertura
técnica completa/continuación durable dependen del propietario007:T037/T038. T076:
consolidación local realizada, aceptación integral abierta por esos gates y escenarios
no ejecutados. No se marcan verificaciones de001/002/006/007 desde este incremento.

La operación física exige IDs/topología y captura del firmware que demuestre la convención
de sesión. Las pruebas sintéticas no certifican hardware ni VPS. No se inicia ningún
servicio de producción, ni se publica o confirma un despliegue desde este trabajo.

Manifiestos/hashes y mediciones largas saneadas: [local-evidence.json](local-evidence.json).
