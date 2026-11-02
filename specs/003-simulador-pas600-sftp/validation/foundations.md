# Evidencia parcial — preparación y fundamentos

2026-11-02. Python3.14.4; lock independiente en
`tools/pas600_simulator/uv.lock`. No se declara aceptación de US1–US4.

Comandos ejecutados desde raíz:

```sh
uv lock --project tools/pas600_simulator
uv sync --project tools/pas600_simulator --locked
uv run --directory tools/pas600_simulator --locked pytest -c pyproject.toml tests
uv sync --directory tools/pas600_simulator --locked --no-dev
uv run --directory tools/pas600_simulator --locked --no-dev pas600-sim validate --scenario /tmp/pas600-default.json
git diff --check
```

Resultado: 18 pruebas pasan. Se comprobó primero fallo por módulos de comportamiento
aún ausentes. La primera invocación pytest desde raíz recogió configuración backend;
se corrigió seleccionando directorio/configuración propios antes del ciclo TDD.

Casos: siete medidores por defecto; ausencia sin canal/rango/tasas; duplicación de
identidad/categoría; rechazo de campos desconocidos, NaN/Infinity y float; divisibilidad,
offsets y zona IANA; hora repetida DST; quantum representable; checksum canónico con
dominios separados; orden de categorías estable; formato excluido del hash lógico;
output ocupado; fallo de rename conserva estado previo. Estado inicial `generating`
y UUID/reloj reales persisten mediante temporal/fsync/rename/fsync de directorio.

Se verificó instalación sin pytest y sin imports `ecs_ec`; se construyó escenario
por defecto en `/tmp/pas600-default.json` y CLI devolvió código0/JSON válido.
`validate` es el único subcomando disponible; no se marca T018 completa porque
`generate` depende todavía de escritores, generación y referencias.

T001/T002/T004/T005/T006/T007 completas. T003 tiene oráculo aritmético inicial,
pero revisión documental/fixtures aún pendientes: ver
[procedencia y bloqueo](../../../tools/pas600_simulator/tests/fixtures/reference/README.md).
No se reemplaza DOCA0172EN-19 por revisión20 ni se acredita conformidad solo con
los ejemplos de diseño existentes. El usuario autorizó diferir T003 y continuar el desarrollo el 2026-11-02; la conformidad documental sigue pendiente.
No se modifican checklists de revisión ni se ejecutan otras specs.

No existe `.specify/extensions.yml`: sin hooks before_implement/after_implement.
