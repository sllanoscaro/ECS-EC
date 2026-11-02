# Research: Reportes PDF de una página por período

**Date**: 2026-11-01. Investigación documental; la instalación y generación real pertenecen a implementación.

## R1. Motor PDF dentro del monolito

**Decision**: ReportLab 5.1.0, Canvas y gráficos vectoriales; fuente TTF Unicode incrustada y distribuida con su licencia. Dependencia fijada con uv dentro de la imagen Python compartida.

**Rationale**: Permite controlar coordenadas, tamaños de fuente y geometría, necesarios para una página A4 con mínimo 10 pt. La metadata mantenida en PyPI declara Python >=3.9 y clasificador 3.14; eso orienta compatibilidad, pero no sustituye la instalación y prueba con las transitivas fijadas. Las fuentes incrustadas evitan depender de descargas al leer el PDF sin conexión.

**Alternatives considered**: HTML a PDF con navegador añade runtime y dependencias que no necesita esta síntesis; imprimir la interfaz no garantiza sus cortes, una página ni fuentes. Un motor externo desplegado separadamente incumpliría la unidad monolítica.

**Sources**: [ReportLab/PyPI](https://pypi.org/project/reportlab/), [Canvas](https://docs.reportlab.com/reportlab/userguide/ch2_graphics/), [fuentes TTF](https://docs.reportlab.com/reportlab/userguide/ch3_fonts/), [gráficos](https://docs.reportlab.com/reportlab/userguide/ch11_graphics/).

## R2. Composición y comprobación independiente

**Decision**: Presupuesto de seis bandas, texto medido antes de dibujarlo y manifiesto de cajas/tamaños por objeto. pypdf 6.21.4 analiza bytes resultantes: página, MediaBox, contenido y fuentes; revisión visual completa el control de geometría.

**Rationale**: pypdf permite contar páginas y extraer texto/metadata; la extracción no demuestra por sí sola legibilidad o ausencia de solapamientos. Se requieren el manifiesto, detección de intersecciones incompatibles y revisión de impresión al 100 %. El algoritmo nunca añade una segunda página ni reduce texto por debajo del mínimo.

**Alternatives considered**: Comparar solo capturas puede omitir errores de datos; extraer solo texto no detecta todos los recortes; aceptar una segunda página contradice FR-004.

**Sources**: [pypdf/PyPI](https://pypi.org/project/pypdf/), [extracción y límites](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).

## R3. Captura coherente y límites financieros

**Decision**: Una unidad de trabajo PostgreSQL REPEATABLE READ consulta energía/calidad y `Costs.read_snapshot` con corte UTC fijado al inicio; persistir la captura antes de liberar la transacción y renderizar fuera de ella. Usar únicamente revisiones registradas y vigentes al corte.

**Rationale**: Aísla la composición de cambios recibidos durante el render. Energía mantiene sus bloques calendario; costos incluyen solo cierres efectivos en `[inicio,fin)` ocurridos al corte. Un snapshot financiero real ya proporciona desglose, impuestos, revisiones y pares; PDF no recalcula BT4.3.

**Alternatives considered**: Consultas separadas sin transacción pueden mezclar revisiones. Mantener locks durante el render bloquearía trabajo ajeno. Consultar precios actuales para un snapshot histórico rompería reproducibilidad.

**Sources**: [aislamiento PostgreSQL 18](https://www.postgresql.org/docs/18/transaction-iso.html), [sesiones SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html), [contrato de costos](../004-costos-tarifa-bt43/contracts/integrations.md).

## R4. Resultado y fallo durable independientes de notificaciones

**Decision**: Guardar captura JSONB tipada, resultado y binario BYTEA con hash en PostgreSQL; publicar estado exitoso y bytes juntos. Persistir resultado fallido y `pdf.failed` juntos mediante `audit.events.EventWriter`, sin importar `notifications`.

**Rationale**: El binario incompleto no puede quedar descargable. Una excepción se traduce a una razón funcional y una referencia opaca; el evento se confirma con el resultado de fallo en una transacción nueva si la operación de generación ya se revirtió. No se intenta conservar el evento dentro de una transacción abortada.

**Alternatives considered**: Emitir solo logs no da evidencia durable; llamar al consumidor durante la generación crea dependencia circular; archivos públicos y estado en otra base exigen coordinación adicional.

**Sources**: [transacciones PostgreSQL](https://www.postgresql.org/docs/18/tutorial-transactions.html), [contrato de eventos](contracts/integrations.md).

## R5. Dependencias, tareas y límites de aceptación

**Decision**: Reutilizar capacidades reales de identidad/consumo/auditoría y construir reports en spec-005. Spec-004 entrega costos reales; spec-008 únicamente consume eventos. Supervisor interno y executor inicial de dos plazas, sin un servicio de aplicación aparte.

**Rationale**: Conserva la arquitectura y elimina el supuesto de productores ya implementados. Dobles permiten trabajo aislado, pero la guía exige integración final real. La generación de artefactos no acredita pruebas ni una entrega remota.

**Alternatives considered**: Expandir spec-008 para construir PDF oculta su alcance; usar un PDF ficticio no satisface la dependencia del productor.

**Sources**: [constitución](../../.specify/memory/constitution.md), [spec](spec.md), [arquitectura del monolito](../../docs/architecture.md).
