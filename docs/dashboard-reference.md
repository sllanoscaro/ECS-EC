# Referencia propuesta: navegación y dashboard

Estado: quinta iteración visual aprobada por el usuario para integración. Implementada localmente en `/`, con alcance y evidencia en [ui-implementation.md](ui-implementation.md). Esto no declara aceptación integral de las specs ni despliegue real.

Actualización de identidad: el usuario valoró la primera composición como una buena aproximación y solicitó integrar los logos de Electro Conforma y conservar sus colores en todos los diseños posteriores. La [versión 2](../.impeccable/mocks/dashboard-navigation-v2.png) incorpora el logo principal y la paleta extraída de los SVG. La identidad queda registrada en [DESIGN.md](../DESIGN.md); la composición revisada sigue pendiente de revisión.

## Requisitos indicados por el usuario

- Panel de navegación desplegable a la izquierda, con los apartados de la aplicación.
- Dashboard general como primera vista al entrar en la plataforma.
- Gráfico de consumo energético en kWh frente al tiempo, en intervalos de 15 minutos.
- Desglose por categorías a la derecha del gráfico principal en escritorio.
- Vista diaria que se actualiza a medida que llegan lecturas; sin selector de fecha en el dashboard. La consulta histórica se mantiene en Consumo.
- Dos indicadores: «Energía total medida» con «Consumo acumulado de hoy.» y «Cobertura del período» con «Tiempo transcurrido con datos válidos.». Retirar «Intervalos disponibles».
- Retirar el enlace «Ver detalle de consumo», el selector «15 min» y las leyendas repetidas de fecha e intervalo dentro del gráfico. La fecha del día permanece en el encabezado de página; el intervalo de lectura sigue siendo parte del comportamiento previsto.
- Al pie del gráfico, «Hora de la próxima actualización: HH:MM». El ejemplo muestra 14:45; es una hora ilustrativa, no una garantía de llegada de lecturas.
- Reloj y zona horaria en el pie con texto gris uniforme y peso normal, sin icono de reloj ni cifras en negrita.

## Artefactos

Referencia vigente: [versión 5](../.impeccable/mocks/dashboard-navigation-v5.png) y [prompt de edición](../.impeccable/mocks/dashboard-navigation-v5.json), generada con `image_gen` sobre la versión 4. Conserva sus dos indicadores, próximas actualizaciones y pie temporal; cambia la sección activa a fondo `#4F9A17` con icono/texto blancos y aplica la paleta estable de categorías de [DESIGN.md](../DESIGN.md). El total del gráfico es verde profundo y coincide con CAT-01 en Consumo. El reloj sigue siendo ilustrativo.

La [versión 4](../.impeccable/mocks/dashboard-navigation-v4.png) y su [prompt](../.impeccable/mocks/dashboard-navigation-v4.json) se conservan como antecedentes.

La [versión 3](../.impeccable/mocks/dashboard-navigation-v3.png) y su [prompt](../.impeccable/mocks/dashboard-navigation-v3.json) se conservan como antecedentes.

- [Imagen de referencia](../.impeccable/mocks/dashboard-navigation-v1.png).
- [Prompt exacto y procedencia](../.impeccable/mocks/dashboard-navigation-v1.json). Generada con la herramienta integrada `image_gen`.
- [Referencia actual con identidad Electro Conforma](../.impeccable/mocks/dashboard-navigation-v2.png) y [prompt de edición](../.impeccable/mocks/dashboard-navigation-v2.json), generados con `image_gen` usando la maqueta anterior y los logos originales como referencias.

La propuesta muestra el menú expandido y el control para plegarlo. Separa monitoreo y administración; representa la vista del Administrador técnico. En la implementación, los apartados visibles deberán respetar los permisos existentes. Reportes aparece como capacidad próxima, sin prometer generación disponible.

El gráfico usa barras por intervalo, escala en kWh y zona horaria explícita. Los valores son ilustrativos y no representan mediciones, tarifas ni un estado real del sistema. La implementación deberá derivar valores y cobertura de sus fuentes reales, preservar vacíos y distinguir total medido de total calculado según las reglas de consumo. No se deduce de la maqueta que el total físico siempre coincida con la suma de categorías.

## Pendiente para la implementación

Confirmar la propuesta visual con el usuario y definir los estados del panel plegado y de móvil, así como carga, error, datos incompletos y ausencia de medidor. Verificar la disponibilidad de consultas reales para intervalos de 15 minutos y para el desglose del mismo período, respetando la propiedad de consumo001/002 e identidad006. La imagen no cambia contratos ni agrega por sí misma una agrupación nueva a la API.

Definir el mecanismo real de actualización automática y su programación antes de implementar el horario mostrado. La próxima actualización de la vista y la llegada de una nueva lectura son sucesos distintos: no prometer mediciones a una hora fija a partir del intervalo de quince minutos. Si el horario no se conoce, el estado real debe decirlo. La marca de última lectura, el reloj y el próximo intento deben provenir de sus respectivas fuentes, sin deducir uno del otro.

La maqueta corta las barras en la última lectura ilustrativa, 14:30, y deja vacío el resto del día; no proyecta valores futuros. La fórmula de cobertura debe especificar el tramo evaluado del día transcurrido y el tratamiento de latencia, sin incluir como faltantes los intervalos futuros ni ocultar huecos anteriores. Valores, porcentajes y geometría de la imagen son ilustrativos: en código deberán derivarse del mismo conjunto real de datos.

Esta entrega es una referencia de composición para la navegación compartida y la futura portada; no modifica las vistas existentes ni sustituye los artefactos de Spec Kit.
