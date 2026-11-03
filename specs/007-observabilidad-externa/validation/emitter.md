# Emisor fundamental: evidencia parcial

Fecha local2026-11-02. No acredita US1–US4 ni cobertura de productores.

- Serializador inicial:32 fallos de comportamiento y1 éxito en contrato (no import errors).
- Primera implementación:59 éxitos/1 fallo real por `date-time` sin validador opcional de jsonschema.
  Se añadió validación UTC explícita sin depender de extras.
- Suite ampliada inicial:65 tests correctos, cobertura de líneas86% del módulo.
  Un caso adicional detectó el reloj implícito del SDK; spans usan ahora UTC/reloj
  monotónico común y prueba de250ms conocida. Suite fundamental final:67 tests correctos, incluyendo rechazo de resultados inválidos
  antes de exportar spans. Incluye límites,
  códigos/NaN, privacidad previa, contextvars concurrentes, spool/TTL, worker detenido,
  deadline OTLP real y parcial_success, reintentos, counters independientes, heartbeat15/45s,
  config inválida y terminal único. Repetir el comando de abajo tras cambios.
- `alloy validate`, `loki -verify-config=true -config.expand-env=true` y
  `jaeger validate --config=…` pasan en imágenes fijadas; no acredita transporte integrado.
- Scripts CA: preparación test/local en `/tmp/ecs-007-implementation-tls`, reutilización
  correcta, modos0700/0600, CA separadas y rechazo de descendiente del repo comprobados.

```sh
uv sync --locked
uv run pytest backend/tests/unit/observability backend/tests/contract/observability --cov=ecs_ec.observability --cov-report=term-missing -q
```

Versiones/digests en [dependencias](dependencies.md). El puerto conceptual `continue`
se escribe `continue_operation` en Python por ser palabra reservada. Configuración y
límites reales documentados en `backend/src/ecs_ec/observability/README.md`.

Pendientes: integración Compose/mTLS/acceso Programador, cuotas reales, deduplicación
Loki, retención24h/GC y aislamiento funcional con productores reales; estas pruebas
unitarias no satisfacen sus tareas. No se modifican checklists de revisión.
