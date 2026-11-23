# CAD verification library design

This document is the normative technical design for
`lib.py.cad.verfication`.

`docs/requirements.md` defines observable behaviour. If implementation needs
a semantic choice not described here, update this document before coding it.

## 1. Architecture

The library has one narrow responsibility:

> Execute one explicit verification request and describe its result.

It sits below a consumer-owned `model_verify` command and above
consumer/engine-specific check functions.

~~~text
CAD-CI model_verify step
        |
        v
consumer verification definition
        |
        v
cad_verification.verify()
        |
        +--> consumer check
        +--> consumer check
        +--> consumer check
        |
        v
verification.json
~~~

There is no repository planner, scheduler, dependency graph or cache.

## 2. Package layout

~~~text
cad_verification/
  __init__.py
  errors.py
  evidence.py
  model.py
  process.py
  verification.py
~~~

### model.py

Owns immutable public data objects:

- `VerificationContext`;
- `CheckOutcome`;
- `VerificationCheck`;
- `CommandResult`.

### errors.py

Owns public exception classes and keeps domain failure distinct from
infrastructure/process failure.

### evidence.py

Validates output artifacts and produces deterministic file/directory records.

### process.py

Executes one explicit external argv command. It has no knowledge of CAD-CI or
verification plans.

### verification.py

Validates one request, executes checks sequentially and writes the final report.

## 3. Public API

~~~python
context = VerificationContext(
    verification_id="simple-box",
    input_path=Path("solidcraft.json"),
    output_dir=Path("build/model_verify"),
)

checks = (
    VerificationCheck("build", build_check),
    VerificationCheck("geometry", geometry_check),
)

report = verify(context, checks)
~~~

A check receives the immutable context and returns either:

- `None`, meaning pass with no extra evidence;
- `CheckOutcome.passed(...)`;
- `CheckOutcome.skipped(reason, ...)`.

For an expected mismatch it raises `VerificationFailure`.

Any other exception is an infrastructure/error result.

## 4. Sequential semantics

A verification request contains at least one check. A zero-check request is a
configuration error rather than a vacuous pass.

Checks are deliberately sequential because later CAD verification operations
often consume artifacts from earlier operations.

The library executes exactly the supplied order.

It does not:

- discover prerequisites;
- skip current work;
- restore cached work;
- rerun subsets by itself.

Those concerns remain outside this library.

On the first `fail` or `error`, execution stops and the final report is
written immediately.

## 5. Artifact evidence

All check artifacts are interpreted relative to or resolved beneath
`context.output_dir`.

For a regular file, evidence contains:

~~~json
{
  "path": "native/model.step",
  "kind": "file",
  "size": 1234,
  "sha256": "..."
}
~~~

For a directory:

~~~json
{
  "path": "native/renders",
  "kind": "directory",
  "entries": 4,
  "sha256": "..."
}
~~~

Directory digest input is a lexical sequence of records containing entry type,
relative path and file content hash. Empty directories participate. Symlinks
are rejected.

The library report itself is not a check artifact.

## 6. Report schema

Schema 1:

~~~json
{
  "schema": "cad-verification",
  "schema_version": 1,
  "verification_id": "simple-box",
  "status": "pass",
  "input": "solidcraft.json",
  "metadata": {},
  "checks": [
    {
      "id": "build",
      "status": "pass",
      "reason": null,
      "error": null,
      "evidence": {},
      "artifacts": []
    }
  ]
}
~~~

Allowed check statuses:

- `pass`;
- `skipped`;
- `fail`;
- `error`.

Allowed overall statuses:

- `pass`;
- `fail`;
- `error`.

The report deliberately contains no start/end timestamps.

## 7. Expected failure

`VerificationFailure` means:

> The verification mechanism worked and proved that the model does not satisfy
> an expected condition.

The exception carries a human-readable message and optional JSON-compatible
evidence.

The verification operation records a `fail` row and stops.

## 8. Unexpected error

Configuration errors, unsafe artifacts, missing artifacts, process failures
not explicitly converted by the consumer, and unexpected exceptions are
`error`.

The report records the exception class and message. Python tracebacks are not
embedded in durable JSON evidence.

The original exception is re-raised only when the caller requests
`raise_on_error=True`; the default API returns the structured report so a
consumer can choose its own exit handling.

Expected verification failure is never re-raised by `raise_on_error`.

## 9. Process helper

`run_command()` calls `subprocess.run(..., shell=False)`.

Environment behaviour:

- start from the current process environment;
- overlay caller-provided values;
- stringify keys/values.

Timeout must be a positive number when supplied.

Success returns `CommandResult` with argv, return code, stdout and stderr.

Non-zero exit raises `CommandFailed`.

Timeout raises `CommandTimedOut`.

## 10. CAD-engine verification boundary

The verification library may provide an engine-specific adapter that calls or
reads a CAD engine when that behavior is part of reusable verification.

A consumer may still supply the engine input and model-specific expectation
data. For example:

~~~python
def build_check(ctx):
    run_command(
        ["solidcraft-cli", "run", str(ctx.input_path), ...],
        cwd=ctx.work_dir,
    )
    return CheckOutcome.passed(
        artifacts=(ctx.output_dir / "native/model.sc",)
    )
~~~

Shared SolidCraft inspection/parsing/checking behavior belongs in this library.

Geometry expectations such as body counts, bounds, parameter values, mutation
targets and required views stay with the model in Forge and are passed into the
library as data.

