# Tests

This directory will contain public, reproducible verification for recipes, data contracts, and operational workflows.

Verification should cover result parsing, failure status, supported platforms, and repeated updates that preserve human notes. Tests and fixtures must use synthetic data rather than private host details or credentials.

## Inventory access and partitioned data

`test_inventory_access.py` covers canonical sudo-password presence/null/empty/control values, strict quoted sudo disabling, root/passwordless/default modes, whole-batch rejection, dryrun/check-access without collection or writes, force skip/fallback without alternate-password retries, collection-time rejection, unknown restoration/cleanup, platform parser units and empty/zero/missing values, output/time budgets, retention/exchange and CSV formula escaping. Sessions and credentials are synthetic; no native SSH/sudo or real-host extended inventory is exercised. Existing routing tests explicitly mock the new access boundary; retained integration uses a synthetic UID or explicit ordinary-account policy. Optional fields do not change the seven-field completion rules.

## Configuration utility tests

With Python 3.11+ and PyYAML installed, run:

```sh
python -B -m unittest discover -s tests -p 'test_*.py'
```

`test_opsfeast.py` checks connection-test credential/key/jump mapping, fixed commands, failure reporting and cleanup with mocked Sessions, per-hop diagnostics, credential omission and frames-only tracebacks, JSON dumps of merged and nested settings, dump error handling, initialization preservation, cross-file references, duplicate definitions, include and jump-host cycles, recipe selection, and path boundaries using temporary directories and synthetic values. The default tests do not contact hosts; real connection tests are invoked separately with `test-connection`.

## First-use onboarding tests

`test_onboarding.py` validates every complete YAML example in the first-host guide without connecting, checks that initialization labels synthetic hosts, and tests the optional activation helper in installed Bash/Zsh shells. Temporary paths include spaces; cases cover another working directory, missing environments, failed activation and rejected direct execution with a quoted source command. Interactive-shell cases cover noisy directory-change hooks, shell function overrides and an inherited Bash marker in Zsh; missing-environment diagnostics show the expected path. The activation fixture is synthetic: no dependencies are installed and no existing environment is modified.

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

`test_profiles.py` verifies named/default/path initialization, attach registration of existing and legacy directories without changes, name conflicts and suggested names, interactive selection/cancellation, noninteractive failure, explicit profile selection in both CLIs, sibling boundaries, separate result locations, schema 1 compatibility and atomic write failure. Detach cases cover data preservation/reattachment, protected main, unknown names, missing/nondefault directories, atomic main fallback, missing/unregistered/invalid main, entry symlink escapes, active legacy registry retention, write rollback, removed add alias and read-only basic profile status. All directories and Sessions are temporary or mocked.

Result summary tests cover detected kernels, reasons and messages for success, partial, unsupported and failed runs, cleanup-error precedence, and equality between CLI summaries and saved reports. CLI short paths select checkout recipes and bare `recipes/` prefixes are rejected before connecting with a correction hint; explicit `./` paths retain management-root semantics.

`test_host_runtime.py` covers platform facts, cache refresh/invalidation, target changes, su/sudo identities, independent/repeated chains, credential precedence and account-password fallback, host credential scope, empty/null/invalid credentials, no retry after rejected overrides, missing credentials, test-host aggregation and enabled passwordless policy, safe diagnostic flags/tracebacks, three-platform runner dispatch, implementation versions and batch continuation. All account/SSH tests are synthetic; no real privileged accounts are tested.

Identity-output tests cover CLI success explanations without credential disclosure, expected/actual UID evidence on mismatch, incomplete target lookup, same-UID account aliases, separate prerequisite su/final sudo evidence, not-run entry/skipped checks, and failed parent restoration. These use synthetic consoles and do not establish native su/sudo behavior.

## Retained observations, identity and exchange

test_result_data.py verifies non-root probes, explicit sudo capability/override policy, root entry/restoration and secret-safe failures, Linux machine-id hashing, FreeBSD/macOS/ESXi device evidence, fallback warnings, automatic runner retention, stage-2 recovery, raw/receipt replay, partial/excluded states, source isolation, no historical reassignment, concurrent insertion, database/schema/path safeguards, SQL inventory view, filtered UTC export, strict exchange validation, two-source combination and content conflicts. All targets, credentials and command outputs are synthetic. No real SSH, sudo, ESXi or serial-number collection occurs. Contracts and example exchanges receive structural/semantic checks; the full suite remains the delivery check.

HostMetadataTests additionally covers exact user-assigned keys across independent sources, native-identity precedence, duplicate/configuration rejection, Unicode/multiline display metadata, source label preservation, key/identity validation and version-1 database upgrades without changing historical records or source identity.

## Recipe discovery, reports, artifacts, bundles and jobs

`test_recipe_experience.py` uses synthetic JSON, temporary independent Feasts and mocked host execution. It covers multi-source discovery, static signatures/IDs/conflicts, disabled/missing/escaping sources, filters and plain HTML; offline report execution without SSH, parameter/input/result/artifact validation, unknown/failed data and source times/quality, escaping and output integrity; raw result paths/index errors; explicit-file bundle allowlists/digests/unsafe entries/limits/candidate boundaries and cross-Feast reuse; saved invocation reruns, drift and private binding preservation. No real dataset, host, model, scheduler or Exchange is used. Existing operation suites verify compatibility through the delegated runner.

