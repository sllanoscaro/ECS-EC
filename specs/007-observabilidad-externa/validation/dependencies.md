# Dependencias de007 verificadas

2026-11-02 (hora local). CPython3.14.4 convencional, FastAPI0.162.0 preservados.
`uv add opentelemetry-exporter-otlp-proto-http==1.45.2 httpx==0.28.1` y
`uv sync --locked`: correctos. Loguru0.7.3, OTel API/SDK1.45.2,
jsonschema4.26.0. Bcrypt5.0.0 añadido para provisión técnica. Lockfile resuelto con66 paquetes;64 instalados/verificados.
20 pruebas de `backend/tests/unit/core` pasan tras la actualización.

Imágenes descargadas con `docker pull`; digests reales en
`deploy/observability/versions.env`: Nginx1.31.8-alpine, Alloy1.21.3,
Loki3.7.9, Grafana13.3.0 y Jaeger2.22.0. Comandos `nginx -v`,
`alloy --version`, `loki -version`, `jaeger --version` ejecutados en
contenedores sin red. La descarga no acredita integración/seguridad/retención.

Fuentes para selección: [Alloy](https://github.com/grafana/alloy/releases),
[Loki](https://github.com/grafana/loki/releases),
[Grafana](https://github.com/grafana/grafana/releases),
[Nginx](https://github.com/nginx/nginx/releases),
[Jaeger](https://www.jaegertracing.io/docs/2.22/getting-started/).
La configuración se comprobará sobre estas imágenes, no contra `latest`.

Ignore files existentes: `.gitignore`/`.dockerignore` cubren venv, cachés,
node_modules, artefactos web, logs y `.env*`, con excepción explícita `.env.example`.
Frontend es privado; no corresponde `.npmignore`. Sin ESLint/Prettier/Terraform/Helm.
Las credenciales técnicas se generarán exclusivamente fuera del repositorio.
