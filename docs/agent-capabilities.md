# Reuse OpsFeast tools and Python modules

Use `opsfeast.py` as the public execution entrypoint: recipes run for reviewed operations/reports, inventory query/run for selective collection. The internal recipe_runner module owns shared execution/storage helpers and requires an explicit recipe. The standalone runner and snapshot inventory execution path are removed; inventory uses descriptor 0.3.0, inventory-jobs 0.1.0 and inventory-job-observations 0.1.0. See [the canonical execution guide](recipe-execution.md).


## Inventory collection service 0.1.0

Use [inventory jobs](inventory-jobs.md) and the recipe's [collection table](../recipes/system/inventory/overview/collection-plan.md) for property/job discovery, no-store utility queries, explicit saved refreshes, interval overrides and marked current-user cron management. `inventory describe/query/run/configure/status/dispatch/latest/cron` are implemented. `query` defaults to no OpsFeast writes; `--save` uses shared raw/retention/consumer infrastructure. Scheduling requires explicitly enabled inventory.yaml hosts and does not retry failures. This is a deterministic inventory scheduler, not a general job scheduler or AI heartbeat.

Checkout helpers are `inventory_jobs.catalog()`, `collect_host(root, host, properties=["storage.filesystems.used_percent"], save=False)`, `dispatch(root, dry_run=True)` and `latest_groups(records)`. Core `profile.retention.query/show` supplies retained input. The recipe owns jobs.py, details.py and capture.py for bounded original stream acquisition, plus fixed public YANG/extension definitions and inventory-job-observations 0.1.0 normalization; storage and consumer delivery remain shared. Per-property source times, actor scope, explicit gaps and identity warnings survive manual/periodic collection. New data.probes retains original stdout/stderr (262144 UTF-8 bytes per stream) with truncation flags; latest_groups attaches source_probes from the exact selected records and dependency probes. Read via retention query/show rather than scraping Markdown or reconnecting. Vault current pages show these in closed code disclosures; unavailable historical output stays unknown. No-store queries connect and can use the existing privilege policy; inspection/dry-run/latest reads do not connect. Linux-specific new probes and native verification limits are explicit in the guide. Full YANG datastore conformance is not claimed.


Top-level `opsfeast.py -h` groups commands into setup/profiles, hosts/access, recipes/reports, retention/consumers and Vault. These are reusable task areas, not enforced sequential stages or new command prefixes.

