# Historial, decisiones y conservación008 —2026-11-25

Implementados los filtros de período/estado/regla/cuenta y cursor firmado. Operador
solo consulta su cuenta y todo contenido todavía autorizado; filtros administrativos
se rechazan y objetos ajenos no revelan metadatos. La degradación a Operador impide
también consultar contenido administrativo histórico que antes estaba autorizado.

El reenvío exige Administrador, motivo1..500, reconocimiento explícito, regla/activación
vigentes, destinatario elegible y entrega fallida/indeterminada. Crea decisión auditada,
nueva generación/Message-ID y vínculo; no cambia el estado ni intentos originales.
Misma clave/cuerpo conserva la decisión; otra petición incompatible devuelve409.
Resolver un replay autorizado precede a condiciones de una decisión nueva.

Pruebas observadas:12 casos de reenvío/recuperación/conservación y14 de coordinación
con identidad/reenvío; otros6 verifican aislamiento y permisos. Backend real y Mailpit
confirman que perder el registro después de DATA aceptado deja indeterminado tras
recuperación y no dispara SMTP automáticamente. La memoria transitoria de resultados
está acotada por plazas; si el proceso conserva la confirmación, repite solo su registro
en DB. Tras perder esa evidencia se exige la decisión manual.

El helper009 resuelve12 meses calendario; los casos independientes verifican29 de
febrero, hueco y segunda hora repetida. Intentos/decisiones extienden padres, evidencia
y referencias protegidas al máximo; consultas y replay no renuevan. No hay purga
automática ni dependencia de la retención técnica. Una cuenta desactivada conserva UUID.

Playwright real conserva indeterminación, abre el diálogo accesible con motivo/aviso,
crea entrega vinculada y verifica que el Operador ajeno no consulta ni reenvía. Dos
escenarios urgencia/historial se ejecutan en orden explícito en el arnés privado;
la última ejecución observada aprobó en7,32s. El test usa una aceptación real Mailpit
y pérdida privada del registro, sin endpoint público para provocar fallos.

Recepción, cálculo100000CLP sobre entradas reales y PDF descargable conservaron sus
resultados con SMTP loopback rechazado y fallos/saturación del emisor007 real. La cola
técnica permanece acotada; el fallo de correo solo queda en su entrega, sin recursión.
Esto no sustituye pruebas de relay/VPS o la evaluación con personas.
