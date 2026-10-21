# Ops command-line reference

## Revisit an observation batch

An Observation ID identifies one explicit execution batch over selected hosts; a Result ID identifies one host's saved raw result. Use the same profile/root as the original execution:

```sh
python -B tools/opsfeast.py observation --profile main
python -B tools/opsfeast.py observation latest --profile main
python -B tools/opsfeast.py observation --status failed --profile main
python -B tools/opsfeast.py observation latest --status failed partial --profile main
python -B tools/opsfeast.py observation OBSERVATION_ID --profile main --json
```

No positional ID and no --status lists batches newest first. A full Observation UUID, unique hexadecimal UUID prefix of at least eight characters, or latest selects a batch. The list displays collision-aware UUID prefixes; they are independent of Result ID digests. --status always filters saved host collection states: pending, success, partial, failed or skipped. Values form a union and repeated --status is supported. With --status and no ID, the ID is implicitly latest. It does not list failed batches or search backwards for a matching host.

latest means the most recently started batch in the selected profile, including scheduled, other-recipe and running batches. Equal start times use UUID ordering. Always check the displayed full Observation ID, start time, recipe and original selectors; use a fixed ID when investigating an earlier batch. Original selectors/outcomes absent from old records remain Not recorded.

A selected batch displays whole-batch state counts, shown/total hosts, execution outcome separately from collection status, and a compact Host/Status/Reason/Result ID table. Filters do not change batch membership or counts. Retention/publication failures remain separate warnings, even when a host-state filter hides the associated row; command failure does not imply every host has collection status failed. Empty filters display No hosts match and return 0.

Result IDs link only when a unique saved raw result explicitly names this observation_run_id and host. Missing/deleted raw files, unavailable old associations or multiple matching raw files show a dash; batch failure evidence remains visible. No timestamp or latest-host matching substitutes another execution. Invalid raw files are reported as excluded links. Follow a displayed Result ID with observation result RESULT_ID; observation result without an ID reads per-host result history, not a batch index. New general recipe batch outputs persist observation_run_id as inventory already does; old raw files are not modified. Index JSON adds this nullable metadata field.

These are read-only views: no connections, initialization, consumer dispatch or files are changed. Success returns 0 independently of saved batch failure; missing/ambiguous IDs, no latest batch or storage/configuration errors return 1; syntax/invalid status options return 2. An empty batch index is a successful read. Terminal stdout displays compact text/tables; --json and non-TTY stdout return [observation view 0.1.0](../schemas/observation-view.schema.json). List contains observations summaries; selected views contain observation metadata, statuses, hosts and warnings. Complete immutable run data remains available through inventory runs list/show and Core/report retention.runs()/run().

Checkout content authors can reuse observation_cli.query(root, identifier=None, *, statuses=None) and render(view), Python 3.11+ helpers over the existing retention/read-result services. The JSON view has separate schema/versioning and does not rewrite or filter the underlying observation-run contract. Public tests cover latest/running selection, exact membership, status unions, unknown metadata, missing/ambiguous raw links, UUID-prefix collisions, control escaping and byte-for-byte read-only behavior. No new live-host execution or automatic recovery is implied.

## Inventory property queries and periodic jobs

Recipe 0.4.0 supplies `opsfeast.py inventory describe`, `query`, `run`, `configure`, `status`, `dispatch`, `latest`, `runs list/show` and `cron`. Read the [canonical inventory job guide](inventory-jobs.md) for exact selectors, examples, settings/override precedence, effects, outputs, source times, YANG mapping, platform limits and exit codes. `query` defaults to no storage; `--save` records an immediate comparison through retention/consumers without changing the schedule. `dispatch --dry-run` performs no host operations; ordinary dispatch requires inventory.yaml opt-in plus enabled host/source/resolved recipe policy, with no retries. `cron install` manages a marked current-user minute entry and enables no hosts. This scheduler differs from retention-consumer dispatch and saved invocation jobs. New job observations use a separate contract; old history is not converted or deleted.


## Read what a command does

Top-level `python -B tools/opsfeast.py -h` groups commands by task:

| Help section | Commands |
| --- | --- |
| Profiles and setup | init, profiles, use, attach, detach, instance |
| Hosts and access (hosts.yaml) | check, dump, test-connection, host-init, test-host, test-su, test-sudo, check-access |
| Recipes and reports | inspect-recipe, recipes |
| Retained data and consumers | observation, retention, consumers |
| Vault content | vault |

After cloning and preparing dependencies, create a Feast with init or register an existing one with attach, then edit its hosts.yaml. These sections guide discovery; they are not mandatory sequential stages or additional subcommand levels. Revisit access diagnostics after changing hosts or investigating a recipe failure. Reports, consumers and Vault can reuse saved data without collecting again. Command paths, flags and parsing remain unchanged; for example, continue using recipes run and consumers dispatch directly.

Every main command and recipe subcommand now includes its purpose in its own --help screen, before the argument list. Parent help also summarizes its child commands. Delegated usage includes the complete prefix, such as opsfeast.py recipes jobs run. Existing argument syntax, execution behavior and result formats are unchanged.

```sh
python -B tools/opsfeast.py recipes --help
python -B tools/opsfeast.py recipes run --help
python -B tools/opsfeast.py recipes jobs save --help
python -B tools/opsfeast.py consumers dispatch --help
python -B tools/opsfeast.py recipes run --help
```

recipes run explains host operations versus offline reports, raw result saving, declared retention/consumer updates and examples of both recipe kinds. jobs save describes writing a definition without execution or scheduling; jobs run describes content verification followed by actual execution. artifact describes verified JSON metadata and an absolute file path, not streaming artifact bytes. Profile/configuration/diagnostic commands distinguish registry/local writes from connections. Retention, consumers and Vault include action overviews separating reads, writes, replay, publication and dispatch. The standalone observation_store subcommands explain exchange input/output and write behavior.

--help takes priority over --tui and exits successfully before profile resolution, target selection, connections or operation writes, even when required execution arguments are omitted. It can be read from an empty working directory. Help is an introduction to a command; continue with this reference and the selected recipe/consumer documentation for complete contracts, evidence and authorization scope.

Bundled recipes now use [classified paths](recipe-taxonomy.md): system/network/check/port, system/account/check/identity, system/inventory/overview, feast/report/execution-summary and feast/report/retention-summary. Recipe selectors accept complete paths of variable depth; old bundle paths have no aliases. Update configuration/scripts/jobs/exact consumer subscriptions deliberately. Data query --recipe filters can still select historical reference strings without resolving an executable recipe.

