# ECS-EC — Contexto de producto

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Operador**: persona encargada de monitorear el edificio. Consulta consumo, historial, costos y boletas; puede generar y descargar los reportes PDF definidos en su especificación. No modifica datos de negocio ni configuraciones.
- **Administrador técnico**: dispone de las consultas del Operador y administra cuentas y configuraciones del sistema, con trazabilidad de sus acciones.
- **Programador**: accede a herramientas técnicas externas de observabilidad. Ese acceso no concede permisos funcionales dentro de ECS-EC.

El producto contempla un edificio y dos perfiles funcionales fijos. La [spec de acceso](specs/006-acceso-usuarios-rbac/spec.md) define la matriz de permisos.

## Product Purpose

Monitorear y visualizar el consumo eléctrico de un edificio para reconocer su evolución, revisar valores exactos y comprender costos y calidad de los datos disponibles.

El éxito se evalúa mediante las historias y criterios de aceptación de cada funcionalidad: consultas comprensibles, representaciones coherentes con los datos de origen y diferencias explícitas entre mediciones, cálculos, vacíos y errores. El monitoreo no implica una garantía de tiempo real.

## Positioning

El alcance específico combina siete categorías de consumo del edificio, trazabilidad de mediciones e historial, análisis del suministro general bajo tarifa BT4.3 y contraste con boletas. No se ha establecido una afirmación de exclusividad comercial.

## Operating Context

- Interfaz web en español. Desarrollo y verificaciones actuales locales; el destino previsto es una VPS con acceso autorizado por internet desde redes externas al edificio. Esto no acredita despliegue ni aceptación externos.
- Flujo de consulta: elegir categoría y período, revisar gráficos y tablas consistentes, interpretar cobertura y procedencia; consultar agrupaciones horarias, diarias, mensuales y anuales según la funcionalidad.
- Portada solicitada: dashboard del día que incorpora las lecturas a medida que llegan, con navegación lateral plegable, evolución de consumo y desglose por categoría. La consulta se actualiza una vez por cuarto de hora, cinco segundos después del cierre, y admite actualización manual, sin prometer adquisición en tiempo real; el resumen diario se lee desde consumo001/002. La consulta histórica permanece en la sección Consumo.
- Flujo de costos: revisar el desglose BT4.3, contrastarlo con boletas y consultar resultados históricos reproducibles. El Administrador técnico mantiene condiciones y vigencias.
- PDF y notificaciones programables forman parte del alcance especificado. Su disponibilidad debe comprobarse en la implementación y evidencia de sus respectivas funcionalidades.
- Recepción de archivos PAS600/SFTP y simulador externo de pruebas según la [spec de adquisición](specs/003-simulador-pas600-sftp/spec.md).

## Capabilities and Constraints

- Catálogo: energía total; HVAC y agua caliente sanitaria; iluminación exterior; iluminación interior; enchufes; sistema sanitario; ascensores. Una instalación puede tener solo algunas categorías medidas.
- El total puede ser medido o calculado desde las categorías presentes. Deben identificarse procedencia y base. Si existe medidor total, una lectura ausente no se sustituye por la suma de parciales; si falta un contribuyente requerido, no se presenta un total calculado completo.
- Los costos BT4.3 requieren un medidor total asociado al suministro general; no utilizan el total calculado de categorías.
- Toda vista de consumo identifica magnitud, unidad, período y zona horaria. Cero, ausencia, datos incompletos, carga y fallo son estados distinguibles. Los gráficos y tablas del mismo conjunto y filtros conservan valores coherentes.
- Conservación funcional de al menos doce meses calendario según las reglas de cada dominio; no sustituir meses por un número fijo de días.
- Monolito modular: FastAPI y exportación estática de Next.js/React/TypeScript, servidos por una única aplicación; PostgreSQL para persistencia. No requiere un servidor Node en producción. Los datos privados se consultan mediante API autenticada y permisos comprobados en servidor.
- La [constitución](.specify/memory/constitution.md) gobierna el alcance, integridad, documentación y verificación. La [arquitectura](docs/architecture.md) y la [hoja de ruta](docs/implementation-roadmap.md) gobiernan límites, propietarios y dependencias. Cada `spec.md`, `plan.md`, `tasks.md` y contrato conserva su autoridad en `specs/`; este documento no los reemplaza ni declara tareas completadas.

## Brand Commitments

Nombre existente: **ECS-EC**. Mantener la terminología funcional documentada y el idioma español de la interfaz.

Identidad de presentación confirmada por el usuario: **Electro Conforma**, con los logos originales en [Identidad Visual Electro Conforma](<docs/Identidad Visual Electro Conforma/>). Integrar sus versiones existentes y conservar sus colores en todos los diseños futuros. Los SVG definen verde profundo `#0D4A37`, verde `#4F9A17`, lima `#A6E04B`, blanco `#FFFFFF` y negro `#111111`. ECS-EC sigue siendo el identificador del sistema; la identidad de presentación no implica un cambio de alcance o nombre técnico. [DESIGN.md](DESIGN.md) registra los criterios de aplicación.

El usuario solicita una asociación estable entre categoría energética y color en todos los gráficos, y sección activa del panel lateral con fondo `#4F9A17`, texto e icono blancos en todas las vistas. Los colores adicionales para categorías tienen una función de identificación de datos y no reemplazan la paleta de marca. La correspondencia propuesta está en [DESIGN.md](DESIGN.md).

El usuario confirmó que las interfaces implementadas no cumplen con lo esperado. Su presencia acredita comportamiento y contenido existentes, pero no constituye aprobación de su solución de interfaz. La dirección visual futura sigue pendiente de definición con el usuario.

## Evidence on Hand

- [Especificaciones e historias de usuario](specs/): fuente principal de necesidades, reglas y criterios de aceptación, confirmada por el usuario.
- [Arquitectura](docs/architecture.md), [hoja de ruta](docs/implementation-roadmap.md) y [README](README.md): contexto compartido, estado por capacidad y ejecución local. Consultar la evidencia de validación de cada funcionalidad para distinguir implementación local de aceptación integral.
- [Frontend existente](frontend/src/) y [backend](backend/src/ecs_ec/): evidencia de implementación; las rutas y componentes existentes no demuestran aceptación de todas las capacidades.
- Datos sintéticos y ejemplos locales sirven para pruebas, no como mediciones reales, tarifas vigentes de la instalación ni prueba de despliegue.

## Product Principles

1. Mantener el monitoreo del edificio como propósito de cada funcionalidad.
2. Preservar origen, unidad, referencia temporal y reglas de cálculo de los datos.
3. Facilitar la comprensión de valores y limitaciones sin presentar ausencias como consumo cero.
4. Respetar permisos y separación entre consulta, administración y operación técnica.
5. Evaluar el trabajo contra historias y evidencia verificable; incorporar la retroalimentación del usuario durante el desarrollo.

## Open Decisions

Las necesidades se extraen primero de la documentación y las historias de usuario. El usuario aportará retroalimentación durante el trabajo. Dispositivos habituales, experiencia previa de los operadores y requisitos específicos de accesibilidad se precisarán cuando la documentación o esa retroalimentación los establezcan; no se fija aquí un estándar no confirmado.
