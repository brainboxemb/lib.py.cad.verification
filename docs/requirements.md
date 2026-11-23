# CAD verification requirements

This document is the product contract for `lib.py.cad.verfication`.
Implementation details belong in `docs/design.md`.

## 1. Scope

The library provides reusable mechanics and CAD-engine-specific verification
adapters for verifying one already-selected CAD model or verification case.

The library is not a CI runner. `tool.cad.ci` remains responsible for
repository selection, SCons execution, dependency ordering, incremental
rebuilds and cache reuse.

A normal consumer flow is:

~~~text
tool.cad.ci
  -> selected item
    -> model_verify step
      -> consumer verification definition
        -> lib.py.cad.verfication
~~~

## 2. Consumer ownership

The consumer owns:

- the verification identifier;
- the model/command input;
- model-specific expected values and tolerances;
- model-specific mutation definitions;
- model-specific required views and policy;
- engine installation/runtime selection.

The library owns the shared mechanics for applying those expectations to a CAD
result. This includes CAD-engine-specific result parsing and checking where the
same behavior is reusable across consumers.

For SolidCraft, shared knowledge of result/measurement schemas, native
inspection output and how model expectations are evaluated against that output
belongs in this library.

The library must not contain Forge model names, Forge model dimensions or other
model-specific expectations.

## 3. Verification request

One verification request contains:

- a stable verification ID;
- an input path;
- an output directory;
- an optional working directory;
- optional JSON-compatible metadata;
- an ordered list of checks.

The caller explicitly invokes the request. The request must contain at least one
check; an empty verification is invalid and may never produce a passing report.
The library performs no repository discovery or changed-file selection.

## 4. Checks

A check has:

- a stable ID;
- one callable supplied by the consumer.

Checks run in declared order.

A check may:

- pass;
- be skipped with an explicit reason;
- fail with an expected verification failure;
- raise an unexpected error.

A failed or errored check stops later checks. This keeps dependent CAD
operations from running on invalid prerequisite evidence.

The library does not decide whether a check is dirty/current and does not cache
check results.

## 5. Verification status

The complete verification status is:

- `pass`: every executed check passed or was explicitly skipped;
- `fail`: a check reported an expected verification failure;
- `error`: verification infrastructure, artifact validation or an unexpected
  exception failed.

Skipped checks are recorded but do not make the complete verification fail.

## 6. Produced artifacts

A passing or skipped check may declare produced artifacts.

Every declared artifact:

- must exist when the check returns;
- must resolve below the verification output directory;
- may be a regular file or directory;
- may not be a symlink;
- receives deterministic size/hash evidence.

Directory evidence recursively includes lexical relative paths and file hashes,
so nested output changes are visible.

A missing, unsafe or unsupported artifact is an `error`, not a model
verification `fail`.

## 7. External commands

The library provides a small reusable process helper for CAD commands.

It must:

- execute an explicit argv sequence without a shell;
- support a working directory;
- support environment overrides;
- capture stdout and stderr;
- support an optional positive timeout;
- distinguish non-zero exit from timeout;
- never reinterpret timeout/network/authentication failures as a domain result.

The caller remains responsible for command meaning.

## 8. Evidence

Every verification writes one JSON report:

~~~text
<output-dir>/verification.json
~~~

The report records at least:

- schema and schema version;
- verification ID;
- overall status;
- consumer metadata;
- ordered check results;
- per-check status/reason/error;
- produced artifact records.

The report is evidence only. It is not rebuild/cache state.

The report must not use the CAD-CI reserved `.cad-ci` namespace.

## 9. IDs and paths

Verification and check IDs use lowercase engineering names containing letters,
digits, `-` and `_`.

Duplicate check IDs are invalid configuration.

The report path is owned by the library. Consumers may not declare
`verification.json` as a check artifact.

## 10. Error model

The public error model distinguishes at least:

- invalid verification/check configuration;
- expected verification failure;
- missing/unsafe artifact;
- command non-zero exit;
- command timeout;
- unexpected consumer exception.