Vault host pages live under hosts/PRIMARY_GROUP/HOST/, using first membership or _ungrouped. Full rebuild updates host pages and group links after membership changes; human notes remain at their old locations for deliberate relocation. Observation pages show the host first and one final metadata section. Vault page names use consumer titles plus source/record discriminators; historical observation pages use compact UTC seconds plus label (YYYYMMDDHHMMSS-title.md), without UUIDs. Rebuild replaces old owned paths and generated links; manual links need updates. Optional collection_evidence supplies the actual actor and query commands/reasons to new pages; it is visible through retention show/export, while older records explicitly lack it. Rebuild never recollects missing inventory. See [collection evidence](retention.md#local-collection-evidence).

Vault observation readability is owned by the [bundled content renderer](host-vault.md#recipe-retention-and-markdown). Use vault rebuild --profile NAME --json within authorized publication scope to refresh existing yearly/latest Markdown into tables with readable inventory and source details. It performs no collection or retention rewrite; owned outputs are replaced and human notes are preserved.

## Retention consumer discovery and delivery

```sh
python -B tools/opsfeast.py consumers list --recipe system/inventory/overview --profile main --json
python -B tools/opsfeast.py consumers show vault --profile main --json
python -B tools/opsfeast.py consumers inspect --profile main --json
python -B tools/opsfeast.py consumers dispatch vault --profile main --json
```

`list`/`show ID` perform static discovery; `--recipe REFERENCE` resolves a catalog recipe and filters exact reference plus declared contract/version. `recipes show` includes the same relation. `inspect [ID]` reads event/delivery history; `dispatch [ID]` runs enabled reviewed consumers for pending/running/failed pairs. All accept mutually exclusive `--root PATH`/`--profile NAME` and explicit `--json`, and always return JSON. Exit 0 means successful command, 1 validation/storage/delivery failure, 2 parsing error. inspect success does not imply successful individual deliveries. IDs precede options; show requires ID, and only list/show accept --recipe. Dispatch can execute registered local code and update its reviewed outputs, while list/show/inspect do not execute it.

See [consumer contract 0.1.0](retention-consumers.md) for placement, exact descriptor/registration syntax, supported Python/data versions, backlog/retry, at-least-once output requirements and failure limits. The existing `content_update` receipt now aggregates per-consumer attempts; consumers reading its old single-Vault fields must update. No pending match produces success with an empty attempt list. `vault.auto_refresh: false` only disables the Vault consumer. Prior annual records without events are not automatically backfilled; use explicit application rebuilds for historical output.

## Retention and vault commands

Use [retention contracts and examples](retention.md) before selecting data, and [offline replay](retention-replay.md) for recovery. Recipe discovery/show/inspect exposes `retention` declarations and retrieval instructions. Read commands do not create storage or connect.

| Command | Behavior |
| --- | --- |
| `retention list` / `retention export` | Complete validated envelopes; repeated --host, exact source-qualified --recipe, inclusive --since/--until, --status and --kind filters |
| `retention show RECORD_ID` | One full retained record; unknown ID fails |
| `retention inspect` | Settings, data directory and authoritative records |
| `retention ingest FILE...` / `retention ingest --all` | Offline raw replay; --dry-run and explicit reviewed --recipe-dir supported |
| `retention delete-observation ID` | Explicit read-only deletion; --dry-run supported; write/unknown and linked evidence protected |
| `retention rebuild` | Recreate cumulative/recent SQLite projections from annual archives |
| `vault rebuild` | Recreate bundled Markdown content and group links without writing SQLite or executing recipes |
| `vault groups` / `vault inspect` | Refresh group links / read content settings and location |

All accept mutually exclusive `--root PROFILE_ROOT` / `--profile NAME` and `--json`; output is JSON in terminals and pipes. Files/IDs precede options. List/export sort oldest first by UTC source time then record ID; empty selections succeed. Export writes stdout only and authorizes no transmission. Exit 0 means success, 1 data/content/storage failure, 2 parsing error.

`init NAME [--namespace VALUE] --json` establishes independent `retention/` and `vault/` directories. Namespace defaults to saved value or first profile name and cannot be changed through reinit. `vault.auto_refresh` in feast.yaml defaults to true. Set Boolean false to save data without automatic Vault publication; other consumers remain independently enabled; explicit vault rebuild remains available. Saved results and execution summaries distinguish recipe status, `retention` and `content_update`. Consumer failure preserves collected data/status and returns nonzero; retry `consumers dispatch [ID]`. Explicit `vault rebuild` regenerates Vault content without acknowledging events. Receipts do not affect raw identity/digest. Old SQLite-in-vault layouts and template snapshots are incompatible; see [required user action](retention.md#development-incompatibility). `vault migrate/ingest/delete-observation` have been removed; use init or the retention commands above.

Inventory discovery exposes the recipe-owned structured retention declaration, schema path/digest and registered normalizer source/digest. Current inventory raw snapshots bind those digests; old inventory raw without them requires `retention ingest FILE --recipe-dir REVIEWED_RECIPE --dry-run --profile NAME --json` before authorized actual replay. Candidate collection/normalizer code is never imported. See [inventory retention 0.1.0](../recipes/system/inventory/overview/README.md#recipe-owned-retention-contract).

For task-to-tool discovery and Python composition, consult [the existing capability map](agent-capabilities.md). Prefer suitable implemented interfaces before writing replacement configuration, execution, storage or export code.

OpsFeast provides two command-line entrypoints:

- **`tools/opsfeast.py` prepares and diagnoses the host environment.** It provides recipes list/show/run, raw results/artifacts, offline reports, bundle candidates and saved jobs; inspects recipe metadata and platform coverage; manages profiles, validates host configuration, discovers platform facts, and tests configured login/su/sudo capabilities.
- **`opsfeast.py recipes run` executes inventory jobs and compatible Python recipes.** Inventory uses its single job collector. General recipes use one execute entrypoint. Both accept typed invocation inputs and save versioned raw results; inventory and declared host-values recipes have structured retention. See [the general contract](recipe-execution.md).

Platform-specific entrypoints share one result contract. Administrators do not need to maintain a separate recipe selection for every OS. Routine probing, dispatch and collection run as Python code without an LLM in the execution path. Agents can use this reference to choose the right command and explain its actual outcome.

Host configuration loading (including check/dump) validates icon as exactly one Unicode Symbol code point. Effective host/account dumps include resolved icons from entry hosts.yaml defaults (default.icon.host/user, per-group groups.<name>.icon.host/user, and named-account default.users.<account>.icon; built-ins 🍎/👤); other selected values remain unmasked, including credentials. See [host icons](hosts-yaml.md#host-icon).

## Terminal tables and JSON

Human console output uses the shared `tools/console_output.py` presentation layer. When `sys.stdout.isatty()` is true, supported summaries use tabulate rounded-outline tables. An explicit `--json` takes priority. When stdout is piped/redirected, each command preserves its previous JSON or text format; this is not a blanket conversion of text commands into JSON. Stdin need not be a terminal for table rendering; interactive profile choices still require terminal stdin and stdout.

| Command family | Terminal view | Explicit machine output |
| --- | --- | --- |
| profiles / interactive use selection | Profile/root/status/default table; numbered selection remains available | profiles --json; named use retains its confirmation text |
| check / init | Host icons, selected-recipe counts, skips and notes; init also retains creation/registration messages | check --json; init retains existing text output |
| instance inspect/init/set/renew/relocate | Field/value tables with the same report values | --json |
| inspect-recipe | Recipe/platform/static-status table; requested platform constraints/errors remain visible | --json; --details retains the full text view |
| test-connection, host-init, test-host, test-su, test-sudo | Status/host/test/user/reason tables; facts and cache/source times when available | --json |
| recipes run | Host, collection identity, result and result id; use check-access for separate diagnostic tables | --json |
| recipes list/show/results list | Catalog/source, metadata or result-index tables | --json; --html retains its explicit export behavior |
| recipes jobs list/show/save/run | Job list/details, save report or execution summary | --json; this presentation flag is not persisted in job invocation data |
| check_environment.py / recipe_identity.py defaults / skill_bundle.py check or download | Field/value readiness, author or bundle reports | --json (place after the subcommand where applicable) |

Exceptions preserve data interfaces: dump, observation result --raw, recipes results show, artifact, pack/unpack and observation-store JSON/CSV/export/validation/combination remain structured even on a terminal. Check-access preserves its existing default table even for non-TTY stdout; use --json for its full report. Textual Home/workbench/--tui keep their DataTable interfaces and pipe-based child streams. Execution TUI rows display separate Retention and Content cells while preserving the recipe status and process exit code. Help, prompts, simple confirmations, stderr progress/errors/debug and raw saved files are not converted into tables.

Human `observation result` replaces identity quality with the actual collection user (unknown when unsupported or unverified). TTY lists omit the long identity-warnings column; redirected list text and list HTML retain warnings. Identity quality and warnings remain available through --json and --detail/--raw without changing saved evidence. See [the collection-user rules](#saved-result-collection-user).

Tables preserve failure/partial/skipped/unknown states; no missing evidence becomes PASS. Connection, prerequisite su, actor sudo, restoration and cleanup remain distinct where present. A successful collection with failed retention still returns nonzero. Host and diagnostic/access account labels include resolved icons (built-ins 🍎/👤; see [global precedence](hosts-yaml.md#global-and-account-icons)); historical result views use the default when current configuration is unavailable, without rewriting IDs/data. Unicode widths, leading-zero identifiers and escaped terminal control characters use the same renderer settings as check-access. Terminal tables wrap headers and values to fit the current terminal cell width, preserving complete values instead of truncating them. Existing JSON/report/SQLite schemas, observation times, execution scope and exit codes are unchanged.

Width is read on each render using the standard terminal-size lookup (including COLUMNS when set, with an 80-column fallback when unavailable). Naturally short columns keep their space; wide columns share the remaining width, including border/header padding. Wrapping measures Unicode display cells, including Chinese and emoji, and can split long identifiers/paths. Control characters remain escaped. If columns cannot each retain a readable width, the same rows switch to labeled Record 1, Record 2, ... blocks with wrapped header/value pairs. Empty tables still display their headings. This applies to shared terminal tables, including recipes show and check-access. An indivisible two-cell character cannot fit a one-column terminal; rendering uses a minimum of two cells.

For example, on terminal stdout, COLUMNS=80 python -B tools/opsfeast.py recipes show system/inventory/overview --checkout-only previews an 80-column metadata table without a profile or host execution. Add --json for the complete structured representation. Wrapping changes only presentation: redirected tables retain their previous layout, other non-TTY outputs retain their command-specific format, and --json/raw files/HTML/TUI formats are unchanged. Free-standing prose such as diagnostic count footers is not governed by table wrapping.

Terminal display requires the declared tabulate[widechars] dependency. Operational commands check it before execution and never install packages automatically; --json bypasses table rendering. The environment checker is a deliberate exception: if display dependencies are unavailable it emits its JSON readiness report so missing packages remain diagnosable. Use the actual selected interpreter, not another environment's installed packages.

The new profiles/check JSON views identify `report_version: "0.1.0"`. Profiles contains a profiles list with name/root/status/default (a Boolean); an empty registry yields an empty list. These are basic registration states, not full configuration/connectivity checks. Check success contains status, yaml_files count, hosts (plain host ID, selected_recipes count and skipped references/reasons), and notes; errors retain stderr/nonzero behavior without a fabricated success JSON. Neither view emits credentials or rewrites configuration.

For agents/pipelines, explicitly select --json where supported, especially when running under a PTY. Presentation is not an execution authorization. The checkout-level helpers `human_output(json_output=False)`, `prepare(json_output=False)`, `table(headers, rows)` and `print_report(value, json_output=..., kind=...)` reuse the same policy; they are not a versioned Core API. table(headers, rows) escapes controls and formats human timestamps, then fits terminal width automatically; retain the original structured inputs. render_table(headers, rows) is the checkout adapter for already escaped display strings, used by check-access to avoid escaping twice. Both retain unconstrained tabulate layout on non-TTY stdout. Do not replace raw-data export interfaces with display tables.

## Installation identity and read-only inspection

`python -B tools/opsfeast.py instance ACTION [--installation DIRECTORY] [--name NAME] [--description TEXT]` follows the terminal table/JSON policy above. ACTION is inspect (read-only instance/configuration/dependency snapshot), init (create/preserve identity and optionally set name/description), set (update existing metadata), renew (new UUID for this copy), or relocate (preserve identity after moving the original). Name/description apply only to init/set. Default installation is this checkout; it is not a management root. Exit 0 is success, 1 is partial inspection/configuration/filesystem failure; syntax errors use 2. The command does not connect or execute recipes. See [identity/copy semantics and API](core-api.md).

Normal management `init` also initializes installation identity after successful validation/registration; repeated init preserves it. Profile selection does not change instance identity. Missing UUID inspection uses a nil placeholder and writes nothing. New python-recipe 0.1.0 recipes use the same opsfeast.py recipes run/recipes run options as python-session; no extra execution flag is required.

## Inventory access and historical CSV

Current inventory uses [job queries and schedules](inventory-jobs.md); all inventory execution follows the same bounded actor policy. Use check-access for separate authorized account diagnostics. Job data is queried/exported through retention. Legacy observation_store exchange/CSV applies only to historical snapshot records and does not export the new job dataset.

## Conventions and prerequisites

Run examples from the repository checkout. `python` means the interpreter selected for your environment; `-B` avoids writing Python bytecode. Replace synthetic host IDs, account names and `/srv/feasts/main` with your settings. Host/configuration commands read `hosts.yaml` from the chosen management environment; a host ID is a configuration key, not necessarily its hostname.

| Operation | Controller requirements |
| --- | --- |
| Profiles, init, attach, detach, use, check, dump, inspect-recipe, recipes metadata/results/packages/jobs and offline reports | Python 3.11+ and PyYAML; no SSHScript Session |
| Standalone test-connection | Python 3.11+, PyYAML and the supported SSHScript command contract (documented minimum 4.0.1) |
| Host-init, test-host, test-su, test-sudo, test-connection --host-init, opsfeast.py recipes run | Python 3.11+, PyYAML and matching SSHScript import/distribution **5.0.0** |

Both environment-check scopes require PyYAML 6.0.3 and tabulate[widechars] 0.10.0 (including wcwidth); the full check additionally requires SSHScript 5.0.0:

```sh
python -B tools/check_environment.py
python -B tools/check_environment.py --scope init
python -B tools/opsfeast.py --help
python -B tools/opsfeast.py recipes run --help
```

Environment checks only report readiness. Tools do not automatically create Python environments, install dependencies, upgrade SSHScript or download skills. See [getting started](getting-started.md) for setup and [host configuration](hosts-yaml.md) for connection/key/jump-host rules.

The former tools/ops.py entrypoint is removed; use tools/opsfeast.py. New checkouts use .opsfeast.yaml and feasts/; an existing .my-ops.yaml remains active. Named init reuses registered roots. New feast.yaml definitions use kind: opsfeast; legacy my-ops.yaml definitions use kind: sshscript-ops. Both naming generations together are a conflict. See [rename compatibility and migration](migration.md).

## Manual environment use

From the confirmed OpsFeast clone, an existing checkout .venv can be activated in Bash or Zsh:

```sh
cd "/absolute/path/to/opsfeast"
source tools/activate.sh
python -B tools/opsfeast.py check --profile main
```

Replace the path/profile with yours. The helper exports PYTHONDONTWRITEBYTECODE=1 after activation, finds .venv relative to its own file and preserves the current directory. It requires the existing .venv/bin/activate; absence returns nonzero without installation or initialization. Direct execution is rejected; source is required to modify your current shell. The export lasts for that shell; standard deactivate restores the Python environment but does not unset this export. It prevents subsequent Python bytecode writes, not every kind of generated file or removal of existing caches.

For other shells or user-selected environments, call the interpreter directly. Agents should use the selected interpreter with -B; activation is optional and need not persist between tool calls. See [getting started](getting-started.md) for authorized creation/reuse and [first-host examples](first-host.md) for next commands.

## Choose the management environment

For most commands, omit the location to use the selected default profile in the checkout's `.opsfeast.yaml`, or pass `--profile NAME` for one invocation. This does not change the default. An explicit management root and `--profile` cannot be combined for execution/configuration commands. Missing or invalid profiles fail without searching other environments.

The CLI has two forms for an explicit root:

| Entrypoint/subcommands | Root argument |
| --- | --- |
| opsfeast.py check, dump, test-connection | Optional positional `ROOT` |
| opsfeast.py host-init, test-host, test-su, test-sudo | Optional `--root ROOT` |
| opsfeast.py recipes run | `--root ROOT` |
| opsfeast.py init | Optional name or path; `--profile` names the registration |
| opsfeast.py attach | Required existing directory; `--profile` names the registration |

Explicit relative directory paths use the current shell directory; registered relative locations use the checkout. `init inventory` is a name under the checkout's `feasts/`; `init ./inventory` is a path under the shell directory. See [profiles](profiles.md) for registration conflicts, legacy directories and locator migration.

## tools/opsfeast.py: command reference

Run `python -B tools/opsfeast.py COMMAND --help` for that command's parser help. Brackets below mean optional arguments; usernames use spaces, not commas.

| Command syntax after tools/opsfeast.py | Purpose and behavior |
| --- | --- |
| `init [NAME_OR_PATH] [--profile NAME] [--namespace VALUE] [--json]` | Create a management scaffold and namespace-enabled vault, validate, then register. Default: feasts/main, namespace main; preserve existing configuration/namespace/history. JSON includes profile, root, namespace and vault_directory. |
| `attach ROOT [--profile NAME]` | Validate/register an existing directory without creating or changing its scaffold. |
| `profiles` | List registrations, basic directory status and selected default. Missing entries remain registered; no registrations is a normal result. |
| `detach NAME` | Remove one registration while preserving its directory/data. Main is protected; removing the current default validates and switches to main in one registry write. |
| `use [NAME]` | Change the default to a registered environment. Omitted NAME opens an interactive selector; noninteractive use requires a name. |
| `check [ROOT] [--profile NAME]` | Validate YAML, duplicate definitions, connections/users/vars, include/jump cycles, recipe selections and path boundaries. Does not connect or validate complete recipe execution contracts. |
| `inspect-recipe [RECIPE] [--platform OS_NAME ...] [--details | --json]` | Read recipe metadata, declared platform coverage, entrypoint/version status and verification evidence. Omitted RECIPE discovers checkout recipes; repeat --platform for desired OS names. No management profile, SSHScript import or connection. |
| `dump SETTING [ROOT] [--profile NAME]` | Print a dot-separated mapping path from loaded configuration as JSON, including merged hosts. This performs loading checks, not a complete check. List indexes are unsupported. |
| `test-connection [HOST] [ROOT] [--all | --group GROUP...] [--root ROOT | --profile NAME]` | Connect to selected hosts and required hops, then independently run hostname and date. See [selection and progress](#select-and-monitor-connection-tests). Does not switch accounts or run recipes. |
| `host-init HOST [--root ROOT] [--profile NAME]` | Connect and freshly discover platform facts, updating saved initialization data on every explicit invocation. |
| `test-host HOST [--root ROOT] [--profile NAME]` | Test login, reuse or initialize facts, then test the configured account capabilities described below. |
| `test-sudo HOST [USER ...] [--run-as TARGET] [--root ROOT] [--profile NAME]` | Independently test each sudo actor; omitted USER means the actual connection identity. Default TARGET: root. |
| `test-su HOST USER ... [--root ROOT] [--profile NAME]` | Independently test connection-user → each target. At least one target is required. |
| `test-su HOST --chain USER ... [--chain USER ...] [--root ROOT] [--profile NAME]` | Test each ordered chain from a fresh connection identity. Repeat --chain for separate chains. |

Profile/configuration commands and inspect-recipe do not connect or execute recipes. Detach never deletes management data or auto-creates/attaches main. Unknown names or an unavailable main fallback fail before writing; see [profile lifecycle](profiles.md#detach-a-registration). Init/attach preserve an existing default; the first successful registration becomes the default. Use changes only the selected profile. Profiles status is a basic location/definition/entry-file check, not full YAML/recipe or host verification. In interactive registration, a conflicting name may prompt for another name; noninteractive conflicts fail without waiting. Init failure may leave newly created scaffold files for correction, but does not register a failed setup.

### Inspect recipes and platform gaps

```sh
# Discover every recipe.yaml under this checkout's recipes directory.
python -B tools/opsfeast.py inspect-recipe

# Inspect a recipe and compare desired OS names against its declarations.
python -B tools/opsfeast.py inspect-recipe system/inventory/overview --platform linux --platform openbsd

# Read full details, or obtain the complete descriptor/report for an agent.
python -B tools/opsfeast.py inspect-recipe system/inventory/overview --details
python -B tools/opsfeast.py inspect-recipe recipes/system/inventory/overview --json
python -B tools/opsfeast.py inspect-recipe ./my-custom-recipe --json
```

Short paths such as `system/inventory/overview` or `recipes/system/inventory/overview` resolve under this checkout's recipes directory. Absolute paths and explicit `./`, `../` or `~` paths use the shell directory/home, **not a management root**. A supplied path selects one recipe directory containing recipe.yaml; omit it for recursive checkout discovery. This command does not use hosts.yaml, the profile registry, host-init caches or SSHScript. Python 3.11+ and PyYAML suffice.

Default human output is a short recipe summary: identity/version, purpose and implemented/declared-tested/planned-only platforms. With --platform, it focuses on the requested OS names: implemented, planned but missing, or not declared supported; relevant entrypoint health, additional match conditions and recorded verification are shown only for those OS names. Inspection errors and unsupported runner IDs remain visible in either view. Use --details for full human-readable metadata, paths, all implementations, dependencies, privileges, side effects, inputs, output contract and verification. --details and --json are mutually exclusive; --details shows the full report even when --platform is supplied. JSON includes the complete `descriptor`, per-entrypoint static checks, `coverage`, `runner_contract`, errors and inspection report version 0.1.0. No report file is saved.

Coverage compares declarations: `not_declared_implemented` lists requested OS names absent from platforms.implemented; `planned_not_implemented` lists pending declared platforms; `implemented_not_declared_tested` lists implementations without a tested-platform declaration. For the current inventory recipe, requesting openbsd exposes that missing declaration, while Linux/FreeBSD remain implemented but lack local/SSH execution evidence. Requested values are exact os_name labels such as linux, freebsd or macos; repeat the option, rather than using commas. A platform gap is informational and does not change the exit code.

Inspection reads YAML and parses Python VERSION literals without importing or executing entrypoints. Missing files, invalid syntax, version mismatches and escaping descriptor/entrypoint symlinks are reported. For inventory-system, it also uses the current runner's descriptor validator; Python-session descriptors are statically validated (entrypoint path, literal VERSION, execute signature and input definitions) and report valid-python-session or invalid-python-session. Other contracts remain unsupported-recipe-id; there is no arbitrary backend loader. One bad discovered recipe does not hide the others; any inspection error returns 1, and a completed inspection returns 0. Command/path errors use stderr; completed reports use stdout, including failed per-recipe reports in JSON mode.

These are declared capabilities and static checks. They do not establish publisher authenticity, installed dependencies, actual host applicability, platform detection or successful execution. Match conditions may restrict OS/distribution/version/architecture even when a platform name is listed. Read recorded verification and review code before authorized execution.


### Select and monitor connection tests

`test-connection [HOST] [ROOT] [--root ROOT | --profile NAME] [--group GROUP...] [--all] [--timeout SECONDS] [--host-init] [--json] [-v | -q] [--debug] [--traceback]`

Choose a positional host, one or more groups, or their union. Repeat --group to combine groups; duplicate targets run once. --all selects every enabled host and cannot be combined with HOST or --group. Group names refer to hosts.yaml `group` membership. Unknown hosts/groups and invalid connection configuration fail before any connection. Disabled group/all members appear in excluded_hosts with host_disabled; an explicitly selected disabled host produces a skipped result and nonzero exit. An empty selection fails before connection. Use --root for batch management-directory selection; the legacy positional HOST ROOT form remains supported. Do not supply both positional ROOT and --root.

```sh
python -B tools/opsfeast.py test-connection host-01 --profile inventory
python -B tools/opsfeast.py test-connection --group web database --profile inventory
python -B tools/opsfeast.py test-connection --all --root /srv/feasts/main
python -B tools/opsfeast.py test-connection --all --profile inventory --json --quiet
```

Tests run sequentially with independent Sessions, continuing after a host connection, command or cleanup failure. Each target still runs only hostname/date; no su/sudo or inventory is performed. --host-init explicitly refreshes facts for each connected target using the existing separate connection. Timeout applies per stage, not to the complete batch. Selecting all/groups authorizes the necessary configured jump paths as well as selected targets.

When sys.stdout.isatty() is true, stderr displays flushed host start/completion counts and hop/command progress by default; stdout displays each host's status/host/test/user/reason table and command results as it finishes, then batch totals and exclusions. --quiet suppresses progress; --verbose forces it for redirected stdout. --debug implies verbose and cannot be combined with --quiet; --verbose and --quiet are mutually exclusive. --json overrides terminal tables without disabling terminal progress; combine --json --quiet for silent machine consumption.

Non-TTY stdout remains JSON. A positional-host-only invocation retains the existing single-host JSON shape. --all or --group returns batch report_version 0.1.0 with status, hosts (the existing per-host reports), excluded_hosts (host/reason_code), and counts (total/passed/failed/skipped). Counts cover attempted/explicitly skipped targets; excluded members are separate. Overall status is success only when every selected test succeeds; exit 0 means success, 1 means a failed/skipped selected test or selection/configuration failure. Argument syntax errors use exit 2. Retain per-host hops, errors, command results, cleanup_error and optional host_init when interpreting failures. Excluded disabled members do not cause failure when enabled selected hosts all pass. These behaviors have synthetic tests; no new native SSH evidence is implied.

### Connection diagnostics and options

All host-test/init commands accept `--timeout SECONDS`, default 30, a positive finite number. It bounds connection stages/commands and authenticated entry/exit where applicable, **not the complete run**. SSHScript base-shell/capability setup and recovery have separate contract limits.

All host-test/init commands additionally accept:

| Option | Behavior |
| --- | --- |
| `-v`, `--verbose` | Progress on stderr. |
| `--debug` | Safe connection details and, for su/sudo, actor/target and credential-source details on stderr, implying verbose; does not enable SSHScript's raw DEBUG log. |
| `--traceback` | Exception frames without source text, locals or exception messages. |

Only test-connection accepts `--host-init`: also perform a fresh host-init after connecting; currently uses a separate connection.

Test-connection JSON includes host, connected, hops, commands and success. Each hop records its connection result; key_source identifies where identity_file is read. Commands retain stdout/stderr/exitcode or error. Success requires both commands and strict cleanup to succeed; connected alone is insufficient. With --host-init, initialization must also succeed.

```sh
python -B tools/opsfeast.py init inventory
python -B tools/opsfeast.py check --profile inventory
python -B tools/opsfeast.py dump hosts.host-01.connection --profile inventory
python -B tools/opsfeast.py test-connection host-01 --profile inventory --debug
python -B tools/opsfeast.py test-connection host-01 /srv/feasts/main --host-init
```

Dump emits selected values unchanged, including passwords if the selected mapping contains them. Keep real configuration, command output and saved reports in your management environment.

### Host-init: fresh observations and reusable facts

Host-init queries uname for OS/kernel/architecture, maps VMkernel to esxi and records the full vmware -v line for ESXi. Linux distribution information comes from os-release; FreeBSD userland version and macOS product version are separate from kernel release. Missing fields retain their state; sufficient OS evidence can still permit a generic implementation.

```sh
python -B tools/opsfeast.py host-init host-01 --profile inventory
python -B tools/opsfeast.py host-init host-01 --root /srv/feasts/main
```

Facts include os_name, kernel_name, kernel_release, architecture and available OS/distribution names/versions. The JSON includes schema/probe version **0.1.0**, host_id, status, reason_code, observed_at, facts, per-field states, command sources and target_fingerprint. Explicit initialization also returns result_path. The file is atomically replaced at:

```text
<management-root>/observations/host-init/<sha256-of-host-id>.json
```

Test-host and the runner reuse successful facts with the expected schema, matching host/target fingerprint and observation timestamp. Missing, malformed, failed or target-mismatched facts require a new probe. The runner also reprobes once if cached facts cannot select an implementation. Direct host-init and test-connection --host-init always refresh. A failed explicit refresh retains previous_success as historical evidence, but the latest failure prevents cache reuse. Cleanup failure makes fresh initialization fail.

There is no age expiry. Changes to an external SSH config or an OS reinstallation at the same endpoint are not detected by the configuration fingerprint; explicitly refresh after known changes. Cached observations keep their original timestamp and never become a fresh measurement merely by reuse.

### Sudo: actor versus target

```sh
python -B tools/opsfeast.py test-sudo host-01 --profile inventory
python -B tools/opsfeast.py test-sudo host-01 user2 user3 --run-as service-user --profile inventory
```

USER is the account **executing sudo**. TARGET is the identity sudo should enter. Other actors first require verified su entry from the connection account. Results identify whether failure happened at su entry/identity or sudo entry/identity. Independent actors use fresh connections.

Sudo uses [the account presence/control-string policy](inventory-access.md#configure-the-actual-connection-account): canonical sudo-password selects by presence, null/empty select empty passwords, exact "false" selects account password, and account sudo: false disables sudo. Legacy vars credentials apply only when the canonical field is absent. No lower-priority retry occurs. --run-as selects the diagnostic target, default root; inventory always requests root.

To investigate a failed test, add `--debug --traceback`. JSON steps include `password_source` and `password_supplied` when su/sudo credentials are selected; no password value is emitted. A PermissionError during authenticated entry is categorized as `authentication_rejected_or_password_required`: the public SSHScript contract includes explicit rejection, a second password request, or a password request when none was supplied. This category does not identify the exact host-policy cause or prove an incorrect password. Review the failed stage and selected credential source first. Tracebacks contain frames only; exception messages and raw privileged output remain omitted. Progress/debug/traceback output goes to stderr; stdout is JSON with --json or non-TTY output; terminal summaries follow the table policy above.

### Su: independent targets and ordered chains

```sh
python -B tools/opsfeast.py test-su host-01 user2 user3 --profile inventory
python -B tools/opsfeast.py test-su host-01 --chain user2 user3 --chain user3 user2 --profile inventory
```

The first command tests connection-user → user2 and connection-user → user3. The second tests two independent chains:

```text
connection-user → user2 → user3
connection-user → user3 → user2
```

Each --chain group starts a fresh connection. A failed/skipped prerequisite prevents remaining steps in that chain, while other groups continue. Independent lists and chain groups cannot be mixed. The connection account cannot be a target; independent duplicates and adjacent chain duplicates are rejected, while nonadjacent chain repeats are allowed.

Su uses the same selection rule for the target account: `users.<target>.vars.su.password`, host `vars.su.password` only if that target is the actual connection account, then `users.<target>.password`. Test-su excludes the connection account, so its targets use the account override or account password; host su credentials are never borrowed for other targets. Each chain step and the su prerequisite for another sudo actor use this rule. Missing required credentials produce skipped tests; passwordless su is not probed. Identity queries verify effective UID against the requested account. Context exit and strict Session cleanup are checked separately. Bash and id are required by the SSHScript authenticated-console contract. Ops does not prompt interactively for passwords.

Privilege-test JSON includes host, test, status, connection_user when identified, and groups. Each group contains its accounts, chain/independent mode, steps and status. Steps retain from_user, to_user, operation, verified identity or skipped reason/failure stage. Errors omit credential-bearing exception text and raw privileged output.

### Test-host: one configured-host check

```sh
python -B tools/opsfeast.py test-host host-01 --profile inventory
```

Test-host always tests login/hostname/date. It then reuses or initializes facts, tests enabled sudo only for the connection identity, using the selected password or passwordless policy, and independently tests su to other accounts declared in users. It does not enumerate accounts, test chains or execute recipes.

If connection establishment fails, remaining tests are skipped. Host-init failure does not prevent account diagnostics. One account-test failure does not stop other independent groups. Test-host uses separate connections for the diagnostic phases/groups; it is not one atomic remote transaction.

Its JSON contains host, overall status, and tests keyed by test-connection, host-init, test-sudo and test-su. Inspect their individual status, skipped reason, initialization cache/probe source and original observation time. Overall partial means some tests were skipped, rather than all capabilities having been verified.

## tools/opsfeast.py recipes: shared recipe interfaces

The [canonical recipe experience reference](recipe-experience.md) defines catalog/report/artifact/bundle/job versions, JSON fields, source/ID selection, validation, storage, dependencies, outputs, errors and verification. All these commands use the selected interpreter and read/write only within the requested scope; static discovery never executes candidates. --root/--profile select a Feast, mutually exclusively. List/show/pack also accept --checkout-only instead. Metadata and offline report use require Python 3.11+ and PyYAML; operation execution retains matching SSHScript 5.0.0.

| Command | Interface and effects |
| --- | --- |
| recipes list [--query TEXT] [--kind operation/report] [--json] [--html NEW_FILE] | Combine active bundle/profile/external sources. Show disabled/unavailable sources and static compatibility; HTML writes a new escaped table. |
| recipes show RECIPE [--json] | Show identity, purpose, typed inputs, dependencies and verification. Exact references take precedence; ambiguous IDs fail. |
| recipes run RECIPE [operation options] | Operations share opsfeast.py recipes run host/group/all/exclude/threads/timeout/--var/--vars-file/progress semantics. |
| recipes run RECIPE [--input JSON_FILE ...] [--var NAME=VALUE ...] [--vars-file JSON_FILE] [--timeout SECONDS] | Offline python-report recipes receive selected JSON data and isolated parameters, no hosts/Sessions. Save new result/artifact files. |
| recipes results list [--recipe-id ID] [--status STATUS] [--json] [--html NEW_FILE] | Read the ordered offline-report index, with explicit invalid-file errors. Host results use observation result. |
| recipes results detail [RESULT_ID] [--recipe-id ID] [--status STATUS] [--json] | Offline-report vertical index entries or one complete report result; no table-width dependency. |
| recipes results show RESULT_ID [--html NEW_FILE] | Return offline-report JSON or export an escaped field table. RESULT_ID is storage-relative, never an arbitrary path. |
| recipes results diagnose RESULT_ID [--limit N] [--json] | Read bounded offline-report failure evidence; limit defaults to 5 (1–50). Use observation result RESULT_ID for host diagnosis. |
| recipes artifact RESULT_ID NAME | Verify a declared report artifact's path/size/digest and print its local path; do not launch/publish. |
| recipes pack RECIPE --file RELATIVE_FILE ... --output NEW_ZIP | Package one recipe from an explicit file allowlist with manifest/digests; exclude private/storage/hidden/link entries. |
| recipes unpack ZIP --destination NEW_DIRECTORY | Verify exact bundle inventory/digests/bounds and extract a review candidate; no installation, registration or execution. |
| recipes jobs save NAME RECIPE [run options] | Save private invocation/source bindings and reviewed recipe fingerprint; preserve existing definitions. No execution or schedule creation. |
| recipes jobs list / show NAME / run NAME | Inspect saved jobs or rerun their existing recipe, rejecting recipe-content drift. |

Successful metadata/package/save operations return 0. Catalog errors, partial raw indexes, invalid inputs/artifacts/jobs/storage and unsuccessful recipe statuses return 1; argparse usage errors return 2. Report generation success does not mean source operations are successful. stdout follows the terminal table/explicit JSON policy above for catalog/show/index/execution/jobs, while packages and artifacts remain JSON; diagnostics go to stderr. HTML export paths must not exist. Pack/unpack destinations must be new. No scheduler, remote Exchange, automatic installer, notification provider or graphical/MCP application is created by these commands.

## Recipe attribution defaults and reserved identity

`python -B tools/recipe_identity.py defaults [--json]` prints an author/license table on a terminal and JSON with --json or non-TTY output (0 on success, 1 with safe error type on invalid local settings; usage 2). `.opsfeast-author.yaml` is per installation and ignored by Git. Descriptor/catalog/Info metadata includes author name/contacts and license. External `recipes unpack` rejects reserved Bundle authors/contacts before extraction; MIT pack requires explicit LICENSE. See [attribution contract](recipe-attribution.md).

## Optional Textual display

Run `python -B tools/opsfeast.py` without arguments for a version/download Home, masked Hosts, persistent profile switching and bundled Help. Hosts follows the default profile; explicit recipe environments are preserved. Explicit commands remain CLI. Bare `python -B tools/opsfeast.py recipes` opens the recipes workbench; explicit subcommands stay CLI. The workbench starts with checkout-only discovery and provides action forms for catalog, run, results/artifacts, jobs and bundles. Writes/execution require an in-app argument review; opening alone performs no operation. Add `--tui` to supported inspection/configuration/diagnostic/recipe commands for an interactive terminal display. The UI consumes stdout, preserves final result states/storage and returns the existing command exit code after closing. It requires terminal stdin/stdout and optional Textual 8.2.8 (`requirements-tui.txt`); prerequisite failures occur before execution. Use ordinary CLI output for automation. See [terminal display](terminal-ui.md) for the exact supported commands, examples, live-stage behavior, shortcuts, failures and verification limits.

## Operational recipe execution

Use the single public entrypoint for host operations and offline reports:

```sh
python -B tools/opsfeast.py recipes run RECIPE --host HOST --profile main --json
python -B tools/opsfeast.py recipes run RECIPE --group web production --threads 4 --json
python -B tools/opsfeast.py recipes run RECIPE --all --exclude host9 host10 --json
```

RECIPE is a required positional reference: a checkout-relative path (omit recipes/), equivalent bundle:PATH, :profile-path, a registered source:path, or an unambiguous catalog ID. Explicit management-root-relative ./recipes/PATH and authorized absolute recipe paths resolve through the same source boundaries. Paths never fall back to a different source. See [source and input rules](recipe-sources.md) and [general execution](recipe-execution.md).

| Option | Behavior |
| --- | --- |
| --host HOST ... / --group GROUP ... | Repeatable exact selectors; their union preserves first occurrence. |
| --all | All enabled configured hosts, including local/jump hosts; excludes host/group selectors. |
| --exclude HOST ... | Exact host IDs, requires --all; excluded hosts may still be necessary jump hosts. |
| --root ROOT / --profile NAME | Mutually exclusive environment selection; default is the selected profile. |
| --timeout SECONDS | Positive finite connection-stage/command timeout, default 30; no whole-run deadline. |
| --threads N | Positive host concurrency; default min(8, logical CPU count), fallback 1. |
| --vars-file JSON_FILE / --var NAME=VALUE | Typed inputs; defaults/source/resolved recipe settings/invocation merge as [documented](recipe-sources.md#variables-and-implementation-context). Inventory separately saves nonsecret Attention policy. |
| --verbose / --quiet | Force or suppress stderr stages/heartbeats; mutually exclusive. Terminal progress is automatic. |
| --json | Explicit machine-readable output; terminal default uses shared tables. |
| --input FILE | Offline report input only; report recipes do not accept host selectors. |
| --tui | Optional Textual display through opsfeast.py; same operation and authorization. |

Unknown targets, an empty selection and invalid connection configuration fail before execution. Disabled explicit hosts/sources are skipped without connection. Host/group members are deduplicated in merged configuration order; groups do not inherit settings. Each host owns its Session and result. Per-host execution failures do not stop other selected hosts; JSON output preserves selection order. Recipe result, retention receipt and content_update are separate; failure/partial/skipped status or failed retention/content produces a nonzero exit. Saved raw results are under observations/ and can be inspected with observation result [RESULT_ID] without reconnecting.

Bulk/group recipe execution requires host, source and exact-reference recipe enabled; default recipe state is false. New init enables bundled inventory in default.recipes. Explicit --host overrides the three enabled gates for that target, while disabled jump hosts and invalid recipe/vars/path checks still fail. Host diagnostics retain their own rules. An entirely disabled group/all selection may complete as a journaled all-skipped batch without execution; an entirely CLI-excluded selection still fails.

An all-skipped recipe batch still returns its independent content_update receipt; publication failure makes that invocation exit nonzero even when no host executed. Scheduled skipped targets retain their configured recipe reference.

In namespace-enabled profiles, operational CLI execution returns observation_run_id and persists one batch covering target outcomes, including failures with no raw report. Read it with `inventory runs list --profile main --json` or `inventory runs show RUN_UUID --profile main --json`; both accept --root instead. Successful reads return 0 independently of saved run status. New runs include selection (original CLI selectors/exclusions or scheduled host IDs) and a separately journaled execution receipt with actual command success/failure, exit_code, completed_at and content_status. Top-level status still describes collection, not the command result; missing old selection/execution is unknown. Vault shows selector Targets, integer-second duration and the recorded command outcome; retries do not change historical command failures. Dry runs, no-store queries, offline reports, replay and rebuild do not create runs. See [batch schema, storage and limits](observation-runs.md).

For system/inventory/overview, recipes run, inventory run and scheduled dispatch all call the same [job collector](inventory-jobs.md). Use inventory query for property/job selection without storage, or add --save for a retained comparison. The former standalone runner entrypoint, --recipe alias, --dryrun/--force flags and snapshot collection path have been removed. Use check-access for explicitly authorized connection/privilege diagnostics, and inventory dispatch --dry-run for a schedule preview without connection. These are different scopes.

The internal recipe_runner module owns host selection, general recipe execution and atomic result helpers; it is not a second CLI or stable installed SDK. It requires an explicit recipe argument and routes inventory to the job collector. No automatic conversion/deletion of saved results, retained data or private configuration is performed. Existing scripts must switch to the commands above; copied inventory descriptors must use the current job contract. Pinned saved jobs whose fingerprints changed must be reviewed and deliberately recreated.

## Exit codes, output and side effects

Su/sudo JSON includes per-step `identity_verification` (expected/actual username and effective UID, matched/status/message) and per-group `parent_identity_verification` for return to the original connection identity. See [identity evidence](host-diagnostics.md#read-the-identity-evidence) for failed/incomplete/not-run states and separate prerequisite su evidence. --verbose/--debug adds readable successful identity/restoration explanations on stderr; stdout is JSON with --json or non-TTY output; terminal summaries follow the table policy above.

| Command/result | Exit code |
| --- | --- |
| Successful local profile/configuration operation | 0 |
| Interactive use cancellation; profiles with no registrations | 0 |
| Successful connection test, including initialization if requested | 0 |
| Host-init success | 0 |
| Su/sudo/test-host success, partial or skipped | 0; inspect JSON for skipped tests |
| Inventory: every selected host fully successful | 0 |
| Python-session recipes: every selected host returns success with successful cleanup/save | 0; inspect data to assess the operation's observation |
| Actual diagnostic failure; recipe partial/unsupported/skipped/failed; configuration/save error | 1 |
| Invalid CLI syntax/options rejected by argparse | 2 |

Profiles/init/attach/detach/use/check retain confirmations and use terminal tables where described above. Check-access keeps its default per-test table; add --json for its complete report. Other diagnostics and recipe execution use tables on terminals and JSON with --json or non-TTY output. Recipe execution saves full reports; inventory additionally saves eligible retained observations. Python-session results include data, declared retention or skipped no_retention_adapter, and separate content_update. Diagnostic progress/errors go to stderr where supported; preflight errors may produce no JSON report. Init writes the scaffold/registry; attach/detach/use write the registry. Host-init writes facts; test-host and inventory can initialize facts; inventory writes new results and retained data. Standalone test-connection/su/sudo do not automatically save their reports. Use --json and redirect stdout if you need to retain a structured diagnostic report.

Setup/checks do not authorize connections, proxy commands, account switches or recipes. Explicit diagnostics may create authentication/audit records and execute login-shell startup; configured proxies can execute locally. The built-in inventory performs read-only queries; inventory uses the bounded two-candidate su/sudo policy, then collects under the verified root or original login actor. Account sudo: false disables only that account's sudo and excludes it as a second candidate. Custom recipe code must be reviewed within its execution scope; path/version/digest checks do not authenticate a publisher or confine code. Channel closure is not proof of remote-process termination.

## Human and agent workflow

Prepare/register an environment, edit hosts.yaml, and run check. For an authorized readiness check, use test-host and interpret every test state. Explicitly refresh host-init after known OS/endpoint changes. For authorized inventory, select the same recipe for the fleet and read each host's result, selected implementation/version and partial/error evidence. Keep configuration, credentials, observations and human notes in the management environment.

Agents should use --profile or an explicit root for unattended work, explicit profile names instead of interactive use, and the user's chosen interpreter. Read the [hosts skill](../skills/opsfeast-hosts/SKILL.md) for diagnostics and the [recipes skill](../skills/opsfeast-recipes/SKILL.md) for recipe selection, parameterized execution and authoring. Reuse existing authorization and context; ask only for missing information that affects correctness or scope.

Synthetic tests cover configuration, dispatch, cache, account transitions, batch continuation and failure/cleanup handling. macOS local read-only initialization/inventory has been verified. Real Linux/FreeBSD collection, SSH and native su/sudo remain unverified; compatible metadata and synthetic success do not establish those outcomes.

## Retained observations and exchange

All commands require Python 3.11+ and PyYAML; only runner execution additionally requires matching SSHScript 5.0.0. SQLite is included with Python; JSON SQL functions must be available. See the [canonical contract and identity workflow](result-data.md) and [agent skill](../skills/opsfeast-result-data/SKILL.md).

```sh
python -B tools/observation_store.py ingest FILE [FILE ...] [--root ROOT | --profile NAME]
python -B tools/observation_store.py export [--root ROOT | --profile NAME] \
  [--recipe RECIPE_ID] [--host HOST_ID ...] [--since ISO_TIME] [--until ISO_TIME]
python -B tools/observation_store.py validate EXCHANGE_FILE
python -B tools/observation_store.py combine EXCHANGE_FILE [EXCHANGE_FILE ...]
```

Root/profile resolution follows the existing tools. File arguments use shell working-directory paths. Ingest validates selected local raw files before a transactional batch, reports stored/already_stored/skipped, and does not connect. Foreign raw receipts are rejected: exchange retained records instead. Export reads records/observations.sqlite3 and prints JSON exchange 0.1.0; it writes no profile/configuration and sends nothing. Missing databases fail, empty selections succeed. Filters are exact local host IDs, recipe ID inventory-system, and inclusive completion times with explicit timezone. No filters selects all retained records. Output orders by completion time then observation ID. Validate needs no profile and prints valid plus record count. Combine needs no profile, prints a validated union, deduplicates identical observation IDs, and rejects ID/content conflicts. Different observations for one host remain distinct. All four commands return 0 on successful processing, including excluded raw reports and empty exchanges, and 1 for configuration/input/storage errors. Unrecognized arguments return argparse exit 2. Errors go to stderr, without third-party exception text.

The runner automatically performs raw → retained after cleanup, then adds retention and identity_quality to single/batch stdout summaries. Raw schema 0.2.0 receives additive identity 0.1.0 and retention receipt fields. Success/partial operational local/SSH observations are retained; failed/skipped/unsupported/mock results are excluded. Retention failure preserves raw, warns, and makes runner exit 1 even for successful collection; use ingest to retry without remote execution. Retention receipts are persisted in raw but excluded from observation ID hashing. The raw collection status and retention status are separate evidence. Disabled/preflight paths may still have no raw file or retention receipt.

Host identity refers to an OS installation. Linux uses a hashed machine-id candidate with clone/reinstall caveats. FreeBSD/macOS/ESXi lack a verified installation identifier in this implementation and use source UUID plus local host_id fallback, even with valid hardware serials. Fallback emits a warning with remediation and does not establish replacement detection or cross-source equality. Sudo credential selection and whole-inventory access controls are documented in [inventory access](inventory-access.md); legacy identity_sudo no longer selects collection privilege. Unknown cleanup fails collection; no historical keys are automatically reassigned. No receiver database importer, automatic latest-state/conflict resolver, transmission or cleanup tool is implemented.

Host identity_key, label and description are now supported. An explicit identity_key takes precedence and is shared across Feasts as user-assigned identity; change it after OS reinstall/replacement and coordinate its namespace. label/description are captured human text, never identity keys, and are preserved through retention/exchange. See [the canonical host configuration](hosts-yaml.md#explicit-host-identity-and-human-readable-metadata) and [identity/metadata rules](result-data.md#explicit-identity-and-display-metadata). MAC is not an automatic key.

For an ESXi VMkernel target lacking id, check-access uses existing system Python for effective UID/account verification, with additive access.identity_probe/configured_identity_probe and identity_error.reason_code fields. A reachable SSH session with failed identity is shown as PASS connection and FAIL identity; it never becomes successful access. Verified UID 0 skips sudo. See [adapter prerequisites, schemas and tested limits](host-diagnostics.md#esxi-login-identity-without-id). No new flag, setup or credential rule is introduced.

### SSH authentication source selection

All connecting commands use the shared [connection authentication policy](hosts-yaml.md#ssh-authentication-sources):
connection.allow_agent and connection.look_for_keys are independent Booleans, each
defaulting to false on every hop, including SSH config aliases. No CLI flags override
this policy. Reuse test-connection HOST --json --debug for an authorized probe;
effective switches appear in safe stderr debug output. check validates types without
connecting; dump preserves stored values rather than materializing defaults.
Missing all sources after resolution produces missing_authentication_source with a
configuration hint and fails before that host's first connection. Existing command
failure exit codes and partial/batch behavior still apply. See [migration](migration.md#explicit-ssh-authentication-sources).

### Group catalog and bulk host definitions

The shared loader accepts top-level groups with optional label/description/icon/hosts,
flattens bulk hosts into the ordinary host map, and prepends the enclosing group to
their membership. All CLI host IDs, jump references, recipe paths and filtering use
that map. The existing --group selector uses IDs, never labels. A defined empty
group is known but selecting no eligible hosts returns a nonzero no-hosts-selected
error before execution. No new CLI switches are required.

```sh
python -B tools/opsfeast.py check --profile NAME
python -B tools/opsfeast.py dump groups --profile NAME
python -B tools/opsfeast.py dump groups.backup.label --profile NAME
python -B tools/opsfeast.py dump hosts.backup-01.group --profile NAME
```

check/dump remain local reads. Effective dump groups includes defaults and member ID
lists; dump hosts includes bulk hosts. Source YAML is not rewritten. dump is unmasked.
Connection tests/recipes still need their actual operational authorization. See
[canonical schema](hosts-yaml.md#host-groups) and [migration](migration.md#group-catalog-and-bulk-host-definitions).

### Human check overview

`python -B tools/opsfeast.py check --profile NAME` uses a group/host/users table only
when sys.stdout.isatty() is true and --json is absent. The header counts YAML files,
groups (including declared empty groups) and unique host IDs. Groups sort by ID
(case-sensitive ascending string order), independently of labels or declaration order;
members follow effective host order; ungrouped hosts appear last. Empty groups
show (no hosts). A differing label displays as LABEL (ID), followed by the description
when present. Membership determines grouping, never label text.

Multi-group hosts appear in every membership. Only their first membership carries
(primary); the host total still counts each ID once. Disabled hosts remain visible
with [disabled], explained by a legend. This is configuration state, not a connection
failure. Existing effective host/account icons are reused across every group row.
The locally known/configured login is first, followed by the other declared users
in declaration order, without duplicates or a (login) suffix. A local connection uses
the current local account; an omitted
explicit-host user uses the existing local-account fallback. SSH aliases show login
unresolved before any declared users; check does not resolve aliases or create Sessions
for display. Account names are configuration evidence, not authenticated identities.
Only names and icons are shown; passwords, vars and other credential fields are omitted.

The human table omits selected-recipe counts and recipe-skip details. Validation still
checks recipe selections, and invalid recipes still fail with the existing exit code;
notes and the configuration-only limitation remain visible. --json preserves the exact
report_version 0.1.0 payload, including per-host selected_recipes/skipped and notes,
on both terminals and pipes. Without --json, redirected output retains its previous
text summary and detailed recipe/skip lines. init output is unchanged. No flags, data
schemas, stored settings or operational authorization change.


Delivery verification (2026-10-16): 545 tests passed on each of Python 3.11.15,
3.13.13 and 3.14.4. The older interpreters reused the selected environment's
pure-Python dependencies; these runs do not establish native SSH readiness.
TTY fixtures cover group-ID sorting independent of labels, login-first ordering
without suffixes, disabled/empty cases and recipe-validation failure; exact JSON and redirected-text regression assertions passed. Wheel/sdist
build, temporary installation and outside-checkout TTY/JSON checks passed on 3.14.
Documentation links/dates and skill frontmatter checks passed. No real SSH was used.

### ESXi identity failure evidence

check-access --json now includes access.identity_probe.id_exitcode, and ESXi
configured_identity_probe actual/expected username/effective_uid and matched when
that comparison is available. access.actual_identity preserves the observed actor
before a configured-account mismatch; connection_identity remains unpublished until
verification succeeds. No raw stderr or Python output is retained. The top-level
identity_failed reason keeps the specific identity_error.reason_code. See [exact
fallback conditions and interpretation](host-diagnostics.md#diagnose-esxi-identity-failures).
An SSH exec missing-id exit 2 can use the same verified VMkernel/Python adapter as exit
127; arbitrary command errors do not. Connection-level UID mismatch may use the ESXi
root-shell model below; other mismatches fail before sudo/collection.

### ESXi login versus execution identity

check-access can report a successful ordinary SSH login with an effective root shell
on verified ESXi. Its identity row explains shell=root, uid=0 (ESXi); sudo is SKIP /
already_root, and the host passes if all other required checks/cleanup pass. JSON adds
login_identity, shell_identity and identity_model esxi_root_shell. Numeric UID matched
can remain false while configured_identity_probe.status is success and accepted_by
records the model. The final-hop resolved SSH user drives account selection/policy;
connection_identity remains the baseline shell actor. No new flags or YAML settings
are needed. See [precise conditions and verification limits](host-diagnostics.md#ssh-login-and-esxi-root-shell-identity).

## Compact execution summaries

Completed recipe execution on a terminal prints one table with four columns:
`host`, `collection identity`, `result`, and `result id`. This applies to opsfeast.py recipes run, recipes run
and saved-job execution, for both single and batch targets. It does not append field/value
access, data, artifact, count or path tables. Excluded hosts appear as SKIP rows in the
same table. result id is the same collision-aware short ID used by observation result; use it directly with observation result RESULT_ID. Unsaved or excluded targets display a dash. IDs are presentation only: JSON and saved reports are unchanged. A saved batch also prints its shared Observation ID after the table; revisit it with observation ID or observation latest --status failed. Progress/errors remain on stderr; --quiet suppresses runner progress.

Collection identity uses access.actual_identity, for example root (uid=0) after sudo,
not the login or pre-elevation shell. Missing evidence displays unknown; general recipes
do not acquire new identity probes just for display. Failed/partial/skipped/unsupported
states include their reason when available. Retention failure is explicitly FAIL with
the separate collection outcome; fallback_user is PARTIAL when collection itself passed.
Exit codes and the full JSON/saved-report contracts are unchanged. Inventory dryrun and
a blocked preflight still show the existing access-test view because collection did not
start. Recipe-authored stdout is not suppressed by this formatter.

### Inspect one host's saved execution

Use the existing read-only result browser after a run:

```sh
python -B tools/opsfeast.py observation result --host HOST --recipe-id inventory-system --root ROOT
python -B tools/opsfeast.py observation result RESULT_ID --raw --root ROOT
```

Select a displayed short ID (or the complete JSON result_id) from the newest-first list; HOST and ROOT identify the
original management environment. Each saved result contains host_id. --raw returns the
complete raw JSON, including access/collection evidence and saved data. For a basic
HTML view, use observation result RESULT_ID --detail --html NEW_FILE; it creates an escaped file without launching a viewer.
Use observation result --json for the machine-readable host index. These commands do not connect, recollect,
change sudo state or infer a latest result from a filename. Missing/invalid results
remain explicit errors. Source-disabled or blocked preflight attempts may have no saved
result; inspect the original --json diagnostic output in that case.

Verification uses synthetic single/batch states, unknown identities, root/user actors,
retention failures, exclusions and unchanged JSON, plus real local saved-result lookup
by host without any Session. No remote recipe execution is needed for this display change.

## Saved-result collection user

Human `observation result` tables, redirected list text and list HTML show **user**
in place of identity quality. Use --json or observation result RESULT_ID --detail/--raw to inspect preserved
identity_quality and identity warnings. Existing warning display remains unchanged:
the compact TTY table omits warnings, while redirected text and list HTML retain them.

The result index adds nullable `collection_user`; JSON consumers keep identity_quality
and identity_warnings with their existing meanings. Index detail includes all three.
Explicit --detail/--raw preserve the complete saved evidence. Python consumers can
reuse `recipe_reports.collection_user(raw)` on an already loaded result, or obtain
the value through `recipe_reports.results(root, ...)`; no host access is required.

Only inventory-system with an explicitly recorded root/user/fallback_user collection
mode, consistent actual_identity username/effective UID and at least one attempted
core observation supplies a known account. Display actual_identity.username, not the
SSH login, selected su account, or an access-only preflight actor. For example,
operator → su admin → sudo root displays root. A collection that attempted commands
can still display its known account when the final result is failed (for example,
command or cleanup failure). Before collection, all-not_attempted observations leave
the collector unknown even if a login/root identity was probed successfully.

Missing/invalid actor evidence, legacy data without collection scope and unsupported
generic/report recipes return JSON null and display unknown. A generic recipe may
use multiple privilege scopes; its login or last privilege attempt does not prove
who obtained the entire result. No connection, rerun, historical file rewrite or
host-identity quality change occurs. Synthetic tests cover root/user/fallback,
precollection and malformed evidence, failed collections, generic/legacy unknowns,
TTY/pipe/HTML rendering, preserved JSON/detail quality and unchanged raw files.

## Host result history and modes

```sh
python -B tools/opsfeast.py observation result --profile main --host HOST --status failed
python -B tools/opsfeast.py observation result RESULT_ID --profile main
python -B tools/opsfeast.py observation result RESULT_ID --detail --profile main
python -B tools/opsfeast.py observation result RESULT_ID --raw --profile main
```

`observation` browses batches; `observation result` browses individual host results, including older raw files with no batch association. Omit RESULT_ID for the newest-first host index, optionally filtered by --host, --recipe-id and one --status (success, partial, failed, skipped, unsupported). Include RESULT_ID for focused diagnosis by default. --detail gives full vertical evidence; --raw gives the original complete JSON. --json returns index/diagnosis JSON, or complete JSON with selected --detail. --raw requires an ID; selected IDs reject index filters. --limit applies only to selected diagnosis. Mutually exclusive --root/--profile select the original existing data location. These reads never collect or retry.

Without --json, index output is a compact terminal table or pipe-delimited text when redirected; diagnosis and --detail remain text even through pipes. --raw always emits JSON. --html NEW_FILE explicitly creates an escaped HTML index, or a complete selected --detail view, and returns a JSON receipt. It rejects --raw and selected default diagnosis. Malformed host files remain explicit index errors (partial/exit 1); malformed reports do not contaminate host history. Missing/unsafe/wrong-kind/ambiguous IDs return 1; syntax errors return 2. A successful read, including an empty index or stored failed result, returns 0 independently of collection outcome.

`recipes results list/show/detail/diagnose` now accepts offline report results only, with --recipe-id/--status index filters and existing artifact commands. It rejects host IDs and --host; no host compatibility alias is provided. Update scripts to the commands above. Saved paths, globally collision-aware Result IDs, raw files, index 0.1.0 and diagnosis 0.1.0 are unchanged. The Recipes workbench labels its report-only actions Browse report results/Inspect report result; the recipe browser still reads provenance-matched history through the generic read API.

## Diagnose a saved failure

Start with the short result id from the completion table; full storage-relative IDs also work:

```sh
python -B tools/opsfeast.py observation result RESULT_ID --profile main
python -B tools/opsfeast.py observation result RESULT_ID --profile main --limit 10 --json
```

Use the original --root/--profile. This reads one saved result without connections, collection, consumers or file rewrites. Successful reads return 0 even when the saved result failed; missing/unsafe/ambiguous IDs or invalid options return 1, syntax errors 2. In this mode RESULT_ID is required. Index filters and --html are rejected; --limit is supported only by the default diagnosis and must be 1–50 (default 5).

Human output prioritizes execution/cleanup errors, independent retention/content/operation failures, degraded access, failed probes and grouped sample gaps. It omits successful probe output and arbitrary recipe data. Unsupported/unattempted probes are counted separately; budget-exhausted probes remain problems. Acquisition placeholders do not duplicate a recorded outer error. Failed stdout/stderr excerpts contain at most four lines and 400 characters per stream; clipping and capture truncation are explicit. Additional problems are counted, with --limit to inspect more. Controls are escaped for terminal display.

This is evidence selection, not an inferred root-cause engine. Missing exception messages, missing key names or source locations cannot be reconstructed; a non-success result without specific evidence says so. A success status with no recorded failures is not a complete health assessment. Generic recipes contribute only the known top-level execution/receipt fields and known probe structures; arbitrary data.error fields are not recursively guessed to be failures. Use observation result RESULT_ID --detail or --raw for the complete selected evidence.

--json returns the bounded diagnosis projection 0.1.0 ([schema](../schemas/result-diagnosis.schema.json)): requested/full result IDs, host/stored status/reason, probe and unsupported counts, issue/shown/omitted counts, selected issues and interpretation notes. Stored status is separate from retention/content failures. JSON excerpts remain clipped and omitted_count remains explicit; it is not the complete raw payload. The host index/raw schemas and saved files retain their contracts; the CLI namespace changes as described above. Source/state/reason fields are recorded evidence; no automatic retry or repair is authorized by this read.

Public tests in tests/test_result_diagnostics.py cover bounded output, stage/receipt priority, deduplication, grouped gaps, unknown evidence, legacy source exits, JSON/limits/invalid flags and byte-for-byte read-only behavior. These are synthetic/offline checks; they add no real-host collection evidence.

## Vertical result details

Use observation result --detail for long result IDs, similar to MySQL's vertical \G view.
Without RESULT_ID, it reads the same newest-first index as observation result and accepts
--host, --recipe-id and --status. It prints a numbered record separator and one
field: value line per index field, including the complete result_id and host_id.
It does not load every result's full collection payload into the display.

```sh
python -B tools/opsfeast.py observation result --detail --host HOST --recipe-id inventory-system --root ROOT
python -B tools/opsfeast.py observation result RESULT_ID --detail --root ROOT
```

With RESULT_ID, --detail reads one complete raw result. Nested object fields use dotted
names (for example access.actual_identity.username); arrays remain JSON values on a
single line. Null/Boolean values remain explicit and strings retain leading zeroes.
Newlines and terminal controls in keys/values are escaped. No value is truncated or
horizontally combined with other fields. This explicit human view stays vertical for
both terminal and redirected stdout and does not require tabulate. It is not a parser
contract: add --json for the existing index envelope or complete raw-result JSON,
respectively. No new result schema or storage is introduced.

No matches prints No saved results. and returns zero; malformed index files remain
visible as invalid-result errors and return one while preserving readable records.
Missing/unsafe result IDs return an error. RESULT_ID cannot be combined with index
filters. --html NEW_FILE exports the index or a selected --detail view; existing files are never overwritten. --raw emits unchanged raw JSON; the index uses the short IDs described below. Use the original --root or --profile; detail performs no host
connection, sudo, collection, file rewrite or viewer launch. Synthetic tests cover
TTY/pipe/JSON, long names, escaped controls, filters, empty/partial indexes, unsafe IDs,
option errors and operation without table dependencies.

## Short result IDs

Human execution completion tables and results list output (terminal, redirected text and HTML rows) use short IDs,
for example a73c91e2, instead of long storage-relative filenames. Use them directly:

```sh
python -B tools/opsfeast.py observation result --host HOST --root ROOT
python -B tools/opsfeast.py observation result a73c91e2 --raw --root ROOT
python -B tools/opsfeast.py observation result a73c91e2 --detail --root ROOT
```

The ID above is illustrative; use a displayed value from the same management root.
Full storage-relative result IDs still work, and --raw JSON remains the unchanged raw
document. --detail displays the resolved complete result_id; --detail without an ID shows
both result_id and short_id vertically. Index JSON (results version 0.1.0) adds short_id
to records and invalid-file errors while preserving the complete result_id. Use full
result_id in durable automation and --json for machine parsing. Report short IDs also work
with the existing artifact selector through the same checked result resolver.

The lookup key is the SHA-256 hexadecimal digest of the exact UTF-8 storage-relative
result path. This provides a deterministic alias for old inventory filenames, general
recipe runs and report directories, including legacy names without UUIDs. Normal IDs
show the first eight lowercase hexadecimal characters. The prefix extends only as
needed for uniqueness across all candidate result files in that root, including invalid
files, before any recipe/host/status filter. Filtering cannot make a globally ambiguous
prefix resolve silently. Any unique prefix of 8–64 characters can be used for lookup;
unknown or ambiguous prefixes return a nonzero error. A full digest collision rejects
index construction rather than selecting an arbitrary result; full paths remain usable.

These aliases are local lookup handles, not host/observation identity or a new stored
UUID. Existing timestamped filenames and embedded UUIDs, raw documents, result paths,
SQLite records and chronological ordering are unchanged. No migration, manifest,
rewrite or remote operation is needed. Copying an entire management root preserves
aliases; renaming an individual result changes its alias. Adding a colliding result
may extend displayed aliases and makes an old ambiguous prefix fail; retain full IDs
for durable references. Deleted/missing files remain lookup errors, and all existing
symlink/containment/envelope/artifact checks still apply after resolution.

Synthetic verification covers legacy/new-style paths, reports, full and short lookup,
filter-independent prefix extension, ambiguous/missing IDs, complete digest collision,
invalid files, symlinks, unchanged raw bytes and copies of management roots. This
changes local indexing and presentation only, without new SSH or privilege behavior.

## Original inventory command streams

New inventory query/run and recipes run inventory results include bounded command/stdout/stderr in probes; query still writes nothing unless --save is used. Saved probes remain available through retention show RECORD_ID --profile NAME --json (record.data.probes) and Core profile.retention.show(RECORD_ID). Current Vault records append closed code disclosures. Empty/unavailable/truncated streams differ; see [capture semantics and limits](inventory-jobs.md#source-times-histories-and-latest-views). This is recipe-owned property-probe evidence, not a full SSH/login transcript. Rebuild cannot recover unrecorded historical output.

## Human time display policy

Human-facing instants use the running computer's local timezone and
YYYY-MM-DD HH:MM:SS, with no fractional seconds. For example,
2026-10-14T20:34:56.987654Z displays as 2026-10-15 04:34:56 on a controller in
Asia/Taipei. No timezone is hardcoded: the operating system/TZ environment selects
it, and historical daylight-saving offsets apply to each instant. Fractions are
omitted, not rounded into the next second. This is display formatting, not timestamp
regeneration or a change in the observation's time.

The policy covers CLI human tables, results list (including redirected text), vertical
detail, nested human details, HTML result exports, Home download time and TUI Details.
The existing TUI history heading retains its local GMT offset information. Bundled
feast/report/execution-summary 0.1.2 renders both source/generation times in HTML using controller local
time at generation, while its JSON artifact preserves the original timestamps. A static
HTML artifact does not change timezone when opened on another computer.

Formatting copies data at the view boundary. --json, observation result --raw JSON, TUI Original
output, saved reports/receipts, JSON/CSV exports, SQLite, hash inputs, short IDs,
filename UTC prefixes and ordering retain original precision/timezones. These are data
interfaces, not human time views. Duration/measurement numbers and calendar-only dates
are not reinterpreted as instants. Missing values remain missing; generic views leave
malformed/timezone-less values unchanged rather than guessing UTC/local. TUI history
retains its explicit unknown/invalid-or-unzoned indicators.

The internal display_time module supplies format_time/human_times to shared views;
this is a checkout implementation helper, not a versioned Core API. The portable
report recipe includes its own standard-library formatter for the same policy so it
remains shareable without importing an internal checkout module. Public synthetic
checks cover offset/date rollover, fractional truncation, winter/summer DST, nested
values, CLI TTY/pipe/JSON, HTML and TUI display copies, source-byte preservation and
the standalone report's unchanged JSON artifact. No remote operation is required.

Saved-result user display verification (2026-10-17): Python 3.11.15 and 3.14.4
passed all 608 public tests. The first parallel 3.13.13 run hit the existing TUI
0.5-second child-process timing assertion; an independent full rerun passed all 608
without code/test changes. Older interpreters reused shared Python dependencies.
Wheel/sdist and temporary installed imports/CLI checks, credential-free local console
checks, Python 3.11 grammar, skill frontmatter, 194 changed-document local links and
diff whitespace passed. Offline browsing of an existing failed result showed unknown
because collection never started; no host operation or saved-result rewrite occurred.

Current inventory records use records/SUMMARY.md and topic-based current-title pages with icons, optional DGMO and nonempty Attention. They omit uncollected fields and redundant columns while keeping zero/false/observed empty lists; full yearly reports preserve detailed samples, units, source times/states and collection metadata. Packages/services are complete and name-sorted. See [current/report rendering](host-vault.md#recipe-retention-and-markdown); omitted values are not verified absence or health. Rebuild updates owned output without collection or retention changes, while unmanaged notes and deliberate manual links remain user-owned.

Current selection groups each host by origin namespace, recipe-source qualifier (the prefix before a colon, or the unqualified source) and stable recipe ID, then selects the whole record with the greatest (observed_at, record_id). Recipe-directory moves within that source therefore keep one current page without aliases or rewriting historical references. Partial results remain partial. Distinct sources, origin namespaces or recipe IDs remain independent; a shared output title still fails publication explicitly rather than silently replacing another dataset. All historical reports remain available.

Vault Contents links use Obsidian-native heading fragments: `[System](#System)` and `[Collection metadata](#Collection%20metadata)`. Heading case is preserved and spaces/non-ASCII text are URL-encoded; arbitrary HTML anchor IDs are not used. Repeated headings are given unique readable titles (for example Services details) so each link reaches one section. In Obsidian Reading view, click a Contents link; in Live Preview, use the normal follow-link gesture (Cmd-click on macOS or Ctrl-click on Windows/Linux). Other Markdown readers can use different heading-fragment conventions; this is not a universal reader-compatibility guarantee. Rebuild regenerates current and historical observation pages plus the records index from retention, without recollection. See [Obsidian internal links](https://obsidian.md/help/links).

_Last modified: 2026-10-21 12:30:58_
