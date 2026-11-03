---
name: ecs-ui-validation
description: "Auditar y validar visualmente las interfaces de ECS-EC con Playwright MCP, pruebas existentes y Context7. Usar después de cambios de UI o cuando se soliciten screenshots, revisión responsive, accesibilidad, estados de formularios o detección de regresiones visuales."
---

# Validación de interfaz de ECS-EC

## Preparación

1. Leer `AGENTS.md`, `README.md`, `frontend/playwright.config.ts` y la spec de la pantalla objetivo.
2. Confirmar cómo se está sirviendo la aplicación. En producción el frontend es exportación Next.js servida por FastAPI, habitualmente en `http://127.0.0.1:8000`; para maquetación puede usarse temporalmente `npm --prefix frontend run dev`, pero no sustituye la verificación del despliegue real.
3. Utilizar el MCP de Playwright **ya configurado** cuando esté disponible. No reinstalar otro navegador/MCP ni afirmar haberlo usado sin haber abierto la aplicación.
4. No crear credenciales ficticias para obtener acceso. Los recorridos autenticados exigen fixtures/configuración de prueba válidos; si faltan, validar la parte pública e informar el bloqueo.

## Inspección y pruebas con navegador

1. Abrir la ruta objeto del cambio, registrar viewport, sesión/rol, origen y datos disponibles. Revisar consola y errores de red relevantes.
2. Capturar y examinar el estado inicial en escritorio (1440 px), tablet (768 px) y móvil (390 px); incluir alturas apropiadas al contenido.
3. Recorrer con Playwright MCP las interacciones reales del componente: menú, filtros, formularios, acciones y enlaces. Comprobar teclado, foco, nombres accesibles y mensajes de validación.
4. Buscar overflow inesperado, texto cortado, contraste insuficiente, controles demasiado pequeños, saltos de layout y pérdida de contexto en tablas/gráficos.
5. Examinar estados que el entorno permita reproducir legítimamente: carga, vacío, error, cobertura parcial, sesión caducada y acceso denegado. No manipular datos de producción ni sustituir respuestas reales silenciosamente.
6. Al cambiar código, repetir el recorrido y comparar el antes/después cuando se disponga de evidencia. No crear archivos de screenshots en el repositorio salvo que el usuario lo pida.
7. Usar Context7 para verificar documentación vigente cuando se necesite una API de Playwright, React o Next.js sensible a versión.

## Comprobaciones del proyecto

Desde la raíz:

```sh
npm --prefix frontend run typecheck
npm --prefix frontend test
npm --prefix frontend run build
```

Cuando el entorno local, las credenciales sintéticas y el backend estén preparados:

```sh
npm --prefix frontend run test:e2e
```

El `playwright.config.ts` actual limita los escenarios según los archivos de credenciales de fixture presentes. No interpretar «solo corre platform.spec.ts» como cobertura autenticada completa.

## Informe

Entregar una tabla breve con problema, severidad, ruta/componente y evidencia/reproducción. Distinguir claramente: validado con navegador, validado solo con pruebas automatizadas, e inspeccionado en código. No declarar corregido o probado lo que no se pudo ejecutar.
