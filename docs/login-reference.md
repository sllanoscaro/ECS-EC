# Referencias de ingreso

Estado: referencias de escritorio y móvil aprobadas por el usuario e integradas localmente en `/ingreso/`; revisión final **SHIP**. Modo: **Operate**.

- [Escritorio](../.impeccable/mocks/login-desktop-v1.png).
- [Móvil](../.impeccable/mocks/login-mobile-v1.png).

El formulario se centra horizontal y verticalmente en la página, con fondo neutro claro, panel blanco, bordes discretos y botón verde profundo. Mantiene la identidad Electro Conforma y la tipografía de las referencias de dashboard y consumo. En pantallas de poca altura debe permitir desplazamiento sin cortar campos ni controles.

El contenido comprende logo, identificador ECS-EC, título «Ingresar», descripción breve, correo electrónico, contraseña y acción principal. La ayuda remite al administrador técnico para restablecer la contraseña, conforme a la [spec de acceso y usuarios](../specs/006-acceso-usuarios-rbac/spec.md). No se incorporan registro público, acceso social ni recuperación por correo.

La ruta conserva el panel centrado sin navegación privada durante la comprobación de sesión, con sesión iniciada y antes de autenticar. No muestra reloj ni zona horaria; el pie utiliza texto gris discreto. La implementación usa el SVG original en `frontend/public/brand/electro-conforma.svg`, procedente de la [identidad visual](<Identidad Visual Electro Conforma/>); las imágenes generadas son referencias de composición.

Se conservan el cliente de sesión y los flujos existentes: envío de la contraseña exacta y limpieza al finalizar, correo conservado ante rechazo, bloqueo de envío durante la petición o espera por límite de intentos, retorno local seguro y cambio obligatorio de contraseña hacia `/cuenta/`. Tras un ingreso normal sin retorno se abre el dashboard en `/`. Los errores se presentan con texto y color rojo, y el límite de intentos con ámbar y cuenta regresiva. Esos estados no están representados en las dos referencias. Los prompts exactos se conservan en los archivos JSON junto a cada PNG y en sus metadatos.

## Integración y verificación local

La integración comprende `frontend/src/app/ingreso/page.tsx`, `frontend/src/components/identity/LoginForm.tsx`, `frontend/src/components/identity/ApplicationFrame.tsx` y los estilos de ingreso en `frontend/src/app/globals.css`. Extiende el sistema vigente, con ElectroSans autoalojada, panel de ancho máximo 672 px, campos y botón de ancho completo; a 600 px o menos ajusta escala y espacios. La revisión visual final independiente concluyó **SHIP**, sin defectos de interfaz pendientes.

Pasaron 56 pruebas unitarias del frontend, la comprobación de tipos y `npm run build` con exportación estática de Next.js. La [evidencia de Chromium](../frontend/test-results/login-final/results.json) registra 13 escenarios: anchos 1440, 1568, 768, 390 y 320 px (este último con altura de 520 px), rechazo 401, límite 429, envío, comprobación y sesión iniciada, además de las tres redirecciones. No se detectaron desbordamientos horizontales ni excepciones; la pantalla baja permite desplazamiento vertical. Las diez capturas de estados se conservan junto al resultado.

Para repetir la revisión, con el servidor de desarrollo activo, ejecutar desde `frontend/`:

```sh
UI_REVIEW_URL=http://127.0.0.1:3000 node scripts/review-login.mjs test-results/login-review
```

El script usa respuestas sintéticas interceptadas solo en el navegador. Esta evidencia verifica la interfaz y sus transiciones locales; no acredita autenticación contra el backend real ni aceptación integral de la spec-006.

## Direction contract

THESIS: ingreso mediante un único formulario centrado en la página, con la composición aprobada y sin navegación privada alrededor.

OWN-WORLD: hereda los activos originales y los tokens de Electro Conforma. Fondo neutro, panel blanco con borde discreto, controles de radio pequeño, tipografía autoalojada y acción verde profundo.

STORY: reconocer la plataforma, introducir correo y contraseña e ingresar; ante rechazo se conserva el correo, se limpia la contraseña y se explica el resultado. El restablecimiento corresponde al administrador técnico.

FIRST VIEWPORT: logo centrado dentro del panel; identificador ECS-EC, título, descripción, dos campos y botón ancho en columna. Ayuda debajo del botón y pie gris bajo el panel. En móvil se conserva el orden y se permite desplazamiento en alturas reducidas.

FORM: composición de las referencias escritorio y móvil versión 1 aprobadas por el usuario. Solicitud precisa dentro del sistema existente, sin sorteo ni nueva identidad. El envío y la espera existente son las únicas transiciones de estado.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
