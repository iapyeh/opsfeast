# SSHScript Ops to OpsFeast

## Recipe policy and observation runs

Recipe settings now use direct exact-reference mappings at default, group and host levels: `recipes: {system/inventory/overview: {enabled: true, vars: {...}}}`. Do not use descriptor IDs or flatten directory names into hyphens. `bundle:PATH` and bare PATH are equivalent; same-layer duplicates fail. `:PATH` stays profile-scoped and named prefixes stay source-scoped, without fallback. Mappings merge per leaf, ordered first-group precedence wins and lists replace. Nested input objects now retain inherited sibling fields; review inputs that relied on shallow replacement. Within invocation inputs, --var still replaces that same file-provided variable before preparation.

Every recipe defaults disabled; new init explicitly enables bundled inventory in default.recipes, while existing files are preserved. **Existing group/all/scheduled workflows need explicit recipe enablement.** Existing host selection lists remain readable but do not enable bulk execution. Explicit recipe/inventory --host now overrides host/source/recipe enabled flags for that target; disabled jumps and invalid inputs/paths remain errors. Diagnostic/Core-session controls are unchanged. Review automation relying on the former explicit-host skip behavior before rerunning. See [policy and examples](recipe-sources.md).

New namespace-enabled operational invocations and saved inventory collections persist explicit [observation runs 0.1.0](observation-runs.md). Consumer descriptors/event readers must accept retention.run.updated; event record_id is a run UUID, read through retention.run rather than show. Completed batches snapshot policy/findings; rebuild does not fabricate old membership or apply new thresholds to historical runs. Run objects are separate from retention query/export records. No automatic migration, deletion or recollection is provided.