An expected model mismatch must not be reported as an infrastructure error.
An infrastructure error must not be downgraded to a model mismatch.

## 11. Determinism

Given the same consumer-returned evidence and artifact bytes, structural report
content is stable and JSON keys are emitted in deterministic order.

No wall-clock timestamp participates in the report contract.

Timing may be exposed later only through an explicit design change.

## 12. Non-goals

This library does not provide:

- a CLI tool;
- a second CI runner;
- YAML CI configuration;
- SCons integration;
- GitHub Actions workflows;
- Git selection;
- incremental rebuild decisions;
- cache management;
- build/Pages publication;
- CAD-engine installation or image creation;
- model-specific expected values;
- Forge model definitions or Forge compiler behavior.

## 13. Initial acceptance

Before the first release, unit tests must prove:

1. ordered passing checks produce a passing report;
2. an explicit skip is recorded and remains successful;
3. an expected failure stops later checks and produces `fail`;
4. an unexpected exception stops later checks and produces `error`;
5. duplicate/invalid IDs are rejected;
6. missing/out-of-root/symlink artifacts produce `error`;
7. file and directory artifact hashes change when content changes;
8. external command success captures output;
9. non-zero command exit and timeout are distinct errors.


## 14. Numeric and measured-body comparison

Public reusable behavior:

- compare one scalar against an expected value with a non-negative tolerance;
- compare equally-sized numeric vectors with one tolerance;
- compare expected/actual XYZ bounds;
- match unordered lists of body envelopes by XYZ bounds.

All inputs are consumer-supplied measurements. No CAD-engine object is accepted.

Evidence must include expected value(s), actual value(s), deltas, tolerance and
pass/fail. A mismatch raises `VerificationFailure`.

Body-envelope matching must prove:

- every expected envelope has one matching actual envelope;
- no unmatched actual envelope remains;
- matching is independent of input ordering.

Tests must prove:

- exact / inside tolerance / on tolerance / outside tolerance;
- invalid numeric values and negative tolerance are rejected;
- vector length mismatch is rejected;
- unordered multi-body matching succeeds;
- missing, extra and mismatched bodies fail;
- evidence is deterministic and survives through `verify()`.

This work is tracked by issue #8.

## 15. Mesh geometry verification

Public API:

```python
GeometryContract
SurfaceDistanceProbe
validate_mesh_geometry(mesh_path, contract)
MeshLoadError
```

`GeometryContract` contains:

- expected min/max XYZ bounds;
- bounds tolerance;
- optional expected volume + volume tolerance;
- optional expected watertightness;
- `bounds_sufficient` flag;
- ordered surface-distance probes.

A probe contains:

- stable label;
- XYZ point;
- expected nearest-surface distance;
- tolerance.

Rules:

- vectors contain exactly three finite numbers;
- tolerances are non-negative;
- max bounds may not be below min bounds;
- volume requires a volume tolerance;
- probe labels are unique;
- when `bounds_sufficient=False`, volume or at least one surface probe is
  required.

STL loading must:

- reject missing, empty, malformed and non-measurable files with
  `MeshLoadError`;
- combine measurable parts when trimesh returns a multi-part Scene.

Verification always checks bounds and optionally checks volume,
watertightness and probes.

A geometry mismatch raises `VerificationFailure` with all already-evaluated
passing and failing evidence. Loading/infrastructure problems remain errors.

Tests must prove:

- contract/probe validation;
- exact and toleranced bounds;
- volume pass/fail;
- watertight pass/fail;
- probe pass/fail and ordering;
- multi-part mesh envelope;
- bounds-insufficient contract validation;
- `verify()` maps geometry mismatch to fail and load failure to error;
- identical input produces identical evidence;
- no Forge/SolidCraft/reference-CAD dependency exists.

This work is tracked by issue #7.

## 16. Visual regression and expected-shape evidence

The library provides generic image verification and projection/drawing helpers.
It never renders CAD itself.

