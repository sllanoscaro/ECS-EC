# Validación local de evidencia funcional

Ejecutada el 2026-11-02 con productores sintéticos y PostgreSQL 18.3 real, sin consumidores
ni módulos de negocio. Migración `platform_009_initial` aplicada en `ecs_test` independiente.

```sh
uv run --locked pytest backend/tests --cov=ecs_ec --cov-report=term-missing
uv run --locked alembic -c backend/alembic.ini check
```

Resultado inicial de US2: 23 pruebas pasan, cobertura Python total 89%; no hay umbral
numérico adicional en la spec. `alembic check` no detecta diferencias con los modelos.

Verificación final ampliada: 40 pruebas pasan y cobertura Python total 93%. Añade
contrato de alias `type`, persistencia del período medido y conservación estable tras
reintento, reglas IANA fijadas, fecha inexistente de Samoa, configuración de producción
y protección de la base de pruebas frente a destinos coincidentes en `.env`.

- Resultado sintético y evento persisten juntos; rollback elimina ambos.
- Repeticiones dentro de una transacción y posteriores devuelven el UUID original.
- Cuatro productores concurrentes en conexiones independientes producen un solo evento.
- Auditoría acepta actor `process:synthetic` sin FK a identidad y conserva intentos repetidos.
- Esquemas desconocidos, campos secretos y valores ajenos al vocabulario son rechazados.
- Cobertura completa con cero conocido, parcial con conteo observado y desconocida con NULL
  permanecen distintas tras persistir. Períodos/huecos se conservan con origen/revisión/corte.
- Ventanas invertidas, conteos negativos, períodos solapados/fuera de ventana y estados
  inconsistentes son rechazados antes de escribir. PostgreSQL conserva restricciones
  representables adicionales e índices, sin cascadas ni tablas de negocio.

La ejecución encontró una diferencia entre JSON `null` y SQL NULL en una ventana opcional;
se corrigió con `JSONB(none_as_null=True)` y la suite pasó después. Los resultados funcionales
de identidad, consumo, costos o PDF se validarán en sus specs propietarias.