Vault uses records/SUMMARY.md and readable topic-based current pages with optional DGMO definitions. Full yearly reports preserve detailed data/evidence. Observation filename collisions now use ordinal suffixes instead of failing or appending IDs/digests. Update hand-written links after rebuilding owned pages; unmanaged notes and prior retained/raw data remain intact. Current Attention uses current recipe vars; saved batch Attention uses the recorded policy. See [current/report separation](host-vault.md#recipe-retention-and-markdown).

## 2026-10-20: one recipe execution entrypoint

Use opsfeast.py recipes run for operations/reports and inventory query/run for selective collection. tools/run_recipe.py and its --recipe, --dryrun and --force options are removed. All inventory execution uses descriptor 0.3.0, inventory-jobs 0.1.0 and inventory-job-observations 0.1.0. Update scripts and reviewed copied inventory descriptors explicitly; use check-access for independent account diagnostics. The old all-host access gate is removed; each host acquires its actor and records its own outcome.

The current recipe's primary retention declaration now describes the job dataset. Consumers subscribed specifically to inventory-observations must deliberately add/change their subscription to inventory-job-observations after reviewing its schema; wildcard Vault continues to handle both. Historical data is preserved and is not converted automatically. Pinned saved jobs must be reviewed and recreated when fingerprints change. Historical replay requires its saved definition or an explicitly reviewed matching historical definition, not today's descriptor.

The dated sections below describe previous releases and must not be used as current invocation instructions.


## Readable Vault page paths and optional evidence

Vault host content now lives under hosts/PRIMARY_GROUP/HOST/, selecting first membership or the distinct _ungrouped bucket. Full rebuild regenerates owned pages and all generated links at current locations. Unmanaged notes and old host README files remain unchanged at their original paths; move/link those deliberately. Authoritative retention layout and identity remain group-independent. Observation report names use YYYYMMDDHHMMSS-title.md without identifiers; equal-second/equal-title collisions receive ordinal suffixes without deleting retained history. Header-only host identification and one final metadata section replace the success banner and separate account block.

The Vault consumer now chooses titles and replaces encoded-reference/full-digest Markdown names with title slugs and whole-second UTC observation names plus titles (operation pages retain discriminators; current pages use current-title names). An authorized vault rebuild updates managed pages/indexes and removes stale owned paths; update manual links yourself. Human notes remain unmanaged. No data migration, alias or automatic host rerun is added. See [naming and ownership](host-vault.md#directory-and-ownership).

Inventory recipe 0.3.2 fixes CRLF producer-marker parsing and records optional local collection_evidence 0.1.0. Existing snapshots keep their registered normalizer/schema digests. Old retained observations remain unchanged; rebuild cannot fill their missing account/query metadata or inventory values. A new authorized collection creates separate history. Strict local envelope readers should accept the new schema property before consuming new reports; the legacy normalized exchange excludes it.

## Classified bundled recipe paths

The five bundled recipe directories now follow [domain/subdomains/action/name](recipe-taxonomy.md#bundled-path-relocation). Existing IDs/versions and data contracts remain unchanged, including byte-identical inventory retention normalizer/schema. Update bundle path selectors, saved invocations/jobs and exact consumer/report selections using the mapping. Old bundle directories are removed without aliases. Profile/external recipe trees, raw files, retained records and queued events are not rewritten. Historical references remain queryable as their original exact strings. No automated relocation or user-data migration tool is supplied.

## Consumer delivery receipt change

Retention-to-content updates now use [registered consumers 0.1.0](retention-consumers.md). Existing raw/retained schemas and human notes are preserved. The `content_update` payload changes from a single Vault result to an aggregate with a `consumers` attempt list; callers must update field access. Vault remains enabled by default and retains vault.auto_refresh control. Additional consumers require explicit registration. New writes/deletions commit durable events; prior eventless records are not backfilled, including deduplicated replay. Use explicit application rebuilds for historical output, and `consumers dispatch [ID]` for journal-backed retries. No automatic data migration or historical recipe rerun is performed.

## Retention/content development incompatibility

Authoritative data now lives under retention/, while vault/ contains content and human notes. Old SQLite-in-vault layouts are rejected; there is no automatic relocation, fallback reader or new migration tool. Preserve the old profile and notes, initialize a separate profile with the same namespace and use `retention ingest` on explicitly selected raw. Existing raw receipts preserve source identity. No old data is automatically removed.

General host-values declarations are now 0.2.0 and require dataset/field descriptions. Data-only snapshots are 0.2.0; `markdown_template`, snapshot template text and retained rendered Markdown are removed. Old general snapshots require a reviewed current --recipe-dir override for offline replay; original write/unknown classification remains protected. Move content logic into an offline report using context.retention. See [exact contracts and recovery](retention.md#development-incompatibility).

Storage imports move from host_vault to retention_store; Core programs prefer profile.retention.query/show. Use `retention ingest/delete-observation/rebuild` for data and `vault rebuild/groups/inspect` for content. Default automatic vault refresh remains, configurable through vault.auto_refresh; retention and content receipts are separate. No web hosting, publication or scheduler is added.

system/inventory/overview recipe 0.3.1 now owns explicit inventory-observations 0.1.0 retention, its local retention.schema.json and the registered retention.py normalizer. Raw output no longer accepts retention_adapter/retained_contract_version/exchange_version keys. Copied descriptors need the new declaration, matching schema and explicit access_mode. Old inventory raw requires a current snapshot or explicit reviewed --recipe-dir; changed installed normalizer/schema digests require reviewed extraction selection. Preserve original execution classification and existing records; conflicting definitions are never silently rewritten. No migration, candidate-code loading or automatic deletion is introduced.

The product and repository are now OpsFeast (`iapyeh/opsfeast`). The local checkout does not need to move. Private management directories, profile names, targets, credentials, human notes, observations and execution history retain their existing locations and contents.

## Recipe.root console (2026-10-17)

Core 0.1.0 adds `Recipe.root()` and public `RootUnavailableError`. Use
`with recipe.root() as root:` then `root("id -u", check=True)` for authorized root-only
operations. It shares inventory's ordered two-candidate selection, verifies UID 0 and
raises on failure; there is no required/fallback argument. It yields a scoped callable
console, whereas existing Recipe.su/sudo continue yielding child Recipe objects. Thus
root uses command strings directly, not root.session.exec_command(argv). See
[API examples, console prerequisites, lifetime and errors](core-api.md#automatic-root-console).

No descriptor, CLI, configuration or retained schema migration is needed. Existing
explicit privilege calls retain their behavior. Generic recipes must explicitly opt
in; callers may inspect RootUnavailableError.report only after verified restoration.
Unsafe acquisition/cleanup disables the scope. The runner and inventory share the
strict helper; inventory alone chooses safe login fallback. The already-root public
console requires Bash, while inventory's existing root exec path remains unchanged.

## Inventory account selection (2026-10-17)

Inventory now selects at most the login account and the first other `users` account
whose sudo is true or omitted, preserving YAML order. An eligible second account named
root is tried with su before login sudo; other second accounts follow login sudo and
use su then sudo. No third account or alternate credential is tried. Missing su
credentials skip that route. See [the complete policy and example](inventory-access.md#inventory-account-selection).

Review users order and existing execution authorization before resuming inventory:
login `sudo: false` now disables only that actor's sudo and can still allow root through
the selected second account. To keep ordinary collection intentional, also leave no
eligible second account. No new admin field or private configuration rewrite is needed.
Safe login fallback no longer requires --force; its data remains retainable and its
execution exit is nonzero. --force now permits skipping unusable hosts, never uncertain
identity or recovery. Dryrun uses the same two-candidate access policy and can succeed
with safe user fallback; explicit check-access continues independent account diagnostics.
Failed/skipped preflight routes are not retried during collection. Existing result and
retained schemas remain valid; raw access evidence adds selection and attempt details.
The runner now preserves the authenticated final-hop login when accepting an ESXi root
shell and includes identity reason codes in collection errors and summaries. Historical
failed results are not rewritten or automatically rerun. Synthetic tests establish
policy/cleanup behavior, not native SSH, su/sudo or ESXi inventory compatibility.

## Host icon default (2026-10-15)

Effective loaded hosts now always include icon, default 🍎; source YAML/comments remain unchanged. Explicit icons must be exactly one Unicode Symbol code point. Consumers that assume an exact set of host dictionary keys must accept this optional configuration field/default. Persisted inventory/retained/exchange schemas and identities are unchanged. See [host icon rules](hosts-yaml.md#host-icon).

## Core package and installation identity (2026-10-15)

Instance now precisely means the entire installation/checkout; management roots are profile environments. Existing profile registry and feast.yaml schemas/data remain valid. Read-only use of an older installation exposes a nil UUID placeholder; the next authorized init creates identity. Copies receive a new UUID; actual moves explicitly relocate identity. See [Core API](core-api.md).

The public package owns shared configuration functions; tools/opsfeast.py remains a compatibility launcher/import bridge. Distribute the complete checkout or built wheel, not that launcher alone. Legacy Python-session, report and inventory recipes retain their entrypoints and results. New python-recipe 0.1.0 explicitly receives execute(recipe); change descriptor and code together. No automatic recipe rewrite, package installation, data migration or PyPI publication occurs.

## Centralized skill sources (2026-10-13)

The complete bundled SSHScript snapshot moved from `.agents/skills/sshscript/` to `skills/sshscript/`, alongside all OpsFeast skills. Its contents, documentation contract and provenance are unchanged. Environment and bundle-check tools use the new location. Update explicit links and local integrations that used the former path; do not create a second source copy there. Existing agent installation copies are not automatically moved or updated. For duplicate names, version/instruction differences or loader conflicts, preserve local files and agree on the user's integration plan as described in [agent guidance](agent-guidance.md#skill-storage-and-conflict-resolution). Feast-specific user skills use `<management-root>/skills/`; this convention adds no automatic installer or discovery mechanism.

## Parameterized Python recipes (2026-10-13)

opsfeast.py recipes run now accepts --var NAME=VALUE and a JSON --vars-file for inventory and general Python-session recipes. Invocation inputs overlay existing defaults/source/host values without rewriting configuration. Existing inventory descriptor/result 0.2.0, legacy collectors without effective vars, host/group selection and retention stay supported. Other IDs require descriptor 0.3.0, runner python-session 0.1.0 and execute(session, *, context, timeout); existing standalone main.py --host programs are not automatically adapted. Move only their operation into execute and declare inputs/results after reviewing the complete implementation. See [execution/migration](recipe-execution.md) and [authoring](recipe-authoring.md). Generic results save raw JSON with skipped inventory retention.

## Name mapping

| Former name | New default | Compatibility |
| --- | --- | --- |
| SSHScript Ops / sshscript-ops | OpsFeast / opsfeast | Update clone URLs and repository references. |
| tools/ops.py / Python import ops | tools/opsfeast.py / import opsfeast | Old CLI/import names are removed; update callers to the new names. |
| skills/sshscript-ops-hosts | skills/opsfeast-hosts | Update skill paths/names and install complete candidates through the agent platform's procedure when authorized. |
| skills/sshscript-ops-recipes | skills/opsfeast-recipes | Update skill paths/names; linked guides remain part of the complete skill. |
| .my-ops.yaml | .opsfeast.yaml | Read and update the existing legacy registry if it is the only one. New checkouts use the new filename. |
| my-ops.yaml, schema 1, kind sshscript-ops | feast.yaml, schema 1, kind opsfeast | Validate each filename against its corresponding kind. Existing definitions are preserved. |
| my-ops/main or my-ops/NAME | feasts/main or feasts/NAME | New profiles use feasts/. Named init reuses an already registered profile's root. Existing directories are not moved. |

The SSHScript library, public skill snapshot, source provenance, recipe IDs and recipe/result versions keep their original identity. There is no new pip-installed OpsFeast package or bare opsfeast executable in this rename; use the Python script entrypoint.

The earlier tools/my_ops.py and tools/ops.py entrypoints are removed. Configuration/data compatibility remains supported; CLI and Python callers must use opsfeast.py / opsfeast.

## Use an existing checkout without data migration

After updating the checkout, use the same interpreter:

```sh
python -B tools/opsfeast.py profiles
python -B tools/opsfeast.py check --profile main
```

Choose an existing profile name from profiles; old schema-1 locators expose the name default, not main. Both commands are read-only and do not connect. Update old commands to tools/opsfeast.py and Python imports to opsfeast; no ops.py wrapper is provided.

Only one registry may exist at a time: .opsfeast.yaml or .my-ops.yaml. Both together fail with a conflict instead of silently preferring one. The same rule applies to feast.yaml and my-ops.yaml within a Feast. Symlinks, wrong entry types and unsupported definitions remain errors; dangling symlinks count as present.

Registry schema 1 is still interpreted as a default profile. Registration or use writes schema 2 to the same active registry filename; read-only commands do not convert it. This preserves prior behavior and does not rename the registry.

## Optional explicit naming migration

Migration is unnecessary for continued use. Perform it only after reviewing the affected paths and authorizing that specific migration. Stop concurrent writers and keep a private backup outside public publication inputs.

1. Check the current profile registry and definitions with profiles/check. If both naming generations exist, review both first and consolidate registrations manually; do not discard an unreviewed file.
2. To rename the registry, confirm .opsfeast.yaml is absent, then rename .my-ops.yaml to .opsfeast.yaml without changing its contents. Schema 1 or 2 remains supported. Keep all profile names, selected default and root values.
3. For each definition being migrated, confirm feast.yaml is absent. In the backed-up my-ops.yaml, change only kind from sshscript-ops to opsfeast, retaining schema_version: 1 and comments, then rename it to feast.yaml. Keep the environment offline during this two-step edit. A filename/kind mismatch fails validation.
4. Leave existing management directories in place. Moving them is a separate operation requiring review of registry roots and any absolute paths or integrations.
5. Run profiles and check for every affected profile. Confirm configuration, notes and historical files were preserved before resuming work. These checks do not establish connectivity or execution success.

The tools do not provide a migration command or automatically rewrite private data. A newer definition schema should be introduced only for an actual contract change, not for a brand rename.

## Profile command names

The former add ROOT command is replaced by attach ROOT, retaining --profile NAME for registration naming. There is no add alias. Detach NAME unregisters an exact name without deleting its management directory; main cannot be detached. Removing the selected default first validates a registered usable main and switches to it atomically, or fails without changing the registry. Profiles now shows basic location status, retaining missing registrations. Registry/definition filename and schema compatibility remain unchanged; see [profiles](profiles.md).

## Host group field

Host membership uses `group: NAME` for one group or `group: [NAME, ...]` for multiple groups. Rename the former `groups` key to `group`, retaining its values and comments; groups is not an alias, and configurations with either the old key alone or both names fail with a migration hint. Omitted group or group: [] means no membership. Run check after updating the defining YAML files, including includes; see [host groups](hosts-yaml.md#host-groups). No connection or recipe execution is required to validate the migration.

## Named recipe sources and input context

Bare system/inventory/overview keeps its checkout meaning; :system/inventory/overview selects profile recipes/, and source:system/inventory/overview selects an explicitly registered recipe_sources root in entry hosts.yaml. Existing recipes/... YAML and ./ instance paths remain supported. Source registrations do not widen include/output paths or authorize execution. Enabled source/host flags and --all --exclude add explicit skips/omissions without rewriting settings. See [sources and controls](recipe-sources.md).

Host recipes lists now accept strings or mappings with vars. Vars-bearing inventory implementations must accept the context keyword and declare inputs.variables; legacy four-argument collectors remain valid without effective vars. The bundled recipe is 0.2.1, with descriptor/result schema 0.2.0 unchanged. Linux implementation is 0.1.2 and FreeBSD/macOS are 0.1.1. Required/type/bound checks and first-level overlay precedence are documented in the [input contract](recipe-sources.md#variables-and-implementation-context); no arbitrary-recipe runner or installer is added.

## Inventory runner arguments

The inventory runner now requires explicit recipe and target selection. Replace positional host/root arguments and --hosts with `opsfeast.py recipes run system/inventory/overview --host HOST ... --root ROOT`. Use --group for group names, or exclusive --all for every configured host. A positional recipe must come first; --recipe DIRECTORY may appear at any option position. Omitting the recipe no longer uses host YAML selectors. See the [runner reference](cli.md#operational-recipe-execution) for the complete interface, examples and result behavior. Existing YAML recipe selections, profiles and private data are preserved.

## Git and local integrations

New clones use https://github.com/iapyeh/opsfeast.git. Existing clones can update origin explicitly:

```sh
git remote set-url origin https://github.com/iapyeh/opsfeast.git
git remote -v
```

Review scripts, bookmarks, installed agent skills and local project settings that refer to the old repository or skill paths. Do not modify the bundled skills/sshscript/ knowledge snapshot as part of the OpsFeast rename. Local checkout paths can stay unchanged; moving a checkout requires separately updating those local integrations.

## Inventory result pipeline 0.2.2

Updating to inventory-system recipe 0.2.2 adds ESXi dispatch, read-only identity probes and automatic stage-2 retention. Raw schema/descriptor remain 0.2.0; identity and retained/exchange contracts are 0.1.0. Existing management directories receive records/observations.sqlite3 only when eligible data is first retained. Existing raw reports are not scanned automatically; backfill selected originating-source files with observation_store.py ingest. Preserve raw evidence and human records.

Explicit sudo credentials for the connection account can enable failed identity probes; a login password alone does not. Set recipe variable identity_sudo false to disable, or true for authorized passwordless sudo. Existing collection-only authorizations must be reviewed before enabling privilege changes. Root probes are fixed and read-only. No target identifier file is created. See [identity scope and limitations](result-data.md#sudo-selection-and-authorization).

Single/batch runner summaries now include retention and identity_quality; a retention failure returns 1 even if collection status is success. Raw files include a receipt. Consumers must check collection and retention independently. Copies of the retained database preserve source UUID and must not seed independent installations. Structured JSON export/combine, not raw re-ingestion or database file merging, is the sharing path.

Host identity_key, label and description are now supported. An explicit identity_key takes precedence and is shared across Feasts as user-assigned identity; change it after OS reinstall/replacement and coordinate its namespace. label/description are captured human text, never identity keys, and are preserved through retention/exchange. See [the canonical host configuration](hosts-yaml.md#explicit-host-identity-and-human-readable-metadata) and [identity/metadata rules](result-data.md#explicit-identity-and-display-metadata). MAC is not an automatic key.

## Inventory 0.3.0 access and result extension

Inventory now tests selected login/root access before the whole batch, attempts sudo by default and collects under the verified root actor. The current two-candidate selection is described in the dated migration section above; sudo false disables only that account's sudo, not another account's root route. Account sudo accepts only booleans: false disables, true/omission enables. Quoted "false"/"true", null and numeric values are rejected; change old sudo: "false" entries to sudo: false explicitly. Canonical sudo-password selects by presence; null/empty are empty passwords and "false" selects account password. Legacy explicit sudo vars follow the same presence migration; no alternate-credential retry. Test-host now permits enabled passwordless sudo when no password is selected; inventory --dryrun uses the bounded inventory account selection without platform collection; check-access also tests independent su and enabled sudo for declared non-login users without platform collection. Review existing authorization before executing the changed defaults.

Six-section inventory-values 0.1.0 is an additive raw/retained/exchange extension; old seven-field results remain readable and unchanged. Update strict validators before reading new extension fields. New report-summary 0.1.1 displays values/scope. Recipe changes invalidate pinned jobs; review and save new definitions without automatic scheduling. No private settings, historical records or environments are rewritten. See [the complete access, CSV and migration guide](inventory-access.md).

## Inventory raw filenames with UTC start seconds

New inventory results use `YYYYMMDDTHHMMSSZ-inventory-system-UUID.json`, derived from started_at in UTC with seconds only. Prior unprefixed names remain untouched and readable. External consumers that glob only inventory-system-*.json must accept the new prefix or use the built-in result query interfaces; JSON contracts and timestamp precision are unchanged. Filename sorting groups new runs by start second; UUID ties and mixed historical names are not strict chronological ordering.

## Terminal summary presentation

Supported CLI summaries now use tabulate only when stdout is a TTY; use --json explicitly for machine consumption, including under PTYs. Existing non-TTY JSON/text output is preserved, raw export commands stay structured, and Textual interfaces keep their pipe-based child behavior. Check-access retains its existing default table. New profiles/check JSON reports identify report_version 0.1.0. Display flags are not saved-job input fields, do not widen authorization and do not change data schemas, exit codes or retained records. See [the complete command/flag matrix](cli.md#terminal-tables-and-json).

Icon defaults live in optional entry hosts.yaml `default.icon.user/host` and per-group `groups.<name>.icon.user/host`. Named-account defaults in `default.users.<account>.icon` precede group user defaults; explicit host-account icons still win. Otherwise resolve host/user separately using the first defined value in host group order, then the global default. Group icon defaults now live at top-level groups.<name>.icon; named-user defaults remain default.users.<account>.icon. See the group-catalog migration below. Older default.icon.groups/users and singular default.icon.group are unsupported; host membership remains group. Flat default-user-icon/default-host-icon/default-group-icon keys are unsupported; use the nested structure. Existing configurations retain 🍎 for hosts and now show 👤 for account labels. Explicit `users.<account>.icon` overrides the user default; see [precedence and validation](hosts-yaml.md#global-and-account-icons). Optional default.users.<account>.email is readable metadata only, with no inheritance or notification behavior. Operational JSON identifiers remain unchanged; effective configuration dumps gain account icon fields.

## Explicit SSH authentication sources

SSH connection.allow_agent and connection.look_for_keys now each default to false.
There is no compatibility fallback and no password-dependent default. Set
allow_agent: true for agent-based login or look_for_keys: true for default local
key discovery, independently on every affected host or inline via hop. Referenced
jump hosts use their own settings. Explicit identity_file, resolved SSH config
IdentityFile and configured login passwords remain available with both flags false.
Do not rewrite private settings automatically; inspect the intended credential source.

The two flags accept only YAML Booleans, including with ssh_config_alias. They are
invalid on local connections and via.host reference objects. YAML controls the flags
after SSH config resolution. Missing all sources now fails during planning, before
any session/connection in that host's chain, with missing_authentication_source.
Static check validates fields but cannot prove resolved credentials or connectivity.
Run check after editing; connect only with the user's existing authorization.
See [complete rules and synthetic examples](hosts-yaml.md#ssh-authentication-sources).

## Group catalog and bulk host definitions

Move default.groups.<id>.icon to top-level groups.<id>.icon. The old location now
fails with an explicit migration hint, even if empty or accompanied by new groups;
there is no fallback or automatic YAML rewrite. Keep default.icon and default.users
at their current locations in entry hosts.yaml. Groups may now be declared in entry
or included YAML, but each explicit group ID must have exactly one definition.

Groups accept optional label (default ID), description (default empty string), icon
and hosts. To collect many host definitions, move each complete host mapping under
groups.<id>.hosts and remove its old definition. Its enclosing group is prepended to
its group memberships and duplicates removed; review ordering because the first
group controls primary-group presentation and per-field icon precedence. Host IDs,
connections, credentials and authorization do not change just because of nesting.
Relative recipes still resolve from the actual declaring YAML file; if a move changes
that file, review relative paths. Repeat host IDs anywhere are errors, not merged.

Per-host group remains singular; host-groups is not an alias. CLI selection always
uses group IDs, never labels. Effective dump groups now returns metadata/defaults
and member ID lists; dump hosts is the flattened host map. Consumers needing original
nested declarations must read their source files, not treat the catalog as source YAML.
Core callers can use profile.hosts.groups(); profile.inspect and the TUI include the
same catalog. Run check locally after migration; no connection is required or implied.
See [the canonical rules and example](hosts-yaml.md#host-groups).

Current inventory records use records/SUMMARY.md and topic-based current-title pages with icons, optional DGMO and nonempty Attention. They omit uncollected fields and redundant columns while keeping zero/false/observed empty lists; full yearly reports preserve detailed samples, units, source times/states and collection metadata. Packages/services are complete and name-sorted. See [current/report rendering](host-vault.md#recipe-retention-and-markdown); omitted values are not verified absence or health. Rebuild updates owned output without collection or retention changes, while unmanaged notes and deliberate manual links remain user-owned.

Current selection groups each host by origin namespace, recipe-source qualifier (the prefix before a colon, or the unqualified source) and stable recipe ID, then selects the whole record with the greatest (observed_at, record_id). Recipe-directory moves within that source therefore keep one current page without aliases or rewriting historical references. Partial results remain partial. Distinct sources, origin namespaces or recipe IDs remain independent; a shared output title still fails publication explicitly rather than silently replacing another dataset. All historical reports remain available.

Vault Contents links use Obsidian-native heading fragments: `[System](#System)` and `[Collection metadata](#Collection%20metadata)`. Heading case is preserved and spaces/non-ASCII text are URL-encoded; arbitrary HTML anchor IDs are not used. Repeated headings are given unique readable titles (for example Services details) so each link reaches one section. In Obsidian Reading view, click a Contents link; in Live Preview, use the normal follow-link gesture (Cmd-click on macOS or Ctrl-click on Windows/Linux). Other Markdown readers can use different heading-fragment conventions; this is not a universal reader-compatibility guarantee. Rebuild regenerates current and historical observation pages plus the records index from retention, without recollection. See [Obsidian internal links](https://obsidian.md/help/links).

Generated host navigation now targets host/SUMMARY.md; records/SUMMARY.md remains the current-record index, while existing unmanaged README notes stay unchanged. Rebuild updates owned navigation only; users update any manual links themselves. Observation-run reads add optional selection/execution metadata for newly recorded invocations. Old selectors and command outcomes were not saved and display Not recorded; rebuild does not guess or backfill them. Completed collection snapshots remain unchanged. See [execution evidence](observation-runs.md#selection-and-command-outcome).

New inventory property collections preserve bounded original stdout/stderr in raw and retained probes by default, with closed code disclosures on current Vault records. No hosts.yaml change is required. Existing records remain readable; missing historical streams stay Not recorded, and rebuild cannot reconstruct them. Collector/normalizer/schema fingerprints change; review saved invocation fingerprints before rerunning, and follow the ordinary replay digest checks rather than editing old raw provenance. No user data is rewritten to add output. See [stream evidence](inventory-jobs.md#source-times-histories-and-latest-views).

Focused saved-host diagnosis is available through observation result RESULT_ID; --detail/--raw retain complete evidence. The former recipes results host forms move as described below. Full non-Linux inventory no longer fails conversion solely because unsupported field probes lacked source timestamps. New collections retain those unsupported-state determination times; existing failed results cannot recover lost intermediate evidence by rebuilding. No historical data is edited or automatic collection performed.

The new top-level observation CLI provides compact batch views; inventory runs list/show and complete run contracts remain unchanged. New general recipe batch raw results now persist observation_run_id, and results index JSON exposes this nullable field. Missing old/raw associations are not backfilled; UUID prefixes and Result IDs are display selectors, so preserve full IDs for durable references. No user data is rewritten by these queries.

## Host results move to observation

Host raw result lookup moves from recipes results to `observation result` without aliases. Replace recipes results list with observation result, detail [ID] with observation result [ID] --detail, show ID with observation result ID --raw, and diagnose ID with observation result ID. Keep --host/--recipe-id/--status on the new host index; selected diagnosis supports --limit and --json. Recipes results now reads offline reports only and rejects host IDs/--host. Existing artifacts remain under recipes artifact. Update operator scripts and saved commands; no data move, re-collection or historical rewrite is required, and Result IDs are unchanged. See [complete modes and validation](cli.md#host-result-history-and-modes).

_Last modified: 2026-10-21 12:30:58_
