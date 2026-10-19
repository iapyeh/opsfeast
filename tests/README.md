# Tests

## Host-vault verification

`test_host_vault.py` uses temporary synthetic Feasts to verify namespace migration and replay, unchanged legacy bytes and IDs, annual archives, cumulative/recent copies, logical identity through native machine-ID changes, partial state, projection repair, group indexes and human-note preservation, safe/case-distinct filenames and symlinks, concurrent writers/conflicts, scalar retention/templates, mappings/manifests and runner audit failures before connection/after execution. No real host is contacted. See [the contract and limitations](../docs/host-vault.md).

This directory will contain public, reproducible verification for recipes, data contracts, and operational workflows.

Verification should cover result parsing, failure status, supported platforms, and repeated updates that preserve human notes. Tests and fixtures must use synthetic data rather than private host details or credentials.

## Inventory access and partitioned data

`test_inventory_access.py` covers canonical sudo-password presence/null/empty/control values, strict Boolean sudo policy, root/passwordless/default modes, whole-batch rejection, dryrun/check-access without collection or writes, force skip/fallback without alternate-password retries, collection-time rejection, unknown restoration/cleanup, platform parser units and empty/zero/missing values, output/time budgets, retention/exchange and CSV formula escaping. Check-access display tests additionally cover the per-test status/host/test/user/reason tabulate table, Unicode/❌ column alignment, leading-zero identifiers, default/custom host icons in progress/tables/exclusions without changing JSON IDs or YAML, missing display dependencies rejected before connection, JSON/quiet modes, progress before connection, parallel completion with ordered final results, failure/disabled/unknown accounts, exclusions and escaped terminal controls. Sessions and credentials are synthetic; no native SSH/sudo or real-host extended inventory is exercised. Existing routing tests explicitly mock the new access boundary; retained integration uses a synthetic UID or explicit ordinary-account policy. Optional fields do not change the seven-field completion rules.

`test_access_accounts.py` verifies check-access independent su → enabled sudo, actor-scoped credentials, sudo-disabled success, su/sudo failures, continued independent checks, missing-password skips/nonzero status, unavailable login, cleanup failure, account progress, JSON/quiet output and unchanged login-only inventory preflight. Per-test cases cover successful connection with failed login sudo, successful su with failed actor sudo, failed su with skipped sudo, missing credentials, suppressed duplicate successful reconnects, and separate restoration/cleanup failure rows. It reuses synthetic console fixtures; no native authentication is exercised.

## Saved-result collection user

Result browser tests cover actual root/user/fallback actors, intermediate/login-account
exclusion, failed-but-attempted collection, precollection and malformed/legacy unknowns,
generic/report uncertainty, human table/pipe/HTML output and preserved JSON/detail
identity quality. Raw-result bytes remain unchanged and no host operations occur.

## Recipe.root console

`test_recipe_root.py` covers callable console results/buffers, command/job budgets,
interactive delegation, root-second and ordinary-second ordering, typed safe failure
without body execution, copied/redacted evidence, already-root console setup, parent
and cross-thread guards, cached methods after exit, explicit nested-scope rejection,
identity/restoration/console-exit failures, preserved body errors with cleanup notes,
runner-supplied Recipe integration and failure even when unsafe errors are swallowed.
The package test also checks installed Recipe.root/RootUnavailableError and inclusion
of the shared strict helper. Existing inventory tests exercise the adapter's explicit
safe fallback and failed-preflight reuse. All authentication and root-console policy
cases use synthetic actors; native su/sudo compatibility requires separate evidence.

## Two-candidate inventory selection

`test_inventory_actor.py` uses synthetic actors to cover login-first selection,
first-eligible YAML order across include/group loading, root-second su priority,
su/sudo failure and missing/empty credentials, actor-scoped credential selection,
no third candidate or alternate credential, root UID verification, safe user fallback,
preflight reuse without failed-route authentication retries, later entry rejection,
unknown entered identity, nested recovery and exit failures, collection-body failure,
force boundaries, human attempt rows and the runner's ESXi authenticated-login handoff.
The existing inventory access suite also checks successful fallback collection and
retention without --force. Explicit account diagnostics retain their original scope.
Fixtures never use private host bindings or invoke native authentication.

## Configuration utility tests

With Python 3.11+ and requirements-init.txt installed (PyYAML and tabulate[widechars]), run:

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