Generic behavior includes:

1. load an image, convert RGB/RGBA to grayscale and normalize to a requested
   target size;
2. encode/decode deterministic approved baseline payloads;
3. compare normalized current/reference images using:
   - mean absolute pixel difference;
   - changed-pixel fraction above a caller-supplied pixel-difference threshold;
4. create a deterministic diff/comparison image;
5. project consumer-supplied 3D points with an orthographic camera containing
   target, yaw, pitch and distance;
6. draw consumer-supplied expected 3D boxes;
7. draw generic through-hole, straight through-slot and polyline through-slot expected features;
8. produce goal and overlay images where the actual render remains visible;
9. verify one already-rendered visual view by composing normalization, optional
   approved-baseline regression, deterministic diff output, optional expected
   geometry goal/overlay generation and one `VisualViewEvidence`.

The consumer owns:

- required view names;
- actual CAD rendering;
- model cameras;
- approved baselines;
- model boxes/features;
- image thresholds;
- artifact/evidence references used for the already-rendered view.

The single-view verification function:
- accepts an already-rendered actual image and never invokes a CAD engine;
- treats an absent baseline as explicit `missing`, not as a pixel mismatch;
- compares an existing baseline with caller-supplied thresholds;
- always writes the deterministic diff when baseline comparison is attempted;
- preserves complete visual-view evidence when regression fails;
- optionally creates goal and overlay images only from caller-supplied generic
  camera/box/hole/straight-slot/path-slot values;
- returns one deterministic `VisualViewEvidence` on success or missing
  baseline;
- raises `VerificationFailure` on regression mismatch with the complete
  visual-view evidence attached;
- does not choose view names, cameras, baselines, expected model geometry or
  required/optional policy.

Tests must prove:

- RGB/RGBA normalization and resize;
- baseline encode/decode including compressed and PNG payloads;
- identical/changed image metrics and both independent threshold failures;
- deterministic diff output;
- front projection X-right/Z-up;
- top projection X-right/Y-up;
- valid top/bottom camera basis;
- deterministic expected-box drawing;
- through-hole, straight through-slot and polyline through-slot drawing;
- invalid/unknown feature input is rejected;
- goal image contains independent expected geometry;
- overlay preserves actual pixels and adds expected geometry;
- missing baseline/image is distinguishable from pixel mismatch;
- single-view pass evidence and caller-controlled artifact references;
- single-view regression failure preserves complete visual evidence;
- single-view missing baseline remains explicit without approving anything;
- single-view goal and overlay generation use the existing generic drawing
  primitives;
- no SolidCraft/CADCraft/model policy is embedded.

Primitive visual behavior was introduced by issue #9. Generic single-view
orchestration is completed by issue #26.

Issue #75 extends expected-shape geometry with a polyline through-slot primitive.
Its centerline contains at least two finite XY points. Consecutive points may
not be identical, width must be positive, and z_max may not be below z_min.
A two-point path slot must draw the same slot geometry as the existing straight
`ThroughSlot`. The library owns tangent-normal path-outline generation and
projection; consumers own the concrete centerline points.

## 17. Semantic verification result composition

The library can compose already-produced verification evidence without
executing CAD work.

A consumer supplies ordered semantic checks containing:

- check name;
- status;
- whether the check is required;
- optional reason;
- JSON-compatible evidence.

Generic statuses are:

```text
pass
fail
error
missing
review
blocked
not-required
skipped
```

Overall status precedence for required checks is:

1. error;
2. fail;
3. incomplete when missing;
4. review;
5. blocked;
6. pass.

Optional `not-required` and `skipped` checks do not fail the result.

The library must:

- preserve consumer check order and evidence;
- validate that a composed result is complete/pass when requested;
- aggregate multiple already-composed item results;
- map existing `verification.json` check records into generic semantic input.

The library must not contain Forge-specific semantic names such as
`native_model`, `saved_design`, `visual` or `reference`; Forge supplies
those names.

