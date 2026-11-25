# Verificación externa008 — pendiente

008:T091 permanece abierta. Esta ejecución no dispone de una VPS/dominio/relay reales
proporcionados para su validación. No se activó SMTP de producción ni se enviaron
mensajes a destinatarios externos. Mailpit y los certificados locales no acreditan
esa comprobación.

Al disponer del entorno, aplicar [deploy](../../../deploy/README.md) y comprobar desde
otra red los enlaces públicos HTTPS con sesión/permisos, transporte identificado,
remitente autorizado, submission587 autenticado, STARTTLS y certificado/hostname
verificados. Registrar fechas, referencias y resultados sin secretos ni datos personales.
La aceptación por relay no acredita bandeja o lectura.