Inventory filename regressions verify UTC conversion across date boundaries, second-only prefixes derived from start rather than completion, unchanged precise JSON timestamps, same-second UUID uniqueness and mixed legacy/new result discovery/lookup without renaming old files. All runs are synthetic. Delivery validation on 2026-10-14 passed 419 tests on each of Python 3.11.15, 3.13.13 and 3.14.4, including headless UI checks. The older interpreters reused pure-Python dependencies; native SSH/sudo readiness is not established by these suites.

## Inventory and runner tests

Runner progress tests cover automatic stdout TTY detection, verbose/quiet overrides, JSON separation, failed-host continuation with sanitized error types, collection stages, waiting heartbeats without sleeping, and worker/context cleanup on failure. Parallel tests additionally cover the worker limit, actual overlap, CPU-based default/cap/fallback, sequential mode, rejected --thread alias, out-of-order completion with ordered JSON, failure/context isolation, and separate Sessions, host facts and result files through the complete runner. All collection uses synthetic sessions; no network connections are made.

`test_host_selection.py` covers optional/scalar/list group memberships, unchanged dump representation, rejected former groups keys, invalid group types, cross-include union ordering, duplicate removal, explicit --host/--group kinds, unknown-target rejection before execution, all-host selection including local/jump/ungrouped hosts, empty inventory, root/profile forwarding, leading/flag recipe syntax, required recipe/targets, invalid option combinations, single-host output and batch continuation after failures. Fixtures are temporary and synthetic; runner execution is mocked and no host is contacted.

`test_inventory_system.py` covers Linux synthetic outputs, safe os-release parsing, missing-file fallback, permission denial, unsupported platforms, command and transport failures, timeout partial output, strict cleanup, recipe selection and manifest/version validation, output symlink rejection and repeated result preservation. These tests never contact SSH targets. The legacy Linux collector unsupported-platform path remains covered; SSHScript 5.0.0 credential-free quickstart was checked locally; full Linux/FreeBSD and SSH collection remain unverified. macOS now has a collector with separate local read-only validation.

CLI recipe selection tests cover `--recipe` precedence, absent/empty host selections, invalid host selections bypassed by a valid override, management-root relative paths with includes, absolute paths, invalid overrides without fallback, recipe/descriptor symlink escapes, and CLI argument forwarding.

Checkout recipe tests cover execution without instance copies, included YAML selection, directory/glob expansion, duplicate selection, explicitly selected custom implementations and stale instance copies, separate include and recipe boundaries, and result paths within the instance. Legacy custom copies use explicit `./recipes/...` paths.

Management-directory discovery tests cover default and custom initialization, shared default selection in both CLIs, explicit overrides, definition preservation, invalid locators/definitions and missing registered directories without fallback, and failed init preserving the previous default. All instances and locators use temporary directories.

`test_setup_tools.py` verifies base PyYAML/tabulate/wcwidth environment readiness, environment scope and import/distribution mismatches, full skill candidate/provenance preservation, read-only comparisons, local changes and incompatible contracts, failed downloads, existing destinations, failed writes, unsafe ZIP paths/links/duplicates and expansion limits. It uses synthetic ZIPs and mocked network responses; it never installs packages or changes schedulers. Public bundle check/download CLI verification is reported separately.

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


## Core API delivery

`test_core_api.py` and `test_core_delivery.py` cover installation identity/nil/reserved/copy/move behavior, metadata and profile isolation, runtime YAML snapshots, read-only inspection, session ownership/lifetimes, credential precedence, nested su/sudo identity/restoration, poisoned scopes, python-recipe static discovery/execution/results and explicit wheel/sdist boundaries. Temporary installations and synthetic accounts/transports protect private bindings. Native SSH/PAM/sudo policy remains separate evidence.

Delivery verification (2026-10-15): 456 tests passed on each of Python 3.11.15, 3.13.13 and 3.14.4, including headless Textual checks. Older interpreters reused the selected environment's pure-Python dependencies; these runs do not establish native SSHScript dependency readiness. Matching SSHScript 5.0.0 and credential-free local Core/identity execution were verified on 3.14. Wheel build, pip installation into a temporary target, import/session use outside the checkout, public resource inspection, skill validation and changed-document checks passed. Native SSH/su/sudo remain unverified. An existing TUI regression test now waits for deferred refresh completion instead of fixed short sleeps.



