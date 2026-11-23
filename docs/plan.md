# Repository plan

This file is the current source of truth for unfinished work in
`lib.py.cad.verification`.

## Current accepted baseline

Reusable verification semantics, evidence, geometry/visual helpers and the
SolidCraft adapter are already library-owned. Consumers own model-specific
expected values, tolerances, mutations, views and other policy.

## Current goal

### #79 — reusable verification runner boundary

**Now.**

Remove the remaining generic definition-loading and base verification launcher
logic from Forge so CAD-CI can consume this library directly.

Initial accepted slice:

1. load existing schema-1 `reference_geometry.json` as
   `GeometryContract`;
2. run mesh geometry through the existing `verify()` report engine;
3. load model-local Python `VERIFICATION = SolidCraftVerification(...)`;
4. delegate that definition to the existing SolidCraft verification runner;
5. keep Docker/runtime selection, CAD-CI/SCons and Forge compilation outside;
6. keep preview/presentation work outside this initial slice.

After library CI is green, open/merge one PR and publish an immutable release
before CAD-CI #110 consumes the new API.

## Open issue assessment — 2026-11-23

| Issue | Status | Assessment |
| --- | --- | --- |
| #79 Own the reusable SolidCraft verification runner/process used by CAD consumers | **now** | Required owner work for `lib.py.cad.ci#110`; implement the bounded base-runner slice above. |
| #80 Align historical changelog with shared meta template and guidance | later / docs-only | Does not block verification integration. |
| #48 Replace remaining lib.py.cad.verfication repository-name references | later | Naming cleanup unrelated to the current runtime contract. |

## Next checkpoint

Green #79 library PR with no CAD-CI/SCons dependency and no new runtime/process
startup behavior.
