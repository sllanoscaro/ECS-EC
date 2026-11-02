# Oráculos locales de anomalías

`examples/anomalies-100.json`: CAT-03 tiene100 intervalos originales y una referencia
acumulada adicional. Floor(100×10/100)=10 por cada clase; posiciones deliberadas
exclusivas:30; normales:70. Las otras seis categorías tienen100 normales cada una.
La banda es0..10kWh/15min, quantum0.001kWh. Superior10.001, inferior−0.001.
La referencia inicial100kWh no se altera. Vecinos sin un extremo observable se
informan como consecuencias, sin aumentar esos30 defectos.

Las pruebas cubren0/100%, tipo/fecha, incremento superior/inferior y selección
explícita; `test_structural_anomalies.py` verifica corrupción por archivo separada.
Las asignaciones/hashes se conservan en el control de cada ejecución reproducible.
Esto no acredita recepción ni rechazo real. Un positivo superior a10 puede ser
aceptado legítimamente por001 si la instalación no define esa banda física.