`test_host_icon.py` covers the in-memory default without YAML/raw-document mutation, explicit Symbol categories, invalid types/code points/compound emoji, includes, Core reload/inspection, CLI dumps and UI read models. All fixtures are synthetic; no host operations occur.

`test_console_output.py` checks actual TTY/non-TTY rendering and explicit --json priority across profiles/check/instance/inspection, connection/host/privilege diagnostics, recipe catalogs/results/jobs/execution and utility reports. It preserves raw data commands, nullable/zero/leading-zero values, failure/partial/skipped/unknown and retention states, escaped controls, icon metadata, saved-job inputs and readiness reporting with missing display dependencies. Native Session factories are guarded; all data, transports and writes are synthetic/temporary. Existing progress/profile tests now assert terminal tables while retaining pipe/JSON and interaction checks; isolated-checkout fixtures include the shared presentation module.

Shared console delivery verification (2026-10-15): Python 3.11.15, 3.13.13 and 3.14.4 each passed 490 public tests, including Textual headless checks and package boundaries. Eleven new console tests exercise TTY/non-TTY/explicit-JSON behavior with guarded synthetic Sessions and temporary data. Temporary tabulate/wcwidth dependencies were used without changing existing environments; older interpreters reused the selected environment's remaining dependencies. Wheel build, temporary no-dependency installation, isolated shared-renderer import, Unicode/retention output and explicit JSON passed. AST, documentation links/dates and skill frontmatter passed. No native SSH/su/sudo validation or product publication was performed.

Icon defaults delivery verification (2026-10-15): Python 3.11.15/3.13.13/3.14.4 each passed 499 public tests. Synthetic cases cover default.icon with sibling default.groups/default.users records across includes, named-account icons before group defaults, explicit host/account overrides, independent per-field group precedence in list order, implicit account labels, email-only metadata reading without host-account inheritance, raw-document preservation, invalid symbols/structures and included-file rejection. Headless Textual checks verify host/account labels while preserving plain group headings. Installed-wheel Unicode rendering outside the checkout, changed Python AST, local documentation links/dates, skill frontmatter and diff whitespace checks passed. Temporary dependencies and older-interpreter reuse have the same limits above; no real SSH/su/sudo or publication occurred.

`test_connection_selection.py` exercises connection-only all/group selection, union/deduplication, unknown/conflicting selectors before sessions, disabled exclusions/skips, continued testing after failure, independent cleanup, legacy single-host JSON, batch counts/schema, TTY progress/tables and JSON/quiet/verbose output. All Sessions are synthetic; no real host connection is made.

Connection selection delivery verification (2026-10-16): Python 3.11.15, 3.13.13 and 3.14.4 each passed 511 public tests, including Textual headless checks. Older interpreters reused the shared maintenance environment's Python dependencies without changing it. Tests also preserve --quiet/-q when forwarding connection tests through the optional TUI. Python 3.11 grammar, changed-document links/dates, skill frontmatter, wheel build, temporary no-dependency installation, isolated CLI help and diff whitespace checks passed. No native SSH/su/sudo, private host connection or publication was performed.

Root-login regression tests verify check-access CLI table/JSON success with sudo enabled, disabled or omitted, without invoking login sudo, and preserve independent checks for other declared accounts. The existing effective-UID-0 skip behavior requires no product-code change.

`test_esxi_identity.py` verifies the shared effective-UID adapter: fallback only for missing id plus VMkernel, fixed system-interpreter selection, no retry after probe rejection, OS-derived ordinary/root identity, configured-target UID matching, console argv quoting, missing/invalid/truncated/oversized evidence, safe error text, unchanged return shape and check-access CLI JSON/cleanup with root sudo skipped. A local execution of the actual portable Python expression validates OS/pwd calls; synthetic remote sessions never connect. Real ESXi root access evidence and scope limits are recorded in docs/host-diagnostics.md without private connection bindings.