The boundary is therefore:

- Forge knows **what this model should be**;
- this library knows **how to prove that against SolidCraft**;
- neither side duplicates the other's responsibility.

## 11. Relationship with CAD-CI

CAD-CI sees one ordinary consumer command:

~~~yaml
- id: model_verify
  run: [python, verify_model.py]
  outputs:
    - model_verify
~~~

CAD-CI owns whether that command runs. If it runs, this library owns only the
verification operation inside that command.

The library never reads `CAD_CI_*` variables itself. A consumer may use those
variables to construct `VerificationContext`.

## 12. Implementation order

1. requirements and this design;
2. immutable model/error types;
3. artifact evidence;
4. process helper;
5. sequential verification execution/report;
6. unit tests covering the acceptance list;
7. release only after independent tests pass;
8. only then consume from Forge.

Do not migrate Forge code into this repository before steps 1-7 are complete.


## 13. Geometry verification

### 13.1 Module

Add one module:

```text
cad_verification/
  geometry.py
```

It owns only generic mesh geometry verification.

### 13.2 Public immutable types

`geometry.py` defines frozen dataclasses:

```python
SurfaceDistanceProbe
GeometryContract
```

Their `__post_init__` methods normalize numeric vectors to float tuples and
raise `VerificationConfigError` for invalid configuration.

### 13.3 Mesh library

Use `trimesh>=4,<5` and `scipy>=1.12,<2` as explicit package dependencies. `scipy` is required by trimesh's validated topology-processing path used by the watertightness check.

`validate_mesh_geometry()` loads the supplied STL with trimesh.

If trimesh returns a Scene, concatenate measurable geometries into one mesh.

Reject:

- missing paths;
- empty files;
- load/parse failures;
- geometries without vertices or faces.

Those cases raise `MeshLoadError`, which derives from
`VerificationError`.

### 13.4 Measurements

The validator computes one evidence dictionary in deterministic insertion order.

Bounds:

- use mesh bounds directly;
- compare each min/max coordinate with the configured tolerance.

Volume:

- use absolute mesh volume;
- only evaluate when configured.

Watertightness:

- evaluate `is_watertight` on a copy of the mesh;
- do not mutate the mesh used for other measurements.

Surface probes:

- use trimesh nearest-surface calculation without consumer-specific policy;
- preserve contract probe order.

Contract sufficiency:

- `bounds_sufficient=True` allows a bounds-only contract;
- `bounds_sufficient=False` requires volume or at least one surface probe;
- this preserves the historical rule that internal-feature cases cannot pass
  solely because their outer envelope matches.

### 13.5 Mismatch handling

Do not raise on the first geometry mismatch.

Evaluate every configured geometry check, store all evidence, then raise one
`VerificationFailure` if any check failed.

This preserves passing evidence when a later check fails.

### 13.6 Existing verification integration

No changes to `verify()` semantics are required.

- `VerificationFailure` is already recorded as `fail`;
- `MeshLoadError` is an ordinary unexpected `VerificationError` and is
  recorded as `error`.

### 13.7 Public exports

Export from `cad_verification.__init__`:

```python
GeometryContract
SurfaceDistanceProbe
validate_mesh_geometry
MeshLoadError
```

### 13.8 Test construction

`tests/test_geometry.py` generates small mesh fixtures using trimesh.

The canonical fixture is a centered 10 x 20 x 30 mm box.

An open-box fixture removes one face from the generated mesh.

A disconnected multi-part fixture combines two generated boxes before STL
export.

Tests run through the built wheel using the existing library CI path.

## 14. Numeric and measured-body comparison

### 14.1 Module

Add one CAD-engine-neutral module:

```text
cad_verification/
  comparison.py
```

The generic comparison module accepts only Python numeric values, vectors and
normalized body envelopes. It remains independent of SolidCraft and Forge.

Engine-specific modules may depend on the public generic comparison API, but
must not embed Forge model knowledge.

### 14.2 BodyEnvelope

Expose one frozen `BodyEnvelope` dataclass containing:

- `minimum`: XYZ minimum;
- `maximum`: XYZ maximum;
- optional `label`.

Construction normalizes XYZ values to finite float tuples and rejects inverted
bounds. Labels are descriptive evidence only; bounds determine matching.

### 14.3 Scalar and vector comparison

Expose:

```python
compare_scalar(expected, actual, tolerance, *, label=None)
compare_vector(expected, actual, tolerance, *, label=None)
```

Both functions validate finite numeric input and a non-negative tolerance.

A passing comparison returns deterministic JSON-compatible evidence. A mismatch
raises `VerificationFailure` with exactly that evidence.

Vector comparison requires equal non-empty vectors and records per-element
absolute deltas plus the maximum delta.

### 14.4 Bounds comparison

Expose:

```python
compare_bounds(
    expected_min,
    expected_max,
    actual_min,
    actual_max,
    tolerance,
    *,
    label=None,
)
```

All four vectors are normalized as XYZ values. Expected and actual bounds must
not be inverted. Evidence records expected/actual min/max vectors, six absolute
coordinate deltas, maximum delta, tolerance and pass/fail.

### 14.5 Body-envelope matching

Expose:

```python
match_body_envelopes(expected, actual, tolerance)
```

Inputs contain `BodyEnvelope` values.

Matching is one-to-one and independent of actual input order:

