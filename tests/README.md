# Tests

This directory will contain public, reproducible verification for recipes, data contracts, and operational workflows.

Verification should cover result parsing, failure status, supported platforms, and repeated updates that preserve human notes. Tests and fixtures must use synthetic data rather than private host details or credentials.

## Configuration utility tests

With Python 3.11+ and PyYAML installed, run:

```sh
python -B -m unittest discover -s tests -p 'test_*.py'
```

`test_opsfeast.py` checks connection-test credential/key/jump mapping, fixed commands, failure reporting and cleanup with mocked Sessions, per-hop diagnostics, credential omission and frames-only tracebacks, JSON dumps of merged and nested settings, dump error handling, initialization preservation, cross-file references, duplicate definitions, include and jump-host cycles, recipe selection, and path boundaries using temporary directories and synthetic values. The default tests do not contact hosts; real connection tests are invoked separately with `test-connection`.

## Rename compatibility tests

`test_rename.py` verifies both CLI entrypoints and the shared import alias, old registry/definition preservation, schema-1 locator upgrades, reuse of registered roots, mixed-generation conflicts, invalid legacy definitions, dangling symlink rejection and explicit filename migration. Fixtures and subprocess checkouts are temporary and synthetic; no real user environment is changed.

## Recipe inspection tests

`test_recipe_inspection.py` covers read-only discovery without profile access, requested/planned/tested coverage gaps, full match-condition retention, unsupported runner IDs, missing/version-mismatched/invalid entrypoints, descriptor/entrypoint symlink escapes, malformed-recipe continuation, path semantics, concise default output, requested-platform focus/constraints, opt-in full details and CLI status/output. Synthetic entrypoints contain a raising top-level statement to prove inspection never executes them. The bundled inventory descriptor is also inspected with the existing static validator. No host is contacted.

## Inventory and runner tests

`test_inventory_system.py` covers Linux synthetic outputs, safe os-release parsing, missing-file fallback, permission denial, unsupported platforms, command and transport failures, timeout partial output, strict cleanup, recipe selection and manifest/version validation, output symlink rejection and repeated result preservation. These tests never contact SSH targets. The legacy Linux collector unsupported-platform path remains covered; SSHScript 5.0.0 credential-free quickstart was checked locally; full Linux/FreeBSD and SSH collection remain unverified. macOS now has a collector with separate local read-only validation.

CLI recipe selection tests cover `--recipe` precedence, absent/empty host selections, invalid host selections bypassed by a valid override, management-root relative paths with includes, absolute paths, invalid overrides without fallback, recipe/descriptor symlink escapes, and CLI argument forwarding.

Checkout recipe tests cover execution without instance copies, included YAML selection, directory/glob expansion, duplicate selection, explicitly selected custom implementations and stale instance copies, separate include and recipe boundaries, and result paths within the instance. Legacy custom copies use explicit `./recipes/...` paths.

Management-directory discovery tests cover default and custom initialization, shared default selection in both CLIs, explicit overrides, definition preservation, invalid locators/definitions and missing registered directories without fallback, and failed init preserving the previous default. All instances and locators use temporary directories.

`test_setup_tools.py` verifies environment scope and import/distribution mismatches, full skill candidate/provenance preservation, read-only comparisons, local changes and incompatible contracts, failed downloads, existing destinations, failed writes, unsafe ZIP paths/links/duplicates and expansion limits. It uses synthetic ZIPs and mocked network responses; it never installs packages or changes schedulers. Public bundle check/download CLI verification is reported separately.

`test_profiles.py` verifies named/default/path initialization, registration of existing and legacy directories without changes, name conflicts and suggested names, interactive selection/cancellation, noninteractive failure, explicit profile selection in both CLIs, sibling boundaries, separate result locations, schema 1 compatibility and atomic write failure. All directories and Sessions are temporary or mocked.

Result summary tests cover detected kernels, reasons and messages for success, partial, unsupported and failed runs, cleanup-error precedence, and equality between CLI summaries and saved reports. CLI short paths select checkout recipes and bare `recipes/` prefixes are rejected before connecting with a correction hint; explicit `./` paths retain management-root semantics.

`test_host_runtime.py` covers platform facts, cache refresh/invalidation, target changes, su/sudo identities, independent/repeated chains, missing credentials, test-host aggregation, three-platform runner dispatch, implementation versions and batch continuation. All account/SSH tests are synthetic; no real privileged accounts are tested.

_Last modified: 2026-10-12_
