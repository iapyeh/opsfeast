# Tests

test_vault_layout.py verifies compact second-resolution observation names, a single final metadata section and absent success banner, scalar/ordered primary-group routing, distinct ungrouped/reserved groups, archived-host placement, valid secondary-group/index/overview links, regeneration after group changes, unchanged retention and preserved old human notes. Same-second/title collisions preserve both retained records and existing published bytes; operation-journal filenames remain distinct.

test_vault_evidence.py verifies title/UTC page names, same-time/source separation, safe bounded filenames and explicit collision failure; verified actor capture, output/credential omission, optional local retention metadata, unchanged legacy exchange, typed validation, historical unknowns, managed-path cleanup and human-note preservation. Collector tests cover LF/CRLF, distinct marker/exit/parser reasons and byte-limit checks before normalization. Existing synthetic runner tests verify actor metadata, and historical snapshot tests continue to bind unchanged inventory normalizer/schema bytes.

test_vault_readability.py verifies labeled provenance placement, all six inventory sections, nested and heterogeneous lists, capacity/duration conversion with exact base values, null/zero/false/empty distinctions, visible partial/identity/coverage warnings, generic scalar recipe views, markup/fence escaping and original-record immutability. A synthetic rebuild verifies both yearly/latest layouts, unchanged retention database bytes and preserved human notes. No real profile or host is used.

`test_console_width.py` verifies actual offline recipes show output at 40/80/120 terminal columns, complete long Unicode identifiers, wide/combining characters, escaped controls, long headers, empty/ragged tables, dynamic resizing, narrow labeled-record views and the shared check-access adapter. It asserts unchanged source data, wide/non-TTY layout and JSON dependency/width bypass. Fixtures are synthetic; no host or recipe code executes.

`test_cli_help.py` also verifies top-level task grouping/order, every registered command appearing once, reusable-stage guidance, unchanged leaf help/parsing, aliases and visibility of future unassigned commands. Wheel checks include the formatter module.

`test_cli_help.py` verifies meaningful purpose text before parameter listings for the main command, profile/configuration/host diagnostics, recipes and saved jobs, retained data/consumers/Vault and standalone runner/exchange commands. Tests check host versus offline execution, output/side-effect distinctions, examples, complete nested usage and successful help with required execution arguments omitted. Profile resolution, session loading and execution/dispatch functions are guarded against accidental invocation; an actual subprocess reads recipes run -h from an empty directory without creating files.

`test_recipe_taxonomy.py` verifies the exact five classified bundle paths with stable IDs/versions, absent old aliases, static deep inspection/CLI, profile/external paths deeper than four levels, recursive/glob selection, saved normalizer/schema digest bindings, preserved historical references and current-reference consumer matching. Existing runner, browser, report, job and installed-wheel tests now use the classified bundle paths. All operational fixtures remain synthetic.

`test_retention_consumers.py` verifies static discovery and reverse recipe relations, explicit activation, source/contract/version selectors, deduplication, disabled backlog, independent failures/retries, transaction rollback, projection failure recovery, interrupted running attempts, deletion/reinsertion, concurrent dispatch and operation events. The installed-wheel test also verifies packaged consumer resources and a registered local consumer outside checkout source. All fixtures are synthetic and local; no private Feast is modified or host contacted.

## Host-vault verification

Vault tests cover dedicated vault/ output and input separation, automatic CLI/Core
profile initialization, default/explicit/saved namespaces, invalid defaults rejected
before filesystem writes, namespace continuity through profile rename, first inventory
run automatically retained without migration, reinit preserving archived values, and
storage failure reported without registering a partial profile (retry succeeds).
The former development layout has no compatibility-copy implementation or tests.

Automatic-init verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each
passed 649 tests. Wheel/sdist build, temporary no-dependency wheel installation, 56
installed vault/profile tests and installed CLI JSON initialization outside the checkout passed.
First-inventory integration uses a synthetic session and mocked collection-actor scope;
no real SSH/su/sudo or private profile changes occurred. Older interpreter tests reused
pure-Python dependencies and do not establish native execution dependency readiness.

Human-view regressions cover executable shell-quoted rebuild guidance, comma-separated
groups, partial/empty observation status, second-resolution local times throughout
generated Markdown and unchanged precise archive payloads.

Vault human-view verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4
each passed 641 tests. Wheel/sdist builds, temporary no-dependency wheel installation,
19 installed vault tests and execution of the generated rebuild command outside the
checkout passed. Older interpreters reused pure-Python dependencies; these synthetic
checks do not establish native SSH/su/sudo readiness or change real Feast data.

`test_host_vault.py` uses temporary synthetic profiles to verify independent annual/cumulative/recent retention data, namespace identity, replay, preserved legacy files, partial state, data/content failure repair, group indexes, human notes, safe paths, concurrent writers and protected operation journals. `test_retention_replay.py` covers data-only snapshots, explicit overrides, source identity, dedup/conflicts and protected deletion. No host is contacted. See [retention contracts](../docs/retention.md) and [vault content](../docs/host-vault.md).

`test_retention_content.py` verifies read-only CLI/Core queries, source-qualified filters, zero/null/partial values, disabled content refresh, independent failure receipts/exit codes, old-layout refusal without changes, author ownership, replacement of edited generated files and protection of unmanaged files, stale-output cleanup, vault rebuild without database writes and offline multi-recipe Markdown/HTML. `test_terminal_ui.py` verifies separate Retention and Content cells. `test_core_delivery.py` verifies the new modules/schema/example are packaged and runs an isolated installed-wheel retention/content smoke check.

