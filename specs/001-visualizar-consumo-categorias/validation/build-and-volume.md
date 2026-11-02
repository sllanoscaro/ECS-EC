# Construcción y volumen local (T057 completa)

ExportNext y TypeScript aprobados.91 intervalos en trece meses/siete categorías, ingresados
por `Reception.accept` real 002, devuelven13 filas por categoría sin truncamiento;40296 bytes
JSON totales,0.074 s en la regresión completa. Fixture disperso: no acredita cobertura mensual
completa, un SLO, concurrencia masiva ni un volumen mayor.

Prueba reproducible:
`uv run --locked pytest backend/tests/integration/consumption/test_detail_queries.py -q --no-cov`
con `TEST_DATABASE_URL` explícita a una base separada `_test`.

Uvicorn sirvió la exportación y API sin servidor Node en runtime durante Playwright.
La imagen `ecs-spec001-validation:local` se construyó y ejecutó con el mismo Dockerfile009,
locks actuales y exportación nueva. Digest local:
`sha256:5803638c388db9e1a599b5304d49223e9a92699e594bab95f545e0876228179e`.
Playwright físico volvió a pasar2/2,3.3s contra la imagen, base sintética browser existente
y credenciales ya renovadas. UID10001; `shutil.which("node")` devuelve null; health ready.
La inspección de procesos encuentra Uvicorn y solo el Python del comando de inspección.
Node se usa únicamente en la etapa de construcción, no en runtime.

Comandos de verificación de imagen:

```sh
docker build -t ecs-spec001-validation:local .
# Ejecutar con las mismas variables006 y DB sintética de quickstart, nunca secretos de producción.
# Playwright usa E2E_BASE_URL con el origen loopback de esa instancia y CONSUMPTION_E2E_RENEWED=1.
```

La primera construcción salió139/SIGSEGV en trazas de Next tras generar páginas.
La segunda pasó sin cambios. El fallo y la repetición quedan registrados, sin ocultar
que las pruebas numéricas y de navegador no acreditan estabilidad de compilador nativo.
