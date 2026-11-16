For login-to-river handoff, use [browser readiness 0.1.0](browser-events.md): open the exact river so login retains its scoped next URL, then continue already-authorized work without waiting for a "logged in" reply. The reader reports `reader.opened` and the owner controller pushes `browser_event` on its existing stdout; this is readiness evidence, never approval or automatic model wakeup. Separate installations use namespaced authentication/editing cookies.

For system profiling, first use `opsfeast.profiling.catalog()` or
`opsfeast.py profiling describe --json` to discover partial integrations and gaps.
Use `inspect_host(profile, host_id)` / `profiling show --profile NAME --host HOST
--json` for retained values, failures and original times; Web exposes the same read
model under each host's 系統全貌 tab. These data-only reads do not acquire, install,
schedule or establish readiness. Recipe authors may reuse `recipe.profile`;
full datasets still use retention query/show. See [profiling 0.1.0](profiling.md)
for schemas, pagination, provider extension, prerequisites and verification.

For per-installation Web ports and agent ownership, follow [Web endpoint 0.2.0](web-server.md): External installation-data `web-server.json` stores the port; first launch allocates it, `--port N` persists an explicit choice, and the returned URL is authoritative. Reuse `opsfeast.web_settings.read_port/configure_port/bind_server` for checkout-level operations; occupied ports never authorize stopping an unidentified process.

For agent website operations, use the [memory-only owner controller](agent-owner.md): independent highest Web capability, administrator/password setup, API requests and Console workers without token files. Human authorization remains required.

# Reuse OpsFeast tools and Python modules