For command discovery, use `opsfeast.py COMMAND --help` or `opsfeast.py recipes SUBCOMMAND --help`: command purpose, local/remote effects, saved outputs and relevant examples precede parameter details. `recipes run` distinguishes host execution from offline reports, and jobs save/run distinguishes definition storage from execution. Reading help needs no selected profile and performs no operations. The [CLI reference](cli.md#read-what-a-command-does) remains the complete behavior/contract guide; no invocation or Core API changed in this help improvement.

Recipe discovery/selection supports variable-depth classified paths. Start with [taxonomy and relocation](recipe-taxonomy.md) and the [five bundled recipes](../recipes/README.md); reuse the selected profile's recipes/ for user work and registered sources for shared work. Classification-only moves retain descriptor IDs and saved retention/event references. Exact path selectors and consumer subscriptions must use reviewed current references; no move command, path aliases or automatic private-data migration is implemented.

## Retention consumers

Use [consumer contract 0.1.0](retention-consumers.md) before authoring another retention handler/converter. Programs live in checkout `consumers/NAME` or `<profile-root>/consumers/NAME`, declare subscriptions in consumer.yaml and require explicit Feast registration except the default `builtin:vault`. Reuse `execute(context)` with `context.retention.query/show` and reviewed output publishers. `consumers list/show --recipe REFERENCE` and `recipes show` expose reverse dependencies without imports. `consumers inspect` reads durable attempts; `consumers dispatch [ID]` retries pending/running/failed events. All use --profile/--root and --json. Enabled code executes locally with controller privileges; no sandbox or timeout is provided.

Checkout `retention_consumers.catalog/related/inspect_deliveries/dispatch` are documented module interfaces, not Core SDK methods. Shared retention writes commit events in the annual transaction; dispatch runs after writes and records each consumer independently in content_update.consumers. Creation dedup, deletion tombstones, disabled backlog and at-least-once idempotency requirements apply. Prior eventless history needs explicit application rebuilds. See the [bundled Vault implementation](../consumers/vault/README.md) for installed requirements, output ownership and extension points. Synthetic tests and installed-wheel checks do not prove native connections or external delivery.

## Recipe retention and content applications

Vault content uses vault_content.host_location(runtime, host): one host tree under its first group, or the distinct _ungrouped bucket. Retention identity/storage is unchanged. Reuse full vault rebuild after changing primary groups to refresh host pages and all generated links; groups only updates membership links. Human notes remain at their original paths and require deliberate relocation/linking. Report headers show the host, while the historical report’s final Collection metadata section owns provenance/account/query details. See [content layout and note preservation](host-vault.md#directory-and-ownership).

For human page names, reuse vault_content.page_title/latest_filename/history_filename in the bundled content application. Titles belong to the consumer; source-qualified identities remain in historical report metadata. Current page names use only the current prefix and title; operation names retain short discriminators. Historical observation filenames use compact whole-second UTC time plus label, without UUID/hash suffixes for whole-snapshot observations; job observations and operation journals retain discriminators. These are checkout presentation helpers, not recipe-path or Core APIs; see [naming and replacement rules](host-vault.md#directory-and-ownership).

For collection provenance use the optional collection_evidence envelope, read through profile.retention or retention CLI; collection_evidence.capture/validate are checkout producer/validation helpers for local evidence 0.1.0. The runner captures verified actor and query metadata for inventory 0.3.2. Consumers must preserve missing historical evidence and distinguish base status from extended coverage. See [contracts, privacy and limits](retention.md#local-collection-evidence).

Vault observation Markdown uses shared vault_content.render_observation(record) with readable inventory sections, collection states/coverage and labeled source/record details; no model or remote command is needed. This is a checkout renderer, not a Core or data-contract API. Reuse vault rebuild --profile NAME --json to regenerate both history and latest pages from retained records, within authorized publication scope; do not edit generated pages or rerun host collection to restyle them. See [readable Vault content](host-vault.md#recipe-retention-and-markdown).

Start with [retention](retention.md) for discovery, data meaning and read interfaces. `recipes list/show` and `inspect-recipe` expose retention metadata. General creators declare host-values 0.2.0 with dataset/field descriptions and units; system/inventory/overview 0.3.2 declares inventory-observations 0.1.0 with creator-owned schema/normalizer. Discovery never synthesizes that declaration from recipe ID. `profile.retention.query/show`, checkout `retention_store.query/show/Reader` and `opsfeast.py retention list/show/export/inspect` read complete authoritative records without writing or connecting. Exact recipe-reference filters distinguish sources sharing an ID.

Replay through `retention ingest` / `retention_replay.ingest`; explicit deletion uses `retention delete-observation` / `retention_store.delete_observation`. Data rebuild uses `retention rebuild`. Reuse snapshot/provenance and protection logic; do not write deletion SQL or scanners. Current snapshots are data-only 0.2.0; old templates require explicit reviewed overrides. Write/unknown operation evidence remains protected.

`Instance.init_profile(name, namespace=...)` creates independent retention/vault areas. `host_vault.rebuild/refresh_groups/publish` manage content only; `vault_content` is the bundled author using public retention queries. `vault.auto_refresh` defaults true and can be disabled. Markdown uses local seconds, while data preserves original precision/statuses. Check separate retention/content receipts. Old SQLite-in-vault layouts are rejected and never moved automatically.

Offline `python-report` receives `context.retention.query/show` and keeps validated artifacts/results/jobs. [feast/report/retention-summary](../recipes/feast/report/retention-summary/README.md) produces Markdown and HTML from one or many retained recipe datasets with no raw dependency, connections, network/models or hosting. Use the same data for custom graph/web content. Reports record selected record IDs, source times and digests in retention_sources. [Vault ownership](host-vault.md#directory-and-ownership) protects unmanaged human files and separate authors. Regeneration overwrites manifest-owned generated outputs even after editing or editor formatting; obsolete owned outputs are removed.

This guide is for **DevOps users and their agents** operating OpsFeast or authoring specialized recipes. OpsFeast product developers have the complementary mission to reduce user-side development by providing complete, broad and stable tools/modules; see [the two roles](vision.md#distinguish-product-developers-from-devops-users). Both roles use reviewed programs for repeated work so AI can focus on new needs, judgment, changes and exceptions.

OpsFeast accumulates reusable operational knowledge and executable capabilities. Before writing a parser, connection wrapper, discovery scanner, result store, exporter or recurring script, look for an existing tool, recipe or module here. Start with the [skill index](../skills/README.md), select the relevant skill, then use the [CLI reference](cli.md) and the task's canonical guide. This reference describes the current checkout; it does not make every internal Python function a stable public SDK.

Inventory raw files now use UTC start-second prefixes with UUIDs; old files remain valid. Reuse observation result or recipe_reports results/show_result, which read both naming formats and sort by stored timestamps, instead of writing a filename-specific scanner. See [raw result names](cli.md#compact-execution-summaries).

Console presentation uses the checkout-level [console_output helpers](../tools/console_output.py): TTY tables, explicit --json precedence and preserved non-TTY/raw-data contracts. See [the command-specific policy](cli.md#terminal-tables-and-json) before choosing agent invocations. Rendering does not authorize operations, and is not a versioned Core API. Reuse console_output.table(headers, rows) for terminal-cell-aware wrapping of headers and values; no extra width flag is needed. Width is recalculated per render, and many-column views use labeled records when too narrow. Existing already escaped display rows can use render_table(headers, rows), as check-access does. JSON and non-TTY contracts remain unchanged; raw data must not be regenerated from wrapped text.

Registered data semantics live in the owning recipe: [inventory retention](../recipes/system/inventory/overview/README.md#recipe-owned-retention-contract) supplies retention.py and retention.schema.json. Checkout `retention_contracts.validate_declaration/normalize/validate_payload` select supported contract/version implementations; static discovery only reads metadata/schema/digests. Inventory raw snapshots bind both normalizer and schema; missing/drifting snapshots need explicit reviewed --recipe-dir. Candidate normalizer imports are unsupported. Users reuse runner/replay/query interfaces rather than writing storage or adapter-selection code.

## Decide what to reuse

1. Identify the requested outcome, selected Feast/targets/data and existing authorization. Discover relevant capabilities without running operations: recipe catalog/inspection, published contracts and implementation sources are the starting points.
2. Prefer an existing compatible recipe or CLI command for the complete task. Use structured JSON output for automation; do not scrape human text or replace the command's validation and result interpretation.
3. When developing Python that needs in-process data or composition, reuse an applicable module below. Inspect its current signature, dependencies, return values and caller/tests. For runner-managed recipes, use supplied Sessions/contexts rather than implementing a second configuration/connection lifecycle.
4. Check actual environment, configuration and input readiness. Static compatibility is not proof of execution readiness. A listed write/connection interface is not permission to run it.
5. Implement only the missing task-specific logic. If an existing capability is unsuitable, explain the concrete gap (contract, behavior, dependency, platform, user-selected tool or authorization constraint), reuse the parts that fit, and preserve a reviewed recipe/helper for repetition. Do not require an LLM to recreate working code on ordinary reruns.

Reuse is a default decision rule, not a requirement to force an unsuitable tool. User-selected tools and environment constraints take precedence. Do not independently recreate established include rules, recipe selectors, typed-input overlays, identity semantics, storage schemas, archive validation or artifact checks merely because the agent can generate code for them.

## Task-to-tool catalog

Commands below are command families, not permission grants or complete copyable invocations. Consult the linked guide for exact arguments, defaults, exit codes and effects. Use the selected interpreter with `-B` from the trusted checkout.

| Need | Existing interface to try first | Evidence and limits |
| --- | --- | --- |
| Check interpreter/dependencies and skill snapshot | `tools/check_environment.py` | Read-only readiness check; no installation or connection. [Setup](getting-started.md) |
| Create/select/register a Feast | `tools/opsfeast.py init`, `profiles`, `attach`, `detach`, `use` | Registry/scaffold changes are distinct from host operations. [Profiles](profiles.md) |
| Load/validate/query host settings | `opsfeast.py check`, `dump`; `opsfeast.Validator` | Includes/path/duplicate checks; dump exposes raw selected values. [Configuration Python interface](hosts-yaml.md#read-host-configuration-from-python) |
| Find recipes and inspect compatibility | `opsfeast.py recipes list/show`, `inspect-recipe` | Static metadata/signatures only; no recipe import, connection or dependency installation. [Catalog](recipe-experience.md#discovery-and-selection) |
| Initialize facts or test configured access | `opsfeast.py host-init`, `test-connection`, `test-host`, `test-su`, `test-sudo`, `check-access` | Real local/SSH operations and possible privilege attempts; use the appropriate narrow scope. check-access tests login plus independent su/enabled sudo for other declared users, using Boolean sudo policy (false disables; true/omission enables; strings rejected), with a tabulate per-test status/host/test/user/reason table (configured host icon or default 🍎; ❌ on failure; tabulate[widechars] 0.10.0 supplies Unicode alignment) and stderr progress; inventory collection uses the two-candidate su/sudo policy, with safe login fallback; add --json --quiet for full machine-readable evidence. [Diagnostics](host-diagnostics.md), [inventory access](inventory-access.md) |
| Obtain a root console in a user recipe | `with recipe.root() as root: root("id -u", check=True)` | Public Core API: shared two-candidate policy, verified UID 0 or RootUnavailableError, callable scoped console and automatic restoration. No silent user fallback; [API, errors and examples](core-api.md#automatic-root-console). |
| Run an operation with inputs/targets | `opsfeast.py recipes run` | Existing selection, typed vars, sessions, cleanup and results; Inventory uses the job collector; independent check-access makes real diagnostic connections. [Execution](recipe-execution.md), [sources](recipe-sources.md) |
| Author identity/license defaults | `tools/recipe_identity.py defaults`; `recipe_identity.defaults()` | Read installation-level defaults; reserved Bundle attribution remains protected. [Attribution](recipe-attribution.md) |
| Generate offline reports/basic HTML | `opsfeast.py recipes run feast/report/execution-summary`, catalog/results `--html` | Local report execution writes artifacts; renderer code requires review. No dummy host needed. [Reports](recipe-experience.md#offline-report-contract) |
| Find saved results/verify artifacts | `opsfeast.py observation result`, `recipes results list/show`, `recipes artifact` | Read-only lookup and digest/path checks; no viewer launch or publication. [Results](recipe-experience.md#results-and-artifacts) |
| Recover/export/validate/combine observations | `tools/observation_store.py ingest/export/validate/combine` | Ingest writes; JSON/CSV export reads retained data; combination preserves history. No transmission or foreign raw ingestion. [Data contracts](result-data.md), [CSV](inventory-access.md) |
| Package/review a portable recipe candidate | `opsfeast.py recipes pack/unpack` | Explicit allowlist and integrity/path checks; creates files/candidate, no installation or publisher authentication. [Bundles](recipe-experience.md#portable-recipe-bundles) |
| Save/rerun reviewed work | `opsfeast.py recipes jobs save/list/show/run` | Private bindings and content verification; run executes again. No bundled scheduler. [Jobs](recipe-experience.md#saved-jobs-and-recurring-work) |
| Check/stage public SSHScript skill updates | `tools/skill_bundle.py check/download` | Authorized network download/check only; no activation or package upgrade. [Skill updates](skill-updates.md) |

The shared loader resolves host/account icons using entry hosts.yaml `default.icon.user`, `default.icon.host`, per-group `groups.<name>.icon.user/host`, and named-account `default.users.<account>.icon` (built-ins 👤/🍎). Explicit host/account icons override defaults; named-account defaults then precede group user defaults. For each remaining field independently, the first configured value in host group order precedes the global default. Optional default.users.<account>.email is readable source metadata (CLI dump), without host-account inheritance or notification behavior. Icons must be one Unicode Symbol code point. Core/CLI/runner share effective values without rewriting YAML. See [host icon contract](hosts-yaml.md#host-icon); it is display metadata, not host identity.

## Public Core Python API

Prefer [Core API 0.1.0](core-api.md) and the [Core skill](../skills/opsfeast-core/SKILL.md) for installation identity/profiles, hosts snapshots, standalone sessions and scoped Recipe su/sudo, and read-only inspection. From the checkout root or an authorized installed package use `from opsfeast import Instance`; select `Instance.open(installation=...).profile(...)`. Core replaces the need for caller-managed tools import paths for these capabilities. Existing python-session recipes remain compatible; python-recipe entrypoints receive execute(recipe). Logging/notifications remain deferred. See canonical examples, dependencies, error/lifecycle rules and copy/UUID policy in that guide.

## Python reuse map

These modules live in `tools/` and use sibling imports. Put the selected trusted checkout's `tools/` on `sys.path` or `PYTHONPATH`; these checkout modules have internal or documented composition interfaces rather than the versioned Core API. The bundled package is installable; prefer Core for its supported operations. Use Python 3.11+ and the selected environment's dependencies. Configuration/catalog/results/exchange processing need PyYAML; operational interfaces additionally require matching SSHScript 5.0.0. Extra renderers/providers have their own dependencies. Pass filesystem arguments as `pathlib.Path` where the implementation expects paths.

| Module and current interface | Reusable result or behavior | Caller responsibility |
| --- | --- | --- |
| `opsfeast.resolve_root(root=None, profile=None)`; `Validator(root).load(path)` / `.check_connections()` / `.check()` | Feast selection and merged, validated settings | See the [complete loading example](hosts-yaml.md#read-host-configuration-from-python). Secrets remain raw; do not log settings. |
| `recipe_runner.run(root, host, timeout=30, *, recipe=REFERENCE, explicit_host=True, observation_run_id=None, ...)`; `execute_hosts(root, recipe, invocation, json_output=False)` | Explicit host execution or shared batch CLI workflow | Internal checkout services, not a stable installed SDK; inventory always delegates to inventory_jobs.collect_host. No main/parser/snapshot fallback. Bulk callers pass explicit_host=False; a containing batch passes observation_run_id. Preserve actor scope, raw/retention/content receipts and exit status. |
| `recipe_catalog.catalog(root=None, query=None, kind=None)`; `choose(root, selector)` | Catalog dict with sources/recipes/status; selected recipe dict | `root=None` scans checkout only. Inspect errors and selected `runnable`; ambiguous IDs fail. `choose` alone does not enforce execution readiness. |
| `recipe_inspection.inspect_recipes(value=None, requested=())` | Static recipe/platform inspection report | Check report errors/coverage, not merely the presence of a descriptor. See [inspection](cli.md#inspect-recipes-and-platform-gaps). |
| `recipe_inputs.cli_variables(metadata, values=None, assignments=())`; `prepare_vars(metadata, source_vars, host_vars, cli_vars=None)` | Parsed assignments and validated independent effective-vars dict | Preparation deep-merges defaults/source/resolved recipe settings/CLI; lists replace and caller passes the right layers. Runner already does this for recipes. `RecipeContext` has only `host_id` and `vars`. |
| `recipe_identity.defaults(root=ROOT)` | Normalized author/contacts/license dict | `root` is the installation checkout, not the Feast. Preserve reserved attribution and packaging obligations. |
| `recipe_reports.results(root, recipe=None, host=None, status=None, *, kind=None)`; `show_result(root, identifier, *, kind=None)`; `show_artifact(root, identifier, name)` | Result index (including nullable collection_user with preserved identity quality), raw document or verified artifact metadata/path | Inspect partial/errors and source times; obtain identifiers from the index. Artifact names are declared relative paths. These reads do not execute or publish. |
| `observation_store.export(root, *, recipe=None, hosts=None, since=None, until=None)`; `validate_exchange(bundle)`; `combine(bundles)` | Exchange dict; validated record count; validated deduplicated union | Export reads the existing database, missing storage fails. Time filters use observation completion time. Preserve identity quality and conflicts. JSON values are input objects, not filenames. CSV is a CLI presentation surface. |
| `management_view.masked(value)`; `hosts_snapshot()`; `profiles_snapshot()` | Masked local UI read models | Snapshots use this checkout's registry/default profile, not a supplied root. Inspect message/status fields; masking recognizes key names and is not a guarantee against arbitrary secret content. Do not substitute masked settings for execution configuration. |
| `root_access.candidates(config, host, login)`; `root_actor(session, config, host, timeout, report, *, authenticated_user=None, preflight=None)` | Shared strict two-candidate root acquisition and verified restoration | Internal checkout helper; prefer public Recipe.root() for agent composition. Inventory's collection_actor adapter alone provides safe login fallback. See [selection/evidence](inventory-access.md#inventory-account-selection) and [public console API](core-api.md#automatic-root-console). |
| `inventory_values.validate_inventory(data)` | Validation of the partitioned inventory-values contract | Use the [inventory access/results contract](inventory-access.md); this does not validate a complete raw or exchange envelope. |
| `recipe_jobs.listing(root)`; `load(root, name, verify=True)` | Saved names/definition with default content verification | `verify=False` is inspection only, not permission to execute changed content. Use CLI jobs save/run for invocation preparation and execution. |

For writes and host operations, prefer the complete CLI/runner workflow: `opsfeast.py recipes run`, `recipe_reports.run_report`, `recipe_packages.pack/unpack`, `recipe_jobs.save`, `observation_store.retain`, `host_runtime` and `access_check` are implementation owners, not interchangeable task shortcuts. Direct composition must preserve their prerequisites, caller preparation, target selection, enabled flags, cleanup, storage and failure rules. For example, CLI ingest validates an eligible batch before a transaction; calling `retain` in a loop does not provide that batch guarantee. Do not bypass the workflow merely to import a lower-level function. Use the canonical task contracts and public synthetic tests before proposing a new adapter.

## Minimal read-only composition example

After adding the checkout's tools directory as in the [configuration example](hosts-yaml.md#read-host-configuration-from-python), a standalone program can reuse discovery and result lookup without generating scanners:

```python
from opsfeast import resolve_root
from recipe_catalog import catalog
from recipe_reports import results

available = catalog(query="port", kind="operation")  # Checkout-only discovery.
if available["status"] != "success":
    raise RuntimeError("Recipe discovery needs review")

root = resolve_root(profile="main").resolve()  # Select an existing registered Feast.
index = results(root, status="success")
if index["errors"]:
    raise RuntimeError("Some saved results could not be read")
# Consume available["recipes"] and index["results"] locally.
# A recorded success is execution evidence, not proof that a service is healthy.
```

Choose profile/root from invocation inputs in reusable programs; `main` here illustrates an explicit selection. This example neither runs a recipe nor verifies live host readiness. Check each function's result states and catch `ConfigError`/filesystem or database failures at the application's boundary with secret-safe messages. Missing files, failed inspection and unsupported contracts must not silently fall back to a homemade parser or stale embedded configuration.

## Extend and maintain the learning path

For a DevOps user needing an unimplemented capability, describe the gap and a concrete workflow within scope rather than inventing commands. For product developers, assess that gap as a candidate for reusable product support that reduces future user-side development; documenting a workaround alone does not fulfill that mission. Logging/notification services, additional execution backends, a live exchange, automatic installation/publication and a general scheduler remain planned. Recipient-selected analysis and richer report renderers can use documented data/report contracts; no general recipient database importer is bundled.

Every added or changed usable capability must update its canonical guide, this map where applicable, relevant skill routing and examples in the same delivery. Include supported versions, availability/dependency checks, exact CLI and/or Python interface, inputs/outputs, effects, failure/skipped states, extension points and verification limits. Record when a module is internal or an interface has changed. Remove obsolete “planned” claims when implementation is delivered, and do not confuse recipe version, descriptor version and result/data-contract version.

The [development principle](vision.md#make-existing-capabilities-the-first-choice-for-agents) and [contributor gate](../AGENTS.md#before-every-commit) make agent knowledge transfer part of functionality delivery. Documentation is a procedure, not an automatic loader or enforcement mechanism; agents must read the current sources and installation copies need the [update procedure](skill-updates.md).

Connection-only batch diagnostics are available through `test-connection --all --profile NAME` or `test-connection --group web database --profile NAME`; reuse this CLI before writing a connection loop. It preserves the existing single-host report, returns versioned batch JSON with --json, excludes disabled group/all members, validates selection before connections, and supplies automatic TTY progress/per-host tables. Combine --json --quiet for machine consumption. See [canonical syntax and result interpretation](cli.md#select-and-monitor-connection-tests) and the [hosts skill](../skills/opsfeast-hosts/SKILL.md#connection-selection-and-progress). This is a checkout CLI capability, not a new Core API or permission to connect.

## ESXi login identity

Reuse `check-access --host HOST --profile NAME --json --quiet` for login/root readiness; the shared `host_runtime.identity(session, timeout, console=False, target=None, verification=None, evidence=None)` checkout helper supplies OS-derived username/effective_uid and optional backend evidence on an already-authorized Session. Standard id is preferred; only missing id plus verified VMkernel selects the fixed system Python adapter. This adds no Core API/configuration field, installation or permission to connect/enter privileges. The access gate, diagnostics and existing Core identity checks reuse the helper. Read [prerequisites, canonical CLI/import examples, fields, errors, backend extension and verification limits](host-diagnostics.md#esxi-login-identity-without-id). Public tests are in tests/test_esxi_identity.py. One ESXi 7.0 root login passed; other releases/non-root access and native su/sudo/inventory remain unverified. Do not write a second ESXi identity probe in each recipe.

## Explicit SSH authentication sources

Reuse the shared planner through existing diagnostics, runner or Core sessions.
connection.allow_agent and connection.look_for_keys are strict Boolean settings,
both default false for each SSH hop and SSH config alias. Explicit credentials
remain usable; no password-dependent switching or automatic ambient fallback occurs.
Missing sources fail planning before any Session is created for that target chain,
with missing_authentication_source and a safe hint. Do not recreate authentication
selection in recipes. See [configuration and examples](hosts-yaml.md#ssh-authentication-sources),
[CLI](cli.md#ssh-authentication-source-selection) and [migration](migration.md#explicit-ssh-authentication-sources).
Synthetic policy/CLI/Core/runner tests do not establish native SSH agent behavior.

## Group catalog and bulk host definitions

Reuse the shared loader and `profile.hosts.groups()` for group metadata/membership.
Top-level groups can define label/description/icon and complete host mappings under
hosts; hosts become ordinary IDs usable by all existing execution APIs. The catalog
contains declared/implicit groups and member ID lists, including empty groups, without
nested credentials. The first effective host membership is primary; enclosing groups
are prepended and deduplicated. IDs drive selection; labels only affect presentation.
Do not write a second YAML expander or silently merge repeated hosts/group definitions.
Use check/dump groups for local CLI inspection, and the TUI for label/description
browsing. default.groups has moved; private migration requires review, not an automatic
rewrite. See [schema and examples](hosts-yaml.md#host-groups), [Core API](core-api.md#host-group-catalog),
[CLI](cli.md#group-catalog-and-bulk-host-definitions) and [migration](migration.md#group-catalog-and-bulk-host-definitions).
Configuration-only inspection does not authorize host operations.

## Human check overview

Reuse check for local configuration validation. Its interactive-terminal table now
lists group/host/users with catalog labels/descriptions, account icons, primary-group
and disabled-host markers. Groups sort by ID, and the known login is first without
a (login) suffix. Declared empty groups and ungrouped hosts remain visible;
unique host totals do not double-count repeated membership. This display does not
connect or resolve SSH aliases. Recipe selections are still validated. Agents should
continue selecting --json for the unchanged detailed report, including selected_recipes,
skipped and notes. Redirected text is unchanged. See [CLI display and interpretation](cli.md#human-check-overview).
This is a CLI presentation change; Core snapshots, selection and execution APIs are unchanged.

## ESXi SSH-exec identity diagnostics

Reuse check-access and the shared host_runtime identity probe for ESXi missing-id
SSH exec channels. In addition to exit 127, the exact recognized exit 2 missing-id
signature may reach the VMkernel/Python adapter. The access report now records the
initial id exit code and configured-account actual/expected UID comparison, preserving
the observed actor even on mismatch. An unequal UID can be accepted only by the verified ESXi root-shell model, keeping SSH login and shell identity separate. Other platforms and explicit privilege targets remain strict; root-shell access does not authorize new operations.
No new CLI flags or recipe-specific fallback are needed. See [canonical diagnosis,
boundaries and native evidence](host-diagnostics.md#diagnose-esxi-identity-failures).

## ESXi login/root-shell relationship

Reuse check-access, Core and runner connection verification rather than a per-recipe
UID bypass. The successful final-hop SSH username is recorded separately from the
observed shell. Verified VMkernel plus a stable UID 0 shell can accept an ordinary
login as esxi_root_shell; Linux/non-root/unknown-principal mismatches and explicit
su/sudo targets stay strict. Account policy and extra-user exclusion use login_identity;
shell_identity is the execution/restoration baseline. JSON and the identity table row
explain the accepted relationship. No flags, account rewrites or role inference are
required. See [canonical model and examples](host-diagnostics.md#ssh-login-and-esxi-root-shell-identity).

## Revisit observation batches

Prefer `opsfeast.py observation --profile NAME` for the batch index and `observation latest --status failed partial --profile NAME` to recover failed/incomplete hosts after completion output scrolls away. ID/latest selects one batch; --status without ID selects latest. This is independent of observation result (individual raw results). Checkout observation_cli.query(root, identifier=None, *, statuses=None) and render(view) expose compact view 0.1.0; complete data remains observation_runs.list_runs/show or Core retention.runs/run. Exact batch/host raw associations supply Result IDs for observation result, while missing/ambiguous links stay unavailable. Requires existing profile data and Python 3.11+, performs no collection/writes and returns read success independently of execution failure. [CLI selection/state semantics](cli.md#revisit-an-observation-batch) and [schema](../schemas/observation-view.schema.json) define latest, filters, counts, gaps and extension limits.

## Compact execution and host-specific result inspection

Runner/recipes run/jobs run TTY completion shows host, collection identity, result and result id; full access/data/path details stay in JSON and saved results. Reuse
`opsfeast.py observation result --host HOST --recipe-id inventory-system --root ROOT`,
then `observation result RESULT_ID --raw --root ROOT` for offline evidence with host_id.
Use --json for agent-facing lists or runs. See [output semantics and the complete viewing workflow](cli.md#compact-execution-summaries),
including unknown actors, failure/retention states and attempts with no saved result.
The result id is a collision-aware short ID accepted by observation result RESULT_ID; a dash means no saved result is available. Checkout recipe_reports.result_short_ids(root) maps saved result paths to the same IDs as results list without reading raw payloads; console_output reuses it only for human completion display. These are existing checkout CLI capabilities, not a new Core API or collection authorization.

## Focused saved-result diagnosis

Prefer `opsfeast.py observation result RESULT_ID --profile NAME` for human failure triage, then --detail/--raw for selected full evidence. Checkout `result_diagnostics.diagnose(root, identifier, *, limit=5, kind=None)` returns diagnosis 0.1.0; `format_diagnosis(report)` renders escaped concise text. Requires Python 3.11+, a selected existing management root and a saved raw result. Reuses the checked short/full-ID resolver; no connection, execution, retention/content writes or arbitrary recipe-data inference. Execution/receipt failures precede probe failures; outputs, issue counts and grouped gaps are bounded/explicit. Missing exception message/source details remain unknown. --json provides the same projection; read exit status is independent of saved execution outcome. See [CLI rules](cli.md#diagnose-a-saved-failure) and [schema](../schemas/result-diagnosis.schema.json).

## Vertical saved-result inspection

`opsfeast.py observation result [RESULT_ID] --detail` is a read-only vertical alternative
to the host index/raw view. Omit the ID for a newest-first index with --host/--recipe-id/--status;
provide the returned ID for one full raw result. Reuse --root/--profile and --json for
automation (same index/raw contracts). Human output is field: value even through a
pipe, without table dependencies. See [syntax, failures and verification limits](cli.md#vertical-result-details).
No new Core API, storage, remote operation or execution authorization is added.

## Resolve short saved-result IDs

Human observation result now uses short IDs accepted by observation result RESULT_ID in the
same root/profile. Reuse recipe_reports.results / show_result / result_path instead of
truncating filenames or implementing a separate lookup. Index JSON adds short_id while
retaining result_id; raw documents and their embedded UUIDs/paths are unchanged.
Prefix uniqueness spans the whole root before filters, and ambiguity/missing IDs fail.
Use complete result_id for durable references. See [canonical examples and algorithm](cli.md#short-result-ids)
for alias lifetime, collision/symlink failures and synthetic verification limits. These
remain checkout-level helpers, not a new versioned Core API or remote authorization.

Human TTY observation result shows collection user and status, omitting identity warnings; --json preserves quality and warnings. Use `observation result --json` or explicit --detail/--raw for complete warnings. Reuse the [console policy](cli.md#terminal-tables-and-json); do not delete warnings from saved results to shorten the display.

## Human timestamps and preserved data

Use existing CLI/TUI/HTML views for OS-local YYYY-MM-DD HH:MM:SS timestamps; do not
rewrite saved results to change timezone/precision. Human results list/detail and TUI
Details now apply the same policy as history; Home download time and bundled
feast/report/execution-summary 0.1.2 HTML do too. --json, raw show, Original output, JSON/CSV exports and
storage remain unchanged. Preserve originals for identity, ordering and analysis.
See [the canonical time policy and verification limits](cli.md#human-time-display-policy),
including unknown timezone handling and portable report formatting. Shared display
helpers remain internal, not a new Core API or remote service.

Current inventory records prioritize readability: records/SUMMARY.md indexes records/current-<title>.md, with host icons, topic-grouped values, complete name-sorted packages/services, optional DGMO definitions and only nonempty Attention. Uncollected fields/sections and single cumulative I/O counters are omitted; zero/false/observed empty lists remain distinct. Full yearly reports preserve detailed sample/unit/source/time/state and collection metadata. Follow the source-report links and read structured retention instead of treating an omitted field as absence or health. See [current/report semantics](host-vault.md#recipe-retention-and-markdown).

Reuse vault_content.current_identity(record) for this checkout presentation grouping; it is not a Core API or retention query filter. Exact recipe-reference filters in retention APIs remain unchanged. Current selection groups each host by origin namespace, recipe-source qualifier (the prefix before a colon, or the unqualified source) and stable recipe ID, then selects the whole record with the greatest (observed_at, record_id). Recipe-directory moves within that source therefore keep one current page without aliases or rewriting historical references. Partial results remain partial. Distinct sources, origin namespaces or recipe IDs remain independent; a shared output title still fails publication explicitly rather than silently replacing another dataset. All historical reports remain available.

Vault Contents links use Obsidian-native heading fragments: `[System](#System)` and `[Collection metadata](#Collection%20metadata)`. Heading case is preserved and spaces/non-ASCII text are URL-encoded; arbitrary HTML anchor IDs are not used. Repeated headings are given unique readable titles (for example Services details) so each link reaches one section. In Obsidian Reading view, click a Contents link; in Live Preview, use the normal follow-link gesture (Cmd-click on macOS or Ctrl-click on Windows/Linux). Other Markdown readers can use different heading-fragment conventions; this is not a universal reader-compatibility guarantee. Rebuild regenerates current and historical observation pages plus the records index from retention, without recollection. See [Obsidian internal links](https://obsidian.md/help/links).

## Recipe policy, run evidence and readable content

| Need | Existing interface | Scope and limits |
| --- | --- | --- |
| Resolve recipe policy without reparsing YAML | Trusted checkout Validator.load/check_connections, then recipe_options(host, reference) | Returns copied merged enabled/vars; absent enabled means false. [Three layers and prefixes](recipe-sources.md). Host snapshots' declared recipes are not a replacement for effective policy; runner recipes use their supplied vars. |
| Read actual observation batches | inventory runs list/show; Core/report retention.runs()/run(run_id) | No connects/writes; exact UUID membership, immutable completed policy/findings. [Contract/schema/storage](observation-runs.md). |
| Compose an authorized producer batch | observation_runs.start(root, targets, reference, trigger="manual", selection=None), record_result(root, run_id, host, result), finish(root, run_id), publish_execution(root, run_id, exit_code, content_receipt) | Checkout services; initialize retention first, select/authorize explicit targets, reuse CLI/collector when possible. After completion dispatch content, then journal/publish the actual command result via publish_execution; use its returned code/receipt. Readers expose optional selection/execution; absent metadata is unknown, and collection status differs from command success/failure. No inferred/backfilled batches. |
| Reuse inventory threshold validation/evaluation | inventory_attention.resolve(value), evaluate(record, policy=None) | Inventory-owned pure checkout services returning resolved policy plus findings/assessed/disabled; finite samples and valid baselines required. Other recipes own their parameter/business validation. [Defaults/ranges](inventory-jobs.md#attention-thresholds). |
| Regenerate current/report/batch pages | vault rebuild; host_vault.rebuild; vault_content.build | Offline read/owned output, no retention changes or new collection. Current pages use current policy, batch pages use stored findings; DGMO is optional. [Ownership/rendering](host-vault.md). |

Use the existing Core/report readers for input and the documented checkout workflow for producer composition; there is no automatic run import/pruning/reconciliation service. New init opts inventory into bulk policy; old configurations need explicit enabled mappings. Synthetic public tests cover success, partial/failure/skip, rollback, disabled jumps, policy snapshots, generated links and chart-label safety. Three supported Python-version test runs and local DGMO renderer checks do not establish native SSH/privilege or universal Obsidian-plugin behavior.

Core/UI group catalogs apply the existing recognized-sensitive-field mask to nested recipe parameters. Explicit CLI dump remains raw. Do not reconstruct execution inputs from masked display snapshots; reuse resolved runner vars or authorized configuration services.

## Host results under observation

Use `opsfeast.py observation result [RESULT_ID]` for host history/diagnosis, `observation result RESULT_ID --detail` for full vertical evidence, and `--raw` for the original complete JSON. No ID lists host history with --host/--recipe-id/--status filters; --json returns structured index/diagnosis (selected --detail returns complete JSON). Use the original root/profile; successful reads return 0 independently of saved failure. Explicit --html exports a new index or selected --detail file without overwriting. These commands perform no collection or retry. `recipes results` is now offline-report-only; old host forms and --host are removed. Files and Result IDs remain unchanged. See [canonical modes, failures and verification limits](cli.md#host-result-history-and-modes).

Checkout readers `recipe_reports.results(..., kind=None)`, `show_result(..., kind=None)` and `result_diagnostics.diagnose(..., kind=None)` accept keyword-only kind="operation" or "report" for scoped reads. Default None preserves the combined reader used by the recipe browser; kind filtering does not change globally resolved short IDs. These are checkout composition helpers, not a new versioned Core API. Artifact verification remains report-only. Public synthetic tests cover separation, ID collisions, filters, wrong-kind failures, modes, read-only behavior, HTML conflicts and TUI forwarding; no host was rerun for this CLI change.

_Last modified: 2026-10-21 12:30:58_
