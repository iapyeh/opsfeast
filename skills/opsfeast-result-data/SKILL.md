---
name: opsfeast-result-data
description: Interpret and recover OpsFeast retained observations, prepare selected JSON exchanges, validate or combine shared data, reuse existing data/result tools and Python modules, and guide recipient-selected analysis without exposing raw execution details.
---

Human terminal tables automatically wrap headers and complete values to the current terminal cell width; narrow multi-column views become labeled records. Reuse the shared console_output.table helper for new checkout summaries. Use --json where supported for agent parsing; wrapped text is presentation, not a data contract. See [console output policy](../../docs/cli.md#terminal-tables-and-json) for width lookup, redirected output and limits.

Top-level `opsfeast.py -h` groups setup/profiles, hosts/access, recipes/reports, retention/consumers and Vault for discovery. Reuse these task areas in any order; no extra command prefix or execution stage is introduced.

Use the selected CLI command's `--help` to first read its purpose, whether it reads/writes local data or connects/executes, and its examples; help itself requires no profile and performs no operations. Recipe/job subcommands have their own purpose text and complete usage prefixes. Continue with the [canonical CLI guide](../../docs/cli.md#read-what-a-command-does), current schemas and selected recipe/consumer guidance before execution. This help update changes descriptions, not authorization, invocation arguments, result formats or Python APIs.

Read [recipe taxonomy and relocation](../../docs/recipe-taxonomy.md) for the current bundle, variable-depth domain/subdomain/action/name convention and default agent-created recipe location. User-specific code goes in the selected profile-root/recipes/, selected by :classified/path; shared code uses a registered external source. The bundle move preserves IDs and data contracts but removes old path selectors. Update reviewed configuration, saved jobs and exact consumer/report references explicitly; preserve historical raw/retention/event references and do not generate aliases or rewrite user data. The inventory normalizer and retention schema keep their saved digest bindings. This is directory organization, not a general move tool or a tags/category metadata API.

For collection account, missing-value diagnosis and source commands, first read optional envelope collection_evidence 0.1.0 through profile.retention.query/show or retention show RECORD_ID --profile NAME --json. It contains the actual actor and per-query command/state/reason/exit code/time, not login guesses or command output. Old observations can lack it; report missing evidence explicitly and inspect selected original raw only when diagnosis is authorized. A content rebuild cannot recollect missing values. New inventory 0.3.2 collection fixes CRLF trailer parsing and produces this metadata. Base success covers seven fields, not every extended query. Local envelope schema changed optionally; normalized inventory/exchange contracts and saved normalizer digests did not. See [local evidence and producer helpers](../../docs/retention.md#local-collection-evidence).

Vault observation pages start with only the host; historical reports end with one Collection metadata section. Historical report names are YYYYMMDDHHMMSS-title.md in UTC, without UUIDs/fractional seconds. Full rebuild routes host content under its first group (or _ungrouped) and updates all generated indexes/group links; other group memberships link to that one location. Retention paths/identity do not change. Preserve old unmanaged notes and README files; users relocate/link those deliberately after a layout/group change. Same-second/title collisions are reported without overwriting retained evidence. See [layout and regeneration limits](../../docs/host-vault.md#directory-and-ownership).

For readable Vault observations, reuse the bundled vault_content.render_observation / vault rebuild workflow described in [Vault content](../../docs/host-vault.md#recipe-retention-and-markdown). Inventory is presented in domain tables; source IDs and full record provenance are in a final disclosure section, while identity/partial warnings and collection coverage remain visible. Human-friendly capacities retain exact base units. Null, zero, false and empty collections remain distinct. Authorized rebuild replaces owned historical/latest Markdown without collection or retention changes and preserves unmanaged notes. Read structured data through retention APIs, not Markdown scraping.

For automatic retention handlers/converters, read [consumer contract 0.1.0](../../docs/retention-consumers.md) and the [bundled Vault consumer](../../consumers/vault/README.md). First discover existing programs with `consumers list --recipe system/inventory/overview --profile NAME --json` or `recipes show`. Sources are checkout consumers/NAME and Feast-local consumers/NAME; candidate discovery never activates code. Before enabling a reviewed program, verify its Python/dependencies, supported retention contracts, input sources, output ownership and authorized side effects. Register source/enabled explicitly in feast.yaml; default builtin:vault is already enabled. Author `execute(context)` with context.retention.query/show and metadata event hints, preserving partial/unknown/identity context. Outputs must tolerate at-least-once delivery, deletion and stale creation hints. Reuse the documented dispatcher rather than modifying runner, scanning raw files or writing SQL acknowledgement code. Inspect per-consumer status/attempts in content_update.consumers or `consumers inspect`; retry with `consumers dispatch [ID]`. Disabled backlog is processed after activation, while eventless historical data needs explicit application rebuild. In-process Python is not sandboxed or time-limited; no network delivery, installer or scheduler is implied.

# OpsFeast result data

Read [offline retention replay and deletion](../../docs/retention-replay.md). Prefer `retention ingest --profile NAME --all --dry-run --json`, then actual ingest; explicit files precede options. General new raw replays its saved snapshot; old general raw requires reviewed --recipe-dir. `retention delete-observation ID` permits only read observations; write/unknown, operation events and linked verification evidence are protected. It preserves raw/human files and rebuilds views. Use the returned source ID, keep raw digest separate, and do not infer execution mode from a revised descriptor.

## Recipe retention and content applications

Read [retention contracts](../../docs/retention.md), [offline replay/protection](../../docs/retention-replay.md) and [vault ownership](../../docs/host-vault.md). Recipe creators define/produce retention; OpsFeast manages recipes/execution and data discovery/storage. User AI agents combine retention into Markdown, graphs or web content. Vault is the bundled content application, not the data contract. Vault rebuild overwrites manifest-owned generated files even after editing or editor formatting and removes obsolete owned outputs; preserve notes in unmanaged files. Unmanaged paths and other authors' outputs retain collision protection.

1. Discover declared datasets with recipes list/show or inspect-recipe --json. Read field meanings, units, versions, limits and source-qualified references before selecting data; metadata is not execution evidence.
2. Query with `retention list/show/export --profile NAME --json`, Core `profile.retention.query/show`, or checkout `retention_store.query/show`. Annual authoritative SQLite lives in retention/; reads never initialize or connect. Preserve source times, origins, identity warnings, partial/unknown states and zero/false values.
3. Authors declare host-values 0.2.0 with dataset/field descriptions; system/inventory/overview 0.3.1 owns inventory-observations 0.1.0, its schema and registered normalizer. Discovery reads the explicit declaration; it never guesses from recipe ID. Retention snapshots 0.2.0 contain data definitions only. No markdown_template or rendered Markdown is retained.
   Read [inventory-owned data semantics](../../recipes/system/inventory/overview/README.md#recipe-owned-retention-contract) before authoring or interpreting inventory: explicit access_mode/retention declaration, recipe-local schema, normalizer/schema digests, supported versions and partial/identity limits. Registered contract/version selects shipped pure normalization; candidate main.py/retention.py is never loaded by replay. A new structured contract requires reviewed product registration and tests, not descriptor executable paths. Reuse runner/replay/query; include retention.schema.json in portable clone bundles. Current envelopes preserve retention_definition and source provenance.
4. Reuse offline python-report's `context.retention.query/show` and artifact/result/job support for content. [feast/report/retention-summary](../../recipes/feast/report/retention-summary/README.md) generates Markdown and HTML and combines multiple recipe references without raw access or connections. Custom renderers declare dependencies and verification; no hosting or transmission is implied.
5. Use retention ingest/delete-observation/rebuild for data and vault rebuild/groups/inspect for content. Replay does not execute recipe code. Write/unknown operations and linked evidence remain protected. Direct Core calls need explicit retention_store.operation_intent/operation_result journaling.
6. Init establishes namespace plus independent retention/vault areas. vault.auto_refresh defaults true and may be disabled. Check recipe status, retention and content_update separately; consumer failure preserves stored data and is retried with consumers dispatch; explicit vault rebuild regenerates current Vault content. Old vault SQLite layouts are rejected and preserved; use a separate profile and explicitly replay raw. Old inventory raw without snapshots, old template snapshots and structured normalizer/schema digest mismatches need a reviewed current --recipe-dir; never reclassify historical execution.

Terminal summaries now use tabulate when stdout is a TTY. For agents, explicitly add `--json` to supported diagnostic, instance, profile/check, recipe/job execution and utility commands; non-TTY output retains existing contracts. Dump/raw results/artifacts/exports remain structured. Check-access retains its existing default table. Read [the command-specific output policy](../../docs/cli.md#terminal-tables-and-json); flags change presentation only, not authorization or saved-job inputs.

Human `recipes results list` displays the actual inventory collection user instead of identity quality; missing or uncertain evidence displays unknown. Never infer the collector from SSH login or a selected intermediate account. TTY lists omit the long identity-warnings column. Select `--json` or detail/show for preserved identity quality and full warnings; the index adds nullable collection_user without rewriting saved data. Read [collector evidence and human output](../../docs/cli.md#saved-result-collection-user).

After every OpsFeast release update, reread the installed release's current object schemas/data contracts, including hosts.yaml, before resuming work, regardless of diffs or earlier reading. Follow the [mandatory release reading list](../../docs/skill-updates.md#required-schema-reread-after-a-release-update). No reading receipt or completion verification is required.

For the public Python package, installation identity, profile/hosts snapshots, scoped sessions and Recipe su/sudo, read [opsfeast-core](../opsfeast-core/SKILL.md) and its [API guide](../../docs/core-api.md). New python-recipe 0.1.0 entrypoints receive execute(recipe); legacy python-session Session/context interfaces remain unchanged.

Start with the [central skill index](../README.md). Keep newly authored Feast-specific skills in the selected management root's `skills/`; check task-relevant source/loaded copies and agree with the user on any naming, version, instruction or loader conflict before the affected action. Follow [storage and conflict resolution](../../docs/agent-guidance.md#skill-storage-and-conflict-resolution).

Read the repository AGENTS.md, [CLI reference](../../docs/cli.md#retained-observations-and-exchange) and [canonical workflow and capability contract](../../docs/result-data.md). Use the [recipe skill](../opsfeast-recipes/SKILL.md) for authorized execution. This skill and its linked guides/schemas must be distributed together; automatic skill loading is not required.

General recipes without namespace/declarations remain raw-only. In namespace-enabled profiles, general raw with a retention snapshot supports retention ingest; old general raw needs an explicit descriptor override. The legacy observation_store inventory recovery/exchange format does not ingest general results. See [general results](../../docs/recipe-execution.md#results-failure-states-and-storage).

## Prefer existing OpsFeast capabilities

This workflow serves DevOps users and their agents, including specialized recipe authors. OpsFeast product developers must provide broad, complete and stable building blocks to reduce user-side development; see [the distinct roles and shared principle](../../docs/vision.md#distinguish-product-developers-from-devops-users). For both roles, use reviewed programs for routine repetition and reserve AI for new needs, judgment, changes and exceptions.

Before writing operational code, consult the [tool and Python module capability map](../../docs/agent-capabilities.md). Discover a suitable existing recipe/CLI workflow first; reuse documented modules for appropriate Python composition after checking current signatures and prerequisites. Implement only missing task logic and explain a concrete gap when an existing capability cannot fit. Preserve workflow validation, enabled controls, authorization and failure evidence; do not infer execution permission from availability.

Use the existing retention adapter, export/validate/combine interfaces and JSON/CSV surfaces before creating storage or exchange code. For in-process analysis reuse `observation_store.export`, `validate_exchange` and `combine`; for saved raw results/artifacts reuse `recipe_reports` lookups. Author only recipient-specific queries/transforms/rendering not covered by existing contracts; do not read host credentials for offline data processing.

Inventory raw result filenames use the UTC started_at second plus UUID (`YYYYMMDDTHHMMSSZ-inventory-system-UUID.json`). Preserve older unprefixed files; reuse recipes results list/show or recipe_reports results/show_result rather than assuming one filename prefix. Name order is start-second order only; same-second UUID ordering is arbitrary. Use stored full-precision times for interpretation and retention/exchange, and the returned result_path/result_id for lookup. See [the result reference](../../docs/cli.md#saved-results-and-stdout).

## Inventory access and result capability 0.1.0

Read [the complete inventory access/results guide](../../docs/inventory-access.md) before selecting accounts, testing access, running inventory, authoring collectors or interpreting/exporting new values. It documents exact interfaces, settings, source selection, dependencies, authorization, failure/skip/fallback states, units, scope and verification limits.

- Use check-access for selected hosts.yaml login/root validation plus independent su to every other declared user and sudo as that actor unless its sudo is Boolean false. Missing su credentials are skipped and unverified; su failure prevents that actor's sudo. Inventory --dryrun adds static recipe/input checks and uses the bounded two-candidate inventory policy, including possible su. Both make real connections and privilege attempts without inventory or host-init data. See the [account-check scope and results](../../docs/inventory-access.md#check-access-without-collection). Test-host additionally handles platform facts.
- Inventory selects at most the login account and the first other users account with sudo true/omitted, preserving YAML order. An eligible root second candidate gets su root priority; otherwise login sudo precedes second-account su/sudo. Account sudo: false disables that account's sudo and excludes it as a second candidate. Read the [canonical selection and evidence rules](../../docs/inventory-access.md#inventory-account-selection). Sudo policy is Boolean-only: true/omission enables it, and quoted "false"/"true" are rejected. Canonical sudo-password selects by presence: null/empty mean empty password; exact "false" means account-password fallback. Other disabling representations are invalid; no retry with another credential. Prefer these canonical fields; preserve legacy vars credentials and do not rewrite private configuration.
- The default batch gate rejects collection after any required access failure. Verified login-user fallback is automatic when root is unavailable (nonzero execution exit); force permits unavailable hosts to be skipped; uncertain identity/restoration/cleanup still stops that host. Dryrun/force are mutually exclusive and inventory-only, not saved-job flags. Check access.mode, batch counts and exit code separately from collected values.
- Pure results are inventory.system/hardware/storage/network/software/services with fixed nullable typed fields. Raw collection_process/observations/sources preserve execution evidence. Retention/exchange preserve inventory and minimal collection_scope, omit diagnostics, and keep original times/identity quality. Old records remain valid; update strict consumers before accepting new extension fields.
- For CSV use observation_store.py export --format csv with explicit filters; null becomes an empty cell, zero stays zero, empty lists remain []. JSON is the exchange contract. For SQL query the retained payload with json_extract; for reports reuse the updated offline feast/report/execution-summary or reviewed user recipes. A later run with another account is separate history, not automatic field merging.
- Extra queries have byte/item/command/shared time bounds and platform gaps. Root does not guarantee complete visibility. No new native SSH/sudo or all-platform collection evidence follows from synthetic tests. Do not install missing tools, probe arbitrary files or transmit exports without scope.

## Available capability catalog

| Capability | Interface/version | Availability and limits |
| --- | --- | --- |
| Automatic retained inventory | run_recipe.py → declared inventory-observations 0.1.0; recipe-owned registered normalizer | Raw result 0.2.0, operational local/SSH success/partial; SQLite via Python standard library |
| Recovery | observation_store.py ingest FILE... | Explicit local raw files in their originating Feast; no host connection |
| Shareable export | observation_store.py export; --format csv for presentation | JSON exchange 0.1.0 or fixed CSV columns, recipe/host/time selection; JSON is the exchange contract, no transmission |
| Static exchange validation | observation_store.py validate FILE | Strict record/envelope checking; no database/profile required |
| Exchange combination | observation_store.py combine FILE... | Validated union and ID deduplication; conflicts fail; no host reconciliation |
| Saved-result lookup and artifact verification | opsfeast.py recipes results list/show; recipes artifact; recipe_reports module | Read saved raw/report evidence and verified paths; no new collection or transmission |
| Offline analysis/reporting | feast/report/execution-summary or reviewed python-report recipe | Reuse local report/artifact contracts and basic views; richer renderers and recipient stores are user-selected, no bundled stage-4 database importer |

Check the selected interpreter, available tool files and chosen profile/root first. Setup does not authorize collection or sudo. Reading/exporting existing data does not authorize sending it to others. Do not read hosts.yaml credentials merely to process retained results. A missing retained database is not a successful empty inventory; propose ingestion of specifically identified local results or authorized collection as appropriate.

## Follow the four-stage workflow

1. Explain that raw execution evidence, retained observations, exchange data and analysis storage have independent contracts. Read the relevant result/retained/exchange schemas, not thousands of raw files, to choose a workflow.
2. After authorized recipe execution, inspect collection status **and** retention receipt. Runner automatically attempts stage 1 → 2. Failed/skipped/unsupported/mock results are excluded; partial retains null states. A zero exit requires complete collection and no retention failure. Source-disabled/host-disabled paths may have no report.
3. If retention failed, identify the raw result_path and retry `python -B tools/observation_store.py ingest /absolute/raw.json --profile NAME`. Explain that replay performs no remote work. Inspect stored/already_stored/skipped results and database errors; do not silently change raw files, delete the database or re-run remote operations. Backup/recovery requires its own concrete scope.
4. For sharing, determine the intended recipe, local hosts, completion-time interval and destination from the user's request. Use export with explicit filters where appropriate; absence of filters exports all retained data. Explain that device IDs and hostnames may be included. Export to a new reviewed file, validate it, confirm record count/selection and inspect for unexpected fields. Sending remains separately authorized; there is no transmission tool in this capability.
5. For A/B data, validate each received exchange before combining. Use combine to remove identical observation IDs and reject conflicting content. Preserve all different observations; equal host keys do not authorize collapsing history. Do not ingest foreign raw data as local observations.
6. For recipient analysis, inspect the exchange contract and choose the user's requested store/tool. Preserve IDs, timezones, statuses and identity quality. A missing OpsFeast importer does not block a feasible user-authorized script; report missing dependencies and test transformations with synthetic data. Do not invent a bundled import command.

## Handle identity honestly

Host means OS installation: reinstalling/changing the OS is a different host, even on the same equipment. Rotate user-assigned identity_key after reinstall/replacement; inability to detect a preserved native identifier or fallback continuity is a limitation, not an exception to this definition. IP/hostname are mutable; hardware serial/UUID links equipment and cannot detect reinstall. Linux uses an application-specific machine-id HMAC digest as a candidate, with clone/reinstall caveats. FreeBSD/macOS/ESXi currently use fallback installation identity even if hardware probes succeed. Inspect raw identity.evidence only when investigating a concrete identity problem, and keep raw execution details local.

Fallback keys namespace local host_id by source Feast UUID. They permit local history but cannot prove continuity after target replacement or cross-source equality. Read/relay identity_warning and give a concrete remedy according to probe state. Inventory identity probes use the same verified actor as collection. Account sudo is attempted by default unless Boolean false; legacy identity_sudo no longer selects collection privilege. Do not promise elevation resolves missing OS-identity contracts. No target installation marker is written.

Matching machine-derived keys are evidence, not uniqueness proof. Compare device evidence for contradictions and preserve unresolved conflicts. Do not auto-merge fallback identities, rename keys, assign all old observations to newly discovered identities, or equate lack of a new record with a host disappearing. Reviewed historical aliases and organization-wide asset mapping are not implemented.

## Maintenance and extension

Contract versions and database physical version are distinct. Never mutate schema ad hoc. New recipes need a trusted adapter, versioned retained/transfer contracts, failure and partial rules, tests and discoverable recipe capability references. No arbitrary third-party adapter is executed by ingest/validate/combine. Real sudo/SSH/ESXi support remains unverified beyond documented interfaces and synthetic tests. Preserve human records, source databases and unrelated files; retention deletion/transport/authentication remain separate operations.

Host identity_key, label and description are now supported. An explicit identity_key takes precedence and is shared across Feasts as user-assigned identity; change it after OS reinstall/replacement and coordinate its namespace. label/description are captured human text, never identity keys, and are preserved through retention/exchange. See [the canonical host configuration](../../docs/hosts-yaml.md#explicit-host-identity-and-human-readable-metadata) and [identity/metadata rules](../../docs/result-data.md#explicit-identity-and-display-metadata). MAC is not an automatic key.

## Inspect long result IDs vertically

Reuse `python -B tools/opsfeast.py recipes results detail --host HOST --root ROOT`
for a filtered saved-result index with one field: value per line, then
`python -B tools/opsfeast.py recipes results detail RESULT_ID --root ROOT` for one
complete raw result. This avoids wide filename tables without reconnecting. Nested
object fields use dotted names, arrays remain JSON and controls are escaped.
Explicit --json returns the unchanged index/raw data contract; human detail stays
vertical even through pipes. Empty indexes, invalid files, unsafe/missing IDs and
option conflicts retain explicit outcomes. Use [the canonical detail reference](../../docs/cli.md#vertical-result-details)
for syntax and verification limits. Existing list/show and result files are unchanged;
no remote authorization is required or expanded by these read-only commands.

## Select saved results by short ID

Human `recipes results list --host HOST` displays short IDs; pass a displayed ID to
`recipes results show SHORT_ID` or `recipes results detail SHORT_ID` using the same
--root/--profile. Artifact lookup accepts the same IDs. For automation use --json:
index records/errors add short_id and preserve full result_id; raw show JSON and saved
files are unchanged. Prefer complete result_id for durable stored references.
Do not derive aliases by truncating filenames. Reuse the checked resolver: the alias
is a SHA-256 path prefix, at least eight lowercase hexadecimal characters, extended
for uniqueness across the entire root before filtering. Unknown/ambiguous prefixes
and unsafe paths fail explicitly. Old files need no migration/rewrite or host access.
Read [the canonical short-ID workflow and lifecycle](../../docs/cli.md#short-result-ids)
for copying/renaming, collision boundaries and synthetic verification evidence.

## Interpret human local timestamps

Human CLI tables/results detail, HTML and TUI Details display OS-local time to seconds
(YYYY-MM-DD HH:MM:SS). Reuse these views rather than rewriting saved data. feast/report/execution-summary
0.1.2 HTML uses controller local time at generation; its portable implementation needs
no checkout display-module import. --json, raw results show, Original output, JSON/CSV
exports and saved data preserve original precision/offsets for analysis and hashing.
Missing/unzoned instants do not acquire an invented timezone. Read [the canonical display
policy and synthetic verification](../../docs/cli.md#human-time-display-policy) before
comparing display strings, interpreting DST or authoring another human report.

Current records use records/current-<title>.md, contain data and a Latest report link, and omit Collection metadata. Both current and historical observation pages start with a Contents index; only historical reports end with Collection metadata, including identity/coverage warnings and queries. The redundant Field observations table is removed. Missing sections say No data was collected; observed empty collections remain No entries reported. Read structured retention records for original field states and timestamps. Rebuild regenerates owned pages without collecting again or rewriting retention; old manual links require deliberate updates. Current title collisions across sources fail publication without overwriting evidence.

Current selection groups each host by origin namespace, recipe-source qualifier (the prefix before a colon, or the unqualified source) and stable recipe ID, then selects the whole record with the greatest (observed_at, record_id). Recipe-directory moves within that source therefore keep one current page without aliases or rewriting historical references. Partial results remain partial. Distinct sources, origin namespaces or recipe IDs remain independent; a shared output title still fails publication explicitly rather than silently replacing another dataset. All historical reports remain available.

Vault Contents links use Obsidian-native heading fragments: `[System](#System)` and `[Collection metadata](#Collection%20metadata)`. Heading case is preserved and spaces/non-ASCII text are URL-encoded; arbitrary HTML anchor IDs are not used. Repeated headings are given unique readable titles (for example Services details) so each link reaches one section. In Obsidian Reading view, click a Contents link; in Live Preview, use the normal follow-link gesture (Cmd-click on macOS or Ctrl-click on Windows/Linux). Other Markdown readers can use different heading-fragment conventions; this is not a universal reader-compatibility guarantee. Rebuild regenerates current and historical observation pages plus the records index from retention, without recollection. See [Obsidian internal links](https://obsidian.md/help/links).

_Last modified: 2026-10-19 20:06:02_
