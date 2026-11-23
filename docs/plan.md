# Repository plan

This file is the current source of truth for unfinished work in
`lib.py.cad.verification`.

## Current accepted baseline

Issue #79 implementation is merged on main at
`ca275b2a2d5246fb40c1800961372bae97cb326b` and passed normal library CI.

The library now owns reusable schema-1 geometry-contract loading, mesh
verification through the existing `verify()` engine, model-local
`SolidCraftVerification` definition loading and the definition-file delegate
runner. Consumers still own model-specific expected data and CAD-CI/runtime
orchestration stays outside this library.

## Current goal

### #82 — publish immutable 0.16.0

**Now.**

Promote the tested #79 implementation as immutable 0.16.0 so
`lib.py.cad.ci#110` can consume an exact released verification API.

Release gate:

1. VERSION, pyproject.toml and CHANGELOG.md declare 0.16.0;
2. release PR wheel CI is green;
3. merge the release PR;
4. verify the main release workflow publishes `v0.16.0`;
5. verify the release target equals the exact tested release commit;
6. only then resume CAD-CI #110.

## Open issue assessment — 2026-11-23

| Issue | Status | Assessment |
| --- | --- | --- |
| #82 Publish immutable 0.16.0 verification runner release | **now** | Release gate for `lib.py.cad.ci#110`. |
| #80 Align historical changelog with shared meta template and guidance | later / docs-only | Does not block verification integration. |
| #48 Replace remaining lib.py.cad.verfication repository-name references | later | Naming cleanup unrelated to the current runtime contract. |

## Next checkpoint

Immutable `v0.16.0` targeting the exact green release commit.
