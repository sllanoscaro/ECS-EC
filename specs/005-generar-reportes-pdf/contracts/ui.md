# Contrato de interfaz: Reportes PDF

Página estática `/reportes/`, accesible a Operador/Administrador técnico autorizados. La API protege cada operación; el HTML exportado no contiene datos privados ni ofrece administración técnica.

## Selección y progreso

Selector diario/mensual/anual y campos aplicables: fecha; mes/año; año. Mostrar zona del edificio, período y carácter provisional si está en curso. No controles de formato, tamaños de letra ni secciones omitibles.

Crear conserva selección durante espera, error y reintento. Estados distinguibles: selección incompleta, pendiente/generando, generado con descarga, fallo funcional y sesión vencida. Errores por campo son comprensibles y accesibles mediante etiquetas, foco y teclado. No convertir una respuesta fallida en lista vacía ni volver a generar al repetir una descarga.

`?reporte=<uuid>` selecciona un resultado mediante consulta autenticada, compatible con exportación estática. Ante sesión vencida, ingreso normal con retorno a ruta local segura. Enlaces funcionales no conceden acceso público a PDF.

## Documento de una página

- A4 vertical al 100 %, márgenes de 10 mm y texto >=10 pt, incluida cada nota/eje/leyenda.
- Identificación: ECS-EC, edificio, escala, intervalo/zona, emisión, corte, referencia y provisionalidad.
- Tabla con las siete categorías y nombres inequívocos; energía kWh, cobertura y estado; origen medido/calculado/mixto y base/alcance de los segmentos calculados de CAT-01; sin fuente distinguida de sin datos y cero válido. Cuando cambien modo, fuente o base, identificar «Origen mixto» si corresponde y sintetizar períodos, fuentes y bases sin ocultar cambios relevantes ni recalcular el total del productor.
- Evolución CAT-01 por horas/días/meses según escala. Todos los bloques permanecen, etiquetas se espacian para lectura; no interpolar vacíos, señalar detalle no disponible y desambiguar horas repetidas por desfase.
- Costos por cierre de ciclo con cantidad, alcance temporal de consumos y subtotal disponible/completitud, sin igualarlo al período de energía. Agrupar solo moneda/base compatibles.
- Contraste con los mismos pares y conceptos en ambos lados, cantidad de pares y diferencia calculado menos facturado; si no hay pares, indicar motivo.
- Cuando exista cálculo y boleta pero falte comparación de sus revisiones seleccionadas, mostrar «Contraste pendiente para estas revisiones». Ese ciclo no integra los importes ni el conteo del contraste agregado; sus importes disponibles conservan su alcance separado. Las diferencias pendientes no se presentan como cero.
- Calidad/procedencia: todas las limitaciones esenciales y origen simulado identificado. No enlaces indispensables para interpretar el documento sin conexión ni informe privado del simulador.

Las bandas tienen presupuesto y reflujo medido. Se permiten nombres cortos inequívocos acompañados de código canónico y agrupación de advertencias del mismo significado con su alcance; no perder nombres/categorías ni ocultar limitaciones para lograr el límite. Si no cabe, indicar fallo y conservar opciones en vez de ofrecer un documento inválido.

## Verificación de uso

SC-006: diez tareas con personas representativas, al menos nueve eligen período, descargan e identifican total/cobertura/situación de costos sin ayuda en <=2 minutos. Una suite E2E no sustituye esta evidencia. Abrir/interpretar el PDF descargado sin red forma parte de los casos de referencia.