Host notes now expose structured `recipe_references` and `tags` through existing
inspect/mutate, CLI and HTTP surfaces. Use exact recipe filtering with general
notes for pre-run experience discovery; repeated tag filters require all tags.
See [metadata contract and examples](host-notes.md#relate-notes-to-recipes).


[Recipe execution experience](../skills/opsfeast-recipes/references/execution-experience.md)
uses existing host-note inspect/mutate and saved-result/retention APIs. Agents
read applicable experience before work and propose evidence-linked notes after
new findings; shared verified methods enter recipe code/tests. This is a procedural
skill, not automatic runtime learning. The shared inventory collector additionally supports
old lsblk rejecting JSON through bounded `-P` parsing; see its recipe guide.


For Linux hosts whose `ip` rejects `-j`, bundled inventory 0.4.2 supports bounded
text address/route queries without installing tools. Reuse the existing inventory
runner and [documented capability handling](../recipes/system/inventory/overview/README.md#linux-iproute2-capabilities-042).
Terminal partial summaries name missing property paths; `observation result ID`
reads saved causes and original probe evidence without connecting.


Profile registration descriptions are editable through
`profiles show/set-description`, `Instance.profiles.set_description` and
administrator `PATCH /api/v1/profiles`. Reuse the revision-checked
`opsfeast.profile_settings.update` helper; metadata edits do not open a management
root or connect to hosts. See [Profile description contract](profiles.md#profile-descriptions).


For one task involving multiple hosts, use [shared task river 0.1.0](shared-console.md): create declared targets through the existing record API, attach separate workers with `session` / `--session`, and preserve each block's target_id. The reader offers 全部/host TABs, independently toggles each host’s blocks open/closed without reordering (dark consistently means all applicable blocks are open, including 全部), and places time first in both states. A far-right ↓/↑ toggle opens/closes each block; open blocks show ↗ full-content links immediately to its left. Per-target activity and exact host-history membership are implemented; source metadata grants no execution permission.

For first-use recovery, an installation with no administrator and no agent control
provides a copyable instruction for the original chat. Follow
[Web startup verification](getting-started.md#include-and-launch-the-web-workspace);
HTTP availability alone is insufficient for administrator onboarding. After startup, call controller `admin.setup-form` (owner-only POST `/api/v1/agent/setup-form`) and present the private short-lived link; the human enters credentials only in Web. Browser-only claim/submit APIs validate one-use authority, browser cookie and CSRF. Check setup completion without retrieving credentials. See [private first-account forms 0.1.0](web-administrator.md#private-first-account-form-010); existing accounts remain unchanged.

The [first-use Web guide](web-administrator.md#first-use-web-guide) opens directly on the homepage before an administrator exists. [Real host configuration](web-hosts.md) now provides administrator-only host creation, basic settings/group autocomplete and confirmed deletion through shared CLI/Python/HTTP interfaces. The old host draft helpers are test fixtures, not the active `/hosts` route.


## Interactive Console 0.1.0

An opt-in isolated `/interactive` page and `python -B -m opsfeast.interactive_client` expose persisted work snapshots, SSE deltas, exact plans, operator confirmation, checkpoints, feedback and text/table analysis. Use [the canonical contract](interactive-console.md) and [agent skill](../skills/opsfeast-interactive/SKILL.md). SSHScript 7.0.1 is required for execution. Default Web startup enables no target; there is one live Console per process, no Python/program stdin or privilege UI, no automatic reconnect/replay, and no general logging/retention integration.

The [saved-data Web workspace](web-workspace.md) reads the selected Profile's actual
Recipe catalog, notification/todo objects, Retention summaries and Recipe/Console
history. Skills, textbook and guide pages show local source documents; settings
shows installed versions. Synthetic records, draft modules and browser-only
command playback have been removed. Empty, failed and partial reads stay distinct.
Saved-data views remain read-only; the confirmed recipe menu now adds execution. Lifecycle changes and data transfer retain
their existing Core/CLI authorization boundaries. General logging, issue tracking,
automatic upgrade and arbitrary Web app hosting remain unavailable.

## Local Web workspace

Use `python -B -u -m opsfeast.web --agent-control` with optional
`requirements-web.txt`; preserve the owner controller handle. The returned URL
uses the installation's saved or automatically allocated port. Follow the
[Web guide](../web/README.md) and [read-only data adapters](web-workspace.md)
for routes, authentication, Profile selection, summary schemas, pagination and
verification limits. `/` is public; private data requires administrator login or
the independent agent capability. Public guide/Skill/textbook source routes serve
only allowlisted Markdown, never private profile files. UI copy remains Traditional
Chinese until English translation is requested. Existing host/site/profile editors
retain their documented writes; data views do not run recipes or connect hosts.

## Official version checks and Settings hierarchy

Use [version checks and Agent handoff](web-updates.md): `opsfeast.updates.current`
reads installed evidence; `check` contacts fixed official sources, with PEP 440
stable release comparison and Git ancestry evidence. CLI: `python -B -m
opsfeast.updates show` / `check --product sshscript|opsfeast`; HTTP uses authenticated
GET `/api/v1/updates` and POST `/api/v1/updates/check`. No check applies an update.
After human confirmation, the page prepares an exact update instruction for the
human to send to their Agent. Preserve local edits and follow release/Skill support;
no automatic message delivery or model wakeup is implied.

[Settings catalog 0.2.0](web-settings.md) groups Site, Profiles and Bundle Recipes
as peers. Profile-owned Hosts/user Recipes/parameters/Retention have parent=profiles.
Bundle catalog reads use `scope=bundle` without a Profile; user catalog reads use
`scope=user&profile=NAME`. These are read-only catalog adapters, not new writers.

## Explain incomplete collection and recover saved IP references

Use [result diagnostics](result-diagnostics.md) through the existing
`observation result ID --profile NAME [--limit 50] [--json]` or checkout-level
`result_diagnostics.diagnose`. Unsupported properties and source failures are
separate evidence. Web host summaries and Recipe history link to the authenticated
latest/diagnosis adapters; no host query is performed. Reuse this classification
rather than building a second interpretation of partial results.

For missing IP projections from already saved inventory, use
`hosts refresh-ips --profile NAME --host HOST ... --json` or
`opsfeast.host_reference.refresh_from_saved`. It writes only derived reference
metadata after raw/retained provenance verification, never history or connection
settings. ESXi IPv4-only sources are supported and explicit; reference views omit
loopback. See [the reference-IP contract](host-reference-ips.md).

## Local administrator and profile configuration

A valid human session opening `/login` redirects to `/workspace` or the supported
local `next` destination; see [login behavior](web-administrator.md). Agent/site-edit
capabilities do not substitute for that human session.

Read [administrator/profile settings](web-administrator.md) before account or
profile changes. `/settings/site` includes owner-entered credentials; no defaults
are provisioned. `admin.status/verify/configure` and `settings admin show/set` share
private salted-password storage. Web sessions protect account changes and profile
APIs; local bootstrap capability cannot access profiles or change an existing
account. A separate 30-minute HttpOnly site-edit session restores editing and first-account setup across navigation; see [unlock/lock](site-presentation.md#local-web-editing-capability). It does not authorize host operations. `profile_settings.inspect/create/use/attach` reuses Core with registry
revisions; status does not verify connectivity. New Web roots are external; existing
profile roots and registry locations remain unchanged. Multiple accounts/agent
roles, profile rename/deletion and account recovery remain unimplemented.

## Persistent installation storage 0.1.0

Use [installation storage](installation-storage.md) for explicit separation and
upgrade-safe reuse of identity, site settings and images. `python -B -m
opsfeast.storage init --data-root ABSENT_ABSOLUTE_PATH` copies/verifies known
prototype data without deleting sources; `attach --data-root EXISTING_PATH`
connects a replacement checkout; `show` reports the selected root. Reuse checkout
`resolve_data_root`, `initialize_data_root` and `bind_data_root`. A broken binding
fails without fallback. Profile registrations and management roots are not moved;
protect them separately before removing product directories. Web/site APIs require
marked external data. No automatic format migration or independent backup is implied.

## Host account declaration editor 0.2.0

Reuse `opsfeast.host_settings.inspect/mutate`, its JSON CLI or the protected
`PATCH /api/v1/hosts` adapter for local account declarations. Send
`changes={"users":{"auditor":{"sudo":False}}}` to add/update sudo policy, or
`{"users":{"auditor":None}}` to remove a declaration under the user's scope.
Require explicit Profile/host and current revision; the writer validates the entire
Profile, preserves hidden fields during updates and backs up the defining source.
Snapshot `users` lists explicit declarations only; `login_user` is independent.
No remote account, password or host operation is performed. See
[host settings 0.2.0](web-hosts.md#account-declarations-020) for errors, examples,
compatibility and synthetic verification. Do not replace this with YAML editing
or credential manipulation scripts.

## Shared settings discovery and site CLI

Use [settings](web-settings.md), `/settings`, `GET /api/v1/settings/catalog`,
`opsfeast.settings.catalog()` or `python -B -m opsfeast.settings catalog` to see
actual availability. Site has Web/Python/HTTP plus `settings site show/update`
CLI interfaces, with required update revisions and selected-field preservation.
Profiles support admin-only status/create/attach/use through Core; see
[account/profile interfaces](web-administrator.md). Host configuration is implemented through the shared [host settings](web-hosts.md) service; recipe management/defaults and retention settings remain planned in this area. Reuse existing domain tools
within their own contracts. Bundled logo/avatar defaults are replaceable and do
not overwrite persistent custom image references.

## Installation presentation 0.1.0

Use `/settings/site` and [the site presentation guide](site-presentation.md) for
installation name inheritance/override, slogan and normalized PNG/JPEG logo/avatar.
The settings/images are public before login; editing requires the per-launch local
capability. Reuse checkout `opsfeast.site.read_site/public_site`,
`upload_image(installation, bytes)` and `save_site(installation, settings,
expected_revision=...)`; preserve UUID, existing name, profile namespace and other
presentation fields. Revision conflicts require rereading/reconciliation. Image
replacement/clearing does not delete old files. A single administrator is supported; no multi-user/agent roles, theme editor,
animated avatar or general Web extension API is provided.

## MySQL and MariaDB replica checks

Prefer [database/mysql/check/replication](../recipes/database/mysql/check/replication/README.md) for repeated replica-status checks. `opsfeast.py recipes run database/mysql/check/replication --profile NAME --host HOST --json` uses the supplied Core session, target python3 and mysql/mariadb batch clients. Configure instances, socket/TCP/TLS, protected credentials, expected source/channel mappings and delay policy through exact-reference recipe vars. It returns sanitized query/input/output/exit evidence, preserves unknown cleanup and defines registered mysql-replication 0.1.0 retention with builtin:vault current/full views. No extra SDK, native privilege escalation, source-host connection or database writes are used. Read the README for supported versions, permissions, failures, public tests and native verification limits. For new needs start with [exploration to reusable artifacts](../skills/opsfeast-recipes/references/exploration-to-recipe.md).


Use `opsfeast.py` as the public execution entrypoint: recipes run for reviewed operations/reports, inventory query/run for selective collection. The internal recipe_runner module owns shared execution/storage helpers and requires an explicit recipe. The standalone runner and snapshot inventory execution path are removed; inventory uses descriptor 0.3.0, inventory-jobs 0.1.0 and inventory-job-observations 0.1.0. See [the canonical execution guide](recipe-execution.md).


## Inventory collection service 0.1.0

Use [inventory jobs](inventory-jobs.md) and the recipe's [collection table](../recipes/system/inventory/overview/collection-plan.md) for property/job discovery, no-store utility queries, explicit saved refreshes, interval overrides and marked current-user cron management. `inventory describe/query/run/configure/status/dispatch/latest/cron` are implemented. `query` defaults to no OpsFeast writes; `--save` uses shared raw/retention/consumer infrastructure. Scheduling requires explicitly enabled inventory.yaml hosts and does not retry failures. This is a deterministic inventory scheduler, not a general job scheduler or AI heartbeat.

Checkout helpers are `inventory_jobs.catalog()`, `collect_host(root, host, properties=["storage.filesystems.used_percent"], save=False)`, `dispatch(root, dry_run=True)` and `latest_groups(records)`. Core `profile.retention.query/show` supplies retained input. The recipe owns jobs.py, details.py and capture.py for bounded original stream acquisition, plus fixed public YANG/extension definitions and inventory-job-observations 0.1.0 normalization; storage and consumer delivery remain shared. Per-property source times, actor scope, explicit gaps and identity warnings survive manual/periodic collection. New data.probes retains original stdout/stderr (262144 UTF-8 bytes per stream) with truncation flags; latest_groups attaches source_probes from the exact selected records and dependency probes. Read via retention query/show rather than scraping Markdown or reconnecting. Vault current pages show these in closed code disclosures; unavailable historical output stays unknown. No-store queries connect and can use the existing privilege policy; inspection/dry-run/latest reads do not connect. Linux-specific new probes and native verification limits are explicit in the guide. Full YANG datastore conformance is not claimed.


Top-level `opsfeast.py -h` groups commands into setup/profiles, hosts/access, recipes/reports, retention/consumers and Vault. These are reusable task areas, not enforced sequential stages or new command prefixes.

For command discovery, use `opsfeast.py COMMAND --help` or `opsfeast.py recipes SUBCOMMAND --help`: command purpose, local/remote effects, saved outputs and relevant examples precede parameter details. `recipes run` distinguishes host execution from offline reports, and jobs save/run distinguishes definition storage from execution. Reading help needs no selected profile and performs no operations. The [CLI reference](cli.md#read-what-a-command-does) remains the complete behavior/contract guide; no invocation or Core API changed in this help improvement.

Recipe discovery/selection supports variable-depth classified paths. Start with [taxonomy and relocation](recipe-taxonomy.md) and the [bundled recipes](../recipes/README.md); reuse the selected profile's recipes/ for user work and registered sources for shared work. Classification-only moves retain descriptor IDs and saved retention/event references. Exact path selectors and consumer subscriptions must use reviewed current references; no move command, path aliases or automatic private-data migration is implemented.

## Retention consumers

Use [consumer contract 0.1.0](retention-consumers.md) before authoring another retention handler/converter. Programs live in checkout `consumers/NAME` or `<profile-root>/consumers/NAME`, declare subscriptions in consumer.yaml and require explicit Feast registration except the default `builtin:vault`. Reuse `execute(context)` with `context.retention.query/show` and reviewed output publishers. `consumers list/show --recipe REFERENCE` and `recipes show` expose reverse dependencies without imports. `consumers inspect` reads durable attempts; `consumers dispatch [ID]` retries pending/running/failed events. All use --profile/--root and --json. Enabled code executes locally with controller privileges; no sandbox or timeout is provided.

Checkout `retention_consumers.catalog/related/inspect_deliveries/dispatch` are documented module interfaces, not Core SDK methods. Shared retention writes commit events in the annual transaction; dispatch runs after writes and records each consumer independently in content_update.consumers. Creation dedup, deletion tombstones, disabled backlog and at-least-once idempotency requirements apply. Prior eventless history needs explicit application rebuilds. See the [bundled Vault implementation](../consumers/vault/README.md) for installed requirements, output ownership and extension points. Synthetic tests and installed-wheel checks do not prove native connections or external delivery.

For textbook or consumer-Vault figure presentation, reuse [the approved figure convention and reference assets](figure-style.md) before designing new styling. This is authoring guidance, not a new Core API or automatic reader-style installer.

Bundled Vault initialization/full rebuild also performs [Obsidian reader setup](host-vault.md#automatic-obsidian-reader-setup): owned CSS publication and initial enablement, preserving other appearance preferences and later disabling. Reuse `vault rebuild`; there is no separate Core reader-installer API. Static inspect and group refresh do not configure reader assets. Validate the content receipt independently of retention.

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

For SSHScript import/distribution mismatch, duplicate metadata or source drift, reuse `tools/check_environment.py --json` with the failing interpreter. The checkout helper `sshscript_runtime.inspect_runtime()` supplies the same read-only diagnostic; it is not a new Core SDK service. Follow [reason codes, error contracts and authorized repair](runtime-troubleshooting.md) rather than writing another package scanner or editing hosts.yaml for an environment failure.

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

Prefer [Core API 0.1.0](core-api.md) and the [Core skill](../skills/opsfeast-core/SKILL.md) for installation identity/profiles, hosts snapshots, standalone sessions and scoped Recipe su/sudo, and read-only inspection. From the checkout root or an authorized installed package use `from opsfeast import Instance`; select `Instance.open(installation=...).profile(...)`. Core replaces the need for caller-managed tools import paths for these capabilities. Existing python-session recipes remain compatible; python-recipe entrypoints receive execute(recipe). Notification/todo services are implemented; use [the shared services](services.md). General logging remains deferred. See canonical examples, dependencies, error/lifecycle rules and copy/UUID policy in that guide.

For a complete temporary agent program, use [authorized Core operations](core-agent-operations.md): host-ID dictionary iteration, public imports, literal shell text, finite per-command budgets, original exception/cleanup evidence and conversion to a reusable recipe. No new API, implicit host authorization or automatic Core journaling is added.

`recipe.host_info` is the public read-only view of saved host-init OS/distribution,
kernel, architecture and optional login-PATH python3 version/executable, with the
original observation time. It returns a copied fixed-key dictionary with None for
unavailable values, never probes or depends on inventory, and reuses existing cache
validity rules. Refresh via authorized host-init; OS/Python/PATH freshness and other
interpreter environments are the user's responsibility. See [Core keys/example](core-api.md#saved-host-information)
and [probe/optional-failure semantics](host-diagnostics.md#initialize-platform-facts).

## Python reuse map

These modules live in `tools/` and use sibling imports. Put the selected trusted checkout's `tools/` on `sys.path` or `PYTHONPATH`; these checkout modules have internal or documented composition interfaces rather than the versioned Core API. The bundled package is installable; prefer Core for its supported operations. Use Python 3.11+ and the selected environment's dependencies. Configuration/catalog/results/exchange processing need PyYAML; operational interfaces additionally require matching SSHScript 7.0.1. Extra renderers/providers have their own dependencies. Pass filesystem arguments as `pathlib.Path` where the implementation expects paths.

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

For package/knowledge refresh, reuse the [SSHScript update prompt and procedure](skill-updates.md#update-sshscript-with-one-prompt), plus `check_environment.py` and `skill_bundle.py check/download`. They inspect readiness and stage complete public bundles; they do not install packages or apply updates automatically. The agent must honor the trusted checkout's exact supported version and learn matching references before using a new contract.

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

For a DevOps user needing an unimplemented capability, describe the gap and a concrete workflow within scope rather than inventing commands. For product developers, assess that gap as a candidate for reusable product support that reduces future user-side development; documenting a workaround alone does not fulfill that mission. General logging, additional execution backends, a live exchange, automatic installation/publication and a general scheduler remain planned. Recipient-selected analysis and richer report renderers can use documented data/report contracts; no general recipient database importer is bundled.

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

Prefer `opsfeast.py observation --profile NAME` for the batch index and `observation latest --status failed partial --profile NAME` to recover failed/incomplete hosts after completion output scrolls away. ID/latest selects one batch; --status without ID selects latest. This is independent of observation result (individual raw results). Checkout observation_cli.query(root, identifier=None, *, statuses=None) and render(view) expose compact view 0.2.0; complete data remains observation_runs.list_runs/show or Core retention.runs/run. Exact batch/host raw associations supply Result IDs for observation result, while missing/ambiguous links stay unavailable. Requires existing profile data and Python 3.11+, performs no collection/writes and returns read success independently of execution failure. [CLI selection/state semantics](cli.md#revisit-an-observation-batch) and [schema](../schemas/observation-view.schema.json) define latest, filters, counts, gaps and extension limits.

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

Current inventory records prioritize readability: records/SUMMARY.md indexes records/current-<title>.md, with host icons, topic-grouped values, complete name-sorted packages/services, Mermaid definitions and only nonempty Attention. Uncollected fields/sections and single cumulative I/O counters are omitted; zero/false/observed empty lists remain distinct. Full yearly reports preserve detailed sample/unit/source/time/state and collection metadata. Follow the source-report links and read structured retention instead of treating an omitted field as absence or health. See [current/report semantics](host-vault.md#recipe-retention-and-markdown).

Reuse vault_content.current_identity(record) for this checkout presentation grouping; it is not a Core API or retention query filter. Exact recipe-reference filters in retention APIs remain unchanged. Current selection groups each host by origin namespace, recipe-source qualifier (the prefix before a colon, or the unqualified source) and stable recipe ID, then selects the whole record with the greatest (observed_at, record_id). Recipe-directory moves within that source therefore keep one current page without aliases or rewriting historical references. Partial results remain partial. Distinct sources, origin namespaces or recipe IDs remain independent; a shared output title still fails publication explicitly rather than silently replacing another dataset. All historical reports remain available.

Vault Contents links use Obsidian-native heading fragments: `[System](#System)` and `[Collection metadata](#Collection%20metadata)`. Heading case is preserved and spaces/non-ASCII text are URL-encoded; arbitrary HTML anchor IDs are not used. Repeated headings are given unique readable titles (for example Services details) so each link reaches one section. In Obsidian Reading view, click a Contents link; in Live Preview, use the normal follow-link gesture (Cmd-click on macOS or Ctrl-click on Windows/Linux). Other Markdown readers can use different heading-fragment conventions; this is not a universal reader-compatibility guarantee. Rebuild regenerates current and historical observation pages plus the records index from retention, without recollection. See [Obsidian internal links](https://obsidian.md/help/links).

## Recipe policy, run evidence and readable content

| Need | Existing interface | Scope and limits |
| --- | --- | --- |
| Resolve recipe policy without reparsing YAML | Trusted checkout Validator.load/check_connections, then recipe_options(host, reference) | Returns copied merged enabled/vars; absent enabled means false. [Three layers and prefixes](recipe-sources.md). Host snapshots' declared recipes are not a replacement for effective policy; runner recipes use their supplied vars. |
| Read actual observation batches | inventory runs list/show; Core/report retention.runs()/run(run_id) | No connects/writes; exact UUID membership, immutable completed policy/findings. [Contract/schema/storage](observation-runs.md). |
| Compose an authorized producer batch | observation_runs.start(root, targets, reference, trigger="manual", selection=None), record_result(root, run_id, host, result), finish(root, run_id), publish_execution(root, run_id, exit_code, content_receipt) | Checkout services; initialize retention first, select/authorize explicit targets, reuse CLI/collector when possible. After completion dispatch content, then journal/publish the actual command result via publish_execution; use its returned code/receipt. Readers expose optional selection/execution; absent metadata is unknown, and collection status differs from command success/failure. No inferred/backfilled batches. |
| Reuse inventory threshold validation/evaluation | inventory_attention.resolve(value), evaluate(record, policy=None) | Inventory-owned pure checkout services returning resolved policy plus findings/assessed/disabled; finite samples and valid baselines required. Other recipes own their parameter/business validation. [Defaults/ranges](inventory-jobs.md#attention-thresholds). |
| Regenerate current/report/batch pages | vault rebuild; host_vault.rebuild; vault_content.build | Offline read/owned output, no retention changes or new collection. Current pages use current policy, batch pages use stored findings; Mermaid rendering is optional. [Ownership/rendering](host-vault.md). |

Use the existing Core/report readers for input and the documented checkout workflow for producer composition; there is no automatic run import/pruning/reconciliation service. New init opts inventory into bulk policy; old configurations need explicit enabled mappings. Synthetic public tests cover success, partial/failure/skip, rollback, disabled jumps, policy snapshots, generated links and chart-label safety. Python tests and standalone Mermaid rendering checks do not establish native SSH/privilege behavior or compatibility with every Markdown reader. See the current verification scope in the Vault guide.

Core/UI group catalogs apply the existing recognized-sensitive-field mask to nested recipe parameters. Explicit CLI dump remains raw. Do not reconstruct execution inputs from masked display snapshots; reuse resolved runner vars or authorized configuration services.

## Consistent batch completion results

`observation_cli.query` view 0.2.0 exposes effective host result_status and pre-filter result_counts alongside original host status/observation.counts (collection states). --status filters the effective result; known retention/content failures override collection and degraded access makes an otherwise successful result partial. Exact raw associations supply nullable collection_identity/access_degraded/content_status; missing/ambiguous raw files are explicit gaps, never another batch's actor or host state. Batch-only publication failures remain warnings. Existing immutable run storage is unchanged.

Checkout `console_output.execution_result(row)` returns `{status, text}` for known collection/retention/content/access fields; `execution_identity(row)` formats recorded access.actual_identity or unknown. Python 3.11+ CLI composition helpers are reused by completion and batch history, with no host execution or storage. Rendering tables still needs the standard console dependency. Use these helpers instead of rebuilding competing status rules; tests cover shared table rows, receipt failures, fallback, unknown evidence and read-only behavior. See [canonical view and filter rules](cli.md#revisit-an-observation-batch).

## Host results under observation

Use `opsfeast.py observation result [RESULT_ID]` for host history/diagnosis, `observation result RESULT_ID --detail` for full vertical evidence, and `--raw` for the original complete JSON. No ID lists host history with --host/--recipe-id/--status filters; --json returns structured index/diagnosis (selected --detail returns complete JSON). Use the original root/profile; successful reads return 0 independently of saved failure. Explicit --html exports a new index or selected --detail file without overwriting. These commands perform no collection or retry. `recipes results` is now offline-report-only; old host forms and --host are removed. Files and Result IDs remain unchanged. See [canonical modes, failures and verification limits](cli.md#host-result-history-and-modes).

Checkout readers `recipe_reports.results(..., kind=None)`, `show_result(..., kind=None)` and `result_diagnostics.diagnose(..., kind=None)` accept keyword-only kind="operation" or "report" for scoped reads. Default None preserves the combined reader used by the recipe browser; kind filtering does not change globally resolved short IDs. These are checkout composition helpers, not a new versioned Core API. Artifact verification remains report-only. Public synthetic tests cover separation, ID collisions, filters, wrong-kind failures, modes, read-only behavior, HTML conflicts and TUI forwarding; no host was rerun for this CLI change.

## Readable execution handoff

`recipes run` human TTY completion now supplies saved raw paths and successful readable Vault entrypoints after its compact ID table. JSON and pipe contracts remain unchanged. For agent-side composition use the checkout helper `host_vault.result_locations(profile.root, host=HOST_ID, record_id=RETAINED_RECORD_ID)` after checking the publication receipt. It returns existing manifest-owned index/host/current paths, with missing pages omitted; current means latest state. It performs read-only config/retention/manifest access, never rebuilds or connects, and rejects unsafe/symlink paths. Invalid configuration or record lookup can raise ConfigError/OSError; presentation must preserve the original execution outcome. This is a checkout module interface, not a new Core method. Follow [the handoff workflow](../skills/opsfeast-recipes/references/exploration-to-recipe.md#finish-the-user-handoff-not-just-the-program) to apply authorized private settings and provide actual copy/paste commands and result locations.

## Reuse proxy subprocess environment support

For differences between terminal, agent, cron and CI environments, start with
`tools/check_environment.py --json` and the [proxy environment guide](process-environment.md).
Configure connection.proxy_environment instead of mutating global os.environ or
rebuilding connection loops. Shared test-connection/Core/runner paths apply the
same child-only policy. Checkout process_environment.proxy_policy(overrides=None,
environ=...) returns explicit changes and value-free evidence; proxy_options is
the connection adapter. These are checkout interfaces, not versioned Core APIs.
Do not apply this proxy policy to remote shells or arbitrary recipe programs by
assumption. Synthetic/local process evidence does not prove real SSH connectivity.

## SSHScript 7.0 pinned runtime support

Use [the source contract and migration guide](sshscript-7.md) for current operational
support. Core/runner/test-connection share the published sshscript==7.0.1 requirement and reviewed release identity and
32-file validation; the version label alone is insufficient. Checkout
sshscript_runtime.source_identity() returns value-free source evidence without
network/Session creation; require_source(module) is the internal execution guard.
Do not recreate connection resolvers or bypass the guard to support another build.
Use parent_key_filename/proxy_command in Python; host YAML retains identity_file
and proxy_command. Public Console, command results and ownership remain library
interfaces, with native local checks and explicit real-host verification limits.

## Read collection accounts across service boundaries

Reuse checkout console_output.execution_identities(raw) for role-tagged evidence,
and execution_identity(raw) for the shared completion/history label. Supported
sources are access.actual_identity, mysql-replication data.instances[].server.
authenticated_user (CURRENT_USER()), and connected/login_identity with source
ssh_connection. The latter is a transport login, not an OS execution identity.
Observation view 0.2.0 adds identity_evidence while preserving OS-only
collection_identity. See [CLI semantics](cli.md#role-aware-collection-identity).
recipes run includes projected identity_evidence in compact single/batch summaries
before it removes full recipe/connection metadata, preserving live/history parity.
Single-instance identity uses DB; multiple instances include their configuration names.
Replication completion/history projects HEALTHY/UNHEALTHY/UNKNOWN/NOT CONFIGURED/ERROR
from saved findings; reuse console_output.replication_health and execution_result.
See [completion health semantics](cli.md#replication-completion-health).
Do not infer service identities from input vars, configured users or SSH accounts,
or reconnect solely to replace an unknown display value.

## Render replication health without obscuring failures

Reuse vault_content.replication_summary/replication_lines through the existing
Vault renderer and authorized vault rebuild. [Current replication views](host-vault.md#replication-status-must-be-visible-first)
put an overall status before Contents, display every instance independently, and
use explicit text/icons plus native callout colors. Details/channels use vertical
two-column tables. Saved health, cleanup and incomplete-record state determine the
summary; do not invent new thresholds, turn unknown into healthy or treat unhealthy
as missing collection. No additional SQL, retention/schema migration or global
reader settings are needed. Full sanitized evidence remains in historical reports.

## Batch consumers and recipe finalization

For a current-state publisher, reuse the [explicit batch consumer interface](retention-consumers.md#batch-delivery-for-current-state-publishers)
rather than adding a recipe/runner-specific publication branch. Declare delivery:
batch and implement execute_batch(context), reading context.events and the shared
retention facade. Event mode keeps execute(context). Both modes retain per-event
attempts, acknowledgements and at-least-once retry; failures never become success.
Builtin Vault uses batch delivery. Do not delete skipped-host history, bypass locks
or alter timeout merely to speed completion. Recipe TTY/--verbose stderr reports
finalization stages and total seconds; --quiet suppresses it. Per-host completed
messages precede that work. Two final dispatches preserve collection and command
outcome publication; they are not one rebuild per selected host. Inspect consumers
and delivery receipts for failures/backlog, without rerunning host operations.


## Shared service and backup capability catalog

| Need | Reuse | Availability and limits |
| --- | --- | --- |
| Notification/todo objects and human lifecycle | `profile.services`, `recipe.services`, consumer `context.services`; `services inspect/list/show/update/history` | [Contract/API 0.1.0](services.md), Python 3.11+, normal dependencies; platform revision/ownership control, source evidence, no automatic execution |
| Presentation and notification delivery | `services dispatch`, builtin:vault, builtin:smtp, reviewed local modules | [Adapter/config contract 0.1.0](service-adapters.md); static inspect does not import/send; explicit external authorization and private provider settings; unknown retry may duplicate |
| Backup-directory checks | `opsfeast.backup_check.descriptor(identity)` / `.execute(recipe)` | [Profile-local setup and inputs](backup-file-checks.md), target POSIX Python 3.8+, supported SSHScript 7.0.1; metadata only, no deletion/content integrity; backup-files-check retention 0.1.0 |
| Convert backup findings into service conditions | builtin:backup-check batch consumer; `opsfeast.backup_policy` implementation | Explicit opt-in [consumer](../consumers/backup-check/README.md), shared context services, live evidence gating; no host reconnection |

Prefer the complete documented workflows to direct internal SQLite/dispatcher helpers. Read configuration and object schemas before service changes; preserve independent raw/retention/consumer/service/provider outcomes. Canonical guides include errors, source review, extension rules and evidence limits. Public reproducible tests cover these contracts; real SSH backup flow is verified, actual SMTP delivery and native FreeBSD scanning are not.


## Portable units and source-independent contracts

| Task | Reuse | Essential boundary |
| --- | --- | --- |
| Define a user's structured dataset | retention mode: portable, embedded data_schema; opsfeast.data_contract | [Dialect/API](portable-contracts.md); recipe performs domain checks, replay/import never execute normalizers |
| Copy/import observations or retention independently | profile.transfer, opsfeast.transfer.Space, transfer CLI | [Unit/package 0.1.0](portability.md); origin-preserving merge/replace, reviewed plan digest, no historical effects |
| Free active storage | transfer archive-plan/archive/resume | Fixed source-time cutoff, external verified package, selected deletion/VACUUM, protected evidence and durable receipts |
| Install/update/coexist/rollback recipes | recipes pack/unpack 0.2.0; opsfeast.recipe_install; transfer recipe-* | Explicit files/dependencies, path conflict plan, exact references for repeated IDs, atomic exchange on macOS/Linux, pinned general-operation/report trees |
| Build complete backup user recipe | opsfeast.backup_check.portable_files(identity) | Scanner/validator/schema/optional consumer source included; receiver settings and consumer activation remain explicit |

Read [portability](portability.md) for exact invocations, storage, recovery, API signatures, failure/content receipts and verified limits. Imports expose saved data without requiring producer installation. Do not use old inventory-only exchange as the generic data transfer/import mechanism or recreate archival using export plus unchecked deletion.


## Recipe assessments and execution account

Reuse the runner/Core recipe-execution 0.1.0 service for login/su/sudo selection and verified cleanup; use optional recipe-assessment 0.1.0 for human finding labels. Supported surfaces are exact-reference execution configuration, `Profile.recipe(..., execution=...)`, `Recipe.execution(policy)` and returned assessment objects. [Results and accounts](recipe-results-and-accounts.md) documents signatures, schemas, failure behavior, portability, transport and tests. These are bundled platform capabilities; arbitrary runner/backend account adapters remain unsupported.

## Physical inventory and independent RAID checks

Prefer [system/storage/inventory/disks-raid 0.4.0](../recipes/system/storage/inventory/disks-raid/README.md). Configure human intent with expected_disks: {data: 4}, boot_policy: mirrored-ssd-pair, and optional expected_raids: 2. No controller FQDD or RAID name is a configuration key. Data counts include every non-boot physical disk across controllers, including spare, unconfigured and standalone drives; physical counts are not derived from RAID membership. The boot pair stays included and can be expected even when its controller disappears. Source hardware IDs remain diagnostic evidence and RAID display names.

Reuse `opsfeast.py recipes run system/storage/inventory/disks-raid --profile NAME --host HOST --json`. Local RACADM is preferred for physical/controller/VD reads; PERC/LSU have explicit source limits. Physical inventory/count/health survive a failed RAID query; role uncertainty and RAID failure stay independent. Healthy Ready/spare/Non-RAID states are not forced to Online. Saved role/usage/count/source health and independent RAID policy/findings feed retention/Vault. Mismatch/unverified configured counts and unknown/unhealthy required evidence yield non-success. No installation, repair, notification or scheduling is implied. Native ESXi RACADM and synthetic spare/standalone cases are distinguished in the recipe.

## Last successful host reference IPs 0.1.0

For “list hosts and their known IPs”, prefer `opsfeast.py hosts list --profile NAME
--json` or `hosts show HOST --profile NAME --json`; Core authors use
`profile.hosts.reference_ips(host_id)`. No connection, DNS lookup, history scan or
write occurs. Inventory recipe 0.4.1 supplies both address families from its
successful interface probe after a saved run. Failures, unrelated selections and
no-store queries preserve previous references. No primary address or connection
endpoint is inferred. See [contract, availability, examples and source limits](host-reference-ips.md).
Use retention APIs for historical network analysis; no backfill/replay refresh,
TTL, automatic recollection or ESXi/old-Linux probe compatibility is added.


## Chat-owned Console worker 0.3.0

The live reader preserves private-input focus and unsent text during polling and
streamed updates, and pauses automatic following while those controls have focus.
Refreshing clears unsent input; see [private-input behavior](console-secrets.md).

For incremental human-directed shell work, follow the [interactive skill](../skills/opsfeast-interactive/SKILL.md) and [chat-shell procedure](../skills/opsfeast-interactive/references/chat-shell.md). These define river-first startup, same-shell continuity, timely acknowledgements, no routine login screenshots and Python-preferred substantive analysis; prompt/input share one command block with shell input rendered as a valid escaped `$(...)` Console expression, active source-reported work displays a processing indicator, and normally terminated nonzero commands retain the shell while waiting for the next instruction.

Use `python -B -u -m opsfeast.console_agent --token-file FILE --host HOST [--profile NAME]` for incremental human/agent interaction. [Canonical startup and JSON-lines controls](console-agent.md) cover create-before-connect, connect/run/sudo/interrupt/close, immediate output, runtime sudo/su/leave and cleanup. The worker publishes initial command/output text in the first write and the HTTP service notifies SSE readers on commit, before command completion. The worker records its connection API call, readable login result and actual SSHScript prompt; raw SSH banners/remote PS1 are not exposed. Identity JSON stays outside river content with a readable toolbar summary. PTY control input avoids canonical-line truncation and restores terminal settings at exit. The worker owns one same-thread Console and publishes to existing block/SSE handlers; no temporary bridge is required. Python/SSHScript 7.0.1 and a running authenticated loopback Web record service are required. Runtime account changes use scoped authorizations without startup flags, reconnects or new rivers; [switching](console-agent.md#runtime-account-switching-worker-030) covers current-actor sudo, target-account su, private missing-password input, nested identities and leave. Optional purpose records concise intent before commands. Entered text programs use enter/input/poll/leave, with explicit readiness states. Private input uses the authenticated ephemeral broker; see [worker operations](console-agent.md#entered-programs-and-private-input-worker-030) and [secret delivery 0.1.0](console-secrets.md). No browser command endpoint, automatic reconnect/replay, arbitrary Python, model wakeup or recipe retention is supplied.

Omit `--profile` to use `.opsfeast.yaml` `default_profile`; use an explicit name only for a selected override. Check the returned `profile` and `hosts_file` before connecting. Invalid selection fails without fallback or changing the registry; local mode does not load a profile.

## Console blocks and human replies 0.2.0

Below the latest visible block, the river distinguishes source-reported agent thinking from running work.
Reuse `Records.activity(sid, {event_id,state,lease_seconds})`, writer-authorized
`POST /api/v1/console-sessions/{sid}/activity`, or `console_client activity`.
See [activity contracts](console-records.md#agent-thinking-and-chat-handoff) for
120-second worker handoffs, 1–300-second explicit leases, idle-before-chat rules,
activity-only SSE events, expiry and absence of a chat/model heartbeat. No extra
SSH operation, output block or remote polling is needed.

[Console blocks](console-records.md) provides HTTP/CLI block creation, idempotent
byte-offset append, bounded snapshot/SSE previews, paged content readers and
administrator-cookie form replies. `console_client wait/responses` delivers saved
human responses to a waiting agent client without model wakeup. Browser users need
login only; no extra reader unlock. Use [the agent skill](../skills/opsfeast-console-records/SKILL.md).
The host's Console 紀錄 tab discovers both human-directed and agent-led records
through administrator-only `GET /api/v1/console-sessions?profile=lab&host_id=web-01`.
Reuse checkout-level `Records.list_sessions('lab / web-01', limit=25, before=None)`
for exact-target local summaries; see [history contracts and availability](console-records.md#discover-saved-console-history-by-host).
No transcript body, live-connection assertion, host connection or command replay is
part of discovery. Existing 0.2.0 worker sessions require no data rewrite.
It does not execute SSH, stop jobs, render arbitrary HTML/media or integrate recipe
logging/retention. Old 0.1 data stays untouched but is not served by the new API.

The live reader `/console/{sid}` and read-only `/console/{sid}/history` are
session-specific views. History links open separately, disable SSE/form submission
and bound expansion to the loaded snapshot's byte sizes. Breadcrumbs/titles expose
target/task/session; optional exact-match Profile/host query context supplies return
navigation without selecting execution. Reuse [reader-mode contracts](console-records.md#separate-live-interaction-from-historical-reading), not a global current-tab/current-host selector.

## Host knowledge notes

For host-specific advice or diagnosis, use the [accumulated-evidence workflow](host-notes.md#answer-host-questions-from-accumulated-evidence) before drawing conclusions: combine host notes, saved observation results, inventory latest and selected retention history through their existing read interfaces. Preserve sample times, failures, scope and conflicting claims. Report missing/inaccessible sources; memory alone does not establish that records were queried. This procedure adds no search service or collection authorization. Use recorded facts to search relevant authoritative documentation (for example, FreeBSD guidance after identifying FreeBSD). If direct and indirect information remain insufficient, ask the user for the missing facts or propose an interactive Console inspection, reusing existing authorization within scope.

Reuse `opsfeast.host_notes.inspect/mutate` or `opsfeast.py host-notes` for private host knowledge; do not invent a parallel store or edit generated Vault pages. [Host notes 0.1.0](host-notes.md) defines UUID/source/timestamp, shared Web/CLI/HTTP operations, revision conflicts, atomic merge/delete and confirmation workflows. Read relevant notes before operations and ask after Console work whether to extract a draft; save only after final human confirmation. No automatic semantic merge, history or TUI editor is implemented.


## Linux profiling collection and specialized retained views

Reuse [local-users](../recipes/system/account/inventory/local-users/README.md) and
[process snapshot](../recipes/system/process/inventory/snapshot/README.md) through
recipes run after host/read authorization. Both use Python-recipe 0.1.0, controller
Python 3.11+/SSHScript 7.0.1, target Linux/Python 3.8+, and selected-actor access.
They do not install or escalate. Product module
`opsfeast.linux_profile.collect(recipe, kind)` reuses the supplied scope for these
two acquisition kinds; it is not an arbitrary probe loader. Defaults: max_items
1000 (1–5000), command timeout 20 seconds (1–120, capped by Recipe timeout).
Returns ordinary recipe results plus final portable data, per-dataset scope/time/
completeness/reasons; transport/invalid-response failures remain raw failures.

Profiling now reads disks-raid 0.4.0, mysql-replication 0.1.0 and both Linux portable
contracts alongside inventory-job-observations 0.1.0. Use the same profiling CLI,
Python and Web interfaces rather than rebuilding raw parsers. Specialized read
adapters are reviewed product code; retention/import never imports producers.
The [coverage review](profiling-coverage.md) and [provider guide](profiling.md)
record interfaces, extension points, scope/health distinctions and verification.


## Linux policy and logging/settings acquisition

Read [policy profiling 0.1.0](linux-policy-profiling.md) before writing SSH/sudo/
firewall/time/logging probes. Five bundled recipe paths and their scopes are listed
there; discover via recipes list/show or profiling describe. Use recipes run with
explicit --profile/--host/--json after the human's target/read authorization.
Controller Python 3.11+/SSHScript 7.0.1, target Linux/Python 3.8+ and existing
applicable tools/access are required. No install, escalation, settings writes or
schedules are implied. Query commands may create native audit/cache effects.

Reuse `opsfeast.linux_profile.collect(recipe, KIND)` for the five new reviewed
kinds, with the supplied Core Recipe; `linux_profile_schema.schema(KIND)` is the
portable definition embedded in each descriptor. Inputs are max_items and
command_timeout_seconds, plus strict optional ssh_context for ssh-policy. Missing
tools/permission, warning, syntax/parse, include/file/output/time limits are gaps.
Raw-only outer failures remain in recipe history. Web/CLI read the same retained
values with explicit basis/source scope and safe command/termination metadata.
New provider code is not needed for each row: reuse the reviewed retained-fields
adapter. This product service does not offer arbitrary remote probes or auto policy
reconciliation. See the guide for exact context/example, sensitive-field omissions,
limits and synthetic versus native verification.

## Web recipe menu and confirmed execution

Prefer the [menu/execution service 0.1.0](web-recipe-menu.md) for human Web selection
or an authorized agent using the existing owner controller. Discover with
`opsfeast.recipe_menu.menu(profile)` or GET `/api/v1/recipe-menu?profile=NAME`;
POST preview/start only within the user's actual target/effect grant. Exact
references, typed overrides, configured identity, dependency/effect evidence and
all 39 blueprint capabilities remain discoverable. The POSIX worker delegates to
`recipe_cli.execute`, including typed in-memory variables, without a second
connection/retention implementation. Preview does not connect/write; explicit
confirmation starts serial work, raw/retention/content receipts remain separate,
and stopping the local worker cannot prove remote cleanup. The guide documents
limits, errors, lifecycle, extension points and reproducible synthetic tests.

## Web inventory scope and report artifact readers

Use [Web menu scope/artifacts](web-recipe-menu.md) instead of writing a parallel
collector or artifact server. inventory_catalog exposes reviewed jobs/properties;
preview accepts optional inventory_selection jobs or properties, which is resolved,
fingerprinted and forwarded through the common executor. Hardware sensors are
explicit opt-in. Checkout recipe_cli.execute / recipe_runner.run/execute_hosts
accept the same optional selector; no new CLI flags or schedules are introduced.
Use GET /api/v1/reports and its result/artifact readers, or checkout
opsfeast.report_view.list_reports/show_report/read_artifact, for saved artifacts.
Requirements, exact inputs, byte limits, errors, profile/path/hash checks, static
HTML sandbox and extension rules are in the canonical guide. These are read-only
consumers; viewing never authorizes collection or consumer redispatch.

## Category-first recipe selection preview

The [current menu layout](web-recipe-menu.md#current-category-first-selection-preview-2026-11-10)
now presents domain scope summaries, separate Bundle/User selections, suggested
sets, individual/group/All host selection and a two-column plate. Main-page search/history/report-index controls stay hidden; the plate now has
scope selection and explicit review/confirmation. Saved run/report URLs and
existing authenticated APIs remain implemented. GET recipe-menu now returns safe
resolved groups and omits host login names. Selection is browser-only and grants
no authority to run; group/All resolves enabled hosts and deduplicates overlap.


## Recipe pages, defaults and reusable meals

Use [recipe library services](web-recipe-menu.md#authenticated-service-and-agent-workflow) for exact-reference declarations/history, nonsensitive typed Profile default edits, custom categories and nested, host-free user meals. These checkout facades and authenticated Web routes preserve revisions, private backups, original timestamps and existing default precedence. Do not create a parallel settings store or interpret saving/applying a meal as execution authorization.


## Recipe field tree and composition design

The [menu](web-recipe-menu.md#recipe-pages-defaults-categories-and-user-meals) now opens recipe titles in new tabs, displays scope notes inline, stacks Bundle before nonempty User lists, and nests dotted fields under closed disclosures. Exact-name field inputs appear beside that field; unmatched inputs stay common. Category creation/renaming stays on the menu. The implemented [routine/meal contract](recipe-routines.md) supplies split inventory recipes, shared host connections, guarded permission phases and independent retained child results.


## Implemented routine meals

Use [routines 0.1.0](recipe-routines.md), `opsfeast.routine_execution.describe/run_host`, `Recipe.child` and `opsfeast.inventory.service.collect/finalize`. They provide frozen definitions, static planning, guarded borrowing, one host connection, login/root ordering, independent retention and incomplete-run checkpoints. Overview is a meal of eleven child recipes, sensors excluded by default. Use these services instead of recreating connections or copying probes. Old execution tools are not silently batched. Native target applicability is not established by synthetic tests.

## Inventory child consumers and reports

Use [the inventory dependency map](inventory-consumers.md) for current
child references, exact report filters, subscription/read-filter updates and
unchanged historical ownership. Vault already subscribes to all observations;
backup-check has no inventory dependency. Retention-summary keeps exact filters;
execution-summary 0.1.3 preserves child/meal outcomes and routine/connection evidence.
Saved-result collection_user is unknown for mixed/unverified routine actors. Existing
Overview-only filters are not aliases for children; private configuration and
historical records are never rewritten automatically. These read/presentation
interfaces require no host access; explicit report, dispatch or rebuild writes
need the human's corresponding scope.



## Nested Web meal selections

Use [the menu contract](web-recipe-menu.md) for preferences 0.2.0. Domain disclosures start closed; Scopes describes the domain alongside Bundle/User recipe lists. Add meal IDs to the plate rather than flattening them. User meals save direct recipes, nested meal IDs and field scopes, never hosts; creation/deletion are supported, editing is deferred. Deletion atomically removes incoming user-meal references and retains empty parents. Use `opsfeast.menu_preferences.expand(profile, recipes, meals)` for current-definition expansion and field union before execution, or pass `meals` to the authenticated recipe preview API. Repeated exact recipes execute once per host; report recipes once locally. Cycles, missing references and conflicting options fail; changed definitions require renewed review. Reads/saving grant no execution authority. Old 0.1.0 preferences are preserved but unsupported; deliberate recreation is required, without automatic migration. Synthetic tests do not establish native SSH/privilege behavior.


Use [execution throttle](web-recipe-menu.md#execution-throttle-and-defaults-010): no fixed host/invocation count cap; default 8 parallel host lanes, sequential within each host. Installation settings and per-run threads are separate.



Execution defaults are discoverable through Settings → Execution and `opsfeast.execution_settings.inspect/save`, with GET/PUT `/api/v1/recipe-execution/settings` and `python -B -m opsfeast.execution_settings show/set`. Pass a positive integer `threads` with the confirmed start API for a temporary execution override. Default 8 is read without writes, defaults live in external installation data, and per-run overrides do not alter them. Threads changes do not require another preview; the plate confirmation still authorizes only the reviewed targets/recipes. Stop ends active owned workers and leaves queued hosts skipped; synthetic concurrency tests do not prove native SSH or remote cleanup. See [the full service/storage/CLI contract](web-recipe-menu.md#execution-throttle-and-defaults-010).

For human Web run inspection, prefer [the execution page/history](web-recipe-menu.md#execution-page-and-return-navigation): shared bounded progress, closed task cards, explicit incomplete-task/field diagnosis and `/recipes?profile=NAME&history=1`. Reuse GET recipe-runs and saved-result diagnosis; reopening never retries execution.



## Agent-led Web setup and handoff

For normal first-use installation, deliver [a verified running Web workspace](getting-started.md#include-and-launch-the-web-workspace) alongside CLI/optional TUI guidance. Reuse `opsfeast.storage` init/attach/show, `opsfeast.web_settings` port selection and `python -B -u -m opsfeast.web --agent-control`; these are existing services, not a new installer or daemon API. Plan Web dependencies, external data and process persistence before the single setup approval; then launch, verify GET `/` and `/api/v1/setup`, report `ready.url` and keep the controller alive. Preserve existing installation identity, credentials, Profiles and other listeners. No managed-host operation or OS service installation is implied; explicit no-Web scope and actual persistence blockers remain visible.



For authorized updates, follow [preserve installation state](update-preservation.md). Reuse external `web-server.json` (endpoint 0.2.0), the same administrator/identity/data root and every resolved Profile root; do not run init or replace menu/default/user-recipe files. Use `opsfeast.web_settings.read_port/configure_port/bind_server` with the resolved data root; `migrate_port` / `python -B -m opsfeast.web_settings migrate-port` is the explicit, backed-up old-registry port transfer only. Compare private before/after state, restore the same Web origin and keep service running. Saved categories, assignments, nested meals and field scopes remain unchanged; unsaved browser plates retain their tab/origin/root lifetime limits.

## Host-note document bundles 0.1.0

Reuse checkout module `opsfeast.note_bundles.create/inspect/read_file/export/delete` and its JSON module CLI for reviewed Profile-local Markdown/HTML report packages. The [canonical guide](host-note-attachments.md) covers stable IDs, revision/cleanup receipts, immutable copied assets, 65 MiB ZIP/64 MiB expanded bounds, safe Markdown images, scoped sandbox HTML/three.js preview and limitations. Browser preview serves local resources through a transient separate port; no uploaded program executes on the server, and no host or Recipe authorization is implied. Discover note summaries first and retrieve only necessary attachment files.

## OS package security 0.3.0

Reuse `system/software/inventory/os-packages`, `feast/report/package-security` and checkout service `opsfeast.package_security` before creating package scanners. The [canonical workflow](os-package-security.md) documents `collect(recipe)`, explicit `fetch/import_local/load`, offline `assess/generate/render` and the JSON module CLI. Collection needs selected-host authorization and SSHScript 7.0.1; vendor download and offline reporting are separate scopes. Debian/Ubuntu native source-version and declared-stream RHEL RPM analysis are implemented; Red Hat fetch is selected RHSA only. FreeBSD, Proxmox VE and ESXi have official native advisory comparison; unsupported distributions, stale/missing/partial data remain unknown. Preserve original sources, hashes, candidate/final status and limitations. No patching, compliance exporter or implicit latest-data lookup.

## Profile lifecycle and backups 0.1.0

Reuse `opsfeast.profile_settings.inspect/create/attach/detach/use/update` and `opsfeast.profile_transfer.export/import_archive/delete` with explicit registry revision and human scope. The [canonical contract](profile-management.md) documents the private ZIP manifest, bounds, SQLite transaction snapshots, external-reference limits, owned-candidate cleanup and recoverable delete. The Web adds authenticated lifecycle endpoints, idle-recipe guard and default-only daily navigation; explicit Core/CLI scopes remain. No vacuum, permanent purge, external-source acquisition or host execution is implied.

## Host-selected package security workflow 0.3.0

Prefer the bundled `bundle:package-security` menu meal / `system/software/check/package-security` operation when the human wants collection through report generation. Reuse checkout `opsfeast.package_security.pipeline.execute(recipe)` and [the canonical workflow](package-security-meal.md), not three disconnected invocations. It borrows one supplied host session, acquires/caches official controller-side advisories and invokes the existing offline report runner. Full inventory/stage evidence is retained; bounded CLI summaries and validated saved-report links keep transport small. RHEL optionally reads only existing DNF cache; stream/freshness/selection gaps remain explicit, never proof of safety. No patching, target metadata refresh or native-platform qualification is implied.

For collector 0.2.0 platform prerequisites, fixed native commands, `platform_details`,
`package_kind`, `packages_complete` and version limits, read [OS package platform support](os-package-platforms.md).
Reuse the collector for ESXi VIB/component metadata, FreeBSD base/kernel patch identity
and Proxmox VE product identification; missing commands remain explicit gaps. Older
0.1.0 inventory inputs must be recollected for the current report; do not rewrite
or delete old evidence. Inventory remains 0.2.0; report/run service 0.3.0 also provides native vendor advisory adapters.


For native vendor acquisition/assessment, read [vendor security 0.3.0](native-vendor-security.md).
Reuse `opsfeast.package_security.advisories.fetch/import_local/load` and
`analysis.assess`, or prefer the existing host-selected meal. FreeBSD uses
VuXML pkg ordering plus separate installed/running kernel and userland targets;
Proxmox uses staff PSAs and confirmed package/product branches; ESXi uses the
official paginated read-only search API and same-update build matrices.
`vendor_advisory_urls` is an optional official-source override in the meal;
missing/failed/unparsed/ambiguous/stale evidence stays unknown. Inspect stage,
retention and linked report receipts. No host execution or remediation follows
from source inspection, download or offline reporting.

For [Recipe activity names](web-workspace.md#recipe-activity-names), reuse the workspace logs API and
`opsfeast.recipe_activity` presentation helpers. Display saved picker/meal titles
with the exact recipe reference as secondary evidence. New Web runs snapshot
names; existing history is resolved read-only and never replayed or rewritten.

Activity summaries separate host completion, collection/advisory/report stages and
retention/downstream receipts. The list uses saved run metadata; selecting an entry
reads at most six incomplete-host result files and shows at most 20 incomplete hosts
with explicit omission counts. Missing raw evidence stays unknown. JSON remains in
the closed advanced disclosure. Reuse `recipe_activity.activity_summary` and the
existing workspace logs API; reads never reconnect, retry or rewrite observations.
Web date/time rendering uses the shared `formatDateTime`/`formatTime` helpers with
Asia/Taipei, seconds and the 00–23 hour cycle, including execution and Console views.

## Manual Web launch and process discovery

Reuse `tools/start_web.sh` and the ordinary `opsfeast.web` CLI for an authorized
local Web start. The shell helper selects the checkout `.venv` or absolute
`OPSFEAST_PYTHON`, forwards arguments and execs the actual server. CLI-owned
`opsfeast.web.process.claim(data_root)` exclusively reserves external
`web-server.pid` (plain PID, mode 0600), refuses live/dead/invalid existing markers
and removes only its own marker on orderly exit. See [launch/PID contract and
recovery](web-server.md#manual-shell-launcher-and-pid-marker). Verify process identity
and HTTP separately; never infer ownership, health or controller authority from a
PID or automatically kill/reinitialize. SIGKILL can leave a stale marker for
human-authorized agent recovery. This does not add a daemon installer or scheduler.

*Last modified: 2026-11-16 14:50:01*
