# Paso4: observabilidad sobre productores reales

Corte2026-11-24. **007:58/65 tareas completas; el paso4 todavía no está aceptado
integralmente.** Se cierran treinta tareas: T022/T028–T030/T033–T058. T031/T032 ya
estaban completas. T059–T065 conservan dependencias, tiempos reales y personas.
Global:487/605,118 pendientes; ningún marcador de otras specs/checklists modificado.

## Implementación y evidencia

| Capacidad | Resultado / evidencia |
| --- | --- |
|Acceso técnico/funcional completo | [US1](access.md): matriz con PDF real, dos perfiles006, dos entornos, TLS/mTLS, revocación y puertos; se elimina la antigua omisión PDF. |
|Productores001–006 y correlación | [Adquisición](coverage-acquisition.md), [negocio](coverage-business.md), [matriz](coverage.md). Integración004 autorizada por el usuario, sin cambiar cálculos/permisos/auditoría. |
|Métricas y continuidad | [Resultados](metrics.md):10/8/2→20%,5/3/1/1, recuperación2ejecuciones/1intento/5novedades,50%vs0%, ventanas1ns, percentiles, replay y E2E. |
|Privacidad/aislamiento y cuotas | [Fallos/commits](isolation.md): cinco sistemas de archivos realmente llenados>=90%, ingesta507 y negocio/PDF conservados; recuperación200. |
|Muestreo/retención | [Políticas y límites](retention.md):0.1 explícito/100logs/20spans, persistencia y ensayo real en marcha; no se afirma TTL/GC cumplido. |
|Documentación y UI | [Revisión](documentation.md):44Python007/49identidad, guías/contratos, plugin manual y capturas responsive. T062–T064 siguen sujetos a su cadena. |

## Verificación ejecutada

Configuración privada exclusivamente sintética en PostgreSQL18.3 sobre puerto55464,
DB ecs_step4_test; stacks técnicos ecs007-step4(test3444), ecs007-step4-other(local3445)
y ecs007-step4-quotas(test3446), CA/directorios/redes distintos. Sin SQLite ni servicios
externos para producir resultados. Aplicación funcional previa del usuario intacta.

```sh
# Cargar configuración privada propia sin imprimirla; ver contratos de fixtures.
uv run pytest backend/tests --junitxml=/ruta/privada/step4.xml
npm --prefix frontend test
npm --prefix frontend run typecheck
node --test deploy/observability/grafana/plugins/ecsec-coverage-panel/reconcile.test.mjs
docker build -t ecs007-step4-app:local .
```

- Backend completo: **768 passed,0 skipped,3 deselected**,766.04s. Incluye las cinco
  cuotas reales, privacidad, propietarios, transporte y dos harnesses de navegador
  con seis recorridos E2E reales. [JUnit](artifacts/step4-final.xml).
- Después se añade contraste del conciliador con las filas reales del replay:
  **50 passed**,18.41s (cardinalidad+unitarias007+catálogo); se solapa con la suite
  completa y no se suma como casos independientes. [JUnit](artifacts/step4-followup.xml).
- **1 harness adicional aprobado**,143.85s, repite los tres recorridos de métricas/diagnóstico
  después de ajustes finales del panel/anotaciones. [JUnit](artifacts/step4-browser-final.xml).
- **91 pruebas frontend**, tipado TypeScript correcto, **13 pruebas del conciliador**.
  [Node](artifacts/step4-panel.tap). Browser usa Node24.22 --jitless por fallo nativo
  inicial del runtime; Chromium valida CA en HOME aislado, sin ignoreHTTPSErrors.
- uv sync --locked correcto (68resueltos/66verificados); Ruff --select F correcto;
  AST44Python007/docstrings y validador00649archivos correctos.
- Compose config --quiet y nginx -t correctos en los tres stacks.
  [Resultados](artifacts/step4-config-checks.json). Imagen final construida:
  sha256:9a85f15f8dfa75dc8590a3a4bd58c821c27f1dffb1fabb10426a12c279698247.
  No sustituye el tag/contenedor funcional existente del usuario.
- RAM posterior a carga y capacidad/overhead físico observados por separado en
  [mediciones](artifacts/step4-capacity.json); no se acredita pico o dimensionamiento
  operacional a partir de límites de payload.

Las tres exclusiones del primer corte son ensayos prolongados/restauración003 ya
seleccionados separadamente por su propietario. Se añadieron dos casos real_time007
para revisar la evidencia24h consultable/física: todavía no ejecutados, por falta de
plazo vencido. No se presentan como aprobados u omisiones de esta suite previa.

## Límites y orden de continuación

Loki nativo contó1001 entregas de1000eventos únicos tras replay; no se oculta con
etiquetas ni se promete exactitud. El panel concilia y declara cobertura parcial/N/D.
T059 espera plazo real y verificación separada de GC;404 no acredita liberación física.
No hay evaluación humanaSC-008, VPS, restauración técnica integral ni recorrido final
SC-009 con salida remota bloqueada. No se cierran por estas pruebas.

1. Revisar ensayo24h y GC dentro del plazo en el [checkpoint](implementation-checkpoint-2026-11-24.md).
2. Completar007:T060 (recorrido local final y sin perfil).
3. Después deT060, T061/personas y cadenaT062→T063→T064 pueden avanzar en paralelo.
4. T065 requiere ambos cierres y matriz integral.008 puede avanzar independientemente.
