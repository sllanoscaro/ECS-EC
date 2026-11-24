# Referencias independientes — preparación incompleta (T003)

`expected.json` es un oráculo aritmético escrito manualmente: 104−100=4 kWh.
No fue producido por un serializador; no es una muestra de hardware ni una
transcripción del caso documental de tensión/IO.

La tarea exige DOCA0172EN-19 pp.126–127 y 274–276. El enlace original del
[perfil](../../../../../specs/003-simulador-pas600-sftp/contracts/pas600-profile.md)
devolvió HTTP404 el 2026-11-02. El intento de descarga histórica desde
`download.schneider-electric.com` con ese nombre de archivo también devolvió404.
La copia alternativa en
<https://www.tekdok.dk/flipbooks/DOCA0172EN/content/DOCA0172EN.pdf>
se descargó correctamente (SHA-256
`707755c132e86b60b4b95c78461a19ecb9ee46777e122ac8d694bea8badc079f`),
pero sus páginas llevan DOCA0172EN-20; no se usa
para acreditar conformidad con la revisión19. Los resultados indexados del buscador
que indicaban19 no coinciden con el archivo servido actualmente.

Pendientes: obtener revisión19 verificable, registrar SHA-256 y procedencia,
revisar visualmente filas CSV y convenciones JSON, preparar fixtures documentales
independientes y confirmar las tres celdas iniciales de presentación.
Los identificadores físicos requieren descriptor/topología propios; el documento
no prueba que el firmware físico cumpla la frontera de sesión SFTP del contrato003.

El2026-11-02 el usuario autorizó saltar temporalmente esta revisión y continuar con
los contratos locales. T003 permanece pendiente; no se declara conformidad documental.

## Revisión del bloqueo — 2026-11-23

Se hizo una búsqueda acotada de la revisión19 y se volvió a consultar el enlace
oficial fijado: devuelve404. La descarga oficial con nombre explícito19 no fue
accesible mediante la herramienta de consulta. La búsqueda también devuelve la
[guía oficial genérica DOCA0172EN](https://download.se.com/files?p_Doc_Ref=DOCA0172EN&p_enDocType=User+guide),
indexada como revisión22; su descarga excedió el límite de lectura de la herramienta.
No se obtuvo ni se inspeccionó una nueva copia19, ni se calculó un nuevo checksum.
Los resultados indexados no acreditan la revisión del archivo servido. No se repitió
la descarga de la copia20 cuyo hash histórico se registra arriba.

La revisión exigida ya está definida; no es una ambigüedad que necesite resolver
`speckit-clarify` ahora. Conviene aclarar el alcance del bloqueo y mantener diferido
el cotejo independiente, conforme a la decisión previa: el desarrollo y las
integraciones sintéticas con003 pueden continuar, pero T003/T008/T009/T021 y su
aceptación asociada siguen pendientes.

Retomar al obtener una copia19 verificable y antes de cerrar la conformidad documental
o003:T076. Registrar procedencia/SHA-256, revisar visualmente pp.126–127 y274–276,
preparar fixtures independientes y ejecutar los contratos sin generar el oráculo con
el writer. Antes de conectar hardware real, verificar además descriptor/topología,
firmware y frontera de sesión. Si se propone otra revisión documental, acordar y
documentar primero el cambio del perfil, contratos, ejemplos y pruebas; esta revisión
no autoriza sustituir19 ni acredita conformidad física.