ESXi identity delivery verification (2026-10-16): Python 3.11.15, 3.13.13 and 3.14.4 each passed 521 public tests, including all prior pending connection-selection/root-login changes. Older interpreters reused shared maintenance dependencies without environment changes. Eight new adapter tests cover success/failure/boundaries, CLI evidence and the portable probe expression. Python 3.11 grammar, changed Markdown links/dates, hosts/recipes skill frontmatter, wheel build, temporary no-dependency installation, isolated installed-adapter execution and CLI help, and diff whitespace checks passed. Real two-hop ESXi 7.0 root check-access passed with effective UID 0, sudo not_needed and strict cleanup; no host settings, packages or inventory data were changed. Other ESXi releases/non-root login, native ESXi su/sudo and ESXi inventory execution remain unverified.

Two-candidate inventory verification (2026-10-17): Python 3.11.15, 3.13.13 and
3.14.4 each passed all 588 public tests, including 22 added selection/runner/error
regressions and the existing headless UI/package checks. Older interpreters reused
the shared environment's Python dependency tree; native dependency readiness and a
credential-free local Session with strict cleanup were checked only on 3.14. Wheel
and sdist boundaries, temporary no-dependency installation, installed policy import
and runner help, Python 3.11 grammar, skill frontmatter, document dates/local links,
two complete synthetic guide YAML examples and diff whitespace checks passed.
No private host connection, native su/sudo, ESXi inventory or release was performed
during these checks. Public SSHScript 5.0.0 knowledge came from the bundled Agent Guide,
API guide authenticated-console/failure sections, versioning guide and SOURCE.json;
no SSHScript library source or upstream snapshot was modified.

Recipe.root delivery verification (2026-10-17): Python 3.11.15, 3.13.13 and
3.14.4 each passed all 604 public tests, including 16 new root-console/Core/runner
cases and the complete preceding inventory/ESXi changes. Older interpreters reused
the shared maintenance environment's Python dependencies without modifying it;
native dependency readiness was checked only on 3.14. Wheel/sdist boundaries,
temporary no-dependency installation, installed Recipe.root/RootUnavailableError and
shared-policy imports, installed runner help, a credential-free local Session,
ordinary-user callable console/managed job and strict cleanup passed. Python 3.11
grammar, Core/recipe Python example syntax, changed skill frontmatter, document dates,
564 local links and diff whitespace checks passed. Operational native su/sudo and
ESXi inventory remain unverified; no private host connection or package/tag release
was performed. Existing data schemas and dependency settings need no update because
the API addition reuses existing contracts and SSHScript 5.0.0. Human/agent docs,
capability routing and public reproducible tests are included in this delivery.

Saved-result user display verification (2026-10-17): Python 3.11.15 and 3.14.4
passed all 608 public tests. The first parallel 3.13.13 run hit the existing TUI
0.5-second child-process timing assertion; an independent full rerun passed all 608
without code/test changes. Older interpreters reused shared Python dependencies.
Wheel/sdist and temporary installed imports/CLI checks, credential-free local console
checks, Python 3.11 grammar, skill frontmatter, 194 changed-document local links and
diff whitespace passed. Offline browsing of an existing failed result showed unknown
because collection never started; no host operation or saved-result rewrite occurred.

Delivery verification (2026-10-17): Python 3.11.15, 3.13.13 and 3.14.4 each passed 625 tests, including headless Textual checks and 17 vault-specific tests. Older interpreters reused the selected maintenance environment's Python dependencies; this does not establish native SSHScript readiness on those interpreters. Wheel/sdist builds, temporary no-dependency pip installation, installed-wheel migration/retention/Markdown/group smoke checks, Python 3.11 grammar, schema syntax/references, skill frontmatter and changed-document checks passed. No real host connection/write, automatic private-data migration, commit, push or release was performed.

`test_retention_replay.py` adds temporary synthetic checks for fixed UUIDs, snapshot-only replay after recipe removal, explicit override conflicts/delete/replay, protected write/unknown and operation-linked verification, stale Markdown cleanup/fallback, projection repair, read-only dry runs, malformed snapshots, mixed batches and runner provenance capture. No recipe code or host is executed by replay.

Verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed 639 tests, including 14 new replay/deletion regressions. The older interpreters reused the maintenance environment's Python dependencies, which does not prove native SSHScript readiness. Wheel/sdist builds, temporary no-dependency installation, installed-wheel snapshot replay/dedup/write protection and legacy migration/provenance-upgrade/deletion smoke checks passed. Python 3.11 grammar, schema syntax/references, skill frontmatter and Markdown link/date checks passed. No real host connection/write, automatic private-data migration, commit, push or release was performed.

_Last modified: 2026-10-19_