1. normalize and canonically sort actual envelopes by label/bounds;
2. walk expected envelopes in their declared order;
3. for each expected envelope, choose the unmatched in-tolerance actual envelope
   with the smallest maximum bounds delta;
4. break equal-distance ties by canonical actual envelope order.

Evidence contains counts, matched pairs, unmatched expected envelopes, unmatched
actual envelopes and pass/fail. Any unmatched envelope raises one
`VerificationFailure` after the complete evidence has been built.

### 14.6 Existing verification integration

No change to `verify()` is required.

Consumers may return passing comparison evidence from a normal check. A raised
`VerificationFailure` is already mapped to check status `fail` and its
evidence is preserved in `verification.json`.

### 14.7 Public exports and tests

Export:

```python
BodyEnvelope
compare_scalar
compare_vector
compare_bounds
match_body_envelopes
```

Tests cover issue #8 R1-R6 and run through the installed wheel using the
repository's released `tool.py.lib.ci` path.

## 15. Visual regression and expected-shape evidence

### 15.1 Module and dependency

Add one generic module:

```text
cad_verification/
  visual.py
```

Declare Pillow explicitly. The module owns image normalization, baseline
payloads, regression metrics, generic orthographic projection and drawing. It
does not render CAD or know model/view names.

### 15.2 Normalized images

`normalize_image(path, width, height)` loads an image with Pillow, converts it
through RGB to grayscale, resizes with LANCZOS and returns a grayscale
`PIL.Image.Image` with the exact requested size.

Missing, unreadable or invalid images raise `VisualEvidenceError`, derived
from `VerificationError`. Width and height must be positive integers.

### 15.3 Baseline payloads

Expose deterministic baseline helpers using a JSON-compatible payload with:

- encoding: `raw`, `zlib` or `png`;
- width;
- height;
- base64 data.

`encode_baseline(image, encoding=...)` accepts a normalized grayscale image.
`decode_baseline(payload)` returns a grayscale image and validates dimensions
and byte count.

Raw and zlib forms encode grayscale bytes. PNG form encodes a deterministic
Pillow PNG byte stream.

### 15.4 Regression comparison

`compare_images(current, reference, ...)` requires same-size grayscale
images and computes:

- mean absolute pixel difference;
- changed-pixel fraction where absolute difference is greater than or equal to
  the caller-supplied changed-pixel threshold.

The caller supplies a maximum mean difference and maximum changed fraction.
Evidence records both metrics, thresholds and pass/fail. Metrics are rounded to
six decimal places for stable evidence. A mismatch raises
`VerificationFailure` with the complete evidence.

### 15.5 Difference image

`write_diff_image(current, reference, output_path)` creates one deterministic
RGB image with current grayscale information and absolute-difference
information visible side by side. The output is twice the normalized width and
keeps the same height.

### 15.6 Orthographic camera

Expose frozen `OrthographicCamera`:

- target XYZ;
- yaw degrees;
- pitch degrees;
- distance.

Distance is the orthographic half-height scale and must be positive. Projection
uses a stable camera basis. Exact top/bottom pitch uses a fallback up vector so
the basis remains valid.

`project_points(points, camera, width, height)` maps consumer-supplied 3D
points to image-space floats. Front orientation maps X right and Z up; top
orientation maps X right and Y up.

### 15.7 Expected geometry types

Expose frozen generic data types:

- `ExpectedBox(minimum, maximum, label=None)`;
- `ThroughHole(center, diameter, z_min, z_max, label=None)`;
- `ThroughSlot(start, end, width, z_min, z_max, label=None)`;
- `ThroughPathSlot(centerline, width, z_min, z_max, label=None)`.

All values are normalized to finite floats. Bounds/ranges must not be inverted.
Straight-slot start and end may not be identical. A path-slot centerline must
contain at least two XY points and may not contain identical neighbouring
points. Width/diameter must be positive.

### 15.8 Expected drawing

`draw_expected_geometry(image, camera, boxes=(), features=(), ...)` returns an
RGB image copy with deterministic outlines. It accepts only the generic types
above and rejects unknown feature objects.

Boxes draw projected edges. Through holes draw projected top/bottom circles and
their connecting side lines. Straight through slots draw projected capsule
outlines at both Z levels and connecting side lines.

A `ThroughPathSlot` computes one deterministic tangent-normal outline from the
consumer-supplied centerline. For each centerline point, the local normal is
derived from the vector between its previous and following neighbours (using
the endpoint itself at the path ends). The outline is the positive-offset path
followed by the reversed negative-offset path. Top/bottom path outlines, endpoint
circles, centerline and four vertical side connectors are projected and drawn.
A two-point `ThroughPathSlot` is geometrically equivalent to `ThroughSlot`.

Labels and translucent fill are optional generic presentation switches; tests do
not depend on fonts.

### 15.9 Goal and overlay

`make_goal_image(size, camera, ...)` creates a blank RGB image and draws only
consumer-supplied expected geometry.

`make_overlay_image(actual, camera, ...)` copies the actual render and draws
the same expected geometry over it, preserving unmodified actual pixels away
from expected geometry.

### 15.10 Visual view evidence

Expose frozen `VisualViewEvidence` containing:

- actual image reference or None;
- baseline status;
- optional regression evidence;
- optional diff image reference;
- goal image reference or None;
- overlay image reference or None;
- expected-shape status.

