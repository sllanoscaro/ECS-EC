# Urgencias008 — validación local,2026-11-25

El evaluador usa ventanas completas de001/002 y compara Decimal exacto. No estima un
total parcial ni interpreta ausencia como cero. Evidencia, cursor válido, episodio,
ocurrencia, mensaje y entregas se confirman juntos. Solo normalidad válida rearma;
datos insuficientes o pérdida de fuente conservan el episodio. Pausa lo finaliza
por regla, sin afirmar normalización.

Resultados observados:16 casos puros de comparaciones/resoluciones; integración real
de consumo persistente/normalizado, silencio por reloj, categoría sin fuente,
duplicados/rechazos que no renuevan silencio, lote histórico y total calculado20kWh
desde12+8 deCAT05/CAT03. Ocho consumidores concurrentes producen una sola apertura,
ocurrencia y entrega. Una contribución faltante no cierra un episodio. Otro caso
verifica el agregado completo20 de tramos medidos y calculados, con alcance explícito.

Costos004 y PDF005 ejecutan sus productores reales y persisten fallo/evento atómicos;
008 consume `cost.failed`/`pdf.failed` sin reemplazar cálculos ni generación. La
inyección privada falla únicamente una frontera interna del productor para observar
su tratamiento real. Dos fallos PDF con igual fecha y UUID descendente se consumen
ambos: el acuse por identidad de evento evita confundir orden de fecha con orden de
commit. Reintentos/lecturas no crean otro episodio del mismo suceso.

Playwright ejecuta UI real con identidad006, fuentes y total calculado002. Muestra
20kWh, umbral15, baseCAT03/CAT05, alcance, período y detección. También verifica los
campos de silencio y sucesos. Su reloj controlado se inyecta solo en el arnés privado;
no existe endpoint de generación de datos, cambio de hora o fallo.

El perfil mixto se ejecuta además con SystemClock y Mailpit reales: diez destinatarios,
dos reglas periódicas y dos de consumo coincidentes,40 entregas iniciales y cuatro
plazas. En el supervisor real con ciclos5s:40/40 aceptadas; máximo inicio3,718829s,
máxima duración0,059385s en el perfil registrado durante la última regresión. Un ensayo separado
con ambas colas materializadas verifica la cuota3urgentes:1periódico;40/40 aceptadas.
No usa esos tiempos del ensayo de equidad como sustituto del supervisor.

El test `test_urgent_latency.py` conserva referencias y tiempos de las40 entregas,
CPU/RSS, versiones y tzdata en los artefactos saneados del
[supervisor](artifacts/mixed40-supervised.json) y de
[equidad](artifacts/mixed40-fairness.json). El [informe de aceptación](acceptance.md)
registra la última regresión completa. Los datos eléctricos son sintéticos y entran
por el normalizador/recepción reales; la medición de despacho utiliza reloj real.
La prueba no promete otros volúmenes ni entrega a buzón externo.
