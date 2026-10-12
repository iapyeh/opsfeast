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

`test_rename.py` verifies the new CLI in an isolated checkout, old registry/definition preservation, schema-1 locator upgrades, reuse of registered roots, mixed-generation conflicts, invalid legacy definitions, dangling symlink rejection and explicit filename migration. Fixtures and subprocess checkouts are temporary and synthetic; no real user environment is changed.

## Recipe inspection tests

`test_recipe_inspection.py` covers read-only discovery without profile access, requested/planned/tested coverage gaps, full match-condition retention, unsupported runner IDs, missing/version-mismatched/invalid entrypoints, descriptor/entrypoint symlink escapes, malformed-recipe continuation, path semantics, concise default output, requested-platform focus/constraints, opt-in full details and CLI status/output. Synthetic entrypoints contain a raising top-level statement to prove inspection never executes them. The bundled inventory descriptor is also inspected with the existing static validator. No host is contacted.

## Recipe source and input tests

`test_recipe_sources.py` covers checkout/profile/external references, entry-only registrations and includes, home/relative roots, path and descriptor symlink escapes, directory/glob expansion, namespaced IDs, shorthand/mapping items, default/source/host vars with first-match precedence, deep-copy/shallow overlays, typed bounds, disabled/missing sources, disabled hosts/jumps, exact CLI exclusions and empty selections. Full inventory execution uses mocked Sessions; no dependencies are installed and no external host is contacted.

## Inventory and runner tests

Runner progress tests cover automatic stdout TTY detection, verbose/quiet overrides, JSON separation, failed-host continuation with sanitized error types, collection stages, waiting heartbeats without sleeping, and worker/context cleanup on failure. Parallel tests additionally cover the worker limit, actual overlap, CPU-based default/cap/fallback, sequential mode, rejected --thread alias, out-of-order completion with ordered JSON, failure/context isolation, and separate Sessions, host facts and result files through the complete runner. All collection uses synthetic sessions; no network connections are made.

`test_host_selection.py` covers optional/scalar/list group memberships, unchanged dump representation, rejected former groups keys, invalid group types, cross-include union ordering, duplicate removal, explicit --host/--group kinds, unknown-target rejection before execution, all-host selection including local/jump/ungrouped hosts, empty inventory, root/profile forwarding, leading/flag recipe syntax, required recipe/targets, invalid option combinations, single-host output and batch continuation after failures. Fixtures are temporary and synthetic; runner execution is mocked and no host is contacted.

`test_inventory_system.py` covers Linux synthetic outputs, safe os-release parsing, missing-file fallback, permission denial, unsupported platforms, command and transport failures, timeout partial output, strict cleanup, recipe selection and manifest/version validation, output symlink rejection and repeated result preservation. These tests never contact SSH targets. The legacy Linux collector unsupported-platform path remains covered; SSHScript 5.0.0 credential-free quickstart was checked locally; full Linux/FreeBSD and SSH collection remain unverified. macOS now has a collector with separate local read-only validation.

CLI recipe selection tests cover `--recipe` precedence, absent/empty host selections, invalid host selections bypassed by a valid override, management-root relative paths with includes, absolute paths, invalid overrides without fallback, recipe/descriptor symlink escapes, and CLI argument forwarding.

Checkout recipe tests cover execution without instance copies, included YAML selection, directory/glob expansion, duplicate selection, explicitly selected custom implementations and stale instance copies, separate include and recipe boundaries, and result paths within the instance. Legacy custom copies use explicit `./recipes/...` paths.

Management-directory discovery tests cover default and custom initialization, shared default selection in both CLIs, explicit overrides, definition preservation, invalid locators/definitions and missing registered directories without fallback, and failed init preserving the previous default. All instances and locators use temporary directories.

`test_setup_tools.py` verifies environment scope and import/distribution mismatches, full skill candidate/provenance preservation, read-only comparisons, local changes and incompatible contracts, failed downloads, existing destinations, failed writes, unsafe ZIP paths/links/duplicates and expansion limits. It uses synthetic ZIPs and mocked network responses; it never installs packages or changes schedulers. Public bundle check/download CLI verification is reported separately.

`test_profiles.py` verifies named/default/path initialization, registration of existing and legacy directories without changes, name conflicts and suggested names, interactive selection/cancellation, noninteractive failure, explicit profile selection in both CLIs, sibling boundaries, separate result locations, schema 1 compatibility and atomic write failure. All directories and Sessions are temporary or mocked.

Result summary tests cover detected kernels, reasons and messages for success, partial, unsupported and failed runs, cleanup-error precedence, and equality between CLI summaries and saved reports. CLI short paths select checkout recipes and bare `recipes/` prefixes are rejected before connecting with a correction hint; explicit `./` paths retain management-root semantics.

`test_host_runtime.py` covers platform facts, cache refresh/invalidation, target changes, su/sudo identities, independent/repeated chains, credential precedence and account-password fallback, host credential scope, empty/null/invalid credentials, no retry after rejected overrides, missing credentials, test-host aggregation, safe diagnostic flags/tracebacks, three-platform runner dispatch, implementation versions and batch continuation. All account/SSH tests are synthetic; no real privileged accounts are tested.

Identity-output tests cover CLI success explanations without credential disclosure, expected/actual UID evidence on mismatch, incomplete target lookup, same-UID account aliases, separate prerequisite su/final sudo evidence, not-run entry/skipped checks, and failed parent restoration. These use synthetic consoles and do not establish native su/sudo behavior.

_Last modified: 2026-10-12_