Its `to_evidence()` output is deterministic JSON-compatible evidence.
Missing baseline is represented explicitly as `missing`. Missing actual,
goal or overlay are represented independently and are not converted into pixel
mismatch.

### 15.11 Boundary and tests

The module must not import or invoke SolidCraft, CADCraft, Forge or a CAD
engine. It owns no required-view list, model camera, baseline or expected
geometry fixture.

Tests cover issue #9 R1-R10 through the installed wheel.

### 15.12 Single-view verification orchestration

Expose one additional generic function:

```python
verify_visual_view(
    actual_path,
    *,
    actual_reference,
    baseline_path=None,
    normalized_size,
    changed_pixel_threshold,
    max_mean_difference,
    max_changed_fraction,
    diff_path,
    diff_reference=None,
    camera=None,
    boxes=(),
    features=(),
    goal_path=None,
    goal_reference=None,
    overlay_path=None,
    overlay_reference=None,
)
```

The function operates on one already-rendered consumer image. It never renders
CAD and does not know a view name.

Behavior:

1. normalize `actual_path` with `normalize_image()`;
2. when `baseline_path` is absent or does not exist, set
   `baseline_status="missing"`, leave regression/diff evidence empty and do
   not create a baseline;
3. when a baseline exists, normalize it, write `diff_path`, then call
   `compare_images()`;
4. if regression fails, retain its evidence and continue composing optional
   goal/overlay evidence before raising one `VerificationFailure`;
5. when `camera` is supplied, at least one expected box/feature and both
   `goal_path` and `overlay_path` are required; create both through the
   existing generic drawing APIs;
6. when `camera` is absent, expected geometry and goal/overlay paths must also
   be absent, and `expected_shape_status="missing"`;
7. return one `VisualViewEvidence` on pass/missing-baseline;
8. on regression mismatch raise `VerificationFailure` with
   `VisualViewEvidence.to_evidence()` as failure evidence.

Evidence references are caller-controlled strings. The library never rewrites
them relative to a repository or output tree. If a produced artifact reference
is omitted, the corresponding evidence reference is `None`.

This function composes only existing visual primitives. It does not introduce a
view loop, required-view policy, model camera conversion, baseline approval or
CAD-engine adapter.

### 15.13 Single-view validation rules

- `normalized_size` contains two positive integers;
- `actual_reference` is a string or `None`;
- diff/goal/overlay references are strings or `None`;
- `diff_path` is required when an existing baseline is compared;
- expected geometry without a camera is invalid;
- a camera without expected geometry is invalid;
- a camera requires both goal and overlay output paths;
- invalid image paths/data retain `VisualEvidenceError` semantics from
  `normalize_image()`;
- invalid numeric/image/drawing configuration retains existing
  `VerificationConfigError` semantics.

Direct tests cover issue #26 without a consumer repository or CAD engine.

Issue #75 adds direct tests for path-slot configuration, two-point equivalence,
curved/polyline drawing, duplicate-neighbour rejection and use through
`verify_visual_view()`.

## 16. Semantic result composition

### 16.1 Module

Add one execution-free module:

```text
cad_verification/
  semantic.py
```

It composes consumer-supplied records and existing report data. It does not
execute checks, read repository state or move artifacts.

### 16.2 SemanticCheck

Expose frozen `SemanticCheck` with:

- `name`;
- `status`;
- `required`;
- optional `reason`;
- JSON-compatible `evidence`.

Names use the same lowercase engineering identifier rule as verification IDs.
Allowed statuses are:

`pass`, `fail`, `error`, `missing`, `review`, `blocked`,
`not-required`, `skipped`.

### 16.3 Composition

`compose_semantic_result(checks)` preserves supplied order and returns:

- overall `status`;
- ordered check records.

Only required checks determine overall status. Precedence is:

1. `error`;
2. `fail`;
3. `missing` -> overall `incomplete`;
4. `review`;
5. `blocked`;
6. otherwise `pass`.

Optional checks remain evidence but never lower the overall status.

### 16.4 Pass requirement

`require_semantic_pass(result)` accepts only a composed `pass` result.
Every other overall status raises `SemanticResultError`, a
`VerificationFailure` subclass carrying the complete semantic result as
evidence.

### 16.5 Aggregate

`compose_item_results(items)` accepts an ordered sequence of
`(item_id, semantic_result)` pairs. It does no work beyond validation and
composition.

Aggregate overall precedence is `error`, `fail`, `incomplete`, `review`,
`blocked`, then `pass`. Input item order is preserved.

### 16.6 Existing report adapter

`semantic_checks_from_report(report)` validates an existing
`cad-verification` report and maps its ordered rows:

- pass -> pass;
- fail -> fail;
- error -> error;
- skipped -> skipped.

The report row ID becomes the semantic check name. Row reason, evidence and
artifact records are preserved in the semantic evidence object. The adapter
does not invent paths or consumer policy.

### 16.7 Boundary and tests

The module contains no consumer-domain check names and no CAD-CI, publication,
materialization or repository-state behavior.

Tests cover issue #10 R1-R8 through the installed wheel.


## 17. Exact-value and predicate verification

### 17.1 Module

Add one engine-neutral module:

```text
cad_verification/
  assertions.py
```

It contains only generic expected/actual evidence and failure mechanics.

### 17.2 Public API

Expose:

```python
require_equal(expected, actual, *, label=None)
require_condition(condition, *, expected, actual, label=None)
```

