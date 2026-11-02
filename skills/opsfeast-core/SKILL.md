---
name: opsfeast-core
description: Use the bundled OpsFeast Python API for installation identity, profiles, runtime hosts loading, scoped sessions and Recipe root/su/sudo, or read-only instance inspection. Use for standalone agent programs and python-recipe authoring; notification/todo services are shared by profiles and Recipes; general logging remains unavailable.
---

For bundled Vault reader setup, use the existing init/default Vault consumer or `vault rebuild`, following [automatic Obsidian reader setup](../../docs/host-vault.md#automatic-obsidian-reader-setup). First publication copies/enables the shared CSS; later rebuilds update owned CSS while preserving unrelated appearance settings and manual disabling. Inspect/groups remain read-only or group-only for this purpose. Do not generate a parallel installer or edit human notes. Malformed settings, unmanaged reserved-name collisions and symlinks are content failures; inspect the separate content receipt. Obsidian itself is installed separately, and user-created/textbook Vaults need agent-assisted reader setup. This does not authorize a live-profile rebuild or application installation by itself.

Use `opsfeast.py` as the public execution entrypoint: recipes run for reviewed operations/reports, inventory query/run for selective collection. The internal recipe_runner module owns shared execution/storage helpers and requires an explicit recipe. The standalone runner and snapshot inventory execution path are removed; inventory uses descriptor 0.3.0, inventory-jobs 0.1.0 and inventory-job-observations 0.1.0. See [the canonical execution guide](../../docs/recipe-execution.md).


Human terminal tables automatically wrap headers and complete values to the current terminal cell width; narrow multi-column views become labeled records. Reuse the shared console_output.table helper for new checkout summaries. Use --json where supported for agent parsing; wrapped text is presentation, not a data contract. See [console output policy](../../docs/cli.md#terminal-tables-and-json) for width lookup, redirected output and limits.

Top-level `opsfeast.py -h` groups setup/profiles, hosts/access, recipes/reports, retention/consumers and Vault for discovery. Reuse these task areas in any order; no extra command prefix or execution stage is introduced.

Use the selected CLI command's `--help` to first read its purpose, whether it reads/writes local data or connects/executes, and its examples; help itself requires no profile and performs no operations. Recipe/job subcommands have their own purpose text and complete usage prefixes. Continue with the [canonical CLI guide](../../docs/cli.md#read-what-a-command-does), current schemas and selected recipe/consumer guidance before execution. This help update changes descriptions, not authorization, invocation arguments, result formats or Python APIs.

Read [recipe taxonomy and relocation](../../docs/recipe-taxonomy.md) for the current bundle, variable-depth domain/subdomain/action/name convention and default agent-created recipe location. User-specific code goes in the selected profile-root/recipes/, selected by :classified/path; shared code uses a registered external source. The bundle move preserves IDs and data contracts but removes old path selectors. Update reviewed configuration, saved jobs and exact consumer/report references explicitly; preserve historical raw/retention/event references and do not generate aliases or rewrite user data. The inventory normalizer and retention schema keep their saved digest bindings. This is directory organization, not a general move tool or a tags/category metadata API.

For automatic retention handlers/converters, read [consumer contract 0.1.0](../../docs/retention-consumers.md) and the [bundled Vault consumer](../../consumers/vault/README.md). First discover existing programs with `consumers list --recipe system/inventory/overview --profile NAME --json` or `recipes show`. Sources are checkout consumers/NAME and Feast-local consumers/NAME; candidate discovery never activates code. Before enabling a reviewed program, verify its Python/dependencies, supported retention contracts, input sources, output ownership and authorized side effects. Register source/enabled explicitly in feast.yaml; default builtin:vault is already enabled. Author `execute(context)` with context.retention.query/show and metadata event hints, preserving partial/unknown/identity context. Outputs must tolerate at-least-once delivery, deletion and stale creation hints. Reuse the documented dispatcher rather than modifying runner, scanning raw files or writing SQL acknowledgement code. Inspect per-consumer status/attempts in content_update.consumers or `consumers inspect`; retry with `consumers dispatch [ID]`. Disabled backlog is processed after activation, while eventless historical data needs explicit application rebuild. In-process Python is not sandboxed or time-limited; no network delivery, installer or scheduler is implied.

For [single-administrator and profile settings](../../docs/web-administrator.md),
use `/settings/site` (站台設定), `/settings/profiles` and their documented APIs.
There are no default credentials: let the human enter their username/password
privately. Local token access can bootstrap only the first admin; account changes
require login/current password and invalidate sessions. Profile APIs require an
admin session, never the site token. Reuse `opsfeast.admin` and
`opsfeast.profile_settings` with revisions, or existing profile CLI. Status is
local configuration evidence, not connectivity. New roots use external data;
existing roots/registry locations remain unchanged. Never recreate or overwrite
an existing environment to satisfy a create request.

For Web/CLI/agent configuration, use the [shared settings guide](../../docs/web-settings.md)
and discover availability with `python -B -m opsfeast.settings catalog` or
`GET /api/v1/settings/catalog`. Site show/update are implemented, using the same
presentation services with required revisions; profile status/create/attach/use are implemented; host/recipe/default/retention
editing is still planned in this surface. Do not infer authority or usable write
APIs from category pages. Null custom logo/avatar references use bundled defaults;
user assets remain in persistent data, never replace product resources.

For persistent installation identity/site data across product upgrades, read
[storage 0.1.0](../../docs/installation-storage.md). Initialize an absent external
root explicitly with `python -B -m opsfeast.storage init --data-root PATH`, or
attach a known existing root on a replacement checkout with `storage attach`.
Never initialize a fresh identity when the intent is to reuse an installation.
Sources remain recovery copies; runtime never falls back to old site files.
Profile registries/management roots are not relocated. Inspect their actual paths
before any product-directory replacement. Site image/settings APIs accept the
marked data root or a bound checkout; Web also accepts an explicit `--data-root`.

For installation site name/slogan/logo/avatar, use the separate checkout module
`opsfeast.site` and [presentation 0.1.0](../../docs/site-presentation.md). It reuses
instance identity for name inheritance without altering the Core instance schema,
UUID, name or profile namespace. Read first with `read_site`, ingest authorized
PNG/JPEG through `upload_image`, then `save_site(..., expected_revision=...)`.
Public-before-login assets, revision conflict handling and local Web edit tokens
have explicit limits; these do not create user accounts or operational authority.

# Operate and compose OpsFeast Core

For real Web/CLI host creation, group autocomplete/updates and confirmed configuration deletion, use [host settings 0.1.0](../../docs/web-hosts.md). Reuse `opsfeast.host_settings.inspect/mutate` or its JSON CLI; require explicit profile/revision and deletion confirmation. No connection or secret/account/recipe-variable editing is performed. Preserve private source backups and fail on unsupported aliases.

## Headless Console integration

For chat-driven sessions use the shipped [Console worker](../../docs/console-agent.md); start it, immediately open its returned reader URL, then send connect/run/sudo/close controls. No temporary bridge is needed. Core `sessions.console(..., sudo_root=True)` explicitly opts into configured login-account sudo to root; the default denies managed switches. Optional `stdout`/`stderr` streams expose synchronous output too. This is trusted code, not an authorization sandbox.

Core now supplies `profile.sessions.console_target(host_id)` (read-only metadata/fingerprint) and the same-thread `profile.sessions.console(host_id, timeout=30, expected_fingerprint=...)` context manager over the shared configured connection. Read [protocol and limits](../../docs/interactive-console.md) and the [interactive skill](../opsfeast-interactive/SKILL.md). This is trusted code, not a sandbox; the Web adapter exposes shell jobs only and keeps operator approval separate from agent credentials.

The checkout [replay/deletion interfaces](../../docs/retention-replay.md#modules-and-schemas) are available alongside the Core API. `operation_intent` may link source_observation_id; linked write/unknown evidence is protected. Default offline general replay uses a saved data-declaration snapshot and never executes a Core/session operation.

## Recipe retention and content applications

Read [retention contracts](../../docs/retention.md), [offline replay/protection](../../docs/retention-replay.md) and [vault ownership](../../docs/host-vault.md). Recipe creators define/produce retention; OpsFeast manages recipes/execution and data discovery/storage. User AI agents combine retention into Markdown, graphs or web content. Vault is the bundled content application, not the data contract.

1. Discover declared datasets with recipes list/show or inspect-recipe --json. Read field meanings, units, versions, limits and source-qualified references before selecting data; metadata is not execution evidence.
2. Query with `retention list/show/export --profile NAME --json`, Core `profile.retention.query/show`, or checkout `retention_store.query/show`. Annual authoritative SQLite lives in retention/; reads never initialize or connect. Preserve source times, origins, identity warnings, partial/unknown states and zero/false values.
3. Authors declare host-values 0.2.0 with dataset/field descriptions; system/inventory/overview 0.3.1 owns inventory-observations 0.1.0, its schema and registered normalizer. Discovery reads the explicit declaration; it never guesses from recipe ID. Retention snapshots 0.2.0 contain data definitions only. No markdown_template or rendered Markdown is retained.
   Read [inventory-owned data semantics](../../recipes/system/inventory/overview/README.md#recipe-owned-retention-contract) before authoring or interpreting inventory: explicit access_mode/retention declaration, recipe-local schema, normalizer/schema digests, supported versions and partial/identity limits. Registered contract/version selects shipped pure normalization; candidate main.py/retention.py is never loaded by replay. A new user-defined structured contract should use mode: portable with an embedded data_schema; product-registered bundled normalizers remain available for their own contracts. Replay never loads descriptor executable paths. Reuse runner/replay/query; include retention.schema.json in portable clone bundles. Current envelopes preserve retention_definition and source provenance.
4. Reuse offline python-report's `context.retention.query/show` and artifact/result/job support for content. [feast/report/retention-summary](../../recipes/feast/report/retention-summary/README.md) generates Markdown and HTML and combines multiple recipe references without raw access or connections. Custom renderers declare dependencies and verification; no hosting or transmission is implied.
5. Use retention ingest/delete-observation/rebuild for data and vault rebuild/groups/inspect for content. Replay does not execute recipe code. Write/unknown operations and linked evidence remain protected. Direct Core calls need explicit retention_store.operation_intent/operation_result journaling.
6. Init establishes namespace plus independent retention/vault areas. vault.auto_refresh defaults true and may be disabled. Check recipe status, retention and content_update separately; consumer failure preserves stored data and is retried with consumers dispatch; explicit vault rebuild regenerates current Vault content. Old vault SQLite layouts are rejected and preserved; use a separate profile and explicitly replay raw. Old inventory raw without snapshots, old template snapshots and structured normalizer/schema digest mismatches need a reviewed current --recipe-dir; never reclassify historical execution.

Terminal summaries now use tabulate when stdout is a TTY. For agents, explicitly add `--json` to supported diagnostic, instance, profile/check, recipe/job execution and utility commands; non-TTY output retains existing contracts. Dump/raw results/artifacts/exports remain structured. Check-access retains its existing default table. Read [the command-specific output policy](../../docs/cli.md#terminal-tables-and-json); flags change presentation only, not authorization or saved-job inputs.

After every OpsFeast release update, reread the installed release's current object schemas/data contracts, including hosts.yaml, before resuming work, regardless of diffs or earlier reading. Follow the [mandatory release reading list](../../docs/skill-updates.md#required-schema-reread-after-a-release-update). No reading receipt or completion verification is required.

Read the [Core API contract and examples](../../docs/core-api.md) for exact signatures, installation, lifecycle, storage, errors and verification limits. API/identity schema 0.1.0, python-recipe runner 0.1.0, descriptor 0.3.0; Python 3.11+, PyYAML 6.0.3, and matching SSHScript 7.0.1 only for execution. Use the selected interpreter and trusted installation; do not install/upgrade solely to inspect.

## Identify the instance and scope

An instance is an installation/checkout, not feasts/ or an individual management root. Open with `Instance.open(installation=...)`; inspect and select its active or explicit profile. Selection is fixed for an operation even if another process switches active profile. Multiple installations/profiles may coexist in a program; never change a process-global default to select one.

A new clone or copy into another directory must receive a new UUID. Use explicit initialization on that copy, never relocate its identity. Copy detection uses the recorded resolved path; same-path copies on another machine require explicit renewal. Only an actual move of the original installation uses relocate_identity to preserve UUID. The UUID ending in 000000000001 is reserved for the original development installation; it must not propagate to copies. Missing UUID uses the standard all-zero placeholder, with inspection exposing placeholder/reason; the user accepts duplicate-identity risk. Name is required/default UUID and description optional; names are not unique or authentication evidence. Assigned identity persists through normal init/profile changes. Do not rewrite identity during a read-only handover.

For temporary operations, follow the [complete Core operation example](../../docs/core-agent-operations.md): public imports need no tools sys.path insertion; hosts.list() returns a host-ID dictionary; use a quoted local heredoc or a reviewed Python file, then quote remote arguments separately. check=False does not suppress timeouts. Preserve step labels, original errors and cleanup evidence, and do not retry uncertain writes or invent Ctrl+C recovery. Convert reviewed repeated work into a recipe.

For saved system context use `recipe.host_info`, a copied dictionary of OS family,
distribution/version, kernel/architecture, observation time and optional login-PATH
python3 version/executable. Missing values are None. Reads never probe or require
inventory; refresh through authorized host-init. Users own freshness and specify
other Python environments. Use the [canonical keys and example](../../docs/core-api.md#saved-host-information),
not private config/cache parsing or an automatic probe.

## Reuse configuration and sessions

Effective hosts and declared users include resolved icon fields (built-ins 🍎/👤). Entry hosts.yaml supports global default.icon.host/user. Entry and included YAML support per-group groups.<name>.icon.host/user. Explicit host/account icons override defaults; default.users.<account>.icon then precedes group user defaults. Each remaining field independently takes the first defined value in host group order, then the global default. Include files inherit defaults; explicit values must be one Unicode Symbol code point, not a multi-code-point glyph. Optional default.users.<account>.email stays in source metadata and is not merged into host-account snapshots. This is display-only and does not rewrite YAML; see [icon rules](../../docs/hosts-yaml.md#host-icon).

Use profile.hosts.list/get and explicit reload rather than another YAML parser or frozen addresses/credentials. Reads are masked copies; reveal_secrets=True is explicit and must never enter logs/shared examples. Masking is key-based and cannot sanitize arbitrary strings. A profile/connection uses a validated snapshot; fresh inspection does not replace that execution snapshot.

Use `with profile.recipe(host_id, vars=..., timeout=...) as recipe` for standalone operation logic; sessions.connect is the narrower connection entry. For runner recipes declare python-recipe 0.1.0 and define execute(recipe). Reuse the supplied Recipe, do not reconnect or close borrowed sessions. The [complete identity recipe](../../recipes/system/account/check/identity/README.md) is a minimal template. Legacy python-session recipes keep execute(session, *, context, timeout); migrate explicitly.

Use recipe.session.exec_command(argv) or start(argv), read actual CommandResult/job states, and finish/stop owned jobs within scope. For privilege use `with recipe.sudo(user="root") as privileged` or `with recipe.su("declared-user") as privileged`, then privileged.session. Parent commands are unavailable while a nested scope is active. No host-init/privilege probe happens just by connecting. Read [SSHScript skill](../sshscript/SKILL.md), its Agent Guide and relevant API sections before command/job automation; Core's facade exposes only the documented subset.

Credentials follow existing account policy with one selected source, no retry; su requires a declared target and credential. Verify authorized target/privilege scope before entry. Failed identity restoration disables the execution; preserve cleanup evidence and do not catch the error to claim success. Core is not a Python sandbox or approval enforcement mechanism.

## Prefer the shared root console

For authorized operations requiring root, use `with recipe.root() as root:` and call
`root("id -u", check=True)` directly. root is a scoped callable console, not another
Recipe; no required flag exists. It returns original CommandResult and supports
exec_command(string), start(string), enter/expect/input/send and stdout/stderr/exitcode.
Read [the canonical interface, examples and errors](../../docs/core-api.md#automatic-root-console)
before use. Preserve finite budgets, shell quoting and job/interactive cleanup.

Reuse the shared two-candidate policy instead of recreating users ordering, credentials
or su/sudo orchestration. A root second candidate gets su priority; otherwise login
sudo is first. Public `from opsfeast import RootUnavailableError` is safe acquisition
failure only after verified restoration, never a license to execute root-only commands
as user. Inspect its copied report. Identity/setup/cleanup failures disable the scope;
do not swallow them. Root requires the login-level Recipe and a usable Bash console,
even for an already-root login. Parent commands are blocked while active; console use
after exit or across threads fails. Inventory alone adapts safe acquisition failure
to its explicit user fallback. Existing Recipe.su/sudo still yield child Recipes.

## Inspect and perform explicit local operations

Instance/profile inspection reads local metadata/configuration/paths and dependency versions, never creates identity, connects, repairs or dispatches. Inspect success/partial, component errors, placeholder identity and available/configuration states separately. Dependency metadata is not runtime/native readiness. Reuse profile.results/jobs and existing artifact verification rather than scanning guessed filenames. Missing service paths are not implemented services: notification/todo availability is described by the shared service facade; general logging remains deferred.

Metadata init/update/renew/relocate, profile init/attach/use/detach are explicit writes with their own scope. Preserve existing roots/data and human notes. This API does not edit hosts YAML or delete history. Public configuration/inspection methods do not authorize host operations. Catch ConfigError/CoreError at the boundary, preserve stable reason codes and safe error types, and avoid arbitrary exception/settings output.

## Select explicit SSH authentication sources

Read [the canonical authentication policy and examples](../../docs/hosts-yaml.md#ssh-authentication-sources)
before configuring or executing SSH hosts. connection.allow_agent and
connection.look_for_keys are strict Booleans, both default false on every hop,
including SSH config aliases; they are not allowed on local/reference objects.
Preserve the user's intended sources: explicit login passwords/identity files
remain usable, agent or default-key discovery requires an explicit true.
Do not infer flags from password presence or bypass the shared planner in a recipe.
Inline hops are independent; referenced hops use the referenced host's settings.

Use check for local type validation. Missing all sources after alias/account resolution
fails before that target chain opens any Session, with missing_authentication_source
and a safe hint; check alone cannot confirm usable credentials. For an authorized
connection test use test-connection HOST --json --debug to inspect effective flags
and results without printing secrets. Configuration changes do not authorize probes.
See [migration](../../docs/migration.md#explicit-ssh-authentication-sources) before
resuming configurations that relied on ambient keys. Policy tests are synthetic;
real SSH/agent authentication requires separate authorized evidence.

## Group catalog and bulk host definitions

Read [the canonical group schema and example](../../docs/hosts-yaml.md#host-groups).
Use top-level groups.<id> for optional label (default ID), description (default empty
string), icon.host/user and hosts. Bulk hosts use the ordinary host schema and enter
the same effective host map; the enclosing group is prepended and memberships are
deduplicated. First membership is primary. Keep host IDs globally unique and explicit
group definitions unique across includes; use membership to share hosts across groups.
Labels never substitute for IDs in selectors. Missing group definitions get default
metadata. Defaults/icon resolution happens after all includes, with existing named-user
and explicit host/account precedence. No connection/vars/recipe inheritance is added.

Prefer `profile.hosts.groups()` for a copied runtime catalog, existing hosts.get and
session/recipe methods for bulk hosts, and check / dump groups for local inspection.
Catalog hosts are member ID lists, not nested raw host mappings. Inspect can show a
fresh catalog without changing the execution snapshot; reload explicitly. See [Core
examples](../../docs/core-api.md#host-group-catalog). The TUI shows labels plus IDs and
read-only group descriptions/member IDs, including empty groups. Group rows do not
start host actions. Old default.groups fails with a migration hint; follow [migration](../../docs/migration.md#group-catalog-and-bulk-host-definitions)
without silently rewriting private configuration. Preserve source-relative paths,
notes, authorization and skipped/failure states. Tests are synthetic; no SSH/privilege
behavior follows from group parsing or display.

## ESXi SSH-exec identity evidence

Read [the shared ESXi diagnosis workflow](../../docs/host-diagnostics.md#diagnose-esxi-identity-failures)
when SSH succeeds but identity fails. The adapter handles exit 127 and the narrowly
recognized exit 2 / empty stdout / shell missing-id stderr form only after verifying
VMkernel; do not broaden it to arbitrary failures. Inspect identity_probe.id_exitcode,
identity_error.reason_code and configured_identity_probe.actual/expected/matched.
access.actual_identity records the observed shell actor even when account comparison
fails; connection_identity is not verified in that case. The ESXi connection-level root-shell model can accept different numeric UIDs with a known successful final-hop SSH login, verified VMkernel and consistently observed UID 0. Keep both identities and the acceptance rule visible; other platform and privilege-target mismatches remain failures. Do not rewrite private bindings to root. Existing authorized
check-access --host HOST --root ROOT --json --quiet is the reusable CLI; Core and runner
use the same probe without new APIs/configuration. No raw command output is retained.
Native two-hop evidence covers a root missing-id exit 2 path and an ordinary login accepted with an effective root shell; other ESXi/privilege scenarios remain outside this evidence. These diagnostics do not
change retained inventory schemas.

## Distinguish SSH login from an ESXi root shell

Read [the canonical identity model and JSON example](../../docs/host-diagnostics.md#ssh-login-and-esxi-root-shell-identity).
Reuse the shared CLI/Core/runner verifier: login_identity comes from the successful
final-hop connection; shell_identity is the observed execution account. Verified
VMkernel and a stable UID 0 shell may accept an ordinary account as esxi_root_shell.
Numeric matched=false is then accepted with status=success and accepted_by explaining
the policy; do not relabel it as failed or silently change hosts.yaml to root.
Account policies, credential selection and extra-user exclusion use the SSH login;
restoration uses the original shell. Explicit privilege targets, other kernels,
non-root mismatches and unknown-principal cases remain strict. No configuration
bypass or new invocation is added. check-access --host HOST --root ROOT --json --quiet
returns the full evidence within an authorized host scope. Human tables explain the
root shell and show sudo already_root. Native evidence covers the two tested two-hop
paths; additional ESXi releases, role assignments and su/sudo remain unverified.

## Recover batch results after terminal output scrolls away

Use `python -B tools/opsfeast.py observation --profile NAME` to list explicit batches newest first. Use `observation latest --status failed partial --profile NAME` or a fixed full/unique-prefix Observation ID to show host/collection identity/result/Result ID. --status alone implies latest and always filters displayed host results, including retention/content failures; it never searches older batches for failed hosts. latest includes running/scheduled batches, so check displayed ID/time/recipe/selectors. Whole-batch counts/outcome remain visible after filtering; storage/publication failures remain separate warnings. Raw links require an exact batch/host match; absent/deleted/ambiguous links remain a dash. Follow Result IDs with observation result. This read does not initialize, collect or write; use --json for view 0.2.0, and Core retention.runs/run for full data. Reuse checkout observation_cli.query/render when composing a viewer. See [canonical CLI rules](../../docs/cli.md#revisit-an-observation-batch) and [view schema](../../schemas/observation-view.schema.json).

## Read execution-batch evidence

Use `python -B tools/opsfeast.py inventory runs list --profile NAME --json`, then `inventory runs show RUN_UUID --profile NAME --json`, or Core/report `profile.retention.runs()/run(run_id)` and `context.retention.runs()/run(run_id)`. See [explicit run contract/lifecycle](../../docs/observation-runs.md) and [schema](../../schemas/observation-run.schema.json). These are read-only; do not query private SQLite tables or group observations by nearby timestamps. Query/show select individual retained records; run IDs require run(), including retention.run.updated consumer events.

Preserve actual selected hosts/icons, major jobs, skipped/preflight-failed targets, retention states, source/baseline IDs and stored policy/findings. Completed collection snapshots are immutable; optional selection preserves original invocation selectors and execution joins the actual command success/failure receipt. Absent old metadata stays unknown; never derive command success from collection status. Publication-failure receipts survive later rebuilds. Generated host/SUMMARY.md is the navigation entrypoint; README.md remains preserved human notes. Later settings/new observations affect current pages only. A running/pending batch can reflect interrupted persistence, and success with all targets skipped is not successful collection. A failed source record link cannot be filled from another observation. No automatic batch backfill, resume/reconciliation, pruning or import is supplied. Rebuild regenerates owned pages without modifying retention/run data or reconnecting. Read [Vault current/report/batch separation](../../docs/host-vault.md) before interpreting omissions or authoring a content consumer.

Group catalogs include configured recipe policy; Core/UI snapshots mask recognized sensitive fields in nested vars, while explicit CLI dump remains raw. Name-based masking does not make arbitrary custom values safe to publish. Use resolved runner vars for execution and keep private bindings out of output.

## Host results under observation

Use `opsfeast.py observation result [RESULT_ID]` for individual host history/diagnosis, `--detail` for full vertical evidence and `--raw` for complete JSON. Use the original root/profile and --json for automation. `recipes results` is offline-report-only; update old host commands without moving data or changing IDs. These reads do not collect or retry. See [canonical modes and failure rules](../../docs/cli.md#host-result-history-and-modes).

## Proxy subprocess environment policy

Core sessions share [OpsFeast proxy environment handling](../../docs/process-environment.md)
with the CLI and runner. Reuse profile.sessions.connect and inspect connection.report
hop proxy_environment evidence; do not change os.environ, construct a second proxy
or reconnect to apply settings. Host connection.proxy_environment accepts quoted
strings/null, masks every non-null value in normal snapshots, and overrides default
NO_COLOR normalization only in the local proxy. There is no remote-shell or arbitrary
subprocess environment policy implied by this support. No new Core method is needed.

## SSHScript 7.0 source migration

Read [the exact source contract](../../docs/sshscript-7.md) before operational work.
This checkout requires published sshscript==7.0.1, release source b8d7c8fe88b4096e8a58e6609ba805ee2bf41049;
Core/runner/diagnostics require matching module/type bytes, not just version text.
Reuse existing Core sessions and host YAML identity_file/proxy_command. New Python
interfaces use parent_key_filename/proxy_command/proxy_jump, missing_host_key_policy
and known_hosts_source; only hostname is positional. No compatibility aliases,
automatic install or real-host authorization follows from this migration.


## Shared notification/todo services

Use `profile.services` for standalone programs and the supplied `recipe.services` inside Recipe scope. Read [services 0.1.0](../../docs/services.md) for reconcile/create/list/show/update/history/snapshot, lifecycle and revision checks, and [adapters](../../docs/service-adapters.md) for static readiness, private configuration and dispatch side effects. Consumer code must use `context.services` to preserve live-evidence eligibility. Read-only inspection never proves provider delivery. General logging remains unavailable; service dispatch may send configured mail, while todos never execute work.


## Portable profile data and recipes

`profile.transfer` is a profile-bound Space with query/select/export, import_plan/import_package, archive_plan/archive and receipts. Read [the canonical API/workflow](../../docs/portability.md) and [data-only contracts](../../docs/portable-contracts.md). API mutations require expected_plan; archive can resume by receipt ID. `opsfeast.recipe_install` exposes recipe plan/install and rollback_plan/rollback; no provider calls or candidate execution occur. Imported retention is a read-only origin-qualified projection through profile.retention; the original payload remains intact in transfer storage. Preserve source identities and independent observation/retention selection. Dependencies and filesystem primitives have explicit inspection/verification limits; never replace a reviewed plan with unconditional overwrite.


## Selected execution scopes

Read [results/accounts](../../docs/recipe-results-and-accounts.md) for `Profile.recipe(..., execution={"via":"sudo","user":"root"})`, `Recipe.execution(policy)`, pipe-console exec/start and exact stdin. Default login requires no escalation; failed acquisition never yields the body, restoration failure disables reuse. Explicit su/sudo defaults changed to get_pty=False; request a PTY only for a reviewed interactive need. Reuse an already-selected root with recipe.root(); do not nest switching loops.

## Read host reference addresses

Use `profile.hosts.reference_ips(host_id)` for last successfully saved inventory
IPv4/IPv6 lists and original observed_at; inside a recipe use
`recipe.profile.hosts.reference_ips(recipe.host_id)`. It reads no connection data,
performs no network operation and creates no files. The configured host must
exist. A never-successful reference returns status unknown, empty arrays and null
time. Existing `hosts.list/get` returns are unchanged. For command-line use,
`opsfeast.py hosts list --profile NAME --json` and `hosts show HOST --profile NAME
--json` expose the same reference data. Read the
[complete 0.1.0 contract and source limits](../../docs/host-reference-ips.md)
before interpreting values; these are not SSH endpoints or current-health claims.

## Local runtime diagnostics

Core session acquisition uses the shared pre-Session runtime guard. `RuntimeEnvironmentError` is a `ConfigError` subclass with a controlled diagnostic report; exact type strings have changed for these failures. Reuse the failing interpreter with `-B tools/check_environment.py --json` and follow [runtime diagnosis and authorized repair](../../docs/runtime-troubleshooting.md) for version/source failures or duplicate metadata. Do not implement a second scanner, retry sessions to diagnose packages, or modify environments without scope.

*Last modified: 2026-11-02 17:03:25*
