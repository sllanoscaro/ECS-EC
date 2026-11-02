# Implementation Plan: [FEATURE]

## Contexto compartido del proyecto (ECS-EC)

Antes de completar este artefacto, leer [arquitectura](../../docs/architecture.md) y
[hoja de ruta](../../docs/implementation-roadmap.md), con rutas relativas al archivo
final `specs/<funcionalidad>/*.md`, además de `AGENTS.md` de la raíz. Mantener las
referencias en el resultado; no copiar todo el diseño común a la funcionalidad activa.
La infraestructura pertenece a 009, identidad a 006, consumo a 001/002 y observabilidad
a 007. Cada funcionalidad implementa su propio módulo y adaptadores; declara faltantes
externos sin implementarlos en su setup. Leer y preservar el alcance de cualquier
`tasks.md` existente marcado Borrador de traslado antes de generar el plan/tareas completo.

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `$speckit-plan` command; its definition describes the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]

**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

[Gates determined based on constitution file]

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file ($speckit-plan command output)
├── research.md          # Phase 0 output ($speckit-plan command)
├── data-model.md        # Phase 1 output ($speckit-plan command)
├── quickstart.md        # Phase 1 output ($speckit-plan command)
├── contracts/           # Phase 1 output ($speckit-plan command)
└── tasks.md             # Phase 2 output ($speckit-tasks command - NOT created by $speckit-plan)
```

### Source Code (repository root, this feature)

<!-- Show only feature-owned modules, tests, migrations and integration points.
     The full layout is docs/architecture.md. Do not recreate core/auth/telemetry
     inside a business feature. Platform009 owns the initial scaffold. -->

```text
backend/src/ecs_ec/[module]/
backend/migrations/versions/[feature_revision].py
backend/tests/{unit,integration,contract}/[module]/
frontend/src/app/[feature-route]/
frontend/src/components/[module]/
frontend/src/lib/api/[module].ts
frontend/tests/{unit,e2e}/
```

**Structure Decision**: [Describe this module, adapters, existing capabilities consumed,
and blockers assigned to their owning specs. Link shared architecture instead of duplicating it.]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