Both return a JSON-compatible evidence object:

```json
{
  "label": "optional label or null",
  "expected": "...caller value...",
  "actual": "...caller value...",
  "pass": true
}
```

On failure the same object is attached to `VerificationFailure` with
`pass=false`.

### 17.3 Equality semantics

`require_equal()` performs exactly `actual == expected`. It does not
normalize numbers, apply tolerance, reorder collections or interpret CAD data.
Consumers use numeric comparison APIs when tolerance is required.

### 17.4 Predicate semantics

`require_condition()` requires `condition` to be exactly `bool`.
Truthiness of numbers, strings, containers or custom objects is rejected.

The consumer constructs the condition from model/domain semantics and supplies
the expected/actual evidence. The library does not inspect or understand that
semantic meaning.

### 17.5 Validation

Expected and actual values must serialize through deterministic
`json.dumps(..., sort_keys=True)`. Labels are `str | None`; empty strings
are allowed as literal descriptive values and are not interpreted.

Invalid inputs raise `VerificationConfigError`. A normal false result raises
`VerificationFailure`.

### 17.6 Boundary

The module must not import CAD libraries, Forge, SolidCraft, repository state,
CI code or publication code. It does not replace toleranced comparison helpers
or semantic-result composition.

Direct built-wheel tests cover issue #29.


## 18. CAD-tool adapter architecture

### 18.1 Package structure

CAD-tool-specific verification lives below:

```text
cad_verification/
  adapters/
    __init__.py
    solidcraft.py
```

Future OpenSCAD, FreeCAD or other adapters use sibling modules. They are added
only when a consumer requires them.

Generic modules such as `comparison.py` and `assertions.py` remain
CAD-tool independent. Adapter modules may call those generic APIs.

### 18.2 Public SolidCraft types

The initial SolidCraft adapter exposes immutable expectation types:

```python
SolidCraftModelExpectation
SolidCraftBodyExpectation
SolidCraftTimelineExpectation
SolidCraftSketchExpectation
```

`SolidCraftModelExpectation` contains only model-specific expected data. It
does not contain callables.

Body-envelope expectations use the existing `BodyEnvelope` type and one
caller-supplied bounds tolerance.

A named-body expectation selects exactly one SolidCraft body by native-name
prefix and may request:

- expected bounds with a tolerance;
- expected volume with a tolerance;
- exact sheet-metal state;
- exact closed/open state.

A timeline expectation contains semantic fields exposed by SolidCraft.
Feature type is always checked. Name/error/warning each have an explicit check
flag. Generated names are ignored unless `check_name=True`; error and warning
checks default to enabled.

A sketch expectation identifies one sketch by name and may request profile
count, curve count and solver status.

### 18.3 SolidCraft evidence normalization

The adapter validates and normalizes the measurement object before performing
requested comparisons.

Required structure is checked only when the corresponding expectation needs it.
When body verification is requested, `bodies` must be a list and each used
body must contain a valid `bbox.min` and `bbox.max`.

When parameter verification is requested, `params` must be a list of rows
with string `name` and finite numeric `value`.

Timeline/sketch verification follows the same rule: malformed requested
evidence raises `SolidCraftEvidenceError`, derived from `VerificationError`.

No malformed row is silently skipped.

### 18.4 Measurement verification

Expose:

```python
verify_solidcraft_measurements(measurements, expectation)
```

The function builds deterministic section evidence in this order:

1. body count;
2. body envelopes;
3. parameters;
4. named bodies;
5. timeline;
6. sketches.

Only sections present in the expectation are evaluated.

Implementation reuses:

- `match_body_envelopes()`;
- `compare_bounds()`;
- `compare_scalar()`;
- `require_equal()`;
- `require_condition()` where required.

A comparison mismatch remains `VerificationFailure`. Schema/parse errors are
`SolidCraftEvidenceError`.

### 18.5 SolidCraft command functions

Expose:

```python
evaluate_solidcraft_model(model_path, destination)
mutate_solidcraft_model(model_path, command_path, destination)
inspect_solidcraft_model(model_path, command_path, destination)
```

The exact commands are:

```text
solidcraft-cli eval <model> --json-out <destination>
solidcraft-cli run <command> --in <model> --param-check strict --save <destination>
solidcraft-cli run <command> --in <model> --param-check strict --results --json-out <destination>
```

All processes go through `run_command()`.

JSON produced by evaluate/inspect is loaded by the adapter. Invalid JSON or an
unexpected top-level shape is a `SolidCraftEvidenceError`.

### 18.6 Consumer boundary

Forge keeps declarations such as:

```python
SolidCraftModelExpectation(
    bodies=(...model-specific expected bounds...),
    parameters={...model-specific expected values...},
    timeline=(...model-specific expected features...),
)
```

Forge does not parse `bodies[].bbox`, `params`, `timeline` or
`sketches` and does not implement shared SolidCraft eval/mutate/inspect
helpers.

The SolidCraft adapter does not compile Forge/SCPF source and does not import
Forge. Initial Forge-to-SolidCraft replay remains a producer concern before the
adapter verifies the produced native design.

### 18.7 Tests

Direct built-wheel tests prove:

- valid body/parameter/timeline/sketch expectations pass;
- numeric mismatches produce `VerificationFailure`;
- malformed requested SolidCraft evidence produces
  `SolidCraftEvidenceError`;