## OpsFeast home

`test_landing_ui.py` verifies empty-argument routing, TTY/dependency checks, version/download receipts with timezone and overwrite/symlink rejection, recursive credential masking without original-data mutation, include/source loading and safe malformed-YAML errors, and shared profile validation. Headless tests cover first-visit keyboard navigation across the six sections, mouse selection, grouped docked Tree sidebar layout, scalar/multiple/duplicate/ungrouped memberships, identical masked settings across duplicate host leaves, first-entry/return Up/Down host selection and detail updates at two terminal sizes without mouse/Tab focus, Enter-triggered profile switching/host refresh and preservation of explicit recipe environment fields. Data and profile writes are temporary or mocked; no real connections/credentials are used. Existing profile tests verify atomic write-failure preservation.

## Host action dialogs

`test_host_actions.py` validates literal argv construction with exact host/root binding, no implicit all-host execution, structured progress/stderr and nonzero subprocess exit codes. Headless tests exercise Enter on a host, the three SelectionList actions, cancel/empty-input preservation, recipe Input submission, active-run ProgressBar/close protection, final partial/retention failure evidence and subsequent connection-test selection. User-action cases additionally verify child creation, login/non-login menu filtering, exact su target/sudo actor/root argv and cancellation without privilege execution. Account-list tests cover explicit login, direct fallback, local identity and unknown SSH aliases. All execution is synthetic or mocked; no real SSH/recipe/su/sudo runs occur.

## Escape focus navigation

`test_focus_navigation.py` checks right-content → sidebar → main-tabs focus, preserved recipe/host selection, Left from Recipes to Profiles, unchanged form text, local Select-dropdown cancellation and modal Escape behavior. All catalog/management data is synthetic and no operations are executed.

## Attribution and reserved Bundle identity

`test_recipe_identity.py` verifies Unknown/custom installation defaults without rewriting files, fresh copies, reserved case/whitespace author/contact values, built-in Bundle/MIT descriptors and license texts, MIT packaging allowlists, external Bundle rejection before candidate creation and manifest spoofing. `attribution_fixture.py` creates explicitly synthetic user recipes for source/sharing tests. Tests that simulate a product checkout retain product attribution deliberately. All data is synthetic; no publication or private identity migration occurs.

## Recipe browser and execution history

`test_recipe_browser.py` verifies two source roots with directory hierarchy, docked layout and source/reference-specific selection, Info/Executions tab switching, literal descriptions and metadata/verification fields, synchronized selection without forced tab changes, stale-data clearing, timestamp/status/host columns, shared-ID separation and legacy records without provenance. `browser_fixture.py` supplies synthetic browser data to all UI suites so they do not scan private Feast catalogs or records. The unified result index adds source/reference fields without changing raw files.

## Recipes workbench

`test_recipe_workbench.py` verifies exact bare-entry routing, nonterminal/missing-dependency failures, every form against the shared CLI grammar, explicit selectors/typed variables, multi-host exclusions, required-field checks and confirmation rules. Headless tests check checkout-only startup, initial/returned table focus, actual Up/Down selection and detail updates at two terminal sizes, input focus preservation, dynamic fields and cancel/confirm behavior with mocked execution. No real host or private Feast is used.

## Optional terminal display

`test_terminal_ui.py` covers synthetic event transport, argument forwarding, TTY/dependency failures before execution, literal text and reported states. With `requirements-tui.txt` installed it also runs headless Textual child-stream/exit-code, active-run close, Unicode, row detail and small-screen checks. Without Textual those UI tests explicitly skip; use the optional environment for full feature validation. No real hosts or privileges are used.

`test_author_editor.py` covers local atomic author-default persistence, reserved/invalid values, file/symlink preservation, write failure cleanup, and synthetic Home Tab/Enter/mouse/save/cancel flows. No personal installation defaults are changed.

Recipe-browser tests also cover Bundle/profile display labels, empty profile suppression, guarded saved output reads and provenance checks, execution-row selection, and clearing output across recipes. Actions output remains separate from recipe history.

Recipe-browser time tests cover OS local timezone conversion, second precision, date rollover, non-hour offsets, daylight-saving differences, and missing/invalid/unzoned values. Synthetic timezone-switching checks require POSIX `tzset`; stored JSON retains its original timestamp.

Focus regression checks ensure a delayed recipe tab-activation callback preserves a user's sidebar or content focus. Packaging boundary tests also reject missing descriptors and malformed YAML with configuration errors before creating an archive.

Inventory 0.3.0 delivery verification (2026-10-14): 415 tests passed on Python 3.11.15/3.13.13/3.14.4, including Textual headless tests. The older interpreter runs reused pure-Python dependencies and do not establish native SSHScript dependency readiness; operational dependency checks and credential-free Session smoke ran on 3.14 only. See [the verification limits](../docs/inventory-access.md#verification-and-migration).

_Last modified: 2026-10-14_
