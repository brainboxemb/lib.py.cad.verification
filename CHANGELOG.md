# Changelog

## 0.16.0

- add reusable loading of existing schema-1 mesh geometry verification contracts;
- add a mesh-geometry runner that writes the normal `cad-verification` report through the existing `verify()` engine;
- add reusable loading of model-local `VERIFICATION = SolidCraftVerification(...)` definitions;
- add a definition-file SolidCraft runner that delegates to the existing declarative verifier;
- preserve the lazy heavy geometry/visual import boundary and keep CAD-CI, Docker/runtime selection and Forge compilation outside this library.

## 0.15.0

- add generic `ThroughPathSlot` expected-shape geometry for polyline/arc slot centerlines;
- keep two-point path slots geometrically compatible with existing `ThroughSlot`;
- support deterministic path-slot goal/overlay drawing and single-view visual evidence;
- preserve lazy public visual imports and existing straight-slot behavior.

## 0.14.0

- add data-only saved-design numeric measurement change expectations;
- compare existing baseline and mutated measurement paths without re-evaluating
  the baseline model;
- use strict absolute-delta thresholds with typed malformed-evidence errors and
  normal verification failures for insufficient change.


## 0.13.1

- allow body center-of-mass expectations to omit individual XYZ axes with
  `None`;
- preserve the 0.13.0 full-XYZ comparison and evidence path unchanged;
- validate and compare only requested sparse axes so omitted coordinates do not
  become consumer contracts.


## 0.13.0

- add optional total face-count expectations for selected SolidCraft bodies;
- add optional body center-of-mass expectations with explicit numeric tolerance;
- add optional SolidCraft sketch DOF expectations;
- keep all three fields sparse: omitted fields are neither parsed nor included
  in evidence;
- report malformed requested SolidCraft fields as typed evidence errors and
  model-value mismatches as normal verification failures.


## 0.12.0

- allow `SolidCraftBodyExpectation(name_prefix=None)` to select the sole
  measured body without requiring or validating its native body name;
- reuse existing bounds, volume, face-type, sheet-metal and closed checks for
  sole-body contracts;
- preserve existing exact-one non-empty `name_prefix` behavior unchanged;
- keep selector-count mismatches as normal verification failures and requested
  malformed property evidence as typed SolidCraft evidence errors.

## 0.11.0

- add explicit subset matching for SolidCraft parameter expectations while preserving exact matching as the default;
- allow SolidCraft sketch expectations to verify only declared stable fields;
- add declarative body, sketch, timeline-feature and face-type count expectations;
- add declarative multi-body groups selected by one caller-supplied name prefix with exact count and optional order-independent envelopes;
- add projected read-only inspection checks with explicit object/list paths, keyed list selection, exact values, numeric tolerances and collection counts;
- keep raw inspection results as evidence artifacts while reporting only requested projected checks;
- preserve all existing exact SolidCraft expectation and inspection behavior.

## 0.10.1

- keep SolidCraft-only public imports independent of geometry and visual
  implementation modules;
- lazy-load existing top-level geometry and visual exports only when requested;
- preserve the complete public API and verification/evidence semantics;
- leave package dependency declarations unchanged for a separate runtime
  packaging decision.


## 0.10.0

- allow SolidCraft timeline expectations to select stable fields explicitly;
- keep feature type mandatory and timeline order/count strict;
- ignore generated native feature names by default;
- retain explicit error and warning checks by default;
- preserve deterministic evidence containing only fields that belong to the model contract.


## 0.9.0

- add declarative `SolidCraftVerification` model verification;
- add declarative saved-design mutations and read-only inspections;
- add `run_solidcraft_verification()` as the reusable baseline/mutation/inspection runner;
- keep the initial native SolidCraft model as consumer-produced input;
- centralize SolidCraft evaluation, mutation, inspection, artifacts and verification report construction;
- remove any need for a model-owned verification CLI;
- keep Forge/SCPF, CAD-CI, SCons and repository selection outside the library.


## 0.8.0

- add the first CAD-tool-specific verification adapter for SolidCraft;
- keep model-specific expected values in consumers while the adapter owns SolidCraft result/schema interpretation;
- add declarative body, parameter, timeline, named-body and sketch expectations;
- add strict SolidCraft evidence validation with typed infrastructure errors;
- add reusable SolidCraft evaluate, mutate and inspect operations;
- package and directly test `cad_verification.adapters` in the built wheel;
- keep Forge compilation, CAD-CI execution and publication outside the library.

## 0.7.0

- add engine-neutral `require_equal()` for exact expected/actual verification;
- add strict-boolean `require_condition()` with caller-supplied evidence;
- preserve deterministic expected/actual/pass evidence on success and failure;
- keep model semantics and CAD-engine interpretation consumer-owned.


## 0.6.0

- add engine-neutral `verify_visual_view()` for one already-rendered view;
- compose normalization, approved-baseline regression and deterministic diff output;
- optionally create generic expected-geometry goal and overlay evidence;
- preserve complete `VisualViewEvidence` on regression failure;
- keep CAD rendering, view selection, camera conversion, baselines and model policy consumer-owned.


## 0.5.0

- add immutable generic semantic check records;
- compose ordered semantic results with deterministic required-check precedence;
- require a complete passing semantic result with typed failure evidence;
- aggregate already-composed item results without executing work;
- adapt existing verification reports while preserving evidence and artifacts.


## 0.4.0

- add deterministic image normalization and baseline payload encoding/decoding;
- add visual regression metrics and comparison image generation;
- add generic orthographic projection and expected box/hole/slot drawing;
- add independent goal and actual-overlay composition;
- add structured per-view visual evidence with explicit missing states;
- declare Pillow as an explicit dependency.


## 0.3.0

- add CAD-engine-neutral scalar, vector and XYZ-bounds comparison helpers;
- add immutable measured-body envelopes and order-independent one-to-one matching;
- preserve deterministic passing/failing comparison evidence through verify();
- reject invalid numeric values, inverted bounds and negative tolerances explicitly.


## 0.2.0

- add reusable immutable geometry contracts and surface-distance probes;
- add STL mesh loading with typed MeshLoadError failures;
- add bounds, volume, watertightness and nearest-surface probe verification;
- preserve structured passing and failing geometry evidence;
- integrate geometry checks with the existing verification report;
- declare trimesh as an explicit library dependency;
- test the installed built wheel together with its declared dependencies.


## 0.1.0

- add the reusable CAD verification request/check/result model;
- add structured pass, skip, fail and error outcomes;
- validate and hash produced verification artifacts;
- add safe external CAD-command execution with explicit timeout/failure types;
- provide a stable JSON verification report;
- keep CI selection, caching, publication and CAD-engine semantics outside the library.
