# Referencias propuestas: Mi cuenta

Estado: segunda alternativa aprobada e integrada localmente en `/cuenta/`. Modo: **Operate**.

## Composiciones

1. [Dos columnas](../.impeccable/mocks/account-v1.png): datos de acceso a la izquierda y formulario vertical a la derecha.
2. [Secciones apiladas](../.impeccable/mocks/account-v2.png): resumen horizontal arriba y formulario debajo, con nueva contraseña y confirmación en paralelo en escritorio.
3. [Superficie única](../.impeccable/mocks/account-v3.png): datos arriba, explicación a la izquierda y formulario vertical a la derecha, dentro de un solo panel.

Las tres heredan identidad, navegación y componentes de las referencias aprobadas de dashboard, consumo e ingreso. «Mi cuenta» se resalta con fondo `#4F9A17`, icono y texto blancos; las demás rutas quedan neutras. El correo y el perfil son texto de consulta. El correo de ejemplo es ilustrativo. En implementación se utilizan los SVG originales, sin reconstruir la marca desde la imagen.

## Alcance funcional

Fuentes: [spec de identidad](../specs/006-acceso-usuarios-rbac/spec.md), `frontend/src/components/identity/PasswordForm.tsx` y captura del estado actual en `frontend/test-results/account-before/`. Los escenarios actuales se recorrieron con respuestas sintéticas solo en el navegador: escritorio, móvil, renovación y sesión anónima. No equivalen a pruebas de autenticación real.

La tarea es reconocer la cuenta y cambiar la propia contraseña. Se conservan correo y perfil de consulta, contraseña actual, nueva contraseña y confirmación. La regla vigente permite de 15 a 128 caracteres, incluidos espacios, sin imponer clases de caracteres ni normalizar el valor. El cambio invalida las sesiones anteriores y requiere ingresar de nuevo; la consecuencia se anticipa junto al formulario. «Salir» se concentra en el panel lateral para evitar duplicación.

No se añaden edición de correo/perfil propios, avatares, nombre personal, dispositivos, MFA ni preferencias de notificaciones. No se inventan fechas de acceso ni zona horaria de instalación. El pie mantiene identidad gris y una aclaración de datos ilustrativos propia de estas referencias.

## Estados y adaptación por resolver

- Renovación obligatoria: aviso ámbar y acceso limitado a renovar contraseña o salir. La navegación completa de estas imágenes solo corresponde a una sesión normal; no debe conservarse durante el ingreso restringido.
- Carga, sesión ausente o vencida, error del servidor, contraseña actual rechazada, confirmación distinta y fallo al cerrar sesión: mensajes comprensibles, errores en rojo y advertencias en ámbar, sin depender solo del color.
- Envío: impedir duplicaciones, limpiar secretos al finalizar y conservar la redirección existente al ingreso después del cambio correcto.
- Móvil: una sola columna, campos de ancho completo y desplazamiento vertical cuando sea necesario; no se ha generado aún una referencia móvil de estas composiciones.

Estas imágenes evalúan composición, no son especificación de nuevos endpoints ni aceptación de la spec-006. La selección del usuario determinará qué distribución se refina antes de implementar. Los prompts exactos están en los JSON junto a los PNG y en sus metadatos, generados con la herramienta integrada `image_gen`.

## Verificación de la integración

Se integraron los paneles apilados y la navegación activa. Pasaron 56 pruebas del frontend y la compilación. Chromium revisó escritorio, móvil, renovación obligatoria y sesión anónima con respuestas sintéticas, sin desbordamientos horizontales ni excepciones; estas capturas no verifican autenticación real.
