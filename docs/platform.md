# Contratos de implementación de plataforma

La [arquitectura](architecture.md) asigna `core`, `audit` y composición a spec-009.
Los modelos y migración inicial son comunes; ningún productor los vuelve a declarar.
El [contrato funcional](../specs/009-fundaciones-plataforma/contracts/integrations.md)
conserva su precedencia sobre detalles de composición.

## Tiempo y persistencia

`Settings` carga entorno sobre `.env`, valida PostgreSQL/Psycopg, URL y zona IANA.
`Database` crea un motor asíncrono, con sesiones UTC y parámetros SQL ocultos.
`UnitOfWork` abre una sesión por contexto: `commit()` es explícito, salir revierte todo
lo no confirmado y cierra la sesión incluso tras excepción/cancelación. Los escritores
no hacen commit. El productor decide cómo convertir errores DB en resultados seguros;
no debe enviar SQL, URLs ni excepciones crudas a la API o evidencia funcional.

`Clock.now()` devuelve UTC consciente y `Clock.monotonic()` sirve para duraciones.
`SystemClock` se usa normalmente; `FrozenClock` solo se inyecta internamente en pruebas.
`anniversary(recorded_at, timezone)` añade 12 meses calendario locales, ajusta el 29 de
febrero al 28 cuando corresponda, elige la segunda ocurrencia ambigua y el primer instante
válido tras una hora/fecha inexistente. Lee reglas desde `tzdata` bloqueado en ambos entornos.
Las lecturas no extienden conservación. No hay tarea de borrado común: los productores
extienden dependencias protegidas según su política antes de habilitar cualquier limpieza.

## Evidencia funcional

Los escritores reciben `UnitOfWork`, reloj, zona y esquemas registrados durante composición.
Cada productor hereda `SafePayload`, registra su código con `PayloadRegistry.register` y
utiliza solo campos aprobados. El registro rechaza objetos abiertos y texto libre: cadenas
deben tener vocabulario, formato UUID/fecha o patrón acotado. La persistencia revalida el
sobre y la carga, verifica JSON Schema, campos sensibles, controles y límite de 16 KiB.
Registrar esquemas es una operación interna confiable, nunca una API de usuarios.
El dueño del esquema revisa la necesidad de cada campo y prohíbe datos personales ajenos
al propósito de la evidencia. No registrar esquemas de otros dominios por adelantado.

```python
from typing import Literal
from ecs_ec.audit.events import PayloadRegistry, SafePayload

class ProducerResult(SafePayload):
    """Synthetic example: only an approved outcome code, with no free text."""
    outcome: Literal["ok", "failed"]

schemas = PayloadRegistry()
schemas.register("example.changed", ProducerResult, results={"succeeded", "denied"})
```

`EventInput` acepta `event_id` y `type` (alias de `event_type`). El escritor los mapea a
`functional_event.id/event_type`. `measurement_window` se convierte a `effective_window`;
su ausencia es SQL NULL y no un período inferido del registro. Los opcionales
`category_id`/`functional_result` se declaran en la carga aprobada por cada productor.
UUID del evento lo genera el productor confiable; `recorded_at`/`retain_until`, el escritor.
`EventWriter.append(uow, event)` usa `ON CONFLICT` por módulo/entidad/revisión/tipo y devuelve
el registro original, también ante concurrencia. El reintento no extiende conservación.
Reutilizar un UUID para otra procedencia es error. Se requiere aislamiento READ COMMITTED,
configuración PostgreSQL predeterminada. Un fallo DB no acredita durabilidad.

`FunctionalAudit.append(uow, AuditInput(...))` valida acción/resultado registrados y genera
un UUID por intento. Actor y entidad son referencias opacas; no hay unicidad que suprima
intentos repetidos ni FK a identidad aún ausente. Acciones administrativas y denegaciones
las define spec-006. Si una operación necesita idempotencia, la aporta su productor.
Resultado de fallo y evento posterior a rollback deben escribirse en una nueva UoW juntos.

`CoverageService.append(uow, CoverageInput(...))` persiste alcance, origen/revisión/corte y
conservación. Las ventanas son `[inicio, fin)` con inicio < fin; intervalos están acotados,
sin solapamientos internos ni intersección entre cobertura y huecos. `completa` requiere
conteo conocido y períodos contiguos de toda la ventana, sin huecos; `incompleta`, huecos
conocidos. `desconocida` conserva NULL sin evidencia observada y nunca inventa cero.
Los períodos observados no pueden exceder el corte. La misma ventana puede tener múltiples
cortes/revisiones. PostgreSQL agrega restricciones de tipos, ventana, conteo e integridad.
La validación detallada de intervalos JSON corresponde al servicio.

Las consultas del contenido y los permisos actuales pertenecen a cada productor/identidad;
el adaptador de spec-008 compone `FunctionalSummary.read`. La plataforma no consulta
módulos ausentes y la cobertura no deriva de logs o heartbeats técnicos.

## Composición y comprobaciones

`create_app(settings, modules, clock)` recibe registros `Module(name, router, lifespan)`.
Nombres son únicos. Los context managers inician después de DB/esquema/export y cierran
en orden inverso antes del pool. Cada módulo supervisa y detiene sus tareas internas.
No existen workers propios desplegados por separado. No hay importaciones a módulos aún
no instalados; SMTP/telemetría no condicionan salud.

Alembic utiliza la URL externa y metadatos de propietarios instalados; cada nueva migración
enlaza el head real. La inicial rechaza downgrade destructivo de evidencia protegida.
Ver [ejecución y pruebas](../README.md), [operación](../deploy/README.md) y
[aceptación](../specs/009-fundaciones-plataforma/validation/acceptance.md).
