# Historial y mantenimiento propios

Consulta real de FunctionalAudit009, sin almacén paralelo ni tablas de otros dominios.
Dos pruebas de contrato pasan: actor autenticado/no autenticado, resultado allowed/denied,
filtros, rango consciente, cursor firmado ligado a filtros, orden descendente y corte
fijo entre páginas. Registro por UUID conserva referencias aun con cuenta desactivada.
Se exponen solo campos de AdministrationEntry, nunca JSONB original ni credenciales.

La composición congela el catálogo de acciones propias. Productores posteriores pueden
aportar sus códigos administrativos a `Identity(..., history_actions=...)`, con metadata
aprobada del contrato común; no se importan sus tablas para consultar evidencia.
UI solo lectura, UTC explícito, estados carga/vacío/error y guard admin; sin editar/borrar.
Vitest y el navegador real comprueban la tabla/consulta filtrada y deniegan la página al
Operador sin mostrar una tabla privada.

Cuatro pruebas de mantenimiento pasan: limpieza técnica tras24h sin borrar cuentas,
espera durable preservada al migrar claves bajo locks, retiro CSRF exige reingreso y
retirada de bucket falla cerrada durante estado reciente con solape de30min. Job interno
acotado, sin worker desplegado ni emisor técnico propio.

Recuperación: ocho casos de servicio y procesoCLI con TTY real verifican cuenta activa
administrativa exclusiva, razón acotada, revisión/renovación/revocación y auditoría de
proceso. No se crea/promueve/reactiva por recuperación. Dos procesosCLI concurrentes
ejercitan el mismo guard PostgreSQL que HTTP. Procedimientos en
[operación](../../../deploy/README.md#identidad-humana-spec-006).