- malformed bodies are never skipped;
- named-body selection requires exactly one match;
- command argv for evaluate/mutate/inspect is exact;
- the adapter imports no Forge/SCPF, SCons or CAD-CI implementation.


## 19. Declarative SolidCraft verification runner

### 19.1 Location

The orchestration remains part of the SolidCraft adapter package:

```text
cad_verification/
  adapters/
    solidcraft.py
```

It composes the already released adapter functions and the generic
`VerificationContext` / `VerificationCheck` / `verify()` mechanism. It
does not introduce a second verification framework.

### 19.2 Public definitions

Expose frozen dataclasses:

```python
SolidCraftSavedDesign(
    id,
    command_path,
    expectation,
)

SolidCraftInspection(
    id,
    command_path,
    expected=None,
)

SolidCraftVerification(
    verification_id,
    baseline,
    saved_designs=(),
    inspections=(),
    metadata={},
)
```

IDs use the existing verification identifier grammar. Duplicate saved-design
or inspection IDs are rejected. The generated check IDs are:

- `baseline`;
- `saved_design_<id>`;
- `inspection_<id>`.

The two generated namespaces are independent.

### 19.3 Output layout

Given `output_dir`, the runner owns:

```text
<output_dir>/
  baseline/
    measurements.json
  saved_designs/
    <id>/
      model.sc
      measurements.json
  inspections/
    <id>/
      results.json
  verification.json
```

All produced paths are therefore valid normal verification artifacts.

### 19.4 Baseline check

The baseline check calls:

```python
evaluate_solidcraft_model(model_path, baseline/measurements.json)
verify_solidcraft_measurements(measurements, definition.baseline)
```

It returns one passing `CheckOutcome` with the expectation evidence and
measurement artifact.

### 19.5 Saved-design checks

Each saved-design check captures only immutable definition data.

It calls:

```python
mutate_solidcraft_model(
    original_model,
    command_path,
    saved_designs/<id>/model.sc,
)
evaluate_solidcraft_model(
    saved_model,
    saved_designs/<id>/measurements.json,
)
verify_solidcraft_measurements(measurements, expectation)
```

The changed model and measurements are artifacts.

Every saved-design check starts from the original model path. A previous
mutation is never an implicit input to the next mutation.

### 19.6 Inspection checks

Each inspection check calls:

```python
inspect_solidcraft_model(
    original_model,
    command_path,
    inspections/<id>/results.json,
)
```

When `expected` is not `None`, it compares the returned JSON value with
`require_equal(expected, actual, label=...)`.

The result JSON is always an artifact.

### 19.7 Runner

`run_solidcraft_verification(model_path, output_dir, definition)` normalizes
the two paths, builds `VerificationContext` with the supplied model as
`input_path`, creates the ordered checks, and delegates execution/reporting to
`verify()`.

Check order is:

1. baseline;
2. saved designs in declared order;
3. inspections in declared order.

The runner itself contains no Forge/SCPF or CAD-CI behavior.

### 19.8 Consumer shape

A normal consumer model should need only a small definition module, for
example:

```python
VERIFICATION = SolidCraftVerification(
    verification_id="simple-box",
    baseline=SolidCraftModelExpectation(...),
    saved_designs=(
        SolidCraftSavedDesign(
            id="length_50",
            command_path=...,
            expectation=SolidCraftModelExpectation(...),
        ),
    ),
)
```

The consumer-specific launcher may produce the initial `.sc` model and then
call the runner. It must not copy the baseline/mutation/inspection execution
logic.


## 20. Partial timeline projection

`SolidCraftTimelineExpectation` fields are:

```python
feature_type: str
name: str | None = None
check_name: bool = False
error: str | None = None
check_error: bool = True
warning: str | None = None
check_warning: bool = True
```

Configuration validation rejects a non-null value for a field whose check flag
is false.

`evidence()` returns only fields that participate in comparison, always
starting with `type`.

During `verify_solidcraft_measurements()`:

1. normalize all actual SolidCraft timeline rows with the existing strict
   schema validation;
2. require actual row count to equal expected row count;
3. for each expected row, project the actual row to exactly the keys returned
   by that expectation's `evidence()`;
4. compare the ordered expected/projected lists with `require_equal()`.

The adapter therefore remains strict about timeline structure and order while
allowing the consumer to omit unstable fields from its model contract.


## Lazy optional public exports

The package root eagerly imports the lightweight core, comparison, semantic and
SolidCraft adapter APIs.

Geometry and visual exports are registered in one private lazy-export map:

```text
public name -> implementation module -> implementation attribute
```

Module-level `__getattr__` resolves one lazy name with
`importlib.import_module()`, caches the resolved object in module globals and
returns it. `__all__` remains unchanged so the public API surface is stable.
`__dir__` includes lazy names for normal introspection.

This design means:

```text
from cad_verification import SolidCraftVerification
  -> no geometry import
  -> no visual import

from cad_verification import GeometryContract
  -> load cad_verification.geometry on demand

from cad_verification import ExpectedBox
  -> load cad_verification.visual on demand
```

The package dependency declaration is not changed by this release. Runtime
packaging decisions remain outside this library.


## Partial SolidCraft parameter matching

`SolidCraftModelExpectation` adds one explicit parameter matching setting:

```python
parameter_match: str = "exact"
```

Supported values are `exact` and `subset`.

The existing parameter normalization helper remains authoritative and always
parses the complete actual `params` list first. Matching changes only after
that strict normalization succeeds.