`test_inventory_retention_contract.py` verifies explicit recipe declarations (no ID fallback), static nonexecution, nested field semantics/units, schema/path/digest failures, registered-only replay, old raw requiring reviewed definitions, preserved source/partial/privacy states, changed-definition conflicts and protected private storage bundle boundaries. Installed-wheel smoke also exercises inventory structured retention through its saved declaration.

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

`test_recipe_sources.py` covers checkout/profile/external references, entry-only registrations and includes, home/relative roots, path and descriptor symlink escapes, directory/glob expansion, namespaced IDs, shorthand/mapping items, default/source/host vars with first-match precedence, deep-copy/shallow overlays, typed bounds, disabled/missing sources, disabled hosts/jumps, exact CLI exclusions and empty selections. Inventory source selection uses static preflight or synthetic job delegation; no dependencies are installed and no external host is contacted.

Inventory filename regressions verify UTC conversion across date boundaries, second-only prefixes derived from start rather than completion, unchanged precise JSON timestamps, same-second UUID uniqueness and mixed legacy/new result discovery/lookup without renaming old files. All runs are synthetic. Delivery validation on 2026-10-14 passed 419 tests on each of Python 3.11.15, 3.13.13 and 3.14.4, including headless UI checks. The older interpreters reused pure-Python dependencies; native SSH/sudo readiness is not established by these suites.

## Inventory and runner tests

test_inventory_jobs.py covers selective acquisition, no-store invariance, raw/retention/Vault histories, failures/gaps, public node projections, schedules, concurrency and cron preservation. test_recipe_runner.py verifies the single execution entrypoint, job delegation, removed snapshot descriptors/flags, explicit recipe selection, safe paths, UTC filenames and receipt failure recovery. test_host_selection.py covers selector unions/order, enabled/excluded targets, progress, concurrency bounds and per-host failure isolation. The pure historical parser/data tests remain for interpreting preserved files; no obsolete snapshot-runner integration is required.

test_host_runtime.py covers platform facts, cache refresh/invalidation, target changes, su/sudo identities, independent/repeated chains, credential precedence and fallback, host credential scope, empty/null/invalid credentials, no retry after rejected overrides, missing credentials, test-host aggregation and safe diagnostic failures. The current job descriptor's entrypoint integrity and symlink boundaries are also tested. All account/SSH tests are synthetic; no native privileged accounts are tested.

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


Retention/content delivery verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed all 665 public tests, including headless TUI checks, 16 independent retention/content tests and isolated installed-wheel data/content assertions. Older interpreters reused the maintenance environment's Python dependencies; this does not establish native execution-library readiness. Wheel/sdist builds, temporary no-dependency pip installation and installed-wheel scalar query, replay/dedup, Markdown/HTML, vault and linked-operation protection smoke passed. Python 3.11 grammar, schema syntax/references, skill frontmatter, document links/footers and diff whitespace checks passed. No native host operation, private-data relocation, commit, push or release was performed.


Inventory-owned retention follow-up verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed all 678 public tests, including 13 new inventory-contract regressions and installed-wheel structured inventory retention assertions. Older interpreters reused the selected maintenance environment's Python dependencies. Wheel/sdist builds, temporary no-dependency pip installation and installed inventory normalization/query/replay/content smoke passed. Python 3.11 grammar, schema syntax/references, skill frontmatter, documentation links/footers and diff whitespace checks passed. This is synthetic/local-package evidence; no native host collection, private-data modification, commit, push or release occurred.

Retention-consumer delivery verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed all 703 public tests, including 24 new consumer tests, headless TUI checks and isolated installed-wheel registration/dispatch. The older interpreters reused the maintenance environment's Python dependencies; this does not establish native execution-library readiness. Wheel/sdist builds, temporary no-dependency/no-index pip installation and all 24 installed consumer tests outside the checkout passed. Python 3.11 grammar, 13 schema files and local references, three changed skill frontmatters, 527 changed-document links, document footers and diff whitespace checks passed. Human/agent documentation, capability routing, data/receipt incompatibility guidance and public reproducible tests are included. Tests used temporary synthetic profiles; no real host operations, private-data migration, commit, push or release occurred.

Classified bundle verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed all 711 public tests, including eight new taxonomy/history/consumer regressions and headless deep-path browser checks. Older interpreters reused the selected maintenance environment's Python dependencies; native execution-library readiness is not established by this matrix. Wheel/sdist builds, temporary no-index/no-dependency pip installation, installed CLI discovery/inspection of all five classified recipes and 45 installed taxonomy/consumer/inventory-contract tests passed outside the checkout. Wheel assertions reject old check/inventory/report bundle directories. Python 3.11 grammar for 44 changed/new Python files, 15 schema files and local references/JSON pointers, four changed skill frontmatters, 873 document links, document timestamps and diff whitespace checks passed. The inventory normalizer and retention schema retain their pre-move byte digests; saved snapshots replay and historical references stay unchanged. Human/agent guidance, source placement, path incompatibilities and manual configuration/job/consumer actions are documented. No host connection, private profile/configuration/history rewrite, commit, push or release occurred.

