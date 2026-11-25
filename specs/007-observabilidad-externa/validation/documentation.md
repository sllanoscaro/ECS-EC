# Revisión documental y visual — paso4

2026-11-24. Documentación actualizada junto al código: contratos/integraciones,
salud esquema1 (dos campos opcionales), catálogo LogQL/conciliación y límite de replay,
cuotas reales/snapshot/corte90%, TTL spool, muestreo, operación y ensayo reanudable.
Las guías comunes corrigen además la afirmación obsoleta de que PDF006 seguía pendiente.
No se cambian checklists de revisión ni se certificaT063 antes de sus prerrequisitos.

Revisión AST de44 archivos Python007 (fuente, unit/integration/contract y scripts):
todos los módulos/clases/funciones con docstrings. El validador006 revisó49 archivos
sin faltantes. Ruff --select F sobre fuente/pruebas/scripts007 pasa; imports de casos
propietarios se declaran como reexports explícitos para su colección pytest, sin copiar
sus pruebas ni eliminarlas como si fueran imports no usados.

Dashboard y plugin son fuente manual; platform.json se provisiona readonly. El generador
render_dashboard.py produce una copia privada por revisión/ratio y documenta origen.
No se editan bundles de imágenes. Node --test verifica el conciliador con13 casos;
E2E verifica fuentes/corte/cobertura y navegación reales. [Resultados](step4.md).

Se aplicó design-taste-frontend: app-screen, dirección data-terminal, semilla219382192,
conservando tipografía/tema/shell nativo Grafana. Se revisó el panel con Playwright a
1440/768/390px y CA/Basic reales en HOME exclusivo. Se corrigió ajuste de tablas/textos
largos para evitar recorte de unidades en móvil; el panel conserva scroll para datos
extensos. La revisión automatizada distribuida no admite esta frontera Basic/CA;
se usó navegador autenticado equivalente, sin proxy público ni TLS desactivado.
Se comprobó que el aviso403 desaparece manteniendo las denegaciones opcionales.
Las anotaciones/alertas automáticas de Grafana se desactivan en este dashboard de
consulta para evitar solicitudes fuera de contrato y su aviso403. APIs opcionales
ofrep/historial de página continúan denegadas; no se habilita escritura para silenciarlas.

Capturas saneadas en artifacts/step4-panel-{1440,768,390}.png y
artifacts/step4-diagnosis-1440.png (deltas de pérdidas/colas y enlaces reales). Muestran únicamente
referencias aleatorias/datos técnicos de fixture, sin sujetos personales/credenciales.
No sustituyen diagnóstico con personasT061 ni nueva revisión finalT062–T064.
