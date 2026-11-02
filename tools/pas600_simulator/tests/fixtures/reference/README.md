# Referencias independientes — preparación incompleta (T003)

`expected.json` es un oráculo aritmético escrito manualmente: 104−100=4 kWh.
No fue producido por un serializador; no es una muestra de hardware ni una
transcripción del caso documental de tensión/IO.

La tarea exige DOCA0172EN-19 pp.126–127 y 274–276. El enlace original del
[perfil](../../../../../../specs/003-simulador-pas600-sftp/contracts/pas600-profile.md)
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