Purpose-first CLI help verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed all 720 public tests, including nine help tests with guarded profile/connection/execution/dispatch calls, complete nested usage, help taking priority over --tui and empty-directory CLI help. Older interpreters reused the maintenance environment's Python dependencies; this does not establish native execution readiness. Wheel/sdist builds, temporary no-index/no-dependency installation and 54 installed help/taxonomy/consumer/inventory-contract tests passed outside the checkout. Python 3.11 grammar for 50 changed/new Python files, 15 schema files and local references/JSON pointers, four changed skill frontmatters, 878 document links, timestamps and diff whitespace checks passed. The pending recipe reclassification is included in this verification; inventory normalizer/schema bytes remain unchanged. Canonical help/CLI guidance and relevant skill/capability routing are updated. Invocation arguments, normal execution/storage/data contracts and Core APIs require no changes for help; only --help/--tui interaction now prioritizes help. No host connection, private data/configuration update, commit, push or release occurred.


Task-grouped root help verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed all 723 public tests, including 12 help tests. Root help lists all 19 commands once in five task areas, explains cross-stage reuse, preserves leaf help and parsing, and keeps unassigned commands discoverable. Formatter column sizing includes the heading indentation on Python 3.11 as well as newer versions. Wheel/sdist builds, temporary no-index/no-dependency installation and 57 installed help/taxonomy/consumer/inventory-contract tests passed. Python 3.11 grammar for 51 changed/new Python files, 15 schemas and local references/JSON pointers, four skill frontmatters, 878 document links, document footers and diff whitespace checks passed. The complete pending recipe-path/help changes are included; the inventory normalizer and retention schema remain byte-identical. Canonical CLI documentation and relevant capability/skill routing describe the final grouping. Command paths, flags, execution/data contracts and Core APIs are unaffected by grouping and need no API migration. Older interpreters reused maintenance-environment dependencies; this is synthetic/local-package evidence, not native host-execution verification. No host connection, private profile/configuration/data change, commit, push or release occurred.

Terminal-width wrapping verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed all 733 public tests, including 10 new width regressions. Existing result-time and profile-selection tests now reconstruct wrapped cells to verify complete timestamps and paths. A real 80-column PTY ran recipes show system/inventory/overview --checkout-only successfully; this reads metadata and executes no recipe or host command. Wheel/sdist builds, temporary no-index/no-dependency installation and 67 installed help/width/taxonomy/consumer/inventory-contract tests passed. Python 3.11 grammar for 54 changed/new Python files, 15 schemas and local references/JSON pointers, four skill frontmatters, 882 document links, footers and diff whitespace checks passed. The complete pending recipe-path/help/presentation changes are included; the inventory normalizer and retention schema remain byte-identical. Human/agent CLI guidance, shared-renderer invocation examples and relevant capability/skill routing are updated. This changes terminal presentation only; JSON, redirected layouts, saved data, execution scope and Core APIs need no migration. Standalone test_profiles.py currently lacks the full discovery suite's module-import setup for vault initialization; profile validation used complete discovery. Older interpreters reused maintenance-environment dependencies, so this does not establish native SSH/su/sudo readiness. No private data/configuration update, host connection, commit, push or release occurred.

Readable Vault observation verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed all 742 public tests, including nine new readability tests. Wheel/sdist builds, temporary no-index/no-dependency installation and 114 installed readability/consumer/retention/replay/help/width/taxonomy tests passed. Python 3.11 grammar, schema/reference checks, changed skill metadata, document links/footers and diff whitespace checks passed. Existing page assertions now verify human labels, explicit unavailable states and boolean words while continuing to assert retained typed values and source-data protection. Both historical/latest pages and generic scalar observations are covered; operation-journal JSON presentation is unchanged. Canonical Vault/CLI guides, consumer documentation, user recipe/result-data skills and capability routing describe the final renderer and authorized regeneration workflow. No retention schema/normalizer/API migration is required; original structured data remains available through retention query/show. HTML disclosure support varies by Markdown reader, and expanded content is still readable. Older interpreters reused maintenance-environment dependencies; these tests do not establish native host-execution readiness. Verification used synthetic temporary profiles only; no actual user Vault rebuild, private data/configuration change, host connection, commit, push or release occurred.

Readable names and collection-evidence verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed all 756 public tests, including 14 new naming/provenance/framing regressions and the prior nine readability tests. Wheel/sdist builds, temporary no-index/no-dependency installation and 128 installed readability/evidence/consumer/retention/replay/help/width/taxonomy tests passed. Python 3.11 grammar for 25 inspected Python files, 16 schemas/references, three changed skill frontmatters, document links/footers and diff whitespace checks passed. Inventory recipe is now 0.3.2; its registered retention normalizer/schema bytes and legacy normalized exchange remain unchanged. Local collection evidence is an optional raw/envelope 0.1.0 metadata contract, not a rewrite or historical backfill. Naming/path changes, manual-link actions, actor/query interpretation, current interfaces and regeneration limits are documented across canonical guides, consumer docs, capability routing and user skills.

A credential-free local Session.shell reproduction using SSHScript import/distribution 5.0.0 returned CRLF and reproduced failure of the old producer-marker regex; normalization made the same marker match. This used the bundled public documentation contract 5.0.0 and its [recorded provenance](../skills/sshscript/SOURCE.json); no SSH connection, su or sudo was performed. Synthetic LF/CRLF, byte bounds and source-failure tests verify the collector correction. Real-host collection was not rerun, so this does not establish current target tool availability, native privilege behavior or complete inventory. Older interpreters reused maintenance-environment dependencies. No real profile/Vault rewrite, private-data migration, commit, push or release occurred.