Tests must prove every status/precedence rule, evidence/order preservation,
pass validation, aggregation, adapter mapping and absence of CAD-CI publication
logic.

This work is tracked by issue #10.

## 18. Exact-value and predicate verification

The library provides two generic requirements for model-specific checks:

```python
require_equal(expected, actual, *, label=None)
require_condition(condition, *, expected, actual, label=None)
```

`require_equal()`:
- performs exact Python equality with no numeric tolerance or coercion;
- accepts JSON-compatible expected and actual evidence;
- returns deterministic evidence containing label, expected, actual and pass;
- raises `VerificationFailure` with the same evidence when values differ.

`require_condition()`:
- accepts only an actual `bool` condition;
- accepts caller-supplied JSON-compatible expected and actual evidence;
- returns the same deterministic evidence shape on true;
- raises `VerificationFailure` with that evidence on false.

For both helpers:
- label is optional descriptive evidence;
- invalid/non-JSON evidence is a `VerificationConfigError`;
- model semantics remain consumer-owned;
- no CAD engine, repository, workflow or publication behavior is allowed.

Tests must prove exact nested equality, mismatch evidence, true/false predicate
behavior, invalid condition types, invalid evidence and deterministic output.

This work is tracked by issue #29.

## 19. Migration completeness

Issue #4 is the migration inventory.

The old Forge qualification stack is split as follows:

- generic scalar/vector/body comparison -> section 14 / issue #8;
- generic STL/mesh validation -> section 15 / issue #7;
- generic visual comparison/projection/overlay -> section 16 / issue #9;
- generic semantic result composition -> section 17 / issue #10;
- generic exact-value/predicate failure evidence -> section 18 / issue #29;
- model-specific geometry values, mutation definitions, cameras, baselines and
  expected shapes remain consumer-owned data;
- CAD-tool-specific execution/parsing/checking may live in a verification
  adapter when it is reusable across consumers;
- CAD-CI selection/materialization/publication remains `tool.cad.ci`;
- diagram rendering and site/report publication remain consumer-owned.

No reusable verification behavior is considered migrated merely because Forge
has a local copy. Each reusable area above must be implemented, tested against
the built wheel and released before Forge consumes it.


## 20. CAD-tool adapters

The library may provide adapters for individual CAD tools under a common
`cad_verification.adapters` package.

An adapter owns reusable knowledge of how to inspect and verify that CAD tool.
It may know the tool's command line and result schema. It must not know Forge
models or other consumer-specific model values.

The first adapter is SolidCraft.

### 20.1 SolidCraft model expectation

Forge or another consumer supplies model-specific data through a
`SolidCraftModelExpectation`.

The expectation may contain:

- expected body envelopes and their tolerance;
- expected parameter values;
- expected timeline rows;
- expected named-body properties;
- expected sketch properties.

A timeline expectation always checks feature type. Name, error and warning are
checked only when that field is enabled by the expectation. Generated
SolidCraft names therefore do not become consumer-owned merely because they are
present in measurement evidence. Timeline row count and row order remain
strict.

The expectation contains data only. It does not contain executable checker
callbacks or SolidCraft JSON field paths.

### 20.2 SolidCraft measurement verification

`verify_solidcraft_measurements(measurements, expectation)` must:

- validate the SolidCraft measurement object before comparing model values;
- interpret SolidCraft `params`, `bodies`, `bbox`, `timeline` and
  `sketches` structures inside the adapter;
- use the existing generic comparison/assertion APIs for numeric and exact
  comparisons;
- return deterministic evidence when all requested expectations pass;
- raise `VerificationFailure` for a genuine model mismatch;
- raise a verification infrastructure/schema error for malformed or incomplete
  SolidCraft evidence.

A malformed SolidCraft result must never be silently reduced to fewer bodies or
converted into an ordinary model mismatch.

### 20.3 SolidCraft command operations

The adapter provides reusable operations for an already-produced native
SolidCraft model:

