# Validación local004

2026-11-02, base Git `23c26d0fb7636b4f6584c9be7d5a2ccb18011d4b` más cambios de esta
implementación. US1–US4 implementadas sobre001/002/006/009 reales; T064/SC-006 pendiente
por falta de participantes. Precios, fuentes y documentos exclusivamente sintéticos;
falta configurar el suministro real antes de afirmar un cálculo aplicable al edificio.

## Verificaciones reproducibles

Se usó PostgreSQL18.3 desechable, contenedor `ecs-spec004-test`, loopback55452. Bases
separadas `_test`: suites, navegador y migraciones/alta inicial. Ninguna prueba apunta a
la base de aplicación; fixtures verifican destino distinto y sufijo. Identidad006 real,
CSRF/permisos actuales, recepción002 y configuración001; sin endpoint de autenticación
ni de cálculo especial para pruebas. Contraseña sintética en archivo0600 temporal.

```sh
TEST_DATABASE_URL="$COSTS_TEST_DATABASE_URL" uv run --locked pytest backend/tests -q --cov=ecs_ec.costs --cov-report=term-missing:skip-covered
npm --prefix frontend run typecheck
npm --prefix frontend test -- --reporter=dot
npm --prefix frontend run build
DATABASE_URL="$COSTS_MIGRATIONS_TEST_DATABASE_URL" ENVIRONMENT=test uv run --locked alembic -c backend/alembic.ini upgrade head
DATABASE_URL="$COSTS_MIGRATIONS_TEST_DATABASE_URL" ENVIRONMENT=test uv run --locked alembic -c backend/alembic.ini check
docker build -t ecs-spec004-validation .
```

Resultados:365 pruebas backend aprobadas en57.67s, incluida referencia de todos los
cargos con historia física completa; cobertura de líneas de004:91% (1310 sentencias,115 sin
recorrer; no equivale a cobertura de todos los estados). Frontend52 pruebas/22 archivos
aprobados en6.33s. Exportación Next de11 rutas,
incluidas `/costos/` y `/administracion/costos/`; typecheck y Alembic check sin diferencias.
Cadena nueva `costs_004_initial`→`costs_004_calculations`→`costs_004_bills`, sobre head
previo `47457bdabdfa`; upgrade completo también probado desde base vacía. Downgrade
rechaza eliminación destructiva de evidencia financiera.

Navegador: ocho recorridos aprobados en dos bases sintéticas. Primero costs.spec.ts (2),
cost-profiles.spec.ts (1), cost-comparisons.spec.ts (3), cost-history.spec.ts (1),
con renovación normal006; luego cost-supply-initial.spec.ts (1), otra base sin004,
contra imagen Docker. Duraciones observadas de los archivos:2.4/3.1/4.0/2.6/2.6 segundos
respectivamente. Son duraciones de suite locales, no garantías de latencia o carga.
Comandos y condiciones de las semillas en [quickstart](../quickstart.md).

Se reiniciaron Uvicorn y PostgreSQL, conservando recursos/cuentas. Los siete recorridos
principales se repitieron tras reinicio con recursos persistidos y sobre la imagen final. Smoke de imagen con
usuario `ecs`: readiness200, ambas páginas200 y API sin sesión401. Un proceso de aplicación
común, sin Node/worker/SMTP en runtime. Imagen final `ecs-spec004-validation`, digest
`sha256:77d26c276421541b694910b18d5fe860b98831edeeae55fda4972d2563e02679`.
Los intentos iniciales de navegador arrancaron antes del readiness y fallaron por conexión rechazada;
se verificó readiness200 antes de repetir el recorrido.

Tamaños observados del fixture de navegador antes de limpieza:21 cálculos/21 capturas,
7 revisiones de boleta y6 comparaciones; máximo JSON textual3075/3642/1009/626 bytes
respectivamente. No mide retención/carga de instalaciones reales. Referencia histórica de
hash/corte en [entrega del productor](producer-handoff.md).

## Integridad y límites

- Decimal textual/NUMERIC, redondeo explícito capturado, sin float monetario. Quantum5
  redondea12.5→15. Impuesto incluido sin desglose conocido mantiene neto/impuesto null;
  configuración fuera de precisión queda limitada, sin producir dinero falso/fallo técnico.
- Resultado/captura/componentes/auditoría en transacción; fallo técnico produce cost.failed
  común atómico. Un writer caído no deja resultado/evento confirmado parcialmente.
- Revocación006 impide lectura/replay. Consumidores008/SMTP/telemetría ausentes o
  indisponibles no bloquean cálculos. Excepciones/secretos no cruzan respuesta/evento.
- Retención por aniversario calendario y grafo de evidencia; reproducción tras retirada
  real002. Lecturas no extienden plazos ni crean cálculo/boleta/comparación.
- Revisiones/ETags/idempotencia y captura al corte conservan evidencia. Comparación
  pendiente no hereda diferencias históricas ni entra al agregado005.

Docstrings propios revisados por AST en42 archivos Python sin elementos ausentes; componentes/helpers/clientes documentados junto a
fórmulas, entradas, efectos y límites. Tipos readonly se generan desde Pydantic004 mediante
`generate_costs_types.py`. Lockfiles/dependencias sin cambios. Checklists de requisitos
leídos como puerta16/16; no se alteraron marcadores de revisión. No hay extensions.yml
ni hooks de implementación registrados.

Detalle: [US1](us1.md), [US2](us2.md), [US3](us3.md), [US4](us4.md),
[trazabilidad](coverage.md), [SC-006 pendiente](usability.md). No acredita aceptación
humana, despliegue VPS, PDF005, notificaciones008, instrumentación007 ni tarifas reales.
