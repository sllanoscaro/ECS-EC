# Entrega del productor004 a005/008

2026-11-02. Implementación real dentro del mismo monolito; no requiere SMTP, scheduler,
worker o consumidor008. Dependencias reales: identidad006, catálogo/fuentes001,
recepción/consulta/conservación002 y UoW/auditoría/eventos009.

- Motor `backend/src/ecs_ec/costs/engine.py`, versión `bt43-v1`: Decimal, políticas
  capturadas y cantidades físicas; referencias independientes en [US1](us1.md).
- Cálculo, componentes y captura persistidos; proceso y PostgreSQL reiniciados y recursos
  recuperados en navegador. El hash de referencia sintética inicial es
  `1773914c37b8ff7f926606ece7c1379a513173dc6aeb10ee35684bcc1131993b`,
  captura `2026-11-02T20:46:18.222234Z`. No corresponde a un cálculo real del edificio.
- Fallo del motor: nueva transacción válida guarda resultado fallido y `cost.failed`
  común009 juntos. Reintento devuelve el mismo resultado/evento; fallo del writer
  revierte ambos y devuelve503 sin afirmar durabilidad. Ver pruebas de eventos004.
- `Costs.read_snapshot(..., unit_of_work=uow)` produce `CostsSnapshot` v1 real. Prueba
  compartida REPEATABLE READ y selección exacta al corte en [US4](us4.md).
- Reproducción pura verifica hash/versión y funciona después de retirar detalle002.

Para005: consumir el servicio compuesto en `app.state.costs`; compartir UoW/corte con
consumo y serializar la captura. No recalcular, prorratear ni retroceder a comparaciones
viejas cuando el par seleccionado esté pendiente.

Para008: leer `FunctionalEvent`009 con `event_type=cost.failed`, identidad/revisión del
resultado y payload funcional saneado. El consumidor decide sus reglas/destinatarios;
no se autoriza modificar el resultado ni introducir dependencias de correo en004.

Contrato vigente: [integraciones](../contracts/integrations.md). Las integraciones005/008
pertenecen a sus specs; no se declaran entregadas por comprobar este productor.