- evaluate a saved `.sc` model into a JSON measurement object;
- apply a saved-design command/mutation to an existing `.sc` model;
- execute a read-only inspection command and load its JSON result.

The adapter uses the library's existing external-command helper.

Forge compilation/replay into the initial SolidCraft design is not part of this
adapter. Forge is responsible for producing its model/command document; the
verification adapter is responsible for checking the resulting SolidCraft
design.

### 20.4 Adapter boundary

The SolidCraft adapter must not import Forge/SCPF or contain:

- Forge model names;
- expected dimensions for a Forge example;
- Forge compiler behavior;
- CAD-CI/SCons logic;
- repository selection, caching or publication.

Tests must prove both the public behavior and this dependency boundary.

This work is tracked by issue #32.


## 21. Declarative SolidCraft model verification

The library provides one reusable runner for an already-produced native
SolidCraft model.

A consumer supplies a `SolidCraftVerification` definition containing:

- a stable verification ID;
- one baseline `SolidCraftModelExpectation`;
- zero or more saved-design mutations;
- zero or more read-only inspections;
- optional JSON-compatible metadata.

The consumer definition contains model-specific data only. It must not contain
verification callbacks.

### 21.1 Baseline

The baseline check must:

1. evaluate the supplied native `.sc` model through the SolidCraft adapter;
2. verify the resulting measurements with
   `verify_solidcraft_measurements()`;
3. retain the measurement JSON as an artifact;
4. record the returned deterministic evidence in the normal verification
   report.

The runner does not create the initial native model. Producing that model is a
consumer responsibility.

### 21.2 Saved-design mutation

A `SolidCraftSavedDesign` contains:

- a stable ID;
- a SolidCraft command JSON path;
- the expected `SolidCraftModelExpectation` after the mutation.

For every saved design the runner must:

1. apply the command to the original native model without rerunning consumer
   source code;
2. save the changed `.sc` model below the verification output directory;
3. evaluate the changed model;
4. verify the changed measurements;
5. retain both the changed model and measurement JSON as artifacts.

Saved-design checks execute in declared order and are independent; each starts
from the original supplied model.

### 21.3 Read-only inspection

A `SolidCraftInspection` contains:

- a stable ID;
- a SolidCraft inspection command JSON path;
- optional exact JSON-compatible expected result data.

The runner executes the inspection against the original supplied native model
and retains its JSON result as an artifact.

When exact expected result data is supplied, the runner compares it with
`require_equal()`. More specialized tolerant inspection semantics are added
to the SolidCraft adapter only when a consumer requires them; consumers must
not reimplement shared inspection parsing merely to bypass the library.

### 21.4 Runner

Expose:

```python
run_solidcraft_verification(
    model_path,
    output_dir,
    definition,
)
```

The function:

- constructs the normal `VerificationContext`;
- constructs the baseline/saved-design/inspection checks from the definition;
- executes them through the existing `verify()` function;
- writes the normal `verification.json`;
- returns that report.

There is no model-owned CLI requirement and no repository discovery.

### 21.5 Boundary

The declarative runner must not:

- import Forge/SCPF;
- compile or replay Forge command documents;
- read CAD-CI environment variables;
- select models from a repository;
- use SCons;
- publish build/Page output.

Tests must prove the runner through the installed built wheel before release.

This work is tracked by issue #36.


## 22. Partial SolidCraft timeline expectations

`SolidCraftTimelineExpectation` supports field-level timeline contracts.

Rules:

- `feature_type` is always required and always compared;
- `name` is compared only when `check_name=True`;
- `error` is compared only when `check_error=True`;
- `warning` is compared only when `check_warning=True`;
- default behavior checks `feature_type`, `error` and `warning`, but does
  not check the generated feature name;
- supplying a non-null value for a field while its corresponding check flag is
  false is invalid configuration;
- timeline row count and order are strict;
- only enabled fields appear in expected/actual comparison evidence.

This lets a model verify stable SolidCraft behavior without claiming ownership
of generated native names.

This work is tracked by issue #40.


## 21. Public import isolation for optional verification stacks

