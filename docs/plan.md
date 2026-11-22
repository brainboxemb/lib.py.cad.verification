# Repository plan

This file is the current source of truth for unfinished work in
`lib.py.cad.verification`.

## Current accepted baseline

Release `v0.15.0` is published from the completed #75 work. The through-path
slot expected-shape capability is therefore no longer unfinished work.

## Current goal

Issue #78 — **now**: support generic SolidCraft verification for intentional
sketch-only designs with zero bodies.

Forge #683 exposed the missing generic behavior: native sketch replay succeeds,
but the verification adapter unconditionally enters the body export path and
fails with `nothing to export: the design has no bodies`.

The verification library must own this behavior. Forge must not add a dummy body
or consumer-local export bypass.

## Execution order

1. [#78, now] Define zero-body verification requirements/design.
2. Add focused adapter tests proving that an explicit `body_count=0` expectation
   skips body export while preserving sketch, parameter, timeline and
   saved-design checks.
3. Preserve the current export/geometry path for expectations that require bodies.
4. Implement the smallest SolidCraft adapter change.
5. Release the next immutable verification-library version from a green exact
   main commit.
6. Let Forge #683 adopt the exact release and rerun its native sketch-only
   save/reopen qualification.
7. [#48, later] Finish repository-name spelling cleanup separately.

## Open issue assessment — 2026-11-22

| Issue | Status | Assessment |
| --- | --- | --- |
| #78 Support SolidCraft verification for sketch-only designs without bodies | **now** | Generic adapter gap blocking Forge #683; requirements/design/tests/implementation/release required here. |
| #48 Replace remaining lib.py.cad.verfication repository-name references | **later** | Repository identity/documentation cleanup; independent of the active verification behavior gap. |

Immediate chain:
`verification #78 -> immutable release -> Forge #683 adoption/qualification`.
