# Prerrequisitos008 —2026-11-24

009core/DB/UoW/reloj/auditoría,006sesiones/permisos/registro neutral,001/002fuentes/
ventanas/resumen,004cost.failed y005pdf.failed están implementados. Se usan los proveedores
reales, sin dependencia inversa sobre008.007 dispone del emisor/capacidad local; su
ensayo24h exclusivo se conserva en ejecución y no se usa para pruebas008.

Mailpitv1.33.1 fijado por digest, descargado desde el [registro oficial](https://github.com/axllent/mailpit/pkgs/container/mailpit).
Puertos solo loopback y perfil mail, sin dependencia de readiness. SMTP habilitado
explícitamente; credenciales externas y producción STARTTLS verificado en587.
Checklist requirements16/16; notificaciones0/36. Usuario autorizó continuar sin marcar
las checklists. Estas conservan todos sus marcadores de revisión.

No hay evaluación humana, VPS/relay real ni aprobación de SC-008/entrega externa.
La disponibilidad inspeccionada se contrastó después mediante las pruebas reales de
[US2](us2.md), [US3](us3.md), [US4](us4.md) y [señales](observability.md). El
[estado vigente](acceptance.md) distingue esos resultados de las comprobaciones externas.