The public package root must not load geometry or visual implementation modules
unless a public API from those modules is actually requested.

In particular:

- importing `SolidCraftVerification` or
  `run_solidcraft_verification` from `cad_verification` must not import
  `cad_verification.geometry` or `cad_verification.visual`;
- the same top-level geometry and visual names remain public and compatible;
- requesting a geometry or visual name may load its implementation module at
  that moment;
- import isolation changes no verification result, evidence schema or
  consumer-facing type/function semantics.

This requirement allows runtime packagers to construct role-specific
environments without forcing unrelated geometry/visual stacks into a
SolidCraft-only process. Dependency packaging remains a separate concern.


## 23. Partial SolidCraft parameter expectations

Existing `SolidCraftModelExpectation.parameters` semantics are an exact
full-map contract and remain backward compatible.

A model expectation may explicitly choose parameter matching mode:

- `exact` — the expected mapping must equal the complete normalized
  SolidCraft parameter mapping;
- `subset` — every requested parameter name must be present and equal, while
  unrelated actual parameters are allowed.

`exact` is the default so already-released consumer definitions retain their
meaning.

In `subset` mode:

- parameter evidence is normalized through the same strict SolidCraft schema
  reader as exact mode;
- duplicate names, malformed rows or non-finite values remain
  `SolidCraftEvidenceError`;
- a missing requested name is an ordinary verification mismatch, not malformed
  SolidCraft evidence;
- expected/actual comparison evidence contains only requested parameter names,
  in deterministic key order.

A non-supported parameter matching mode is
`VerificationConfigError`.

The mode has no effect when no parameter expectation is supplied.


## 24. Partial SolidCraft sketch expectations

`SolidCraftSketchExpectation.name` remains the strict named-sketch selector.

The properties `profiles`, `curves` and `status` are independently
optional checks.

At least one property must be supplied. An expectation containing only a name
is invalid because existence-only semantics are not part of this contract.

For a matched sketch:

- only declared properties are required in SolidCraft evidence;
- only declared properties are normalized and compared;
- undeclared sketch properties may be absent or different without affecting
  the result;
- expected and actual evidence contain the selector name plus only declared
  properties.

The selector still requires exactly one sketch with the requested name.
Missing or duplicate matches are `VerificationFailure`. A malformed requested
property is `SolidCraftEvidenceError`.

Existing expectations that supply all three properties retain their current
meaning.


## 25. SolidCraft count expectations

Declarative SolidCraft expectations support three count forms required by
existing consumer contracts.

### Total sketch count

`SolidCraftModelExpectation.sketch_count` optionally requires the total number
of SolidCraft sketch rows.

### Timeline type counts

`SolidCraftModelExpectation.timeline_type_counts` is an optional mapping from
timeline `type` string to expected non-negative count.

Only requested types participate in the comparison. Unrelated timeline rows are
allowed. A requested type that is not present has actual count zero.

### Named-body face type counts

`SolidCraftBodyExpectation.face_type_counts` is an optional mapping from
SolidCraft body `face_types` key to expected non-negative count.

Only requested face types participate in the comparison. Unrelated face types
are allowed. A requested type omitted from the sparse actual mapping has count
zero.

All configured counts are non-negative integers. Malformed requested SolidCraft
count evidence is `SolidCraftEvidenceError`. Count mismatches are normal
`VerificationFailure`.

These count forms do not replace or change existing exact timeline rows,
named-sketch expectations or named-body geometry checks.


## 26. SolidCraft body-group expectations

Existing `SolidCraftBodyExpectation` semantics remain exact-one selection by
`name_prefix`.

A separate `SolidCraftBodyGroupExpectation` represents contracts where
multiple SolidCraft body rows intentionally share a prefix.

A group expectation contains:

- non-empty `name_prefix`;
- exact non-negative `count`;
- optional order-independent `body_envelopes`;
- non-negative `bounds_tolerance`.

If `body_envelopes` is supplied, its length must equal `count`.

