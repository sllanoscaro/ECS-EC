# Habilitación de Costos en la demo local

El usuario autorizó preparar la instalación local después de comprobar que no tenía suministro, tarifas, ciclos ni boletas. La interfaz nueva y su backend estaban implementados, pero el arranque de la demo únicamente alimentaba consumo y CAT-01 era un total calculado. El reinicio previo no verificó esta dependencia operativa.

## Cambios

- Preparador explícito en `deploy/demo/prepare_costs.py`: valida entorno local/calendario, edificio y fuentes sintéticas; activa prospectivamente el medidor general y guarda suministro/perfil con referencias ilustrativas. Rechaza configuración financiera ajena y cambios de fuente posteriores al preparado. No crea cuentas ni utiliza sesiones humanas para escribir.
- Se reutilizan los servicios propietarios de configuración, captura, motor, persistencia de cálculo, registro de boleta, contraste, retención y auditoría. `_save_comparison` concentra la persistencia común de contrastes, conservando la autorización normal de la API. No se añaden rutas públicas de inicialización ni se ejecutan cálculos al consultar.
- El publicador respeta la vigencia de configuración y omite el intervalo que la cruza. El perfil general ampliado se activa solo con el marcador de Costos; sus lecturas son independientes de las parciales. Estas no cambian al habilitar el general, ni se reetiquetan totales calculados anteriores.
- El ciclo de muestra usa únicamente un tramo contiguo recibido físicamente después del cambio. Sin esas lecturas, el preparador conserva suministro/perfil y espera; no crea energía ni históricos para completar el gráfico.
- Perfil y boleta son sintéticos. El perfil requiere energía, transmisión, fijo, potencia, punta e impuestos; los históricos insuficientes mantienen demanda e impuestos dependientes como no calculables. El gráfico distribuye solo la energía neta disponible. El remanente del general conserva «Sin asignar».
- La vista señala la demostración y muestra horas en ciclos de un mismo día. El estado vacío utiliza el [contrato de preparación](../specs/004-costos-tarifa-bt43/contracts/readiness.md) y distingue permisos, requisitos pendientes y fallos de consulta.

## Operación

Instrucciones e importes ilustrativos: [guía de la demo](../deploy/demo/README.md#preparar-la-vista-de-costos). Antes de modificar la instalación se creó un respaldo PostgreSQL protegido en `/tmp/ecs-before-costs-demo.dump`. No es un artefacto para compartir ni se incluye en Git.

La activación del medidor general se registró a las `2026-11-04T02:28:14.146825Z`, equivalentes a las 23:28 del 3 de noviembre en America/Santiago. El primer intervalo íntegro posterior es 23:30–23:45; los anteriores conservan su origen calculado. La configuración, el marcador y los resultados financieros sobreviven a reinicios. Repetir el preparador conserva el primer cálculo, boleta y contraste; no recalcula silenciosamente una revisión.

## Verificación

Las pruebas automatizadas se ejecutan sobre una base `_test` temporal distinta de la aplicación. La prueba del preparador verifica dos ejecuciones sobre los mismos datos, una sola revisión de cálculo/boleta/contraste, reparto disponible, costo completo ausente por falta de históricos y preservación del registro de consumo. El publicador prueba estabilidad de parciales, total acotado, ausencia de futuro y exclusión de cruces. El frontend comprueba causas del estado vacío, permisos y reintento.

La instalación local quedó con un suministro, un perfil, un ciclo, un cálculo, una boleta y un contraste. Conserva 93 intervalos generales calculados anteriores y recibió un intervalo general medido del simulador por SFTP para el ciclo del 3 de noviembre, 23:30–23:45 America/Santiago. El cálculo de muestra presenta subtotal disponible 8.997 CLP y cargo neto de energía 6.479 CLP; el reparto y el contraste están disponibles. El costo completo permanece ausente por falta de históricos de demanda y de la base completa de impuestos. Repetir el preparador conserva el mismo identificador de cálculo.

Validación: 88 pruebas frontend, 37 unitarias de costos, 23 pruebas de API/integración de costos y siete pruebas del publicador. La prueba del preparador también consulta ciclos y distribución mediante HTTP autenticado como Operador en PostgreSQL aislado. La imagen Docker compila la exportación estática y la comprobación de tipos.

Se verificaron 16 estados de navegador con fixtures de pruebas y dos capturas con respuestas exportadas de la base local: `frontend/test-results/costs-live/costs-1440.png` y `costs-390.png`, sin errores ni desbordamiento. Esa revisión visual utiliza presentación de sesión sintética y respuestas financieras reales de la demo; no sustituye una prueba HTTP autenticada sobre la instalación en ejecución. Las etiquetas dentro del anillo se redondean para evitar que los decimales salgan del color del sector; la tabla conserva los porcentajes del servidor.

La revisión visual independiente de las capturas de escritorio y móvil emitió `disposition: ship`, sin correcciones materiales. El resultado se limita a la presentación de Costos con respuestas exportadas del backend local y sesión de presentación sintética; no acredita autenticación HTTP contra la instalación. El HTTP autenticado se valida por separado en PostgreSQL aislado.

Esta preparación habilita la revisión local con datos sintéticos. No acredita tarifas reales, históricos completos, boletas auténticas ni aceptación integral de BT4.3, personas o VPS.