Compact observation layout and primary-group verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed all 764 public tests, including eight new layout tests and the pending naming/evidence/readability tests. Wheel/sdist builds, temporary no-index/no-dependency installation and 136 installed related tests passed. Python 3.11 grammar for 28 inspected Python files, 16 schemas/references, three changed skill frontmatters, 494 document links, footers and diff whitespace checks passed. Observation history uses whole-second UTC plus label, with explicit collision failure preserving retained records and previously published bytes. Existing independent replay lifecycle fixtures use distinct seconds; a dedicated boundary test covers equal-second collisions. Operation-journal names remain separately discriminated.

Human/agent guides, CLI routing, consumer documentation and migration notes describe the final host-only header, one final Collection metadata section, first-membership host paths and secondary-group links. Rebuild removes stale generated pages and updates indexes/links; old unmanaged README/notes remain at their original locations for deliberate user relocation/linking. Synthetic group-change tests verify unchanged retention bytes and preserved human notes. Inventory normalizer/schema digest bindings and retention identity/layout remain unchanged. Older interpreters reused maintenance-environment dependencies; no new native host-execution evidence is claimed. No actual user Vault rebuild, human-note move, host connection, commit, push or release occurred.

Current-page navigation tests cover plain current filenames, report-link resolution across year boundaries, unique Contents anchors, separate metadata views, removal of Field observations, missing versus empty collections, same-record System field selection and immutable retained data. No recipe, retention or exchange contract change is needed for these presentation refinements.

Current/report split verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed all 772 public tests. Wheel and sdist builds, temporary no-index/no-dependency installation and 144 installed related tests passed. Python 3.11 grammar for 29 inspected Python files, 16 schemas/references, three changed skill frontmatters, 494 document links, footers and diff whitespace checks passed. Eight new current-page tests cover navigation, selected latest report linkage and missing-data interpretation. Current pages link to historical metadata rather than duplicating it. Existing partial-observation tests verify unavailable values in current data and partial status in the linked historical report. This presentation change updates consumer guidance, canonical CLI/content documentation, capability routing and relevant recipe/result-data skills; it adds no retention schema or collection contract change. All test inputs/previews are synthetic; no real profile publication, host collection, commit or push occurred.

Recipe relocation/current selection verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed all 777 public tests. Wheel/sdist builds, temporary no-index/no-dependency installation and 149 installed related tests passed. Five new synthetic cases cover actual retain/rebuild after a recipe move, reverse input order, equal-time ID ordering, independent source/origin isolation and different-recipe title collisions. Current identity is a checkout presentation helper; retention schemas, exact-reference query filters and saved historical references remain unchanged. Canonical Vault/CLI/migration guides, capability routing, bundled consumer and recipe/result-data skills describe the selection rule. Grammar, schema references, skill frontmatter, document links/footers and whitespace checks passed. A local user-authorized content rebuild was also verified separately: retained structured records were identical before and after, and all current report links resolved. This local publication does not establish host collection or privilege behavior; no host connection, commit or push occurred.

Obsidian Contents verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed all 779 public tests. Wheel/sdist builds, temporary no-index/no-dependency installation and 151 installed related tests passed. Current-page navigation assertions now check native heading targets rather than merely matching generated HTML IDs; additional cases cover heading case/space/Unicode encoding and repeated/reserved heading names. No new runtime dependency or retention contract change was required. Canonical consumer, CLI, migration and capability documentation plus recipe/result-data skills explain Obsidian navigation and other-reader limitations. Grammar, schemas, skill frontmatter, document links/footers and whitespace checks passed. Separately, the authorized local Vault rebuild preserved retained record content. Native Obsidian 1.14.4 UI verification confirmed that clicking Interfaces in Reading view scrolled from Contents to the Interfaces heading and its table. That manual test is evidence for this installed reader/version, not universal Markdown compatibility or host execution. No host connection, commit or push occurred.



## Unified recipe execution

Use test_recipe_runner.py for the single public entrypoint, current job delegation, snapshot rejection, path/source resolution, result naming and receipt-write failure checks. Shared selection, progress and concurrency remain covered by test_host_selection.py; general execution, Core scopes, reports, replay and Vault retain their independent suites. Obsolete snapshot-runner and dryrun/force integration assertions were removed; pure historical parser/data fixtures remain for saved-data interpretation. No real SSH/su/sudo execution is implied.

## SSHScript 6.0 update verification

The execution dependency, runtime/diagnostic guards, full-environment readiness and official skill contract now require 6.0.0 together. `test_sshscript_update.py` covers supported execution, old/newer rejection, import/distribution mismatch and package-versus-skill mismatch before Session creation. `test_setup_tools.py` checks matching/newer bundle contracts, complete staging, read-only comparisons, preservation, network failures, invalid archives and the required 6.x console reference. `test_core_delivery.py` checks the exact wheel execution dependency and bundled requirements as well as public package resources.

Run the public regression suite with the selected interpreter:

```sh
python -B -m unittest discover -s tests -p 'test_*.py'
python -B tools/check_environment.py --json
python -m pip check
```

