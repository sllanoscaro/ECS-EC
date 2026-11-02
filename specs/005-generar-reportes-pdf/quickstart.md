# Quickstart y validación: Reportes PDF reales

**Contexto compartido**: [arquitectura](../../docs/architecture.md) y
[hoja de ruta](../../docs/implementation-roadmap.md). La infraestructura común pertenece
a [plataforma009](../009-fundaciones-plataforma/plan.md); esta funcionalidad consume sus capacidades.

Esta guía describe la implementación prevista. Hoy existen artefactos de diseño; los comandos de aplicación/pruebas serán ejecutables después de completar [tasks.md](tasks.md). No se afirma generación real, instalación de bibliotecas ni aceptación de personas ya realizada.

## Prerrequisitos y arranque

- Capacidades reales de identidad/sesión/permisos, consumo/calidad con series versionadas y auditoría/EventWriter dentro del monolito. No depender de la fase completa de notificaciones, su consumidor ni SMTP.
- Spec-004 implementada y `Costs.read_snapshot` disponible con el contrato [integrations.md](contracts/integrations.md); un stub no acredita las pruebas finales de costos/PDF.
- Emisor común real de spec-007 en `backend/src/ecs_ec/observability/logging.py` y `tracing.py`, según su [especificación](../007-observabilidad-externa/spec.md) e [investigación trasladada](../007-observabilidad-externa/research.md), para aceptar la instrumentación propia. No requiere completar sus visores/recolectores ni que estos estén disponibles en ejecución.
- Entorno local de desarrollo de la aplicación: CPython 3.14, uv, Node >=20.9/npm, PostgreSQL 18 y Docker Compose; lockfiles, TTF/licencia y ReportLab/pypdf fijados.
- Aplicar migración `reports_initial.py` después de las capacidades compartidas, sin volver a crear tablas de identidad/auditoría ni modificar mediciones/costos.

Comandos previstos desde la raíz:

```sh
uv sync --locked
npm --prefix frontend ci
docker compose up -d db
uv run alembic -c backend/alembic.ini upgrade head
docker compose up -d app
uv run pytest backend/tests/unit/reports backend/tests/integration/reports backend/tests/contract/reports
npm --prefix frontend run test -- --run
npm --prefix frontend run build
npm --prefix frontend exec playwright test tests/e2e/reports.spec.ts
```

Las pruebas usan base independiente, cuentas sintéticas y fuentes conocidas. `scripts/seed_report_reference.py` debe rechazar configuración de producción; prepara los casos diarios, mensuales y anuales para revisión manual sin un servicio remoto. No se exige activar el perfil SMTP para generar PDF ni emitir el evento durable.

## 1. Selección, resultado y descarga — US1

Ingresar como Operador o Administrador con permiso vigente. Seleccionar día, mes y año en `/reportes/`; cada solicitud identifica `[inicio,fin)`, zona y corte. Período actual mantiene límites y se declara provisional; pasado sin datos produce una página explícita de ausencia. Fecha imposible, campos incompatibles y período totalmente futuro generan error por campo y conservan selección.

La API devuelve solicitud durable; consultar estado hasta generado/fallido. Descarga exitosa contiene bytes `application/pdf` con nombre seguro y no requiere volver a generarlos. Sesión ausente, identidad Programador o permiso retirado no descargan por URL directa. Una repetición HTTP con misma clave no crea otra solicitud; nueva petición de reintento conserva anterior e identifica nueva emisión.

## 2. Una página A4, tabla y gráfico — US2, SC-001/002/005

Generar casos diario/mensual/anual con siete categorías, nombre de edificio de 120 caracteres, nombres de categoría de hasta 80 en las fixtures, energías 0, 0.000001 y 1000000000000 kWh y advertencias de calidad. Estos tamaños son entradas de referencia, no límites nuevos de las fuentes.

Reabrir los bytes con pypdf: una página, A4 vertical dentro de tolerancia 0,1 mm de representación, fuentes/texto efectivo >=10 pt. Comparar números y secciones con snapshot; validar cajas del manifiesto y revisar visualmente impresión A4 al 100 %, incluido gráfico/ejes/notas. No dar SC-001 por aprobado mediante conteo de páginas o extracción de texto solamente.

Día con cambio horario conserva horas reales/desfases; mensual conserva todos los días y anual los doce meses. Ausencias son vacíos visibles sin interpolación. CAT-01 calculada de 20 kWh con base CAT-03/CAT-05 conserva ese total/base y no suma otra vez los parciales; costos declaran falta de medición general.

Preparar una fixture mensual y otra anual cuyo productor conserve un total válido de 30 kWh con segmentos disjuntos de 10 kWh medidos y 20 kWh calculados, estos últimos con base CAT-03/CAT-05. El PDF conserva total y segmentos, identifica «Origen mixto» y muestra períodos, fuentes y bases sin ocultar cambios relevantes. La captura mantiene `source_mode` y `provenance_segments` en filas/bloques; la sección financiera usa el resultado real de spec-004 y no convierte esos 30 kWh en medición física. Comprobar también cambios de base/fuente con el mismo modo; un intervalo no numérico por cambio de configuración conserva su diagnóstico sin inventar energía. Estos casos válidos deben superar también página, fuentes y geometría.

Forzar composición inadmisible o bytes corruptos mediante mecanismo interno de pruebas: resultado fallido sin descarga y con motivo funcional; no reducir fuente, añadir anexo o quitar categoría/advertencia. Todas las fixtures válidas de referencia deben terminar exitosamente; fallar no sustituye ese objetivo.

