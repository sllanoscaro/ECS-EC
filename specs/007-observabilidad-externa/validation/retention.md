# Persistencia, muestreo y retención real — paso4

Corte2026-11-24. **007:T059 permanece pendiente.** No se acredita vencimiento24h/GC
con reloj de pruebas, TTL configurado, consulta404 ni reinicio solamente.
[Estado reanudable y recursos](implementation-checkpoint-2026-11-24.md).

Verificado: configuración normal168h y test24h coincidente en emisor/Loki/Badger;
solo ratios1.0/0.1,0.1 exige revisión distinta de007-v1. Caso real con100 raíces
con IDs conocidos: SDK0.1 exportó diez raíces+diez hijos,100 terminales de log
consultables, revisión visible y una traza no muestreada404. Los IDs de fixture son
privados de prueba y no cambian generador/sampler de producción. Aceptación usa1.0.

Spool: regresión muestra que añadir eventos/reiniciar no extiende el timestamp del
segmento viejo. TTL usa el primer evento original; eliminar el segmento completo
puede perder jóvenes y cuenta esa pérdida conservadora. Prueba unitaria demuestra
la regla, todavía no el transcurso24h. Loki/Jaeger persisten señales entre reinicios
con consulta humana real; la fase inicial del ensayo vuelve a medir10logs/10trazas/
10operaciones antes/después de reinicio con flush Loki explícito del operador.

`scripts/observability/retention_probe.py` emite una fixture técnica, nunca sustituye
consultas funcionales. Guarda UTC real, CLOCK_BOOTTIME y bootID del host, límites,
referencias, lecturas y asignación física por archivo en raíz privada. `run` puede
reanudar espera; reinicio del host invalida la prueba automática de tiempo transcurrido.
Comprueba preTTL, ausencia de logs/métrica/trazas dentro de60min tras TTL y retirada de
segmentos spool originales por su propio plazo. Errores de consulta no equivalen a cero.
No modifica tareas/checklists. Al confirmar expiración consultable deja
`expired_query_confirmed_physical_review_pending`: Badger/GC necesita revisión adicional.

Loki tiene compactor10min y demora10min; Badger mantenimiento10min con persistencia/
consistencia. La implementación fijada de Jaeger usa TTL para accesibilidad y GC del
value log; inferir liberación física solo del404 sería incorrecto. Revisar almacenamiento,
archivos/compacción y presupuesto temporal por separado antes de cerrarT059.
Fuentes primarias: [configuración2.22](https://github.com/jaegertracing/jaeger/blob/v2.22.0/internal/storage/v1/badger/config.go),
[fábrica y mantenimiento](https://github.com/jaegertracing/jaeger/blob/v2.22.0/internal/storage/v1/badger/factory.go).

Después del ensayo, seleccionar explícitamente `-m real_time` con
`OBS_RETENTION_PROBE_ROOT` para `test_real_retention_probe_query_expiry_evidence`;
esa prueba valida solo expiración consultable, no GC. Revisar evidencia física y
retención funcional por sus propios contratos. T060 y cadena final esperanT059.