On 2026-10-23, Python 3.11.15, 3.13.13 and 3.14.4 each passed 856 tests. The older interpreters reused the selected environment's dependencies; this is regression/grammar evidence, not independently installed native dependency validation on those interpreters. The selected OpsFeast .venv uses SSHScript import/distribution/CLI 6.0.0, and full readiness plus pip dependency checks passed. The shared maintenance environment was not changed.

Credential-free native macOS checks using the published wheel passed exact argv/stdin, retained Bash state, ScriptResult/stop metadata and strict cleanup. A piped invocation of the actual console retained Python variables across a dollar command and quit successfully. The bundled identity recipe passed through the actual runner/Core with an isolated temporary local profile. No private management root, SSH, proxy command, su/sudo, inventory schedule or managed-host recipe execution was used. These local checks do not establish remote authentication, privilege policy or Linux/FreeBSD/ESXi behavior with 6.0. Historical evidence explicitly labeled 5.0.0 remains historical.

The official wheel SHA-256 is b3c62588f50608d6ce8a8028216759224f3cc4c2a0b552a6208c2002198dd8ca, verified against PyPI metadata. Complete skill ZIP SHA-256 is 60f032a57e812df831aab79354cdd3045f8acd200aa10c7e792ca29a7b4984ea; the replacement preserves upstream bytes and records provenance in SOURCE.json. Public release commit e70d56e2bb1856acdb555d7d63922e85dd538bbd supplied supplementary changelog/console reading. See [the user/agent update workflow and documentation gaps](../docs/skill-updates.md#update-sshscript-with-one-prompt).

Wheel/sdist builds, temporary no-index/no-dependency installation and 68 installed-library/setup/recipe tests passed. Actual identity execution through the installed wheel also passed outside the checkout. One source-oriented CLI test fails if transplanted into the wheel because it expects checkout tools/package paths; it is covered by the passing source suite and excluded from the installed-library count, consistent with the documented checkout-CLI boundary. New local links, skill frontmatter, structured files, Python 3.11 grammar, footer rules and exact bundle integrity checks passed.

Human/agent documentation, capability routing, recipe dependency declarations and relevant skills are updated together. The reusable user interface is a README prompt plus an existing-tool procedure; no automatic updater or reload service is claimed. No retention schema or stored-data migration is required. No commit, push or release is included.

## SSHScript 6.1 update verification

On 2026-10-24, Python 3.11.15, 3.13.13 and 3.14.4 each passed all 856 public tests with the 6.1.0 dependency/skill contract. The older interpreters reused the selected environment's dependencies; these runs do not establish independently installed native dependencies on those interpreters. Final focused setup/update checks also passed after adding missing embedded-console reference coverage. Version guards reject 6.0.0, unsupported releases and import/distribution mismatches before Session creation.

The selected checkout .venv now imports published SSHScript 6.1.0. All 31 installed Python/type files match the verified PyPI wheel byte for byte; all eight official skill files match the complete downloaded ZIP. The previous skill was backed up outside the checkout. Wheel SHA-256: `5c05857bc2ab62d76a84f8599294f7b1f5b6b03e4b31f5ee74b7b2848708d4a5`; skill ZIP SHA-256: `db59dbe1a8c6e7af049a759f03e4b21766ecf34751d44fe85b87e4c3dcf4987b`. Sources: [PyPI](https://pypi.org/project/sshscript/6.1.0/), [public v6.1.0 changelog](https://github.com/iapyeh/sshscript/blob/v6.1.0/CHANGELOG.md) and bundled SOURCE.json.

Credential-free local macOS PTY checks passed exact argv/stdin, retained Python variables and shell cwd/environment, actual nonzero command exit status (failed/7), borrowed close with session_reuse=confirmed and original-owner command reuse. An initial smoke probe incorrectly used shell `exit 7`, which exits the retained shell itself and produced unknown cleanup; the corrected command uses a child `sh -c 'exit 7'`. Both logs were preserved. No SSHScript changes or state workarounds were used.

Wheel/sdist builds from a staging copy containing only tracked files and the complete new skill, plus a temporary no-index/no-dependency wheel install outside the checkout, passed. Installed imports and embedded-console resources were verified. Full readiness and pip check passed. Human guides, capability routing, skills and recipe dependency declarations were updated together; no data/schema migration or persistent OpsFeast Console adapter is included. Existing profile data, shared environments and unrelated files were preserved. No real SSH/jump/su/sudo, credentials, commit, push or publication were involved. These checks do not repeat the prototype browser acceptance or prove remote privilege behavior.

## MySQL/MariaDB recipe and exploration workflow verification

On 2026-10-24, CPython 3.11.15, 3.13.13 and 3.14.4 each passed 870 public tests. The 3.11/3.13 runs used separate temporary QA environments with their own installed native dependencies. Initial cross-ABI dependency reuse failed the new local integration test; those failures are not passing native evidence. The selected 3.14 environment and both QA environments passed pip check.

`test_mysql_replication.py` supplies 14 public test methods covering MySQL/MariaDB/version syntax, multiple channels/instances, missing/stopped/lagged/wrong-source status, zero thresholds, missing credentials, malformed XML, socket/TCP/TLS client flags, option-file ownership/permissions/escaping, timeout, nonzero/truncated helper output, credential redaction, cleanup uncertainty, recipe-var inheritance, structured retention/dedup/schema validation and Vault. A real local SSHScript process executes a synthetic client protocol fixture through the public CLI and saves raw → retention → Vault. This is not a real local MySQL/MariaDB server. Native MariaDB, TLS and least-privilege account integration remain unverified.

Native SSH against a Linux target running MySQL 8.0.46 also passed repeated actual recipe runs: fixed identity/status SQL, inline database credentials transmitted through SSH stdin/protected temporary option file, healthy replica-side findings, confirmed credential cleanup, stored retention and successful builtin:vault delivery. No source-host connection, OS su/sudo, database repair/write or private hosts.yaml change occurred. The earlier exploratory Console was closed with borrowed Session reuse confirmed and owner cleanup. A final audit found no supplied database password in the checked public files, raw result, retained record, generated database pages or captured process streams. This records observed behavior, not a general sandbox/secret-scanning guarantee.

Wheel/sdist builds used an explicit staging copy that excludes unrelated untracked scripts and the old Console prototype. A temporary no-index/no-dependency install outside the checkout passed all 14 new tests after explicitly importing the installed package before test fixtures add tools/ to sys.path. Invoking the source-oriented test loader without that import exposed the existing tools/opsfeast.py shadowing boundary; no product patch was used to hide it. Package contents include the recipe, schema/normalizer, safe config example and exploration workflow. Source tests cover packaged-resource discovery as well.

Human recipe/config/retention/CLI/Vault guides, capability routing and the recipes skill were updated together. The [exploration-to-recipe workflow](../skills/opsfeast-recipes/references/exploration-to-recipe.md) includes transparent calls/evidence, explicit authorization for destructive effects and a failure-over-damage stopping rule. Skill format, changed Python 3.11 grammar, JSON/YAML, local document link paths, footers and diff whitespace were checked. No independent agent blind evaluation or remote CI/commit/push/publication is claimed. Permanent private recipe configuration is a separately reviewable change, not silently installed by these tests.

## Configuration and readable execution handoff

On 2026-10-24, Python 3.11.15, 3.13.13 and 3.14.4 each passed 876 public tests, with independent native-dependency QA environments for 3.11/3.13. The six new test_execution_handoff cases use real synthetic retention/Vault publication to verify single-host raw/latest links, shared batch destinations, failed/disabled publication versus stale pages, independent consumer success/failure, missing/deleted/unowned/symlink paths, read-only lookup and unchanged JSON/pipe reports. Existing console output tests also passed. A temporary installed wheel outside the checkout passed 20 related handoff/database tests.

An explicitly authorized private configuration update preserved other host/settings data, created a protected backup, saved database settings with bulk disabled and set the source YAML to 0600. An initial temporary-entry validation failed because entry hosts.yaml and included filenames have distinct policies; the original was unchanged. Typed-input prevalidation plus canonical-entry validation/rollback completed successfully. No entry/include policy or product validation was bypassed. Credentials were not printed or placed in the public bundle.

A real SSH/MySQL read check then ran directly from saved configuration, without a password argument or temporary vars file. Actual TTY completion displayed PASS, Result/Observation IDs, the existing raw JSON path and matching Vault latest-state path. Read-back checks confirmed unrelated settings preserved, protected file/backup modes and no supplied password in checked public files, raw/retained output, readable pages or TTY transcript. The helper host_vault.result_locations performs only read access; a display lookup failure cannot replace the actual execution outcome. Current paths mean latest state, not exact historical content.

Human CLI/execution/Vault documentation, capability routing and the recipes skill now require the full handoff: apply authorized known private settings, provide an actual copy/paste command and identify saved/readable results. Schema/normalizer, database operations and JSON contracts did not change in this handoff update. Native MariaDB/TLS, independent agent blind evaluation and remote CI were not added. No commit/push/publication occurred.

## Proxy subprocess environment verification

On 2026-10-24, Python 3.11.15, 3.13.13 and 3.14.4 each passed all 889 public tests.
The 13 new test_process_environment cases exercise real local launcher children,
NO_COLOR absent/empty/1/true/0/unexpected values, explicit overrides/removals, PATH,
stdin/stdout/PID continuity, concurrent isolation, private-file permissions/removal,
start/connect/termination failures, redacted receipts, aliases/first-hop ownership,
Core/UI masking and shared diagnostic/runtime connection boundaries. An actual
SSHScript 6.1.0 Session uses a local failing-handshake proxy fixture and strict
cleanup verifies that its child is gone. This is no real SSH/authentication proof.

The first full matrix exposed one outdated raw-proxy-string assertion. It was
updated to inspect the original argv preserved in the launcher payload while
retaining the jump/password/key assertions; the final full matrix passed. Running
test_ops.py alone also exposes the existing discovery-order/bootstrap dependency;
no product workaround was added. Full discovery covers it successfully. A staged
wheel/sdist build and isolated installed wheel passed all 13 new tests outside the
checkout. Dependencies for Python 3.11/3.13 are in separate temporary QA environments;
the installed-wheel check reuses selected-environment dependencies through a local
.pth without modifying that environment. Readiness, pip check, Python 3.11 grammar,
changed documentation links/footers and whitespace checks passed.

The [policy guide](../docs/process-environment.md) documents config, defaults,
compatibility, privacy and limits. Human guides, capability routing and hosts/Core/
recipes skills were updated together. Core methods and retention schemas are
unchanged. No real host/proxy, credentials, SSHScript source, private profile,
global environment, schedule, commit, push or publication was changed. Remote CI
was not executed and no CI workflow is configured in this checkout.


## Pinned SSHScript 7.0.0 compatibility verification

On 2026-10-24, Python 3.11.15, 3.13.13 and 3.14.4 each passed all 894 public tests
against source commit 7a3b43594eca50cf1600d4f8a1dc67cb266df19e (unreleased 7.0.0).
The selected 3.14 runtime's 32 package/type files match the untouched public source;
the rebuilt wheel from a temporary copy matches those same hashes. Independent
3.11/3.13 QA environments installed that wheel with no dependency upgrades; all
three full readiness checks and pip check passed. Initial build isolation could
not fetch setuptools under sandbox networking; the authorized retry downloaded
only the exact source-declared build dependency to temporary isolation and built
successfully. No SSHScript source or shared environment was edited.

Connection dictionaries and the environment adapter now use parent_key_filename
and proxy_command, retaining key locality and proxy child ownership. The new source
manifest/guard rejects same-version drift before Session creation in Core, runner
and standalone test-connection. Nine runtime tests cover supported/rejected versions,
source/module/type drift, real 7.0 resolver names and rejected old names, exact source
requirements/metadata, and native local borrowed Console state/job/close/reuse.
Existing local proxy and MySQL fake-client/retention/Vault tests run against 7.0.

Wheel/sdist builds used a public allowlist staging copy, excluding private profiles,
agent-installed copies, unrelated scripts and the old Console prototype. An isolated
wheel install outside the checkout passed 41 related tests: eight runtime/identity
cases, 13 environment cases, 14 database cases and six result handoff cases. The
checkout-only dependency-surface test needs pyproject.toml/build_backend.py and is
covered by full source discovery rather than transplanted into wheel resources.
Python 3.11 grammar, YAML/JSON, four Ops skill frontmatters, changed Markdown local
links/footers, public artifact contents and diff whitespace passed. Both SSHScript
skill copies still match the original complete pinned-source ZIP; upstream bytes
were not rewritten to describe OpsFeast support.

The [migration guide](../docs/sshscript-7.md) and runtime manifest document exact
identity, setup, current names, private-key decryption limits, no legacy aliases
and local/synthetic versus real-host evidence. Existing host YAML/result/retention
schemas and stored data are unchanged. Historical 6.1.0 native MySQL evidence is
explicitly historical. No real SSH/wstunnel, jump/su/sudo, credentials, private host
configuration, schedules, commit, push or release were performed. The prototype
browser UI was not revalidated; remote CI was not executed.


## Role-aware execution identity verification

On 2026-10-24, Python 3.11.15, 3.13.13 and 3.14.4 each passed 901 public tests.
Six new test_execution_identity cases cover database versus SSH/OS roles, multiple
instances with independent unknowns, configured-account exclusion, unconfirmed
login, unrelated services, control characters, read-only projection and completion
rendering. A new observation integration case verifies identical live/history
labels, preserved null OS collection_identity, additive identity_evidence and
unchanged raw bytes. An isolated installed wheel outside the checkout passed 48
related tests, including the new identity cases and existing database, environment,
source guard and result-location checks. The checkout-only metadata case remains
covered by source discovery.

Actual local PTY rendering of an existing authorized database observation showed
both recorded database grant identity and final-hop SSH login with explicit role
labels; it did not reconnect or rerun a recipe. Wheel/sdist public staging, Python
3.11 grammar, JSON, two updated skill frontmatters, local documentation links/footer
checks and whitespace passed. Human guides, capability routing, recipe docs and
recipe/result-data skills document the change. Observation view 0.2.0 adds optional
identity_evidence; existing OS identity fields and result-index collection_user keep
their meanings. Raw/retention schemas, normalizer digests, stored data and operation
outcomes are unchanged. No real-host execution, private configuration, credentials,
commit, push or release occurred. Remote CI was not run.


## Prominent replication health verification

On 2026-10-24, Python 3.11.15, 3.13.13 and 3.14.4 each passed 908 public tests.
Seven new test_replication_readability cases cover status-before-Contents, explicit
healthy/unhealthy/unknown/not-configured/mixed labels, cleanup/partial uncertainty,
per-instance/channel findings, two-column tables, zero versus unavailable delay,
complete historical evidence and immutable retained input. The existing database,
Vault and identity tests passed. An isolated installed wheel passed 55 related tests;
public source staging, wheel/sdist, Python 3.11 grammar, JSON, two skill frontmatters,
changed documentation targets/footers and whitespace checks passed.

Actual Obsidian 1.14.4 Reading view verified both a healthy green callout and an
unhealthy red status before Contents. Following the main Contents link showed its
independent status, readable two-column instance details and highlighted channel
findings. No app theme, global font setting, CSS or plugin was changed. Plain
Markdown keeps explicit status text even without callout support.

The user-requested Vault refresh succeeded for the selected private profile using
retention only. All 187 existing protected observation/retention files and 31 human
Markdown notes retained identical bytes; owned views were backed up before rebuild.
No host/SQL query, retention/schema/normalizer rewrite, private configuration change,
commit or push occurred. Human/agent docs and consumer/recipe presentation guidance
were updated. Remote CI was not run; native UI proof is for this installed reader.

## Live recipe summary identity regression

The raw renderer and saved observation tests missed metadata discarded by the
runner's compact live summary. The runner now projects role-aware identity evidence
from the complete report before reducing it. Two public CLI regression tests cover
single-host and batch execution, terminal, explicit JSON and piped output, confirmed
SSH fallback, missing identity, omitted private metadata and unchanged raw input.
The backend is synthetic; these tests do not connect to hosts.

Python 3.11.15, 3.13.13 and 3.14.4 each passed 910 public tests. Wheel/sdist
builds passed; 28 CLI/identity tests passed against the installed wheel outside the
checkout. Python 3.11 grammar, Markdown links/footers, skill metadata and diff
whitespace checks passed. A real local PTY
replayed an existing saved database result through the public recipes run entrypoint
with the backend replaced by that saved report. Completion displayed both database
and SSH roles. This is offline CLI evidence, not a new database or SSH check. The
independent fixture has no Vault entrypoint, so its copied historical publication
receipt cannot resolve a content path there. No profile or saved raw result was
rewritten. Compact JSON gains identity_evidence; retained/raw schemas are unchanged.
Human CLI/execution docs, the capability map and recipe skill now cover this path
and require verification through the public completion boundary. Remote CI and
real-host execution were not performed for this correction.

## Replication completion health and compact identity

Synthetic completion tests cover HEALTHY, UNHEALTHY, UNKNOWN, NOT CONFIGURED and
ERROR, mixed instances, cleanup uncertainty, query/connection failures, preserved
collection status, retention/publication failures and unchanged raw input. Unrelated
recipes and skipped/unsupported outcomes retain their previous labels. One database
instance displays DB; multiple instances retain their configuration names and
independent unknown identities. Public CLI tests cover single/batch TTY, JSON and
pipe summaries. Saved observation integration verifies live/history health parity,
optional replication_health and unchanged saved bytes. No raw/retention schema or
stored data migration is involved; observation view 0.2.0 adds an optional field.

The public CLI was also exercised offline for all five health labels and exit codes
with a synthetic backend; actual local PTY rendering showed the five labels and
compact single-instance identity. No host, credential, database, profile or Vault
operation was performed. The wheel/sdist built successfully, and 52 tests passed
against the installed wheel outside the checkout. Human guides, capability routing
and recipe/result-data skills describe the new presentation and evidence limits.
Final source discovery passed 916 tests on Python 3.13.13 and 3.14.4. Python
3.11.15 discovery ran 916 tests with one existing TUI layout assertion failure
(details pane width read as zero). That test plus the 52 affected tests passed
in an isolated 53-test recheck. The initial failure is preserved in evidence;
no unrelated TUI code/test was changed to suppress it. Grammar, documentation
links/footers, skill metadata, schema JSON and diff whitespace checks passed.
Remote CI and real-host execution were not run.

## Batch consumer finalization verification

Python 3.11.15, 3.13.13 and 3.14.4 each passed 922 public tests, including the
pending health/identity presentation changes. Six added consumer tests cover batch
acknowledgements, deterministic snapshot order, disabled backlog, no-op redispatch,
ordinary exception/returned failure with all-event retry, secret-text omission,
interruption leaving running attempts, skipped acknowledgements, events arriving
during execution, invalid mode/missing batch entrypoint, and a public recipes run
regression with 30 selected hosts, two synthetic successes and 28 skips. All 33
events remain individually acknowledged; finalization does two Vault rebuilds.
Per-event consumers retain existing failure isolation, source checks and semantics.

A matching empty-profile benchmark measured 33 versus two final Vault rebuilds,
and 1.753 versus 0.257 seconds after the final synthetic backend returned. Two-host
execution also performs two final rebuilds. These are local timing samples rather
than managed-profile performance guarantees. The backend was replaced explicitly;
real event journaling, consumer dispatch and Vault rendering ran in independent
temporary profiles. Progress logs show finalization stages and total seconds.
No managed host, real credential, private profile or database was accessed.

Wheel/sdist builds and 99 installed-package tests outside the checkout passed.
Python 3.11 grammar, descriptor/schema JSON/YAML, Markdown links/footers, skill
metadata and diff whitespace checks passed. Human guides, capability map, consumer
catalog and recipe/result-data skills document delivery: batch, execute_batch,
per-event receipts/retry, snapshot boundaries and retained timeout/lock limits.
No event history was pruned; no retention storage migration or private configuration
change is required. Remote CI, commit, push and release were not performed.


## Published SSHScript 7.0.0 verification

On 2026-10-26, the selected OpsFeast Python 3.14.4 environment was reinstalled from the verified published 7.0.0 wheel without dependency upgrades. Its 32 package/type files and complete eight-file skill payload match the previously supported development snapshot. Requirements, built distribution metadata, release source provenance and bundled/agent-local complete skill copies now identify the official release. CPython 3.11.15, 3.12.12, 3.13.13 and 3.14.4 each passed all 1,017 OpsFeast tests, including isolated wheel/sdist delivery. The other interpreters used the same installed pure-Python package with their existing compatible native dependencies; no other environment was upgraded. Full readiness, pip check, CLI version, skill validation and the documented credential-free stdin quickstart with strict cleanup passed. No managed-host SSH/su/sudo, remote CI, profile migration, commit or push was performed. See [release identity and limits](../docs/sshscript-7.md).

*Last modified: 2026-10-26 12:17:54*
