# Investigación: Consumo eléctrico por categorías

**Fecha**: 2026-11-01. [Plan](plan.md), [spec](spec.md),
[arquitectura](../../docs/architecture.md), [hoja de ruta](../../docs/implementation-roadmap.md).
Registro de decisiones de diseño, sin afirmar ejecución de software. La selección de
pila proviene de la arquitectura; no se vuelve a afirmar compatibilidad ejecutada.

## R1 — Propiedad y ausencia de ciclo de implementación

**Decisión**: 001 define dominio, catálogo, fuentes, validación, cálculo candidato y detalle/UI;
002 implementa recepción, almacenamiento, agregaciones y conservación; 003 adapta PAS600/SFTP.
Los puertos quedan en [integrations.md](contracts/integrations.md). Reglas puras de 001
son la primera entrega consumible por 002; no se exige completar la UI de 001 para iniciarlo.
**Razón**: respeta la matriz de propiedad y conserva el alcance de las tareas trasladadas.
**Alternativas**: persistir todo en 001 duplica la responsabilidad de 002; importar
notificaciones o esperar su scheduler introduce dependencias inversas innecesarias.

## R2 — CAT-01 calculada es candidata antes de ser dato incorporado

**Decisión**: sin medidor total, sumar Decimal de todas las categorías presentes no vacías
solo si cada una cubre exactamente el mismo intervalo y la firma modo/base/fuentes de
CAT-01 es estable durante él; registrar referencias/revisiones. Un cambio de firma produce
`calculation_configuration_changed` con segmentos y sin total, conservando parciales.
Con medidor total, usar solo su serie. 002 incorpora candidatos completos respetando
15 minutos desde la última incorporación CAT-01 y los conserva; pendientes se reevalúan
internamente al vencer el límite, dentro del lifespan del monolito. GET no incorpora.
**Razón**: [002 FR-002/006/015](../002-registro-retencion-consumo/spec.md) también protege
frecuencia, primera incorporación y conservación del total calculado.
**Alternativas**: sumar en cada lectura elude el límite; sumar las categorías disponibles
publica un total incompleto; reemplazar huecos del medidor general contradice 001 FR-006.

## R3 — Orígenes y configuración explícitos, con historia estable

**Decisión**: catálogo fijo y configuración administrativa con revisión global de auditoría
y `category_revision` positiva por categoría. Solo cambiar presencia/fuente incrementa
la revisión de una parcial; CAT-01 física depende de su fuente propia y calculada de su
modo/base/pares categoría-fuente. Etiquetas o cambios ajenos no incrementan esa revisión.
Una lectura conserva revisión global de inicio y una categoría estable en todo su intervalo;
puede cruzar revisiones globales ajenas. Cambiar su propia presencia/fuente dentro de él
causa `source_configuration_changed`, sin dividirlo. La primera configuración puede cubrir
historia importada; las posteriores no reinterpretan registros existentes. La zona se
mantiene inmutable desde la primera historia aceptada, incluso tras retirar detalle.
Estas decisiones I1 fueron aprobadas expresamente al aclarar los hallazgos del análisis.
**Razón**: interpretar una consulta histórica con la base actual cambia su significado.
**Alternativas**: inferir medidores de las lecturas confunde fuente ausente con retraso;
editar configuración en sitio pierde trazabilidad; una UI propia de cuentas excede 001;
rechazar todo cruce de revisión global pierde lecturas válidas de categorías sin cambios.

Para U1 se define `MeasurementStore.read_reconfiguration_bounds`, implementado por 002:
historia aceptada global y máximo fin por categoría, conservados después de retirar detalle.
Configuración lo consulta bajo los mismos bloqueos y UoW de escritura que recepción;
proveedor ausente/fallido o claves incompletas impiden modificar, no significan vacío.
Solo el bootstrap de la primera configuración puede preceder a 002. Consultar extent global
o detalle conservado no garantiza estos límites por categoría ni su persistencia histórica.

## R4 — Precisión y equivalencia