## 3. Costos y comparación pareada — US3, SC-003

| Caso | Resultado esperado |
| --- | --- |
| Ciclo octubre–noviembre que cierra en noviembre | Incluido en noviembre con sus fechas/alcance |
| Ciclo solapado que cierra fuera | Excluido, sin prorrateo |
| Cierre exactamente en inicio | Incluido si ya ocurrió al corte |
| Cierre exactamente en fin | Excluido; pertenece al siguiente período |
| Fin previsto aún no alcanzado al corte | No es un cierre efectivo |
| Costos 10/20/30, boletas 9/29 para primero/tercero | Disponible 60 CLP/tres ciclos; contraste 40 frente a 38, diferencia 2/dos pares |
| Cálculo parcial o boleta ausente | Limitación explícita, importe desconocido no es cero |
| Revisiones múltiples | Solo revisión vigente al corte; ciclo contado una vez |
| Cálculo y boleta revisados sin comparación del par exacto | «Contraste pendiente para estas revisiones», diferencias null y exclusión de importes/conteo del contraste agregado; disponibles mantienen su alcance separado |
| Impuestos/créditos/no comparables | Mismos signos, bases y reglas de spec-004 |
| Sin cierres | Mensaje de ausencia financiera; energía permanece disponible |

Usar el productor real de spec-004 y comparar el PDF con su consulta equivalente al mismo corte, sin tarifas inventadas ni lectura de precios actuales para una captura antigua.

Secuencia de revisión: crear cálculo C1, boleta B1 y comparación K1; emitir PDF A y conservar captura/hash. Corregir B1 a B2 sin nueva comparación y emitir PDF B: conserva C1/B2, informa `missing_for_selected_revisions` y el aviso pendiente, sin diferencias ni inclusión de ese ciclo en el contraste. Crear K2 para C1/B2 y emitir PDF C: incluye el nuevo par. Repetir el caso con recálculo C2 sin comparación de C2/B2. Las lecturas no crean comparaciones ni retroceden revisiones; PDF A sigue conservando C1/B1/K1 y sus bytes/hash originales.

## 4. Calidad, corte y reproducibilidad — US4, SC-002/004

Categoría sin medidor, instalada sin datos y cero válido conservan estados distintos. Huecos y registros rechazados no se rellenan. Un agregado anual conservado de referencia de 1200 kWh y detalle mensual retirado sigue mostrando 1200; el gráfico indica detalle no disponible, sin reemplazarlo por la suma parcial restante.

Insertar nuevas mediciones/revisiones durante generación: el documento usa únicamente la captura al corte fijado. Nueva emisión posterior puede reflejar cambios. Repetir datos/opciones/revisiones al mismo corte produce valores, agrupaciones y estados equivalentes aunque el identificador y emisión sean distintos.

Origen simulado identificado queda visible; contraseñas, claves, excepciones y control privado del simulador no aparecen en contenido/metadatos/eventos. Abrir el documento descargado con la red desconectada: todos los elementos indispensables para interpretarlo permanecen en la página.

## 5. Resultado persistido y evento U1

Generar un PDF real y comprobar solicitud, captura, resultado, BYTEA, longitud/hash y estado confirmado. Detener el consumidor de notificaciones o no instalarlo: el productor sigue funcionando.

Provocar fallo admitido de composición o interrupción de generación: resultado fallido y `pdf.failed` quedan en la misma transacción mediante `audit`. Repetir reconciliación no duplica el evento. Una prueba de rollback demuestra que no existe resultado fallido confirmado sin su evento ni evento aislado sin resultado. Una descarga repetida o un formulario inválido no crea un evento de fallo del generador.

## 6. Uso con personas — SC-006

Registrar diez tareas con personas representativas del monitoreo: elegir período, descargar e identificar total/cobertura/situación de costos sin ayuda. Al menos nueve terminan en <=2 minutos. Guardar tiempos, éxito y obstáculos; si faltan participantes o resultados, mantener el criterio pendiente. E2E no sustituye esta evaluación.

## 7. Instrumentación propia — hoja de ruta y spec-007

Ejecutar `backend/tests/integration/reports/test_observability.py` con el emisor común real. Comprobar correlación desde solicitud hasta executor, etapas de captura/espera/render/preflight/publicación y descarga, y distinción entre éxito, rechazo esperado y fallo inesperado. Verificar saneamiento y que no aparecen secretos, binario, consumos ni importes; las referencias únicas no son etiquetas. Los conteos y la duración siguen las unidades, ventanas y exclusiones de [integrations.md](contracts/integrations.md).

Repetir POST con la misma clave y consultar/descargar varias veces: solo la primera admisión incrementa generaciones y cada resultado terminal se observa una vez cuando no hay pérdidas. Provocar fallo interno de generación y comprobar su resultado técnico junto al resultado funcional y `pdf.failed`, sin confundirlos. Interrumpir transporte o saturar la cola técnica mediante mecanismos internos: generación, descarga y commits funcionales siguen operativos; las pérdidas se contabilizan y no se presenta cobertura técnica completa. La comprobación local no exige visores activos ni acredita todavía su aceptación externa en spec-007. Registrar comandos y resultados reales en `validation/observability.md` antes del checkpoint US1.

## Evidencia de aceptación

Guardar comandos, versiones, tzdata/fuentes/plantilla, parámetros de fixtures, hashes y referencias sintéticas de resultado, comparaciones de datos, manifiestos y revisión visual en `validation/`. No guardar datos personales o secretos en reportes técnicos. Los resultados se registran al ejecutar; una guía o un diseño no acreditan el cumplimiento.
