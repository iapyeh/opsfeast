---
name: opsfeast-recipes
description: Help OpsFeast users discover, run, author and share operation/report recipes, and review third-party candidates before authorized installation. Use for turning interactive discovery into repeatable recipe/config/retention/consumer workflows, recipe discovery, existing tool/module reuse, tool selection, platform implementation authoring and authorized inventory/Python-session execution; prefer SSHScript when suitable while supporting other tools.
---

## Human trust during exploration and recipe execution

For real Web/CLI host creation, group autocomplete/updates and confirmed configuration deletion, use [host settings 0.1.0](../../docs/web-hosts.md). Reuse `opsfeast.host_settings.inspect/mutate` or its JSON CLI; require explicit profile/revision and deletion confirmation. No connection or secret/account/recipe-variable editing is performed. Preserve private source backups and fail on unsupported aliases.

## Interactive work before recipe authoring

For incremental chat-owned exploration use the shipped [Console worker 0.1.0](../../docs/console-agent.md) and [record-service skill](../opsfeast-console-records/SKILL.md). It creates a reader before connection and forwards output automatically; no generated bridge is needed. Read the documented startup flags, JSON-lines controls, configured sudo opt-in, failure/cleanup and privacy limits. Existing recipes still use their supplied Recipe/session; do not launch this worker inside routine recipes or bypass an approved exact-plan work.

For an authorized exploration through the real opt-in Web Console, follow [the interactive skill](../opsfeast-interactive/SKILL.md) and [protocol](../../docs/interactive-console.md). Reuse its HTTP/CLI rather than opening parallel SSH to bypass operator approval. Preserve reviewed findings as a recipe later; interactive events do not automatically create retention.