For exact matching:

```text
expected mapping
  vs
complete normalized actual mapping
```

using the existing `require_equal()` path.

For subset matching:

```text
requested names
  -> project normalized actual mapping to names that are present
  -> require_equal(expected requested mapping, projected actual mapping)
```

A requested-but-missing name therefore appears as an absent key in actual
comparison evidence and produces a normal `VerificationFailure`. Unrelated
actual keys never enter subset evidence.

No consumer callback, predicate or custom parser is introduced.


## Partial SolidCraft sketch matching

`SolidCraftSketchExpectation` keeps `name` required and changes:

```python
profiles: int | None = None
curves: int | None = None
status: str | None = None
```

Construction validates each supplied property with its existing field
normalizer and rejects a definition where all three are `None`.

`evidence()` projects only the declared fields:

```text
name + declared expectation fields
```

During measurement verification, the adapter first performs the existing strict
exact-one match by sketch name. It then reads only the fields present in the
expectation projection and normalizes those requested actual values before
`require_equal()`.

No wildcard sketches, consumer predicates or existence-only mode are added.


## SolidCraft count projections

Count expectations are projections over already normalized SolidCraft evidence.

`sketch_count` uses the length of the SolidCraft `sketches` list.

`timeline_type_counts` counts normalized timeline rows by their required
`type` field, then projects only configured type keys:

```text
requested type -> actual count (0 when absent)
```

`face_type_counts` is evaluated inside the existing exact-one named-body
selector. The matched body's `face_types` value must be a mapping. Requested
keys are normalized as count values; an omitted requested key is zero.
Unrequested face-type keys are neither validated as contract values nor included
in comparison evidence.

All three use deterministic sorted mappings and the existing
`require_equal()` mismatch semantics. No consumer predicates or complete-map
requirements are introduced.


## SolidCraft body groups

Add:

```python
@dataclass(frozen=True)
class SolidCraftBodyGroupExpectation:
    name_prefix: str
    count: int
    body_envelopes: tuple[BodyEnvelope, ...] | None = None
    bounds_tolerance: float = 0.0
```

`SolidCraftModelExpectation.body_groups` is a tuple of those definitions.

The adapter reuses the same validated body rows/names as named-body matching.
For each group it:

1. selects all body rows whose name starts with `name_prefix`;
2. records the matched names;
3. applies `require_equal(expected_count, actual_count)`;
4. when configured, converts only matched rows to `BodyEnvelope` and calls the
   existing `match_body_envelopes()`.

This is deliberately separate from `SolidCraftBodyExpectation`, whose
exact-one match remains useful and backward compatible for per-body volume,
face-type, sheet-metal and closed checks.


## Projected SolidCraft inspections

Add two data-only public types:

```python
@dataclass(frozen=True)
class SolidCraftInspectionSelect:
    field: str
    value: JSONScalar

@dataclass(frozen=True)
class SolidCraftInspectionCheck:
    id: str
    path: tuple[str | int | SolidCraftInspectionSelect, ...] = ()
    expected: Any = <unset>
    tolerance: float | None = None
    count: int | None = None
```

`SolidCraftInspection` gains:

```python
checks: tuple[SolidCraftInspectionCheck, ...] = ()
```

Whole-result `expected` and projected `checks` are mutually exclusive.

### Path resolution

Starting with the loaded inspection JSON:

- a string segment requires the current value to be an object and the key to
  exist;
- an integer segment requires an array and an in-range non-negative index;
- a selector requires an array of objects containing the selector field,
  filters rows by exact scalar equality, requires exactly one match and
  continues from that object.

The normalized path stored in evidence represents a selector as:

```json
{"select": {"field": "definition", "value": "Frame"}}
```

This keeps evidence JSON-compatible and deterministic.

### Check execution

For `count`, the resolved value must be an array or object and
`require_equal()` compares its length.

For exact `expected` without tolerance, use `require_equal()`.

For tolerant numeric scalar expected values, use the existing
`compare_scalar()`.

For tolerant flat numeric vectors:

1. validate actual as a JSON array of the same length;
2. normalize every element as finite numeric data;
3. compute per-element absolute differences and the maximum difference;
4. use `require_condition()` with deterministic expected/actual evidence
   containing value, tolerance and maximum difference.

Projected checks execute in declaration order and produce a stable evidence
list. The raw result remains only in `inspections/<id>/results.json`.

This path/selector mechanism is generic JSON structure handling. It has no
knowledge of BOM rows, sheet metal, component names or any Forge model.


## Sole SolidCraft body selector

Extend the existing body expectation without adding a second property schema:

```python
@dataclass(frozen=True)
class SolidCraftBodyExpectation:
    name_prefix: str | None = None
    ...
```

Existing positional and keyword calls with a string remain unchanged.

Verification chooses one of two selector paths:

```text
name_prefix is str
  -> validate body names
  -> select names starting with prefix
  -> require exactly one match

name_prefix is None
  -> do not read body names
  -> require len(validated body rows) == 1
  -> select bodies[0]
```

The common property-check path then applies bounds, volume, face-type counts,
sheet-metal and closed expectations exactly as before.

Evidence uses:

```json
{"selector": "sole", ...requested property evidence...}
```

for the sole selector. It does not include a body name. Named selection keeps
the existing `name_prefix` and actual `body_name` evidence.