Verification selects every body whose validated name starts with the prefix.
The selected count must equal `count`. When envelopes are supplied, only the
selected bodies participate in the existing order-independent body-envelope
comparison.

Evidence records matched body names and the requested count/envelope comparison.
Malformed selected body names or requested bounds remain
`SolidCraftEvidenceError`; mismatches remain `VerificationFailure`.

No Forge-specific occurrence naming rule exists in the library beyond the
caller-supplied prefix string.


## 27. Projected SolidCraft inspection expectations

Existing inspection modes remain valid:

- `SolidCraftInspection(expected=<json>)` compares the complete result exactly;
- an inspection without expectation retains the raw result artifact without
  comparison.

A third mode provides data-only projected checks.

### Inspection selector

`SolidCraftInspectionSelect(field, value)` is a path segment that selects
exactly one object from the current JSON list by exact equality of one required
object field.

Every list member used by that selector must be an object containing the
selector field. Zero or multiple matching rows are verification mismatches.

Selector values are finite JSON scalar values.

### Inspection check

`SolidCraftInspectionCheck` contains:

- stable lowercase engineering `id`;
- a tuple `path` of object-key strings, non-negative list indexes and
  `SolidCraftInspectionSelect` segments;
- exactly one requested operation:
  - exact `expected` JSON-compatible value;
  - tolerant numeric `expected` scalar/vector with non-negative
    `tolerance`;
  - exact collection `count`.

A tolerant vector is a flat finite numeric JSON array of any non-zero length.
Actual vector length must match.

A collection count applies only to JSON arrays or objects.

An inspection may declare projected `checks` only when whole-result
`expected` is not supplied. Check IDs are unique within the inspection.

### Failure and evidence behavior

Missing object keys, out-of-range indexes, malformed selector rows, malformed
numeric values and wrong value kinds are `SolidCraftEvidenceError`.

Selector match-count mismatches, collection-count mismatches and expected-value
mismatches are normal `VerificationFailure`.

Projected check evidence contains:

- check ID;
- normalized path representation;
- comparison evidence for only that requested value/count.

The complete raw inspection result is still written as the normal inspection
artifact but is not copied into projected comparison evidence.

No consumer callbacks, predicates or executable comparison functions are
supported.


## 28. Sole SolidCraft body expectations

`SolidCraftBodyExpectation` supports two exact-one selectors:

- a non-empty `name_prefix`, preserving the existing named-body behavior;
- `name_prefix=None`, meaning the sole measured body.

For the sole-body selector:

- the measured body collection must contain exactly one row;
- zero or multiple rows are normal verification mismatches;
- the body `name` field is not read, required or validated;
- no body name becomes part of expected policy or comparison evidence;
- requested bounds, volume, partial face-type counts, `sheet_metal` and
  `closed` checks use the same semantics as named-body expectations.

For named-body selection, existing strict body-name validation and exact-one
prefix matching remain unchanged.

Malformed evidence for a property that is actually requested remains
`SolidCraftEvidenceError`. The sole-body selector must not validate incidental
unrequested fields merely because they exist.


### 20.7 SolidCraft body face-count, center-of-mass and sketch DOF expectations

A `SolidCraftBodyExpectation` may additionally request:

- total body face count;
- body center of mass as XYZ;
- a non-negative center-of-mass tolerance.

A `SolidCraftSketchExpectation` may additionally request sketch degrees of
freedom (DOF).

These fields are optional. When omitted, the adapter must not read, validate or
include the corresponding SolidCraft evidence field.

When requested:

- face count and DOF are non-negative integer expectations;
- center-of-mass contains exactly three finite numbers;
- center-of-mass tolerance is finite and non-negative;
- the adapter validates the corresponding SolidCraft measurement field before
  comparing it;
- value mismatches are normal `VerificationFailure` results;
- missing, malformed or non-finite requested evidence is a
  `SolidCraftEvidenceError`;
- deterministic evidence includes only fields explicitly requested by the
  consumer.

