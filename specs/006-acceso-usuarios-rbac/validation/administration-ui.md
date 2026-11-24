# Administración en navegador — 2026-11-24

Tres escenarios `identity.spec.ts` pasan consecutivamente sobre una base nueva con
`seed_costs_reference.py`, monolito/export reales y reloj privado. El tercero verifica
formularios y auditoría de los proveedores, sin respuestas funcionales simuladas.

Administrador calcula y recalcula1000kWh, cambia configuración001 y restaura la fuente
con dos revisiones distintas; confirma un nuevo perfil004 y una boleta manual. Zona IANA
inválida se rechaza422 conservando revisión/borrador; precio negativo no publica una
revisión nueva. El historial muestra actores de cuenta y resultados correctos de
configuración, perfiles, boletas y cálculos. Operador no accede a la tabla administrativa.

También se ejecutaron los escenarios propietarios `costs.spec.ts` (2),
`cost-comparisons.spec.ts` (3), `cost-profiles.spec.ts` (1) y `cost-history.spec.ts` (1):
suministro concurrente, perfiles/calendario retroactivo y borrador, boleta/corrección,
replay de respuesta perdida, recálculo y selección histórica. Conservan datos/cálculos
anteriores y borradores inválidos. Se actualizaron selectores antiguos y referencias
históricas para poder repetir los ensayos después de una ejecución interrumpida.

[Resultados globales](regression.md). No se acredita usabilidad con personas ni VPS.