**Decisión**: consumir cadenas decimales, calcular con `Decimal` desde texto y almacenar
NUMERIC sin escala coercitiva en 002. Conversión exacta: Wh × 0.001; kWh × 1; MWh × 1000.
Decisión A1 aprobada: medición normalizada `0 <= E < 10^30 kWh`, múltiplo exacto de
`q=10^-15 kWh`; validar en kWh para preservar equivalencia entre unidades y rechazar con
`energy_out_of_supported_range` sin redondear. `M=10^30-q` es el máximo individual;
CAT-01 calculada admite la suma exacta hasta `6*M`, inclusive. El contexto de precisión 50
cubre conversiones y suma de seis contribuciones (hasta 31 enteros y 15 fraccionarios),
con detección de `Inexact`, `Rounded`, operaciones inválidas y mezcla con float. Conservar
original/evidencia y canonicalizar ceros insignificantes exactamente antes de operar.
HTTP devuelve cadenas fijas; no aplicar el techo individual a totales incorporados.
**Razón**: los números binarios y la escala fija pueden cambiar valores pequeños.
**Alternativas**: `float` y `toFixed(2)` pierden precisión; límites distintos por unidad
rechazan cantidades equivalentes; un máximo individual aplicado al total impide sumas
válidas. El dominio aprobado es técnico, no un umbral físico inferido del edificio.
[Decimal](https://docs.python.org/3.14/library/decimal.html) documenta
contexto y señales; [NUMERIC](https://www.postgresql.org/docs/18/datatype-numeric.html)
permite conservar escala variable.

## R5 — Duplicados y solapamientos bajo concurrencia

**Decisión**: identidad de reenvío = edificio/origen/categoría/inicio/fin UTC. Comparar kWh
exactos antes de considerar un intervalo nuevo. 002 debe serializar recepción por categoría
y proteger unicidad/exclusión en PostgreSQL, incluyendo fuentes sucesivas de la misma serie.
Recomendación: `tstzrange` explícito `[)` y exclusión GiST por edificio/categoría/rango,
con `btree_gist` si combina claves escalares. El resultado por registro conserva el aceptado.
**Razón**: una comprobación previa sin protección transaccional permite aceptar dos intervalos
incompatibles. **Alternativas**: `ON CONFLICT DO UPDATE` sobrescribe evidencia; SQLite no
acredita esta garantía. [Rangos y exclusión PostgreSQL](https://www.postgresql.org/docs/18/rangetypes.html#RANGETYPES-CONSTRAINT)
ofrecen la restricción requerida; su migración pertenece a 002.

## R6 — Fechas, períodos y consulta coherente

**Decisión**: almacenar UTC con precisión de microsegundos; aceptar instantes con offset
y zona IANA configurada. Responder además en hora del edificio con offset. Contención
completa, orden por instantes reales y aviso de intervalos cruzados. Rechazar hora local
inexistente y exigir un offset válido para resolver una repetida. No truncar precisión
temporal al ordenar/filtrar en JavaScript. Una consulta compuesta comparte UoW
REPEATABLE READ y corte; consumidores pueden suministrar la misma UoW.
**Razón**: la zona del navegador no define el intervalo y la hora repetida son dos instantes.
**Alternativas**: fechas ingenuas o una consulta por representación permiten ambigüedades
y conjuntos distintos. [ZoneInfo](https://docs.python.org/3.14/library/zoneinfo.html)
resuelve zonas/fold; [aislamiento PostgreSQL](https://www.postgresql.org/docs/18/transaction-iso.html)
fundamenta la captura. La política de aniversarios de retención no se aplica al formulario.

## R7 — UI exportada, precisa y verificable

**Decisión**: página estática `/consumption/`; un resultado inmutable alimenta SVG y tabla.
Segmentos/barras independientes por intervalo, sin unir huecos ni exigir dos puntos.
Strings originales para etiquetas/tooltip/tabla; `decimal.js` para razones geométricas,
convirtiendo a `number` solo coordenadas normalizadas. Un positivo inferior al píxel
tiene marcador distinguible y texto exacto; cero tiene marcador propio. Sin downsampling
ni reducción silenciosa de registros. No introducir una biblioteca general de charts.
**Razón**: una sola serie por consulta permite verificar cada intervalo con su fila.
**Alternativas**: líneas interpoladas sugieren lecturas ausentes; redondeo por vista produce
contradicciones. Fuentes: [exportación Next](https://nextjs.org/docs/app/guides/static-exports),
[formas SVG](https://www.w3.org/TR/SVG2/shapes.html), [decimal.js](https://mikemcl.github.io/decimal.js/).

## R8 — Respuestas tardías, acceso y actualización

**Decisión**: clave de consulta y generación de solicitud; abortar anterior y descartar
respuestas obsoletas. Separar borrador del rango y último rango válido. Al aceptar una
nueva selección, mostrar carga sin atribuirle valores anteriores; error con reintento.
Leer al abrir, seleccionar y actualizar manualmente, sin streaming. Sesión/CSRF y permisos
de 006, respuestas `no-store`, sin datos privados en build/localStorage. Configuración
solo Administrador; Operador consulta; Programador no obtiene permisos funcionales.
**Razón**: una respuesta de A puede llegar después de B. **Alternativas**: abortar sin
verificar generación no cubre respuestas resueltas; refresco continuo añade una garantía
no especificada. [React](https://react.dev/reference/react/useEffect#fetching-data-with-effects)
documenta ignorar respuestas anteriores. Identidad y permisos proceden de
[spec-006](../006-acceso-usuarios-rbac/spec.md).

## R9 — Entornos y alcance de la evidencia

**Decisión**: fixtures por puerto interno de recepción y PostgreSQL local para desarrollar;
integraciones locales reales con 003/007/008 para SC-006 cuando existan sus propietarios.
007 instrumenta sin hacer de visores un requisito de disponibilidad. Mantener secretos
externos y configurar zona, identidades, destinos y URL por entorno. La aceptación VPS
exige HTTPS/red externa/equipo de desarrollo apagado. Prueba humana SC-005 separada.
**Razón**: contratos preservados permiten validar sin contratar una VPS ni usar servicios
remotos. **Alternativas**: fixture por escritura directa de tablas elude validación;
un test sintético no prueba hardware, SFTP real, comprensión humana ni acceso externo.

No quedan aclaraciones de diseño abiertas. Antes de conectar fuentes reales se debe
confirmar zona, subconjunto instalado, correspondencias nativas y magnitudes con 003;
no se atribuye una configuración sintética a la instalación real.
