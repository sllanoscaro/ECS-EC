# Señales008 sobre infraestructura007 —2026-11-25

008 amplía el catálogo cerrado007 con módulo `notifications`, seis operaciones y
tres eventos terminales: operación, intento SMTP y ciclo de planificación. API incluye
denegaciones tempranas. Cada intento tiene referencia de entrega/intento/ocurrencia y
traza propia; no registra destinatarios, nombres de reglas, umbrales, cuerpos ni errores
crudos. Reintentar el registro de un resultado no emite otro intento SMTP.

Las pruebas usan Telemetry/LogEmitter/SDK007 reales, comprueban cardinalidad, saneado,
trazas y pérdida visible con cola1024 llena. Las comprobaciones de007 seleccionadas
aprobaron86 casos;20 casos de infraestructura ajena se omitieron en esa ejecución
sin entorno explícito. No se presentaron como integración del stack.

La integración adicional sí arrancó un stack007 real exclusivo:
`ecs008-step5-observe`, TLS/mTLS propios y consulta humana en loopback3448. Alloy/Loki
persistieron los eventos008 y Jaeger sus trazas; Grafana publicó `ecs-notifications`.
La puerta solo permite lectura de los dos UID conocidos. UID ajeno y escritura se
deniegan. Revocar el Programador impide la siguiente consulta persistente; cookies
funcionales no autorizan el entorno técnico. Se conserva el esquema de roles007.

Se reutiliza conciliación007 de eventos únicos/cobertura: pérdida, discontinuidad o
replay no conciliable producen N/D. Los registros SMTP se muestran separados de las
operaciones; no se etiquetan como notificaciones únicas ni como entrega externa.
Los13 casos del conciliador JavaScript aprobaron tras ampliar el catálogo.

El stack temporal usa `OBS_REQUIRE_QUOTAS=false` en test; no acredita cuotas físicas
ni TTL24h de007. El ensayo `ecs007-step4-quotas`, sus procesos, mounts y puertos3446
se conservaron. No se reinició ni reutilizó para producir estas señales008.
