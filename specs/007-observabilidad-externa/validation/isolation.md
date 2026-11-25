# Privacidad, fallos y cuotas — paso4

Corte2026-11-24. Solo marcadores sintéticos y recursos exclusivos; ningún servicio
técnico monta DB, mediciones, boletas o PDF. [Regresión](step4.md).

`test_privacy.py` coloca marcadores en credenciales006/cookie de sesión, cabeceras
públicas, consulta con controles, energía001, boleta/importes004, nombre que efectivamente
aparece en el PDF005, archivo/contenido nativo003 y excepción cruda del motor004.
Cero coincidencias en cola, spans pendientes, spool, Loki y cada traza recuperada de
Jaeger. Las pruebas de sanitización rechazan también campos libres email/IP/SQL/URL
antes de cualquier cola, sin convertir objetos a texto. Docker logging=none para
las cinco herramientas/gateway evita persistir stdout genérico sin saneamiento.

`test_observability_isolation.py` consume casos reales de001/002/005/006 y añade004:
fallo de admisión, saturación y spool roto mantienen cálculo inmutable100000CLP,
lectura idéntica, PDF y permisos/commits. Logs<=1024, pendientesOTel<=2048,
shutdown/deadline5s y pérdidas comprobadas en suites fundamentales. Transporte y
consulta fallan por separado en `test_collection_continuity.py`; recuperación no
convierte un hueco en historia completa. Revocación/puertos siguen [acceso](access.md).

Cuotas físicas: cinco ext4 distintos sobre imágenes loop de128MiB/64MiB/2GiB/2GiB/
256MiB; metadatos reducen capacidad útil y10% reservado forma parte del presupuesto
no disponible. En cada uno se asignaron extents reales hasta>=92%; estado15s observado
sin fabricar snapshot, mTLS rechazó507 y la consulta Programador siguió autorizada.
Cálculo004 confirmó el mismo total en los cinco casos; con spool lleno, PDF005 se
publicó/descargó y pérdida de spool creció. Retirado solo el filler propio, estado
recuperó admisión y mTLS respondió200. Cinco casos reales pasan; no se usa un simple
mock de disco para acreditar el corte90%.

El proceso regular ve solo mounts vacíos de capacidad; la comprobación periódica no
bloquea request/commit. Snapshot ausente/inválido/edad>30s deniega ingesta. Configuración
inválida deshabilita solo emisor. Ningún ensayo retira archivos funcionales ni reduce
retención protegida002/009. RAM posterior a carga y overhead ext4 medidos separadamente en
[artefacto de capacidad](artifacts/step4-capacity.json). No es pico de RAM ni dimensionamiento
con carga operacional representativa; no se introduce un SLO de negocio.