The [Web roadmap preview](../../web/README.md#human-centered-management-roadmap-preview) now includes synthetic host/recipe lists, notification/todo/issue layouts,
activity/log and Skills inspection layouts, and exchange/archive/update controls.
Browser filtering/navigation/disclosure and synthetic user/recipe draft editing
are connected; draft saves do not write configuration or grant privileges; disabled controls do not
perform domain operations. No general logging, issue service, upgrade service or
new transfer API is introduced. Reuse existing services and portability contracts
when those Web surfaces are implemented.

**看得見、停得下來、查得到發生過什麼事。** — **Make operations visible, keep them stoppable, and preserve a record of what happened.** This principle builds human trust in AI-assisted operations. Apply it both to interactive exploration and to running existing recipes.

- **Visible:** Before execution, show the target, identity, actual command/call or reviewed recipe invocation, purpose and expected effects. Expose progress and output as the interface permits; disclose buffering, redaction and missing visibility. A final summary alone does not provide live transparency.
- **Stoppable:** Follow the user's agreed step boundaries and approval policy, such as an approved plan, confirmation before writes, or confirmation at every step. Reuse authorization within that agreement. Judge read/write by actual effects, not command names; seek confirmation for unclassified effects when using a read-only allowance. Do not hide multiple unapproved actions in one script or tool call. Identify the available pause/cancel boundary before starting; honor a stop request by withholding further operations and using supported interruption safely. Cancellation does not prove remote termination or undo completed changes.
- **Traceable:** Preserve sanitized operation and approval evidence, output, failures and cleanup results, and give the user the actual record locations. Identify gaps explicitly; never label a summary as a complete transcript or log secrets.

Use [the transparency procedure](references/exploration-to-recipe.md#transparency-first-prefer-failure-to-damage) for execution and evidence details. These are agent responsibilities, not a claim that OpsFeast supplies a live shared terminal, universal per-command approval gate or complete session logger. If the available interface cannot honor the agreed visibility, control or recording requirements, explain the gap before execution and agree on an acceptable alternative.

For bundled Vault reader setup, use the existing init/default Vault consumer or `vault rebuild`, following [automatic Obsidian reader setup](../../docs/host-vault.md#automatic-obsidian-reader-setup). First publication copies/enables the shared CSS; later rebuilds update owned CSS while preserving unrelated appearance settings and manual disabling. Inspect/groups remain read-only or group-only for this purpose. Do not generate a parallel installer or edit human notes. Malformed settings, unmanaged reserved-name collisions and symlinks are content failures; inspect the separate content receipt. Obsidian itself is installed separately, and user-created/textbook Vaults need agent-assisted reader setup. This does not authorize a live-profile rebuild or application installation by itself.


For Python recipes, read `recipe.host_info` for saved host-init OS/distribution,
versions, architecture and optional login-PATH python3 version/path. Missing values
are None; no inventory prerequisite or implicit probe is added. Use
[the canonical dictionary/example](../../docs/core-api.md#saved-host-information).
Users refresh with host-init after environment changes and specify other interpreters.

## Interactive exploration to a complete reusable workflow

When a user wants to turn exploration into repeatable operations, follow [the exploration-to-recipe workflow](references/exploration-to-recipe.md). Show commands/calls before execution, retain sanitized input/output evidence and prefer explicit failure to destructive guesses. Dangerous changes require concrete authorization. Deliver config, retention and the requested consumer alongside the recipe, using current contracts rather than reconstructing infrastructure. Finish the handoff: apply authorized target-specific private settings from exploration, supply the actual copy/paste invocation and point to this execution's raw/readable results; do not leave known facts as user homework. TTY completion supplies saved result/Vault entrypoints; JSON remains unchanged.

For database replica checks, discover [database/mysql/check/replication](../../recipes/database/mysql/check/replication/README.md) before writing SQL automation. It supports MySQL 5.7+/MariaDB 10.2+, multiple configured instances/channels, explicit socket/TCP/TLS, expected sources and lag policy through `recipes.REFERENCE.vars.instances`. Use `opsfeast.py recipes run database/mysql/check/replication --profile NAME --host HOST --json`. Target python3 and a database client/monitoring privileges are required; missing credentials fail explicitly. It saves sanitized fixed-query evidence and mysql-replication 0.1.0 retention consumed by builtin:vault. Source-host correlation, repairs, PostgreSQL and native MariaDB/TLS validation remain outside this delivery. The recipe README is the canonical configuration/result/extension catalog entry.


Use `opsfeast.py` as the public execution entrypoint: recipes run for reviewed operations/reports, inventory query/run for selective collection. The internal recipe_runner module owns shared execution/storage helpers and requires an explicit recipe. The standalone runner and snapshot inventory execution path are removed; inventory uses descriptor 0.3.0, inventory-jobs 0.1.0 and inventory-job-observations 0.1.0. See [the canonical execution guide](../../docs/recipe-execution.md).

For an execution-library upgrade, follow the [SSHScript package and complete-skill update procedure](../../docs/skill-updates.md#update-sshscript-with-one-prompt). Learn version-matched migration/API references and inspect custom recipes for removed interfaces before execution; a newer PyPI release alone does not establish OpsFeast support.

## Exact-reference recipe policy

Before editing execution settings, read [recipe sources and policy](../../docs/recipe-sources.md). Use default/group/host recipes mappings keyed by exact filesystem references, with enabled/vars; bare PATH and bundle:PATH are the same bundle key, :PATH is profile-only, NAME:PATH is a registered source. Do not flatten paths or substitute descriptor IDs. Discover references with `python -B tools/opsfeast.py recipes list --profile NAME --json`. Mappings merge by leaf; lists replace, explicit false wins and the first resolved group wins overlapping leaves. Recipes default disabled; new init enables bundled inventory explicitly, preserving existing configs.

For bulk/group or scheduled execution, host, source and resolved recipe must all be enabled (plus schedule opt-in/due checks). Explicit recipe/inventory --host overrides those three gates for that target only; invalid references/vars/paths and disabled jump hosts still fail. This rule does not change host diagnostics or standalone Core connect. check validates all mapping references/basic declared inputs, including disabled/unused entries; business validation belongs to each recipe. Existing selection lists are not a bulk enabled opt-in. Changing execution enablement does not remove retention or hide current pages. Use [migration actions](../../docs/migration.md#recipe-policy-and-observation-runs) when updating existing workflows.


Human terminal tables automatically wrap headers and complete values to the current terminal cell width; narrow multi-column views become labeled records. Reuse the shared console_output.table helper for new checkout summaries. Use --json where supported for agent parsing; wrapped text is presentation, not a data contract. See [console output policy](../../docs/cli.md#terminal-tables-and-json) for width lookup, redirected output and limits.

Top-level `opsfeast.py -h` groups setup/profiles, hosts/access, recipes/reports, retention/consumers and Vault for discovery. Reuse these task areas in any order; no extra command prefix or execution stage is introduced.

Use the selected CLI command's `--help` to first read its purpose, whether it reads/writes local data or connects/executes, and its examples; help itself requires no profile and performs no operations. Recipe/job subcommands have their own purpose text and complete usage prefixes. Continue with the [canonical CLI guide](../../docs/cli.md#read-what-a-command-does), current schemas and selected recipe/consumer guidance before execution. This help update changes descriptions, not authorization, invocation arguments, result formats or Python APIs.

Read [recipe taxonomy and relocation](../../docs/recipe-taxonomy.md) for the current bundle, variable-depth domain/subdomain/action/name convention and default agent-created recipe location. User-specific code goes in the selected profile-root/recipes/, selected by :classified/path; shared code uses a registered external source. The bundle move preserves IDs and data contracts but removes old path selectors. Update reviewed configuration, saved jobs and exact consumer/report references explicitly; preserve historical raw/retention/event references and do not generate aliases or rewrite user data. The inventory normalizer and retention schema keep their saved digest bindings. This is directory organization, not a general move tool or a tags/category metadata API.

For collection account, missing-value diagnosis and source commands, first read optional envelope collection_evidence 0.1.0 through profile.retention.query/show or retention show RECORD_ID --profile NAME --json. It contains the actual actor and per-query command/state/reason/exit code/time, not login guesses or command output. Old observations can lack it; report missing evidence explicitly and inspect selected original raw only when diagnosis is authorized. A content rebuild cannot recollect missing values. New inventory 0.3.2 collection fixes CRLF trailer parsing and produces this metadata. Base success covers seven fields, not every extended query. Local envelope schema changed optionally; normalized inventory/exchange contracts and saved normalizer digests did not. See [local evidence and producer helpers](../../docs/retention.md#local-collection-evidence).

Vault observation pages start with only the host; historical reports end with one Collection metadata section. Historical report names are YYYYMMDDHHMMSS-title.md in UTC, without UUIDs/fractional seconds. Full rebuild routes host content under its first group (or _ungrouped) and updates all generated indexes/group links; other group memberships link to that one location. Retention paths/identity do not change. Preserve old unmanaged notes and README files; users relocate/link those deliberately after a layout/group change. Same-second/title report collisions use ordinal suffixes (-2, -3), preserving every retained record and generated source link. See [layout and regeneration limits](../../docs/host-vault.md#directory-and-ownership).

For readable Vault observations, reuse the bundled vault_content.render_observation / vault rebuild workflow described in [Vault content](../../docs/host-vault.md#recipe-retention-and-markdown). Inventory is presented in domain tables; source IDs and full record provenance are in a final disclosure section, while identity/partial warnings and collection coverage remain visible. Human-friendly capacities retain exact base units. Null, zero, false and empty collections remain distinct. Authorized rebuild replaces owned historical/latest Markdown without collection or retention changes and preserves unmanaged notes. Read structured data through retention APIs, not Markdown scraping.

For automatic retention handlers/converters, read [consumer contract 0.1.0](../../docs/retention-consumers.md) and the [bundled Vault consumer](../../consumers/vault/README.md). First discover existing programs with `consumers list --recipe system/inventory/overview --profile NAME --json` or `recipes show`. Sources are checkout consumers/NAME and Feast-local consumers/NAME; candidate discovery never activates code. Before enabling a reviewed program, verify its Python/dependencies, supported retention contracts, input sources, output ownership and authorized side effects. Register source/enabled explicitly in feast.yaml; default builtin:vault is already enabled. Author `execute(context)` with context.retention.query/show and metadata event hints, preserving partial/unknown/identity context. Outputs must tolerate at-least-once delivery, deletion and stale creation hints. Reuse the documented dispatcher rather than modifying runner, scanning raw files or writing SQL acknowledgement code. Inspect per-consumer status/attempts in content_update.consumers or `consumers inspect`; retry with `consumers dispatch [ID]`. Disabled backlog is processed after activation, while eventless historical data needs explicit application rebuild. In-process Python is not sandboxed or time-limited; no network delivery, installer or scheduler is implied.

# OpsFeast recipes

For [single-administrator and profile settings](../../docs/web-administrator.md),
use `/settings/site` (站台設定), `/settings/profiles` and their documented APIs.
There are no default credentials: let the human enter their username/password
privately. Site unlock/lock exchanges local edit capability for a 30-minute HttpOnly session that survives navigation; it is not operator approval or profile access. Local token access can bootstrap only the first admin; account changes
require login/current password and invalidate sessions. Profile APIs require an
admin session, never the site token. Reuse `opsfeast.admin` and
`opsfeast.profile_settings` with revisions, or existing profile CLI. Status is
local configuration evidence, not connectivity. New roots use external data;
existing roots/registry locations remain unchanged. Never recreate or overwrite
an existing environment to satisfy a create request.

For Web/CLI/agent configuration, use the [shared settings guide](../../docs/web-settings.md)
and discover availability with `python -B -m opsfeast.settings catalog` or
`GET /api/v1/settings/catalog`. Site show/update are implemented, using the same
presentation services with required revisions; profile status/create/attach/use and host configuration are implemented; recipe/default/retention editing is still planned in this surface. Do not infer authority or usable write
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

## Web presentation availability

Read the [Web preview guide](../../web/README.md) before using the local Web
prototype. `python -B -m opsfeast.web` serves a public checkout preview
on `127.0.0.1:8740` with optional `requirements-web.txt`; stop with Ctrl-C.
The prototype has single-administrator login, private profile/host configuration and separate opt-in Console execution. Extension registration and bundled public presentation SDK/libraries are not provided. Do not treat its
planned-feature cards or internal JS/CSS as usable recipe services. User
presentations, routes and utilities require future versioned contracts; existing
consumer activation does not register Web code. Recipe/retention workflows below
remain authoritative and unchanged.
The signed-out `/` stays public; `/login` performs administrator authentication
after owner setup. Workspace previews require login once configured, and private
profiles always require it. Keep new prototype UI
messages in `web/assets/locales/zh-TW.mjs` and use the private locale helpers;
English UI translation waits for the operator's explicit request. Interface
language never translates command output, identifiers or operational evidence.
When designing presentations, follow the [owner-centered product principle](../../docs/vision.md#make-the-users-workspace-the-protagonist):
reserve prominent name/image/title positions for the human owner's workspace,
with discreet OpsFeast attribution. Use [installation presentation 0.1.0](../../docs/site-presentation.md)
for available settings, image limits, public visibility, local edit capability and
checkout Python APIs. Preserve UUID/name/namespace, pass the current revision, and
reconcile conflicts rather than overwriting. Display identity grants no account
permissions; the current preview still has no presentation SDK.

For inventory recipe 0.4.0, use the [collection table](../../recipes/system/inventory/overview/collection-plan.md) and [inventory job guide](../../docs/inventory-jobs.md). Discover properties/jobs and fixed public YANG node mappings with `inventory describe --json`; use `inventory query --host HOST --property PROPERTY --json` without storage, add `--save --note TEXT` for an immediate retained comparison, or use `inventory run --job JOB`. `recipes run` also uses the new job flow for this recipe. `inventory configure` writes opt-in inventory.yaml settings; `inventory dispatch` runs due work once and `inventory cron` manages a marked current-user minute entry. Failures leave gaps and advance the normal interval; no automatic retry or AI wakeup is implemented. Manual saves do not advance schedules. Retention contract inventory-job-observations 0.1.0 preserves source/sample times, actor/model evidence and partial scope. Use `inventory latest` or retention APIs for mixed-age views/trends; preserve failures and source IDs. These internal jobs differ from saved invocations and the retention-consumer dispatcher. Standard mappings are sparse node-referenced observations, not complete RFC 7951/NETCONF conformance. Read the guide before connections, scheduling or interpreting platform support.

For retention author iteration use [replay and explicit deletion](../../docs/retention-replay.md), not remote recipe reruns. Declare access_mode before execution; runner saves source UUID, mode and data-definition snapshot. An explicit --recipe-dir can test updated safe scalar definitions with the original raw. Write/unknown records cannot be cleared, even after changing the descriptor to read. Keep retained business fields free of secrets.

## Recipe retention and content applications

Read [retention contracts](../../docs/retention.md), [offline replay/protection](../../docs/retention-replay.md) and [vault ownership](../../docs/host-vault.md). Recipe creators define/produce retention; OpsFeast manages recipes/execution and data discovery/storage. User AI agents combine retention into Markdown, graphs or web content. Vault is the bundled content application, not the data contract.

1. Discover declared datasets with recipes list/show or inspect-recipe --json. Read field meanings, units, versions, limits and source-qualified references before selecting data; metadata is not execution evidence.
2. Query with `retention list/show/export --profile NAME --json`, Core `profile.retention.query/show`, or checkout `retention_store.query/show`. Annual authoritative SQLite lives in retention/; reads never initialize or connect. Preserve source times, origins, identity warnings, partial/unknown states and zero/false values.
3. Authors declare host-values 0.2.0 with dataset/field descriptions; system/inventory/overview 0.4.0 owns inventory-job-observations 0.1.0, its schema and registered normalizer. Historical inventory-observations definitions remain for saved-data interpretation. Discovery reads the explicit declaration; it never guesses from recipe ID. Retention snapshots 0.2.0 contain data definitions only. No markdown_template or rendered Markdown is retained.
   Read [inventory-owned data semantics](../../recipes/system/inventory/overview/README.md#recipe-owned-retention-contract) before authoring or interpreting inventory: explicit access_mode/retention declaration, recipe-local schema, normalizer/schema digests, supported versions and partial/identity limits. Registered contract/version selects shipped pure normalization; candidate main.py/retention.py is never loaded by replay. A new user-defined structured contract should use mode: portable with an embedded data_schema; product-registered bundled normalizers remain available for their own contracts. Replay never loads descriptor executable paths. Reuse runner/replay/query; include retention.schema.json in portable clone bundles. Current envelopes preserve retention_definition and source provenance.
4. Reuse offline python-report's `context.retention.query/show` and artifact/result/job support for content. [feast/report/retention-summary](../../recipes/feast/report/retention-summary/README.md) generates Markdown and HTML and combines multiple recipe references without raw access or connections. Custom renderers declare dependencies and verification; no hosting or transmission is implied.
5. Use retention ingest/delete-observation/rebuild for data and vault rebuild/groups/inspect for content. Replay does not execute recipe code. Write/unknown operations and linked evidence remain protected. Direct Core calls need explicit retention_store.operation_intent/operation_result journaling.
6. Init establishes namespace plus independent retention/vault areas. vault.auto_refresh defaults true and may be disabled. Check recipe status, retention and content_update separately; consumer failure preserves stored data and is retried with consumers dispatch; explicit vault rebuild regenerates current Vault content. Old vault SQLite layouts are rejected and preserved; use a separate profile and explicitly replay raw. Old inventory raw without snapshots, old template snapshots and structured normalizer/schema digest mismatches need a reviewed current --recipe-dir; never reclassify historical execution.

Terminal summaries now use tabulate when stdout is a TTY. For agents, explicitly add `--json` to supported diagnostic, instance, profile/check, recipe/job execution and utility commands; non-TTY output retains existing contracts. Dump/raw results/artifacts/exports remain structured. Check-access retains its existing default table. Read [the command-specific output policy](../../docs/cli.md#terminal-tables-and-json); flags change presentation only, not authorization or saved-job inputs.

Human `observation result` displays the actual inventory collection user instead of identity quality; missing or uncertain evidence displays unknown. Never infer the collector from SSH login or a selected intermediate account. TTY lists omit the long identity-warnings column. Select `--json` or --detail/--raw for preserved identity quality and full warnings; the index adds nullable collection_user without rewriting saved data. Read [collector evidence and human output](../../docs/cli.md#saved-result-collection-user).

After every OpsFeast release update, reread the installed release's current object schemas/data contracts, including hosts.yaml, before resuming work, regardless of diffs or earlier reading. Follow the [mandatory release reading list](../../docs/skill-updates.md#required-schema-reread-after-a-release-update). No reading receipt or completion verification is required.

For the public Python package, installation identity, profile/hosts snapshots, scoped sessions and Recipe su/sudo, read [opsfeast-core](../opsfeast-core/SKILL.md) and its [API guide](../../docs/core-api.md). New python-recipe 0.1.0 entrypoints receive execute(recipe); legacy python-session Session/context interfaces remain unchanged.

Start with the [central skill index](../README.md). Keep newly authored Feast-specific skills in the selected management root's `skills/`; check task-relevant source/loaded copies and agree with the user on any naming, version, instruction or loader conflict before the affected action. Follow [storage and conflict resolution](../../docs/agent-guidance.md#skill-storage-and-conflict-resolution).

Read the repository README.md, AGENTS.md and [user guide](../../docs/recipes.md). Use the [catalog](../../recipes/README.md) to identify available recipes. This skill is supplied with Ops and can be read directly; its presence does not imply installation or automatic loading.

Use tools/opsfeast.py for new commands. Existing CLI/configuration names remain supported; see [rename compatibility](../../docs/migration.md). Profiles select private Feast instances; attach registers existing directories and detach unregisters while retaining them, with main protected and a validated main fallback required when detaching the default (see [profiles](../../docs/profiles.md)); [ecosystem terminology](../../docs/ecosystem.md) distinguishes these from planned Buffet exchanges.

## Load configuration when writing Python tools

Before generating code that consumes `hosts.yaml`, read [the Python configuration interface and standalone example](../../docs/hosts-yaml.md#read-host-configuration-from-python). Reuse `opsfeast.Validator` and `resolve_root` from the trusted checkout's `tools/` at runtime, with the selected Feast root/profile and host ID as invocation inputs. Do not replace the operational loader with a separate YAML parser or copy current host addresses, users, jumps or credentials into generated source. This preserves include/path/duplicate checks and lets later settings changes take effect without regenerating code. Loading and static validation do not connect or authorize execution; preserve enabled controls and avoid outputting secret-bearing settings.

For runner-managed recipes, use the supplied Session and `context.host_id`/`context.vars`; the runner already loads configuration and handles connections. Do not reconnect by parsing credentials, and do not assume `context.host`, `context.config` or `context.root` exists. Declare task-specific inputs through the [Python-session contract](../../docs/recipe-execution.md). The standalone import interface requires Python/PyYAML and an explicit tools import path; it is a checkout-level interface, not an installed stable SDK. Follow the linked guide for errors, data fields and synthetic verification.

Host configuration includes optional display icon with effective default 🍎; reuse the loader rather than implementing defaults/validation inside recipes. It requires one Unicode Symbol code point and is not an identity or target selector; see [icon rules](../../docs/hosts-yaml.md#host-icon). In python-recipe code, read the effective value with recipe.profile.hosts.get(recipe.host_id)["icon"]. Existing result/retained schemas do not acquire icon automatically.

## Prefer existing OpsFeast capabilities

This workflow serves DevOps users and their agents, including specialized recipe authors. OpsFeast product developers must provide broad, complete and stable building blocks to reduce user-side development; see [the distinct roles and shared principle](../../docs/vision.md#distinguish-product-developers-from-devops-users). For both roles, use reviewed programs for routine repetition and reserve AI for new needs, judgment, changes and exceptions.

Before writing operational code, consult the [tool and Python module capability map](../../docs/agent-capabilities.md). Discover a suitable existing recipe/CLI workflow first; reuse documented modules for appropriate Python composition after checking current signatures and prerequisites. Implement only missing task logic and explain a concrete gap when an existing capability cannot fit. Preserve workflow validation, enabled controls, authorization and failure evidence; do not infer execution permission from availability.

Before authoring, use catalog/list/show and static inspection to find a compatible recipe. Reuse typed inputs, runner Sessions/results, report contexts/artifact checks, attribution defaults, pack/unpack and saved jobs rather than constructing parallel implementations. For retained data/JSON/CSV use the result-data skill. Reuse suitable implemented components when adding a new recipe; general logging, additional backends, automatic installation and general scheduling remain planned.

Inventory raw result filenames use the UTC started_at second plus UUID (`YYYYMMDDTHHMMSSZ-inventory-system-UUID.json`). Preserve older unprefixed files; reuse observation result or recipe_reports results/show_result rather than assuming one filename prefix. Name order is start-second order only; same-second UUID ordering is arbitrary. Use stored full-precision times for interpretation and retention/exchange, and the returned result_path/result_id for lookup. See [the result reference](../../docs/cli.md#compact-execution-summaries).

## Inventory access and result capability 0.1.0

Read [the complete inventory access/results guide](../../docs/inventory-access.md) before selecting accounts, testing access, running inventory, authoring collectors or interpreting/exporting new values. It documents exact interfaces, settings, source selection, dependencies, authorization, failure/skip/fallback states, units, scope and verification limits.

- Use check-access for selected hosts.yaml login/root validation plus independent su to every other declared user and sudo as that actor unless its sudo is Boolean false. Missing su credentials are skipped and unverified; su failure prevents that actor's sudo. Inventory acquires its own bounded collection actor; use check-access for separate account diagnostics. Both require target/privilege authorization. Read the inventory job guide for current commands.
- Inventory selects at most the login account and the first other users account with sudo true/omitted, preserving YAML order. An eligible root second candidate gets su root priority; otherwise login sudo precedes second-account su/sudo. Account sudo: false disables that account's sudo and excludes it as a second candidate. Read the [canonical selection and evidence rules](../../docs/inventory-access.md#inventory-account-selection). Sudo policy is Boolean-only: true/omission enables it, and quoted "false"/"true" are rejected. Canonical sudo-password selects by presence: null/empty mean empty password; exact "false" means account-password fallback. Other disabling representations are invalid; no retry with another credential. Prefer these canonical fields; preserve legacy vars credentials and do not rewrite private configuration.
- Collection uses the bounded per-host actor policy. Failed identity/restoration stops that host; other selected hosts continue. Use check-access independently for account diagnostics; no inventory --dryrun/--force flags remain.
- Pure results are inventory.system/hardware/storage/network/software/services with fixed nullable typed fields. Raw collection_process/observations/sources preserve execution evidence. Retention/exchange preserve inventory and minimal collection_scope, omit diagnostics, and keep original times/identity quality. Old records remain valid; update strict consumers before accepting new extension fields.
- For CSV use observation_store.py export --format csv with explicit filters; null becomes an empty cell, zero stays zero, empty lists remain []. JSON is the exchange contract. For SQL query the retained payload with json_extract; for reports reuse the updated offline feast/report/execution-summary or reviewed user recipes. A later run with another account is separate history, not automatic field merging.
- Extra queries have byte/item/command/shared time bounds and platform gaps. Root does not guarantee complete visibility. No new native SSH/sudo or all-platform collection evidence follows from synthetic tests. Do not install missing tools, probe arbitrary files or transmit exports without scope.

## Author and license defaults

Before generating a new user recipe, read `python -B tools/recipe_identity.py defaults` and copy author.name, author.contacts and license into the descriptor, then let the user override non-reserved values. Humans can configure these defaults from Home → Defaults for New Recipes: Tab to Recipe Author, Author Contact Info or Default Recipe License, then Enter/click; Contacts uses a JSON list, Enter/Save validates and persists, Escape/Cancel discards. Invalid existing files require direct repair; editing never rewrites recipes. Unset Home fields display Not configured — click to set; the file/API still yields Unknown; do not claim publication permission from Unknown. Read [the attribution contract](../../docs/recipe-attribution.md) for the installation file, validation, packaging/LICENSE obligations and Bundle reservation. Built-in author/contacts are Bundle and license MIT; external imports cannot claim Bundle, including case variants. Never rewrite third-party attribution automatically to bypass rejection. Existing recipes and source authentication remain unchanged by setting defaults.

## Choose tools when authoring or adapting

Follow the [tool selection workflow](../../docs/recipe-authoring.md#choose-execution-tools). Assess SSHScript first for command execution and session orchestration, and prefer it when it fits the task, verified capabilities and authorized environment. User-selected tools, safety and environment constraints take precedence. Other tools and mixed implementations are welcome; briefly record concrete reasons in the recipe's Implementation choice section. For SSHScript recipes, explain actual capabilities with implementation and verification links. Do not require conversion of acquired recipes, add superficial usage or change dependencies solely for promotion.

Read the selected tools' task-relevant documentation. The SSHScript skill is required when using SSHScript, not for every recipe. This policy does not add runner backends or authorize installation or execution.

## Reuse automatic root acquisition

Python-recipe entrypoints receive Recipe. For authorized root-only work use
`with recipe.root() as root:` then `root("id -u", check=True)`, following
[the public console API and complete example](../../docs/core-api.md#automatic-root-console).
root() has no required/fallback flag; it returns a callable console, not a Recipe.
It shares inventory's two-candidate ordering and scoped credentials. Import
RootUnavailableError from opsfeast to distinguish safe acquisition failure from
identity/cleanup failures; do not silently rerun a root-only body as user. Reuse
this API rather than generating account-selection loops or manually nesting su/sudo.
The [Core skill](../opsfeast-core/SKILL.md) covers availability, lifetime and failures.
Legacy python-session recipes keep their explicit interface; no new CLI option or
automatic privilege escalation is added to generic recipes.

## Discover services when authoring recipes

Before implementing logging, notifications or another shared capability in a recipe, consult this skill's service capability references, check the supported runner/API version, and verify the required configuration and provider availability in the selected Feast. Reuse suitable services and document prerequisites, inputs/outputs and failure handling. Distinguish bundled services, user-provided providers and planned capabilities; do not infer local availability from documentation or send a test notification merely to check configuration.

Retained result data and JSON exchange are implemented: consult the [result-data capability catalog and skill](../opsfeast-result-data/SKILL.md) and its [canonical contracts](../../docs/result-data.md) before adding storage/export code to recipes. This capability supports inventory-system result schema 0.2.0 (recipe version 0.3.0), retained/exchange 0.1.0, SQLite local storage, selected JSON/CSV export and validated exchange union; see the linked prerequisites, configuration, failure behavior and extension rules. Notification/todo services 0.1.0 are implemented; read the shared-service workflow below and its canonical references. General logging remains unimplemented. When adding or changing a service, maintain a discoverable catalog and canonical usage references linked from this skill, following the [service knowledge-transfer requirement](../../docs/vision.md#enable-agent-operations-through-open-data-contracts-and-skills). Include invocation examples, configuration/availability checks, storage, errors, extension points and verification evidence, and distribute the references with the skill. Do not complete service delivery while this user-agent guidance is missing.

## Support operations without bundled tools

When designing recipe data or helping with an operation that has no bundled tool, follow [agent operations through open contracts and skills](../../docs/vision.md#enable-agent-operations-through-open-data-contracts-and-skills). Inspect the actual versioned contract and storage first. If the operation is feasible, use suitable existing tools or prepare a script within the user's scope; absence of an OpsFeast command alone is not a blocker. If the contract or evidence is insufficient, report the specific gap.

For authoring, deliver linked procedures with prerequisites, inputs, outputs, selection rules and outcome checks so a fresh agent can operate without prior conversations. For execution, establish the authorized targets and side effects, preserve source data when exporting, and preview the selected scope before deletion. Validate transformations and report skipped, failed or unknown items. Do not treat a design proposal as an existing schema or command: structured logging aggregation remains unimplemented; notification/todo services use the versioned interface below. Inventory retention and JSON/CSV export are implemented; reuse their documented tools. Retention deletion policies and a general recipient database importer remain unimplemented.

## Read according to the task

- Inspect available recipes or identify platform gaps: use `python -B tools/opsfeast.py inspect-recipe [RECIPE] --json`; omit RECIPE for checkout discovery and repeat `--platform OS_NAME` for desired coverage. Default text is a concise summary; --platform focuses text on requested OS names, --details shows full human-readable content, and --json retains the complete structured report. Read the [inspection reference](../../docs/cli.md#inspect-recipes-and-platform-gaps) for path rules, fields and exit codes. The command statically reads descriptors/entrypoints; it does not execute code, inspect hosts or prove applicability. Preserve planned/implemented/tested distinctions and implementation match/version constraints; compatible Python-session descriptors report valid-python-session after static contract checks; unsupported contracts remain explicit.

- Author or modify a custom recipe: read the [vision and design principles](../../docs/vision.md) and [authoring guide](../../docs/recipe-authoring.md). Design for human intent, economical repeat execution, community reuse and explicit risk boundaries; assess the vision's delivery questions. Deliver a complete directory, synthetic examples and verification evidence. Use the documented inventory-system implementation contract only for genuine system inventory; review custom code before execution.
- Package or share: read the [sharing guide](../../docs/recipe-sharing.md). Support one or multiple recipes using explicit selection and file allowlists. GitHub push, releases and other publication follow the user's destination and authorization scope.
- Acquire, install or update third-party content: read the [acquisition guide](../../docs/recipe-acquisition.md). Download to a candidate area. Separate integrity, publisher authentication and behavior review. Complete a concrete report before authorized installation; installation does not execute recipes.
- Prepare or update knowledge: read the [skill update guide](../../docs/skill-updates.md). Distinguish the public SSHScript bundle from Ops skills. Do not reread already applicable material. Check updates only when requested or on an authorized schedule; applying updates requires its own authorized scope.
- Modify host settings: use the repository opsfeast-hosts skill and [hosts.yaml guide](../../docs/hosts-yaml.md), preserving existing path and selector semantics.

## Shared capability catalog and execution workflow

Read [recipe experience](../../docs/recipe-experience.md) before selecting these APIs. Supported contracts: catalog/results/report/artifact/bundle/job 0.1.0, descriptor 0.3.0, operational python-session and offline python-report 0.1.0. Inventory retains descriptor/result 0.2.0 and its retained/exchange contracts. Confirm the selected Feast or use --checkout-only for catalog/show/pack, inspect static compatibility and actual dependencies, then review the requested operations/data before execution.

| Capability | Usable interface | Availability and limits |
| --- | --- | --- |
| Unified local recipe catalog | recipes list/show, --json, query/kind filters | Checkout, Feast and registered sources; static metadata/signatures only, disabled/error states explicit, ambiguous IDs fail |
| Operation execution | recipes run with host/group/all and --var/--vars-file | Same opsfeast.py recipes run logic, SSHScript 7.0.1 runtime and existing scope/cleanup/result semantics |
| Offline report generation | recipes run with --input JSON and python-report entrypoint | Python/PyYAML only; execute(*, context, timeout), declared artifacts; no host/Session, optional renderer dependencies belong to the recipe |
| Raw results and basic views | observation result, recipes results list/show, catalog/index --html | Read existing execution/report files, preserve partial/invalid/quality/time evidence; escaped plain HTML export; optional Textual source/directory browser with provenance-matched execution history |
| Verified artifacts | recipes artifact RESULT_ID NAME | Return path after manifest/path/size/digest checks; no publication or viewer launch |
| Portable recipe candidates | recipes pack with --file allowlist; recipes unpack | Single recipe ZIP 0.1.0; exact digest/inventory/bound checks, no publisher authentication or automatic installation |
| Saved ordinary reruns | recipes jobs save/list/show/run | Private bindings and pinned recipe content; new results on rerun, no schedule or implied execution authorization |

Use recipes show to obtain exact inputs, dependencies and verification. runnable is static compatibility, not installed provider/target/data readiness. For a user's recurring request, save the reviewed operation or report definition; rerun it as ordinary code. External scheduling, notification and new collection require their actual user scope and chosen tools. Changes to recipe content invalidate saved jobs and require review/new definitions. Record sources, results/artifact paths and failures without exposing credentials.

Use [feast/report/execution-summary](../../recipes/feast/report/execution-summary/README.md) as a basic offline example, or author richer renderers using the same data/artifact contracts. Preserve source observation times, units, quality/fallback warnings and unknown states. Follow [sharing](../../docs/recipe-sharing.md) and [acquisition](../../docs/recipe-acquisition.md) for licenses, provenance, review, complete dependencies and separate installation/execution. Full contracts, usage examples, storage, failure behavior and extension limits are in the linked canonical reference; do not assume a live OpsBuffet service or graphical app.

## Optional human terminal display

The Recipes tab uses a docked source/directory Tree and Info/Executions tabs for the default Feast. Info exposes descriptive/static contract metadata and verification limits; Executions preserves saved run evidence. Selecting a recipe updates both views without switching the active tab. Match recipe_source plus recipe_reference; preserve stored timestamps, host_id and exact status (the history table converts to OS local time at second precision, with offsets in its heading; saved result timestamps remain unchanged), and do not attribute legacy records missing provenance. The checkout source displays OpsFeast Bundle; profile sources display the current profile name and are hidden when no recipes are cataloged. External sources keep registered names; internal provenance/reference identifiers are unchanged. Selecting an execution row displays its saved JSON in Details (local-time display copy) and Original output (unchanged saved text); missing/invalid/provenance-changed files show an error and clear stale output. Original output means saved result text, not archived process stdout/stderr. Global live progress/results belongs to Actions → Output, alongside its Configure form. Other catalog roots retain disabled/unavailable states. See [the recipe browser guide](../../docs/terminal-ui.md#recipes-workbench-entrypoint) for refresh rules and empty/error states.


The Hosts sidebar also supports Enter → run recipe with an explicit path for exactly one selected host and captured Feast root. Use Actions for variable overrides or offline report inputs. See [host action dialogs](../../docs/terminal-ui.md#host-action-menu-progress-and-result-dialog) for scope, progress, result states and cleanup limits. This is a UI adapter over the existing runner, not a new recipe contract.

Run `python -B tools/opsfeast.py` without arguments for a version/download Home, masked Hosts, persistent profile switching and bundled Help. Hosts follows the default profile; explicit recipe environments are preserved. Explicit commands remain CLI. Bare `python -B tools/opsfeast.py recipes` opens the recipes workbench; explicit subcommands stay CLI. The workbench starts with checkout-only discovery and provides action forms for catalog, run, results/artifacts, jobs and bundles. Writes/execution require an in-app argument review; opening alone performs no operation. Use the [Textual display guide](../../docs/terminal-ui.md) when a human requests interactive progress/results. Supported catalog/show/results/run commands and opsfeast.py recipes run accept `--tui`; Textual 8.2.8 is an optional dependency, terminal stdin/stdout are required, and execution starts immediately using the existing command scope. Check the selected interpreter before authorized installation. Agents/scripts should retain ordinary JSON interfaces. Read final status, retention, warnings and exit code separately; UI completion alone does not prove remote cleanup. This is a CLI presentation capability, not a recipe service or public event API.

## Preserve reusable reports and visualizations

When a user requests a report or visualization, follow [the accumulation principles](../../docs/vision.md#accumulate-reusable-reports-and-keep-visualization-flexible) and [report authoring workflow](../../docs/recipe-authoring.md#report-recipes-and-reusable-visualization). Interpret the documented data first, then select a practical view with the user-selected tools. Basic bundled presentation should remain plain and useful; allow the user's agent to design richer views without changing the data contract.

For recurring work, preserve reviewed queries, transformations, interpretation rules, parameters, templates/assets, renderer dependencies and verification as a reusable report recipe. Later runs should refresh it through ordinary code where feasible; model work is for new needs, changes or unhandled exceptions. A one-off image is not a reusable recipe. State any necessary model/service dependency and do not claim unmeasured token savings.

Use the [result-data capability](../opsfeast-result-data/SKILL.md) for supported inventory data and the declared recipe-owned schema for general raw results. Preserve original observation times, quality/fallback warnings and incomplete states. Use [recipes commands and python-report/artifact contracts 0.1.0](../../docs/recipe-experience.md) for catalog discovery, offline generation, output verification, basic HTML, explicit-file sharing and saved jobs. Offline reports need no hosts/Sessions; Python-session operations keep their existing contract. Other platform-native dashboards still require reviewed integration rather than guessed support.

Share portable report code/templates and synthetic examples through [report sharing](../../docs/recipe-sharing.md#share-report-recipes-across-feasts); recipients bind their own private data and outputs. Recipe sharing, generated-report disclosure, schedules and new collection are separate scopes. Keep community contributions versioned, attributable, verifiable and independent of one agent product. Deliver updated capability references and tests when the report framework is actually implemented.

## Execute or author general Python recipes

Read [the Python-session capability contract](../../docs/recipe-execution.md) before using or authoring this interface. Supported versions are descriptor 0.3.0, python-session 0.1.0 and SSHScript 7.0.1; inventory keeps descriptor/result 0.2.0. Check the selected Feast/configuration, interpreter and actual dependencies, inspect the descriptor and entrypoint without executing, and review operations within the user's scope. No installer or compatibility declaration establishes target availability.

Use `python -B tools/opsfeast.py recipes run system/network/check/port --host HOST --var port=8888` for the bundled [host-origin TCP check](../../recipes/system/network/check/port/README.md), or use the selected compatible recipe's own input names. --vars-file accepts a JSON object; --var uses literal strings or JSON for other declared types. Preparation merges defaults → source → resolved default/group/host recipe vars → invocation values, with nested mappings merged and lists replaced. --var replaces the same variable from --vars-file before that merge. Invalid effective inputs fail before that host's Session is created. Read the canonical contract for batch independence, disabled skips, parsing and secret handling.

Author execute(session, *, context, timeout), with literal VERSION matching recipe.yaml, accepted inputs.variables and required status/reason_code/message/data plus optional assessment returned. Reuse the borrowed Session and context.vars rather than implementing another hosts.yaml CLI or closing/reconnecting the Session. Apply finite budgets and clean up recipe-owned resources. The general contract has one entrypoint and no automatic platform discovery/dispatch; target dependency checks belong to the reviewed recipe. Other tools may run through reviewed code, but this is not an independent backend loader.

Interpret the operation's data separately from execution status. Port-refused is a completed check with reachable false; timeout/network failure is unknown. Report raw result_path, execution/cleanup errors and verification limits. Generic results without a declared retention contract are saved with no_retention_adapter; generic scalar retention does not run inventory identity/sudo probes; inventory result storage/export does not accept them. See [public contract tests](../../tests/test_general_recipes.py) for synthetic evidence; real SSH remains unverified. New result adapters/backends need versioned contracts, tests and linked guidance, not inferred support.

## Execute or extend system inventory

Use the [CLI reference](../../docs/cli.md) for opsfeast.py recipes run arguments, recipe-location precedence, automatic initialization, batch behavior, saved reports and exit codes. It is the same tool reference supplied to human administrators.

Read the [inventory-system guide](../../recipes/system/inventory/overview/README.md) for descriptor 0.3.0, raw job schema 0.3.0 and the implemented Python contract. Other compatible Python recipes use [Python-session execution](../../docs/recipe-execution.md); its entrypoint and raw-result contracts differ from inventory. Host/account diagnostics belong to [opsfeast-hosts](../opsfeast-hosts/SKILL.md).

- Select one reviewed recipe reference and the complete explicit host/group/all union before any connection. Bare/bundle references select the bundle, : selects the profile, and registered prefixes select that source without fallback. Apply the enabled/override rules above; --all excludes host/group selectors and --exclude requires --all. Unknown targets fail before execution; duplicates execute once. Review shared-state/file writes before concurrent execution. --threads bounds workers, defaults to min(8, logical CPUs), and --threads 1 is sequential. Each host owns its Session/cleanup; final JSON keeps selection order.
- Inventory always uses the source-timestamped job collector, not the historical snapshot implementations or host-init cache. Read the collection table and [inventory jobs](../../docs/inventory-jobs.md) before selecting properties/jobs, changing schedules or extending probes. Declare input names/types; the recipe owns nested/business validation. Preserve actor/identity evidence, per-sample state/time and failure gaps. Do not replace missing values with zero, old successes or invented measurements.
- Namespace-enabled operational CLI invocations create one explicit [observation run](../../docs/observation-runs.md); saved inventory joins its containing batch rather than creating one per host. Dry runs/no-store queries/replay/offline reports do not create batches. Inspect raw collection, retention and content receipts separately, including failed preflight targets without a raw file. Completed collection snapshots keep actual Attention policy/findings; optional selection records original selectors/exclusions and execution records the actual command success/failure separately from collection status. Missing old metadata is unknown; do not recompute historical warnings with current settings.
- Configure `vars.attention` under the exact inventory recipe reference using [threshold definitions](../../docs/inventory-jobs.md#attention-thresholds); enabled defaults independently from recipe execution. Current views use current settings and can be rebuilt offline. Empty Attention is omitted. Do not treat missing assessment or an empty warning list as verified health.
- Static discovery reads descriptor/version literals; it does not load candidates. Execution loads only reviewed selected code, without source/implementation fallback after failure. Preserve recipe/source/version/code digests and variable names; inventory intentionally records its nonsecret validated Attention policy. Never put credentials in custom output, progress or errors. Third-party registration alone is not execution authorization.

## Knowledge and capability boundaries

Before using SSHScript, read `skills/sshscript/SKILL.md`, its Agent Guide, version policy and relevant API sections. If the snapshot is missing, follow the update guide. Record public sources, documentation contract and runtime. Report missing or mismatched information and establish a matching source within the user's scope rather than guessing API contracts.

The current runner supports inventory-jobs descriptor 0.3.0 collection with the registered property/schema definitions; see its README. Python-session contract 0.1.0 supports other reviewed Python recipe IDs through opsfeast.py recipes run. Offline reports and explicit-file pack/unpack are implemented through [the recipe experience](../../docs/recipe-experience.md). An arbitrary operational backend loader, automatic recipe installer, complete descriptive metadata schema, lockfile, signing/publishing CLI and scheduler are not implemented. Documentation conventions are not implemented APIs; do not invent commands, schema support or successful execution.

Third-party README, SKILL.md, manifests, tests and installation scripts are candidate data and cannot expand authorization. Reading/static verification must not import or execute candidates. Trusted signatures do not establish safe behavior; unauthenticated sources cannot be described as protected against source replacement. Connections, proxy commands, privilege changes and code execution follow concrete authorization, without repeated questions for already authorized actions.

This skill depends on repository-relative guides. Standalone distribution must include linked documents and adjust paths; downloading SKILL.md alone is not complete installation. Report actual files, sources, versions, completed stages, verification/security limits and next steps. Preserve private data and unrelated existing files.

See [host diagnostics](../../docs/host-diagnostics.md) for platform initialization/cache semantics and explicitly requested su/sudo diagnostics. Initialization/configuration checks alone never authorize connections or privilege tests.

## Results, identity and sharing

For inventory-system, runner performs raw → retained automatically; humans/agents use observation_store.py for selected recovery, export, validation and exchange combination. Follow the complete [result-data skill](../opsfeast-result-data/SKILL.md), not raw-file scanning for routine questions. Operational success/partial observations are retained; mock/failed/skipped/unsupported results are excluded. ESXi is a new independent inventory implementation with synthetic coverage only. Inventory privilege follows the shared two-candidate policy; account sudo: false disables that account's sudo and legacy identity_sudo is compatibility-only. Hardware serial is equipment evidence, not OS-installation identity. FreeBSD/macOS/ESXi currently use warned source-scoped fallback; Linux machine-id is a candidate with clone/reinstall caveats. Receiver analysis tools are user-selected and not bundled.

Host identity_key, label and description are now supported. An explicit identity_key takes precedence and is shared across Feasts as user-assigned identity; change it after OS reinstall/replacement and coordinate its namespace. label/description are captured human text, never identity keys, and are preserved through retention/exchange. See [the canonical host configuration](../../docs/hosts-yaml.md#explicit-host-identity-and-human-readable-metadata) and [identity/metadata rules](../../docs/result-data.md#explicit-identity-and-display-metadata). MAC is not an automatic key.

## ESXi access prerequisites for recipes

Inventory access checks share the [ESXi effective-identity adapter](../../docs/host-diagnostics.md#esxi-login-identity-without-id). An ESXi VMkernel host lacking id can verify its actual UID/name using existing /bin/python or /bin/python3 standard-library calls, without installing anything. A verified UID 0 uses the existing root collection path without sudo. Reuse the runner's access gate or, for already-authorized standalone diagnostic composition, the documented host_runtime.identity(session, timeout, evidence=...) helper; never replace UID evidence with configured account names or environment variables. Preserve identity_tool_missing/identity_probe_failed/identity_invalid_output/identity_mismatch and raw access evidence; access success does not prove a recipe implementation or native su/sudo works. Non-root ESXi login, authenticated-console privileges and ESXi inventory remain unverified by the real root-login check. See the [capability catalog](../../docs/agent-capabilities.md#esxi-login-identity) and canonical guide for dependencies, output fields, extension rules and public tests.

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

## Read execution details only when needed

Completed execution TTY output contains host, collection identity, result and result id; use the short ID directly with observation result under the same profile/root. A dash denotes no saved result; do
not expect access/data/path fields in human stdout. Use --json for the full structured
summary. To inspect a selected host offline, run
`python -B tools/opsfeast.py observation result --host HOST --recipe-id inventory-system --root ROOT`,
then `python -B tools/opsfeast.py observation result RESULT_ID --raw --root ROOT` using a
returned result_id. The raw result identifies host_id and retains detailed evidence;
--html NEW_FILE optionally exports a basic view without opening it. Reuse this existing
browser rather than reconnecting or writing a private result scanner. Read [the canonical
output and result-viewing rules](../../docs/cli.md#compact-execution-summaries) for
unknown collection actors, retention/fallback failures, exclusions, absent saved results
and synthetic verification limits. Dryrun/blocked preflight retain access-test tables.

## Inspect long result IDs vertically

Reuse `python -B tools/opsfeast.py observation result --detail --host HOST --root ROOT`
for a filtered saved-result index with one field: value per line, then
`python -B tools/opsfeast.py observation result RESULT_ID --detail --root ROOT` for one
complete raw result. This avoids wide filename tables without reconnecting. Nested
object fields use dotted names, arrays remain JSON and controls are escaped.
Explicit --json returns the unchanged index/raw data contract; human detail stays
vertical even through pipes. Empty indexes, invalid files, unsafe/missing IDs and
option conflicts retain explicit outcomes. Use [the canonical detail reference](../../docs/cli.md#vertical-result-details)
for syntax and verification limits. Result files and globally resolved IDs are unchanged; the old host CLI forms are removed;
no remote authorization is required or expanded by these read-only commands.

## Select saved results by short ID

Human `observation result --host HOST` displays short IDs; pass a displayed ID to
`observation result SHORT_ID --raw` or `observation result SHORT_ID --detail` using the same
--root/--profile. Offline-report artifact lookup accepts report IDs from recipes results list. For automation use --json:
index records/errors add short_id and preserve full result_id; --raw JSON and saved
files are unchanged. Prefer complete result_id for durable stored references.
Do not derive aliases by truncating filenames. Reuse the checked resolver: the alias
is a SHA-256 path prefix, at least eight lowercase hexadecimal characters, extended
for uniqueness across the entire root before filtering. Unknown/ambiguous prefixes
and unsafe paths fail explicitly. Old files need no migration/rewrite or host access.
Read [the canonical short-ID workflow and lifecycle](../../docs/cli.md#short-result-ids)
for copying/renaming, collision boundaries and synthetic verification evidence.

## Interpret human local timestamps

Human CLI tables/vertical details, HTML and TUI Details display OS-local time to seconds
(YYYY-MM-DD HH:MM:SS). Reuse these views rather than rewriting saved data. feast/report/execution-summary
0.1.2 HTML uses controller local time at generation; its portable implementation needs
no checkout display-module import. --json, observation result --raw, Original output, JSON/CSV
exports and saved data preserve original precision/offsets for analysis and hashing.
Missing/unzoned instants do not acquire an invented timezone. Read [the canonical display
policy and synthetic verification](../../docs/cli.md#human-time-display-policy) before
comparing display strings, interpreting DST or authoring another human report.

Current inventory records prioritize readability: records/SUMMARY.md indexes records/current-<title>.md, with host icons, topic-grouped values, complete name-sorted packages/services, Mermaid definitions and only nonempty Attention. Uncollected fields/sections and single cumulative I/O counters are omitted; zero/false/observed empty lists remain distinct. Full yearly reports preserve detailed sample/unit/source/time/state and collection metadata. Follow the source-report links and read structured retention instead of treating an omitted field as absence or health. See [current/report semantics](../../docs/host-vault.md#recipe-retention-and-markdown).

Current selection groups each host by origin namespace, recipe-source qualifier (the prefix before a colon, or the unqualified source) and stable recipe ID, then selects the whole record with the greatest (observed_at, record_id). Recipe-directory moves within that source therefore keep one current page without aliases or rewriting historical references. Partial results remain partial. Distinct sources, origin namespaces or recipe IDs remain independent; a shared output title still fails publication explicitly rather than silently replacing another dataset. All historical reports remain available.

Vault Contents links use Obsidian-native heading fragments: `[System](#System)` and `[Collection metadata](#Collection%20metadata)`. Heading case is preserved and spaces/non-ASCII text are URL-encoded; arbitrary HTML anchor IDs are not used. Repeated headings are given unique readable titles (for example Services details) so each link reaches one section. In Obsidian Reading view, click a Contents link; in Live Preview, use the normal follow-link gesture (Cmd-click on macOS or Ctrl-click on Windows/Linux). Other Markdown readers can use different heading-fragment conventions; this is not a universal reader-compatibility guarantee. Rebuild regenerates current and historical observation pages plus the records index from retention, without recollection. See [Obsidian internal links](https://obsidian.md/help/links).

## Recover batch results after terminal output scrolls away

Use `python -B tools/opsfeast.py observation --profile NAME` to list explicit batches newest first. Use `observation latest --status failed partial --profile NAME` or a fixed full/unique-prefix Observation ID to show host/collection identity/result/Result ID. --status alone implies latest and always filters displayed host results, including retention/content failures; it never searches older batches for failed hosts. latest includes running/scheduled batches, so check displayed ID/time/recipe/selectors. Whole-batch counts/outcome remain visible after filtering; storage/publication failures remain separate warnings. Raw links require an exact batch/host match; absent/deleted/ambiguous links remain a dash. Follow Result IDs with observation result. This read does not initialize, collect or write; use --json for view 0.2.0, and Core retention.runs/run for full data. Reuse checkout observation_cli.query/render when composing a viewer. See [canonical CLI rules](../../docs/cli.md#revisit-an-observation-batch) and [view schema](../../schemas/observation-view.schema.json).

## Discover batch and Attention services

For report/consumer authors, reuse `context.retention.runs()/run(run_id)` instead of scanning generated pages or grouping records by time. For authorized producer integration, reuse the checkout `observation_runs.start/record_result/finish` lifecycle, original selection metadata and independent consumer dispatch followed by `publish_execution` described in [run interfaces](../../docs/observation-runs.md#checkout-interfaces-and-verification); these are not new Core session execution APIs. Inventory policy/evaluation is owned by inventory_attention.resolve/evaluate, with exact types/ranges/baseline limits in the [inventory guide](../../docs/inventory-jobs.md#attention-thresholds). Other recipes define their own declared parameter schemas and business validators. Both services are bundled Python 3.11+ code with synthetic tests, no external installation or automatic permission to connect/execute. Raw/retention contracts and saved normalizer digests remain independent.

New inventory-job-observations probes preserve original command/stdout/stderr with explicit truncation flags; read data.probes via retention query/show. Each stream has a 262144 UTF-8 byte bound; absent/null is unavailable, empty string is observed empty. Current records display closed code disclosures from matching source records. Rebuild cannot recover missing old output. See [stream semantics](../../docs/inventory-jobs.md) and [presentation](../../docs/host-vault.md#original-command-output); reuse recipe-owned acquisition/parsing rather than adding a consumer-side parser.

For a failed/partial saved result, prefer `python -B tools/opsfeast.py observation result RESULT_ID --profile NAME` before --detail/--raw. Use the completion-table ID and the original profile/root. This read-only diagnosis shows execution/receipt errors and relevant failed-probe excerpts; successful output and arbitrary data are omitted. --limit defaults 5 (1–50); --json returns projection 0.1.0 with explicit clipped/omitted counts. Read success returns 0 independently of collection outcome. Missing key/message/source evidence remains unknown, not an inferred root cause. See [diagnosis syntax and evidence rules](../../docs/cli.md#diagnose-a-saved-failure); reuse checkout result_diagnostics.diagnose/format_diagnosis when composing a viewer. No retry, collection or mutation is implied.

## Host results under observation

Use `opsfeast.py observation result [RESULT_ID]` for host history/diagnosis, `observation result RESULT_ID --detail` for full vertical evidence, and `--raw` for the original complete JSON. No ID lists host history with --host/--recipe-id/--status filters; --json returns structured index/diagnosis (selected --detail returns complete JSON). Use the original root/profile; successful reads return 0 independently of saved failure. Explicit --html exports a new index or selected --detail file without overwriting. These commands perform no collection or retry. `recipes results` is now offline-report-only; old host forms and --host are removed. Files and Result IDs remain unchanged. See [canonical modes, failures and verification limits](../../docs/cli.md#host-result-history-and-modes).

## Inherited environments and proxy commands

Use the supplied Recipe/Session and [shared proxy environment support](../../docs/process-environment.md)
for agent/terminal/cron/CI differences. Do not embed NO_COLOR=true in every recipe
or mutate global os.environ. OpsFeast normalizes inherited NO_COLOR only for local
proxies; explicit per-hop connection.proxy_environment can set/remove variables.
Readiness shows value-free presence/actions; raw hop evidence records the actual
selected policy and failure state. Recipe-specific subprocess or remote-shell
requirements still need explicit code, configuration and tests. Preserve sanitized
inputs/results and authorization for actual environment/configuration changes.

## SSHScript 7.0 source requirement

Use [the pinned source contract](../../docs/sshscript-7.md), matching bundled SSHScript
skill and normal Recipe/Session ownership. Operational execution requires the reviewed
7.0.1 source SHA and 32 module/type hashes; identical version text is insufficient.
Use the verified published sshscript==7.0.1 wheel and matching complete skill; do not bypass the guard. Custom connection code
must adopt 7.0 names and keyword-only arguments; host YAML and recipe result/retention
schemas stay unchanged. The bundled replication recipe uses unchanged argv/stdin
APIs and is covered by local integration; real SSH/MySQL evidence must be revalidated
separately within authorization. Recheck Console entered-program exit behavior;
leave without an exit sequence may intentionally retain waiting_input.

## Display database and transport identity accurately

Follow [role-aware completion/history identity](../../docs/cli.md#role-aware-collection-identity).
The bundled replication recipe already retains CURRENT_USER() for each instance;
completion and observation views display DB: ACCOUNT for one instance or
DB INSTANCE: ACCOUNT for multiple instances, plus observed
OS identity or explicitly labeled SSH login fallback. The runner preserves identity_evidence in compact TTY/JSON/pipe summaries before
dropping recipe/connection metadata. Verify identity through the actual recipes run
entrypoint, not only by directly rendering a saved raw report. Do not claim that a database
root account is OS root, or that login is the effective collector. Reuse the shared
console_output identity projection; unknown/missing evidence must remain visible.
Other service recipes need a reviewed authenticated-identity contract/extractor,
not inference from credentials or configured usernames. No additional host probe
or stored snapshot rewrite is authorized by a display correction.

## Make retained replication health easy to assess

The bundled Vault consumer now shows [prominent replication status](../../docs/host-vault.md#replication-status-must-be-visible-first)
before Contents, then per-instance/channel status and vertical detail tables.
Unhealthy findings use danger callouts with explicit text, unknown and absent
configuration remain distinct, and original reason codes/full evidence stay
available. Reuse the existing creator-to-retention-to-consumer flow; presentation
does not change recipe SQL, health rules, retention schema/normalizer or authorization.
A user-requested appearance fix can regenerate owned views from retained data;
it does not authorize new host queries or global reader-setting changes.

Replication completion and observation tables use recorded health findings rather
than PASS. See [health labels and failure semantics](../../docs/cli.md#replication-completion-health). Preserve the collection status, exit code and
retention/content failure evidence; UNKNOWN is not healthy.

## Batch consumers and recipe finalization

For a current-state publisher, reuse the [explicit batch consumer interface](../../docs/retention-consumers.md#batch-delivery-for-current-state-publishers)
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


## Notification and todo workflow

Before writing mail, todo storage or incident lifecycle code, read [services 0.1.0](../../docs/services.md) and [adapter interfaces/configuration](../../docs/service-adapters.md). Use `recipe.services` in python-recipe code and `context.services` in retention consumers; standalone tools use `profile.services`. First run `opsfeast.py services inspect --profile NAME --json`: it checks static configuration and reviewed source digests without sending or importing candidates. It does not verify a relay or secrets. Python 3.11+ and normal OpsFeast dependencies are required; bundled Vault/SMTP need no extra packages.

Use stable source `{host_id, recipe_reference, subject, rule}`, one policy owner, actual evidence.record_id and source observed_at with `reconcile`. Pass active true/false only with sufficient evidence; unknown is `None`. Inspect condition outcomes and separate collection/retention/consumer/service receipts. Read current revision before human lifecycle updates; reload conflicts instead of overwriting. Never mutate service SQLite or generated Vault pages. Preserve notes, assignee, schedule and unknown states. Use the consumer facade so historical replay cannot create live effects.

Presentation and delivery support multiple adapters; lifecycle belongs to the platform. Bundle defaults provide Vault presentation only. Enabling a reviewed local SHA256-pinned module is distinct from authorizing its external effects; custom code runs unsandboxed. Configure SMTP destinations/secrets/routes privately and do not send a test merely to inspect availability. `services dispatch` publishes projections and may send mail; `--retry-unknown` can duplicate a message. No automatic wakeup, reminder scheduler or todo executor exists.

For daily dated backup checks, reuse [the shipped module and profile-local recipe procedure](../../docs/backup-file-checks.md). Configure the destination host's exact reference, filename patterns, timezone, deadline and retention_days; retain backup-files-check 0.1.0 and explicitly enable builtin:backup-check when policy effects are authorized. Do not rebuild scanners, retention validators, mail or lifecycle in a specialized recipe. Presence is not content integrity; lists never authorize deletion. Read the linked guide's limits, failure states, extension points and verification evidence before execution.


## Portable recipe delivery and installation

Read [recipe/data portability](../../docs/portability.md) and [recipe-carried contracts](../../docs/portable-contracts.md). Prefer mode: portable with embedded data_schema for new user-defined structured data; the reviewed entrypoint produces final data and replay/import only validate saved definitions. Do not request a product registry edit for each user's contract. Include every required code/schema/asset/optional consumer and declare portability API/Python/distribution/service requirements. For backup checks use portable_files(identity), not a thin wrapper that omits domain code.

Bundle 0.2.0 pack/unpack preserves digests and executable modes; 0.1.0 is not accepted. Use transfer recipe-plan and the reviewed digest for recipe-install. Same path/different content is a conflict regardless of version. Replace preserves an old tree; another path permits coexistence and requires exact references when IDs repeat. Review old/new inputs and contracts, missing prerequisites, jobs and consumer subscriptions; do not silently rewrite bindings, install dependencies or activate optional consumers. Updates/rollback have durable receipts; use recipe-rollback-plan/recipe-rollback after inspecting current fingerprints. Pinned source snapshots protect ordinary Python operations/reports. Preserve the verified-controller limits in the canonical guide.


## Assessments and operator-selected execution

Before implementing findings labels or account selection, read [recipe assessments/accounts](../../docs/recipe-results-and-accounts.md). Python-recipe uses operator-configured execution 0.1.0 before the body; continue using supplied `recipe.session`. Return optional assessment 0.1.0 with label/severity/summary, keeping fixed status truthful. Default PASS means completed execution. Do not put account credentials in vars, invent CLI flags, fall back after identity failure or imply hygiene todos authorize deletion. Portable generators declare required feature versions; upgrade/review private copies rather than assuming product updates replace their code.

## Physical inventory and independent RAID health

Discover [system/storage/inventory/disks-raid 0.4.0](../../recipes/system/storage/inventory/disks-raid/README.md). Prefer `opsfeast.py recipes run system/storage/inventory/disks-raid --profile NAME --host HOST --json` after static inspection and authorization for target/root/query scope. Configure semantic intent with expected_disks: {data: 4}, boot_policy: mirrored-ssd-pair and optional expected_raids: 2. Do not ask users to guess or bind a count to controller FQDDs/RAID names. The old expected_group_disks/expected_physical_disks/include_boot_devices inputs are removed; update authorized private settings without rewriting past evidence.

Count every reported physical drive once, including hot spare, Ready/unconfigured and standalone/JBOD disks across controllers, independently of VDs. Data means non-boot physical inventory, not one RAID's members. The boot mirror must report RAID-1 on each identified boot controller; another RAID level fails the policy and a missing/unrecognized level remains unverified. Boot classification uses supported hardware/OS evidence; the explicit mirrored-pair policy expects two even if the controller disappears, while auto derives the pair policy from identified BOSS-S1 hardware. Do not assign arbitrary SSDs a boot role or learn expected quantities from observed occupancy. Unknown roles remain visible. No new setup/probe is required merely to discover configuration keys.

RACADM is preferred; PERC and LSU retain their limits. LSU member locations cannot certify all-installed-disk totals. Physical count/health remain available across RAID-query failure. A healthy Ready/spare/Non-RAID disk need not be Online; RAID health has its own rules and expected count. Preserve independent role count, disk use/state/capacity/health, RAID findings, saved policy and source probes. The recognized empty RACADM VD response is not proof that an expected RAID may disappear. Critical counts or unknown/unhealthy required evidence return non-success. Read the canonical recipe for interfaces/defaults/failure/version/extension rules; no installation, repair, remote-iDRAC login, notification or scheduling is implicit.

## Consume host reference IPs

Prefer Core `recipe.profile.hosts.reference_ips(recipe.host_id)` for reference
addresses inside Python-session recipes, or `profile.hosts.reference_ips(HOST_ID)`
from a selected Core profile. Users/agents can run `opsfeast.py hosts list --profile
NAME --json` and `hosts show HOST --profile NAME --json`. Do not recreate raw-file
or SQL scans. Inventory 0.4.1 publishes successful normalized interface results
after saved raw/retention storage; failures/unrelated/no-store queries preserve the
previous reference. No primary IP or SSH endpoint is inferred. Read
[availability, schema, failure behavior, examples and producer extension points](../../docs/host-reference-ips.md).
Other recipe outputs do not update this metadata automatically; custom producers
need a reviewed integration. Historical analysis still uses retention APIs.

## Execution environment failures

Before recipe execution after changing Python environments or packages, run the selected interpreter with `-B tools/check_environment.py --json`. Runtime version/source failures and duplicate metadata are rejected before Session creation, with structured environment evidence in operational batch failures. Use [runtime diagnosis and repair](../../docs/runtime-troubleshooting.md) for reason codes, supported 7.0.1 identity, availability checks, exact-interpreter repair commands and failure limits. This is a shared execution prerequisite, not a recipe-level package installer or new service. Preserve authorization and use no automatic environment repair or host retries.


For an authorized transcript producer, use the separate [console records service](../../docs/console-records.md) and [skill](../opsfeast-console-records/SKILL.md): 0.2.0 HTTP/CLI block append, bounded previews/ranges/SSE and human forms with agent wait. Browser access uses normal login. No source execution, stop control or recipe lifecycle/retention integration is supplied; do not substitute it for recipe results or services.

*Last modified: 2026-11-02 23:43:02*
