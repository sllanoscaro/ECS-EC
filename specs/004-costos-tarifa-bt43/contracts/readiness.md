# Preparación de la consulta de Costos

`GET /api/v1/costs/readiness` requiere sesión normal, `costs.read` y `consumption.read`; responde con `Cache-Control: no-store`. No crea configuración, cálculos, boletas ni contrastes.

Respuesta:

```json
{"physical_general": false, "supply_configured": false, "profile_published": false}
```

Las banderas describen la fuente general actual, la existencia del suministro de costos y la existencia de un perfil publicado. No exponen precios administrativos ni garantizan cobertura de un período, compatibilidad completa de todas las vigencias o suficiencia de históricos. Aun con las tres banderas verdaderas, el primer cálculo requiere mediciones físicas del período elegido y puede ser parcial.

El estado vacío presenta los requisitos pendientes. Solo quienes tienen `costs.calculations.create` reciben enlaces a configuración/cálculo; el Operador recibe instrucciones para contactar al administrador. Un fallo de consulta se distingue de configuración pendiente y permite reintentar. Publicar o leer esta pantalla no ejecuta el preparador local de demostración.

Esquema: `CostsReadiness` en `backend/src/ecs_ec/costs/schemas.py`. Pruebas: `backend/tests/contract/costs/test_readiness_api.py` y `frontend/tests/unit/cost-empty-state.test.tsx`.