Comparison labels use `sole body` for the unnamed selector and the configured
prefix for named selection.

This preserves the existing error boundary: malformed requested body
properties are evidence errors; selector count mismatches are normal
verification failures. Sole selection intentionally does not validate the
incidental `name` field.


## SolidCraft additional measured fields

Issue #69 extends the existing data-only expectation objects without adding a
new checker type.

`SolidCraftBodyExpectation` adds:

```python
face_count: int | None = None
center_of_mass: tuple[float, float, float] | None = None
center_of_mass_tolerance: float = 0.0
```

`SolidCraftSketchExpectation` adds:

```python
dof: int | None = None
```

Configuration normalization reuses the adapter's existing finite-number,
non-negative tolerance and non-negative integer validators. Center of mass is
normalized to an exact three-value float tuple.

During body verification the adapter reads `faces` only when `face_count` is
requested and reads `center_of_mass` only when that vector is requested.
Face count uses exact equality. Center of mass uses the existing numeric-vector
comparison semantics and the caller-supplied tolerance.

During sketch verification the adapter reads `dof` only when requested and
uses exact integer equality.

Evidence mirrors the existing sparse expectation model: omitted fields are not
validated and do not appear in expected/actual evidence. This prevents
incidental SolidCraft fields from becoming part of a model contract.


## Sparse center-of-mass projection

Issue #71 refines the 0.13.0 center-of-mass expectation without changing the
SolidCraft measurement schema.

The configuration type becomes:

```python
tuple[float | None, float | None, float | None] | None
```

Normalization preserves `None` and validates only numeric components. An
all-`None` tuple is invalid.

For a full XYZ expectation, verification retains the existing vector-comparison
path and evidence shape.

For a sparse expectation, verification projects the requested axes from the
SolidCraft `center_of_mass` array and compares each requested component with
the existing scalar comparison helper. Omitted components are not passed
through numeric evidence validation. This prevents incidental Y/Z data from
becoming part of an X-only model contract.


## Saved-design numeric change projection

Issue #73 adds one data-only relation to the existing
`SolidCraftSavedDesign` definition:

```python
@dataclass(frozen=True)
class SolidCraftMeasurementChangeExpectation:
    id: str
    path: tuple[str | int, ...]
    minimum_absolute_delta: float

@dataclass(frozen=True)
class SolidCraftSavedDesign:
    id: str
    command_path: Path
    expectation: SolidCraftModelExpectation
    changes: tuple[SolidCraftMeasurementChangeExpectation, ...] = ()
```

The baseline check continues to write
`baseline/measurements.json` before saved-design checks execute. A saved-design
check with relations loads that existing artifact through the adapter's strict
JSON loader; it does not call SolidCraft again for the baseline.

Path resolution is deliberately smaller than projected inspection selection:
only object-key strings and non-negative list indexes are allowed. This is
sufficient for stable SolidCraft measurement paths and avoids adding selectors
or consumer callbacks to mutation relations.

For each relation the adapter resolves the same path against baseline and
mutated measurement objects, normalizes both as finite numbers, computes
`abs(mutated - baseline)`, then uses the existing generic condition assertion
with the strict `>` threshold.

Existing absolute `SolidCraftModelExpectation` verification runs first for the
mutated model. Relation evidence is then added under a separate
`changes` collection. Definitions without `changes` preserve their existing
evidence shape.

## Reusable base verification loaders and runners

Issue #79 removes the remaining generic verification launcher knowledge from
consumer repositories without introducing a second orchestration framework.

### Geometry contract loading

`cad_verification.geometry` adds:

```python
geometry_contract_from_mapping(data) -> GeometryContract
load_geometry_contract(path) -> GeometryContract
```

The mapping function validates the schema-1 public file shape and constructs the
existing `SurfaceDistanceProbe` and `GeometryContract` objects. It rejects
unknown fields so misspelled verification policy cannot silently become
unverified policy.

The file loader performs one direct UTF-8 JSON read and delegates all semantic
validation to the mapping function and existing dataclass validators. It performs
no repository discovery.

### Mesh runner

`cad_verification.geometry` also adds:

```python
run_mesh_geometry_verification(
    mesh_path,
    output_dir,
    contract,
    *,
    verification_id,
) -> dict
```

It constructs one normal `VerificationContext` and one
`VerificationCheck("geometry", ...)`. The check returns
`CheckOutcome.passed(evidence=validate_mesh_geometry(...))`.

The existing `verify()` function remains the only report/status engine. No new
pass/fail/error mapping is introduced.

Geometry APIs remain lazy exports from the package root, preserving the current
optional heavy-import boundary.

### SolidCraft definition runner

`cad_verification.adapters.solidcraft` adds:

```python
load_solidcraft_verification(path) -> SolidCraftVerification
run_solidcraft_verification_file(
    model_path,
    output_dir,
    definition_path,
) -> dict
```

The loader uses `runpy.run_path()`, reads only the global `VERIFICATION`, and
requires that value to be a `SolidCraftVerification`. The runner then delegates
unchanged to `run_solidcraft_verification()`.

This keeps model-specific Python configuration in the consumer while removing
consumer-owned generic loading/status glue.

### Performance boundary

These APIs execute inside an already-selected Python/CAD runtime. They do not
select or launch Docker, inspect Git, scan a repository or create a batch
scheduler. CAD-CI may call them inside an existing shared runtime batch without
adding another process/container start.