The consumer owns the expected values and tolerance. The adapter owns the
SolidCraft field names, parsing and comparison mechanics.


### 20.8 Sparse SolidCraft center-of-mass axes

A body center-of-mass expectation keeps exactly three XYZ positions, but each
position may be either a finite expected number or `None`.

Example:

```python
SolidCraftBodyExpectation(
    center_of_mass=(expected_x, None, None),
    center_of_mass_tolerance=0.001,
)
```

Rules:

- the tuple length is exactly three;
- at least one axis is numeric;
- `None` means that axis is outside the consumer contract;
- only requested axes are read, validated and compared;
- malformed evidence on an omitted axis must not fail verification;
- the existing all-numeric XYZ form remains fully compatible;
- the one non-negative tolerance applies to every requested axis;
- evidence identifies only the requested sparse axes.


## 29. SolidCraft saved-design numeric change expectations

A `SolidCraftSavedDesign` may declare zero or more
`SolidCraftMeasurementChangeExpectation` values.

Each change expectation contains:

- a stable engineering `id`;
- a non-empty JSON measurement `path` made only from object-key strings and
  non-negative list indexes;
- a finite non-negative `minimum_absolute_delta`.

The comparison uses the baseline `measurements.json` already produced by the
baseline check and the saved design's mutated measurements.

For each requested relation:

```text
absolute_delta = abs(mutated_value - baseline_value)
pass when absolute_delta > minimum_absolute_delta
```

The threshold is strict. Equality with the threshold fails.

Both resolved values must be finite numbers. Missing keys, invalid indexes,
non-object/non-list path containers and non-numeric/non-finite requested values
are `SolidCraftEvidenceError`.

An insufficient numeric change is a normal `VerificationFailure`.

Evidence records the definition ID, normalized path, baseline value, mutated
value, absolute delta, threshold and pass/fail comparison.

Saved designs that declare no change expectations retain their current
behavior exactly. Consumers provide data only; no callback or predicate is
accepted.

## 30. Reusable verification definition loading and base runners

The library owns reusable loading and execution of verification definitions.
Consumers supply only model-specific configuration and already-selected model
artifacts.

### 30.1 Geometry contract files

`load_geometry_contract(path)` loads the existing reference-geometry JSON
contract without consumer-specific code.

The file is one JSON object with `schema: 1` and maps directly to
`GeometryContract`:

- required: `bounds_min`, `bounds_max`, `bounds_tolerance_mm`;
- optional: `volume_mm3`, `volume_tolerance_mm3`, `watertight`,
  `bounds_sufficient`;
- optional `surface_distance_probes` rows contain `label`, `point`,
  `distance_mm` and `tolerance_mm`.

Malformed JSON, an unsupported schema, unsupported fields, malformed probe rows
or invalid geometry values are `VerificationConfigError`.

Existing valid Forge `reference_geometry.json` schema-1 files require no
format change.

### 30.2 Mesh geometry runner

`run_mesh_geometry_verification(mesh_path, output_dir, contract,
verification_id)` composes the existing `validate_mesh_geometry()` function
with the existing `verify()` engine.

It:

- runs one check named `geometry`;
- writes the normal `cad-verification` `verification.json`;
- maps `VerificationFailure` to report status `fail`;
- maps mesh/config/infrastructure errors through the normal verification error
  semantics;
- returns the complete report.

The runner does not start a CAD engine, container or subprocess.

### 30.3 SolidCraft definition files

`load_solidcraft_verification(path)` executes one model-local Python
definition and requires a global
`VERIFICATION = SolidCraftVerification(...)`.

`run_solidcraft_verification_file(model_path, output_dir, definition_path)`
loads that definition and delegates to the existing
`run_solidcraft_verification()` implementation.

The loader/runner owns no model-specific expected values.

### 30.4 Boundary

This library does not own CAD-CI selection, SCons graphs, caching, Docker/runtime
selection, Forge compilation or publication.

Preview/presentation generation is outside this initial base-runner contract.

