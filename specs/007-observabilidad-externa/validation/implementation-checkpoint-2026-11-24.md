# Punto de continuación007 — paso4,2026-11-24

Trabajo técnico completado hastaT058;58/65 tareas. [Resultados y pruebas](step4.md).
**No reiniciar todo el plan ni marcarT059–T065 como completadas.** El siguiente paso
es revisar el ensayo real existente, no crear otra cohorte para sustituir su espera.

## Ensayo que sigue en ejecución

- Proyecto exclusivo ecs007-step4-quotas; listener https://localhost:3446, solo loopback.
- Raíz privada: `/home/sebastianll/.local/state/ecs-step4-quota-stack/test`.
- Estado: retention-probe.json; PID del monitor en probe-monitor.pid; salida privada
  probe-monitor.log. El PID no es contrato estable: comprobar cmdline antes de controlarlo.
- Emisor técnico privado: ecs007-step4-quotas-worker. Usa el Telemetry real, heartbeat/
  TTL/snapshot, sin HTTP de negocio/DB. Mantenerlo junto con Alloy/Loki/Jaeger/Grafana/gateway.
- Cohorte emitida:2026-11-24T21:39:33Z aproximadamente;10terminales/10trazas/10operaciones
  consultables antes y después de reiniciar **solo** Loki/Jaeger del ensayo.
- Inicio del ensayo:2026-11-24T21:39:30.471862Z (18:39Santiago).
- PreTTL previsto:2026-11-25T21:29:33.159891Z (18:29Santiago).
- Expiración a comprobar:2026-11-25T21:39:45.188773Z (18:39Santiago).
- Fin del presupuesto de comprobación:2026-11-25T22:39:33.159891Z (19:39Santiago).
- Spool original tiene plazo propio anterior: primer evento2026-11-24T17:34:49.233520Z,
  verificación hasta2026-11-25T18:34:49.233520Z. El monitor observa su retirada sin
  confundir el mismo nombre reutilizado para un segmento nuevo con conservar el viejo.

[Instantánea saneada inicial](artifacts/step4-retention-start.json), sin contraseña.
El estado privado conserva más metadatos físicos. La contraseña/CA privadas siguen
fuera del repositorio y sus contenidos no deben copiarse a documentación/stdout.

```sh
uv run python scripts/observability/retention_probe.py status \
  --root /home/sebastianll/.local/state/ecs-step4-quota-stack/test
# Si el proceso terminó/interrumpió, verificar fase y reanudar con la misma raíz:
uv run python scripts/observability/retention_probe.py run \
  --root /home/sebastianll/.local/state/ecs-step4-quota-stack/test
```

El monitor se reanudó al concretar detección de nombres de spool reutilizados,
conservando UTC/boottime/cohorte/baseline/plazos originales. No se reinició la espera.
Si el host reinicia, la prueba automática de tiempo transcurrido queda invalidada;
no falsificar BOOTTIME ni avanzar reloj. No ejecutar de nuevo pruebas de cuotas,
fallos de servicio, borrado de posiciones ni preparar/desmontar esta raíz durante el ensayo.

## Qué revisar al vencer

Estado esperado tras confirmar expiración consultable:
expired_query_confirmed_physical_review_pending. Exigir preTTL con10/10/10 y después
cero logs/vector ausente/trazas404; errores de consulta no son ausencia. Verificar
segmentos spool originales retirados dentro de su plazo, archivos Loki y Badger,
GC físico/compactación y máximo60min. Los archivos de datos Badger originales pueden
persistir aunque venza la consulta: investigar y corregir mecanismo si ocurre;
no modificar aserciones para convertir404 en borrado físico.

Seleccionar los dos casos real_time007 con OBS_RETENTION_PROBE_ROOT y revisar su
alcance. Uno comprueba consulta y otro exige retirada de archivos físicos originales;
no sustituyen revisión de GC si la evidencia es insuficiente. Solo entonces decidir
si007:T059 tiene evidencia para cerrarse y continuarT060. [Detalle](retention.md).

## Recursos retenidos y limpieza

Cinco imágenes ext4/mounts exclusivos de quota-images/ y sus destinos spool,
data/alloy, data/loki, data/jaeger y data/grafana: techos128MiB,64MiB,2GiB,2GiB,256MiB.
Las reservas/metadatos reducen espacio utilizable; el host conserva asignación física
del ensayo. No desmontar ahora. El pequeño mount piloto previo se retiró tras verificar
su backing, sin tocar estos cinco. No se configuró fstab ni confianza global de CA.

Al terminar revisión: detener exclusivamente worker/proyecto del ensayo, conservar
estado/evidencia y ejecutar prepare_quotas.py unmount con raíz/imagen/--allow-host-mounts.
El helper verifica manifiesto/propietario/mountpoint/backing y conserva imágenes, sin
force/lazy ni volúmenes funcionales. Nunca docker prune/down -v global.
Los proyectos de regresión/DB exclusivos pueden retirarse tras las verificaciones
finales; el cierre de recursos ejecutado se registra al final de este checkpoint.

Contenedores preexistentes ecs-ec-app-1, ecs-ec-simulator-1 y ecs-ec-db-1 permanecen
intactos. No hubo commit, merge o despliegue del servicio funcional del usuario.
Selección persistida Spec Kit003 intacta; checklist00716/16 sin modificaciones y
extensions.yml ausente. [Orden vigente](../../../docs/implementation-priority-plan-2026-11-03.md).

## Cierre de recursos de esta ejecución

Retirados mediante Compose down únicamente ecs007-step4 y ecs007-step4-other,
incluidas sus redes; sus directorios técnicos privados quedan preservados. Detenida
la DB exclusiva ecs-step4-db, conservando datos. Las capturas/JUnit saneados están
versionables en validation/artifacts/. Permanecen ejecutándose solo el stack del
ensayo ecs007-step4-quotas y su worker, además de los tres contenedores preexistentes
del usuario sin cambios. Monitor activo y snapshot de cuotas permitido/fresco
comprobados después de limpiar; no se deshabilitó verificación TLS ni se instaló CA
en la confianza global del usuario. No cerrar/desmontar ese ensayo hasta revisarT059.
