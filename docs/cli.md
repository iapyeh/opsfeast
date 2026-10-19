# Ops command-line reference

## Read what a command does

Top-level `python -B tools/opsfeast.py -h` groups commands by task:

| Help section | Commands |
| --- | --- |
| Profiles and setup | init, profiles, use, attach, detach, instance |
| Hosts and access (hosts.yaml) | check, dump, test-connection, host-init, test-host, test-su, test-sudo, check-access |
| Recipes and reports | inspect-recipe, recipes |
| Retained data and consumers | retention, consumers |
| Vault content | vault |

After cloning and preparing dependencies, create a Feast with init or register an existing one with attach, then edit its hosts.yaml. These sections guide discovery; they are not mandatory sequential stages or additional subcommand levels. Revisit access diagnostics after changing hosts or investigating a recipe failure. Reports, consumers and Vault can reuse saved data without collecting again. Command paths, flags and parsing remain unchanged; for example, continue using recipes run and consumers dispatch directly.

Every main command and recipe subcommand now includes its purpose in its own --help screen, before the argument list. Parent help also summarizes its child commands. Delegated usage includes the complete prefix, such as opsfeast.py recipes jobs run. Existing argument syntax, execution behavior and result formats are unchanged.

```sh
python -B tools/opsfeast.py recipes --help
python -B tools/opsfeast.py recipes run --help
python -B tools/opsfeast.py recipes jobs save --help
python -B tools/opsfeast.py consumers dispatch --help
python -B tools/run_recipe.py --help
```

recipes run explains host operations versus offline reports, raw result saving, declared retention/consumer updates and examples of both recipe kinds. jobs save describes writing a definition without execution or scheduling; jobs run describes content verification followed by actual execution. artifact describes verified JSON metadata and an absolute file path, not streaming artifact bytes. Profile/configuration/diagnostic commands distinguish registry/local writes from connections. Retention, consumers and Vault include action overviews separating reads, writes, replay, publication and dispatch. The standalone observation_store subcommands explain exchange input/output and write behavior.

--help takes priority over --tui and exits successfully before profile resolution, target selection, connections or operation writes, even when required execution arguments are omitted. It can be read from an empty working directory. Help is an introduction to a command; continue with this reference and the selected recipe/consumer documentation for complete contracts, evidence and authorization scope.

Bundled recipes now use [classified paths](recipe-taxonomy.md): system/network/check/port, system/account/check/identity, system/inventory/overview, feast/report/execution-summary and feast/report/retention-summary. Recipe selectors accept complete paths of variable depth; old bundle paths have no aliases. Update configuration/scripts/jobs/exact consumer subscriptions deliberately. Data query --recipe filters can still select historical reference strings without resolving an executable recipe.

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
- **`tools/run_recipe.py` executes inventory and compatible Python-session recipes.** Inventory automatically selects each host's platform implementation. General recipes use one execute entrypoint. Both accept typed invocation inputs and save versioned raw results; inventory and declared host-values recipes have structured retention. See [the general contract](recipe-execution.md).

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
| run_recipe.py / recipes run, including inventory dryrun | Host, collection identity and result only; dryrun/preflight retain access-test tables | --json |
| recipes list/show/results list | Catalog/source, metadata or result-index tables | --json; --html retains its explicit export behavior |
| recipes jobs list/show/save/run | Job list/details, save report or execution summary | --json; this presentation flag is not persisted in job invocation data |
| check_environment.py / recipe_identity.py defaults / skill_bundle.py check or download | Field/value readiness, author or bundle reports | --json (place after the subcommand where applicable) |

Exceptions preserve data interfaces: dump, recipes results show, artifact, pack/unpack and observation-store JSON/CSV/export/validation/combination remain structured even on a terminal. Check-access preserves its existing default table even for non-TTY stdout; use --json for its full report. Textual Home/workbench/--tui keep their DataTable interfaces and pipe-based child streams. Execution TUI rows display separate Retention and Content cells while preserving the recipe status and process exit code. Help, prompts, simple confirmations, stderr progress/errors/debug and raw saved files are not converted into tables.

Human `recipes results list` replaces identity quality with the actual collection user (unknown when unsupported or unverified). TTY lists omit the long identity-warnings column; redirected list text and list HTML retain warnings. Identity quality and warnings remain available through --json and detail/show without changing saved evidence. See [the collection-user rules](#saved-result-collection-user).

Tables preserve failure/partial/skipped/unknown states; no missing evidence becomes PASS. Connection, prerequisite su, actor sudo, restoration and cleanup remain distinct where present. A successful collection with failed retention still returns nonzero. Host and diagnostic/access account labels include resolved icons (built-ins 🍎/👤; see [global precedence](hosts-yaml.md#global-and-account-icons)); historical result views use the default when current configuration is unavailable, without rewriting IDs/data. Unicode widths, leading-zero identifiers and escaped terminal control characters use the same renderer settings as check-access. Terminal tables wrap headers and values to fit the current terminal cell width, preserving complete values instead of truncating them. Existing JSON/report/SQLite schemas, observation times, execution scope and exit codes are unchanged.

Width is read on each render using the standard terminal-size lookup (including COLUMNS when set, with an 80-column fallback when unavailable). Naturally short columns keep their space; wide columns share the remaining width, including border/header padding. Wrapping measures Unicode display cells, including Chinese and emoji, and can split long identifiers/paths. Control characters remain escaped. If columns cannot each retain a readable width, the same rows switch to labeled Record 1, Record 2, ... blocks with wrapped header/value pairs. Empty tables still display their headings. This applies to shared terminal tables, including recipes show and check-access. An indivisible two-cell character cannot fit a one-column terminal; rendering uses a minimum of two cells.

For example, on terminal stdout, COLUMNS=80 python -B tools/opsfeast.py recipes show system/inventory/overview --checkout-only previews an 80-column metadata table without a profile or host execution. Add --json for the complete structured representation. Wrapping changes only presentation: redirected tables retain their previous layout, other non-TTY outputs retain their command-specific format, and --json/raw files/HTML/TUI formats are unchanged. Free-standing prose such as diagnostic count footers is not governed by table wrapping.

Terminal display requires the declared tabulate[widechars] dependency. Operational commands check it before execution and never install packages automatically; --json bypasses table rendering. The environment checker is a deliberate exception: if display dependencies are unavailable it emits its JSON readiness report so missing packages remain diagnosable. Use the actual selected interpreter, not another environment's installed packages.

The new profiles/check JSON views identify `report_version: "0.1.0"`. Profiles contains a profiles list with name/root/status/default (a Boolean); an empty registry yields an empty list. These are basic registration states, not full configuration/connectivity checks. Check success contains status, yaml_files count, hosts (plain host ID, selected_recipes count and skipped references/reasons), and notes; errors retain stderr/nonzero behavior without a fabricated success JSON. Neither view emits credentials or rewrites configuration.

For agents/pipelines, explicitly select --json where supported, especially when running under a PTY. Presentation is not an execution authorization. The checkout-level helpers `human_output(json_output=False)`, `prepare(json_output=False)`, `table(headers, rows)` and `print_report(value, json_output=..., kind=...)` reuse the same policy; they are not a versioned Core API. table(headers, rows) escapes controls and formats human timestamps, then fits terminal width automatically; retain the original structured inputs. render_table(headers, rows) is the checkout adapter for already escaped display strings, used by check-access to avoid escaping twice. Both retain unconstrained tabulate layout on non-TTY stdout. Do not replace raw-data export interfaces with display tables.

## Installation identity and read-only inspection

`python -B tools/opsfeast.py instance ACTION [--installation DIRECTORY] [--name NAME] [--description TEXT]` follows the terminal table/JSON policy above. ACTION is inspect (read-only instance/configuration/dependency snapshot), init (create/preserve identity and optionally set name/description), set (update existing metadata), renew (new UUID for this copy), or relocate (preserve identity after moving the original). Name/description apply only to init/set. Default installation is this checkout; it is not a management root. Exit 0 is success, 1 is partial inspection/configuration/filesystem failure; syntax errors use 2. The command does not connect or execute recipes. See [identity/copy semantics and API](core-api.md).

Normal management `init` also initializes installation identity after successful validation/registration; repeated init preserves it. Profile selection does not change instance identity. Missing UUID inspection uses a nil placeholder and writes nothing. New python-recipe 0.1.0 recipes use the same run_recipe.py/recipes run options as python-session; no extra execution flag is required.

## Inventory access, dryrun and CSV

`opsfeast.py check-access (--host HOST... / --group GROUP... | --all) [--exclude HOST...] [--root ROOT | --profile NAME] [--timeout SECONDS] [--threads N] [--json] [-q | --quiet]` validates selected login/root access plus independent su and enabled sudo for all other declared users, without platform discovery or collection. Default threads is 1. Choose explicit hosts/groups or all; exclude requires all. Unknown targets/configurations fail before connections. Disabled/excluded targets are not contacted. Default stdout is a tabulate table with status, host, test, user and reason columns with PASS, ❌ FAIL or SKIP, short failure reasons and host totals; host labels include the configured icon (default 🍎), and excluded targets are listed separately. Flushed stderr progress shows each host/account as checking begins and completes, including a completion count. Use --quiet to suppress progress, and --json to retain the full structured report on stdout (combine both for silent machine consumption). Exit 0 requires every selected test to pass. See [display and migration details](inventory-access.md#check-access-without-collection).

`run_recipe.py system/inventory/overview ... --dryrun` and `opsfeast.py recipes run system/inventory/overview ... --dryrun` use the [two-candidate inventory policy](inventory-access.md#inventory-account-selection) after static recipe/input validation. Login sudo normally precedes the first other eligible users account's su/sudo; an eligible root second candidate gets su root priority. Verified login-user fallback is automatic. `--force` permits unavailable hosts to be skipped. Dryrun/force are mutually exclusive and inventory-only. Default inventory tests the entire selected batch before starting collection. Execution fallback/skip returns nonzero; dryrun success means a safe actor is available, not necessarily root; optional missing detail fields alone do not. Saved jobs do not store either flag. See [the canonical guide](inventory-access.md) for account settings, timing/race/cleanup limits, six result sections, limits and migration.

`observation_store.py export ... --format csv` uses the same selection filters as JSON export. It prints long-form CSV with missing values as empty cells and spreadsheet formula escaping. JSON remains the validated exchange format; CSV cannot be re-ingested as an exchange. No transmission occurs.

## Conventions and prerequisites

Run examples from the repository checkout. `python` means the interpreter selected for your environment; `-B` avoids writing Python bytecode. Replace synthetic host IDs, account names and `/srv/feasts/main` with your settings. Host/configuration commands read `hosts.yaml` from the chosen management environment; a host ID is a configuration key, not necessarily its hostname.

| Operation | Controller requirements |
| --- | --- |
| Profiles, init, attach, detach, use, check, dump, inspect-recipe, recipes metadata/results/packages/jobs and offline reports | Python 3.11+ and PyYAML; no SSHScript Session |
| Standalone test-connection | Python 3.11+, PyYAML and the supported SSHScript command contract (documented minimum 4.0.1) |
| Host-init, test-host, test-su, test-sudo, test-connection --host-init, run_recipe.py | Python 3.11+, PyYAML and matching SSHScript import/distribution **5.0.0** |

Both environment-check scopes require PyYAML 6.0.3 and tabulate[widechars] 0.10.0 (including wcwidth); the full check additionally requires SSHScript 5.0.0:

```sh
python -B tools/check_environment.py
python -B tools/check_environment.py --scope init
python -B tools/opsfeast.py --help
python -B tools/run_recipe.py --help
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
| run_recipe.py | `--root ROOT` |
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
| recipes run RECIPE [operation options] | Operations share run_recipe.py host/group/all/exclude/threads/timeout/--var/--vars-file/progress semantics. |
| recipes run RECIPE [--input JSON_FILE ...] [--var NAME=VALUE ...] [--vars-file JSON_FILE] [--timeout SECONDS] | Offline python-report recipes receive selected JSON data and isolated parameters, no hosts/Sessions. Save new result/artifact files. |
| recipes results list [--recipe-id ID] [--host HOST] [--status STATUS] [--json] [--html NEW_FILE] | Read ordered raw-run/report index; retain invalid-file errors and inventory quality/retention metadata. |
| recipes results detail [RESULT_ID] [--recipe-id ID] [--host HOST] [--status STATUS] [--json] | Vertical field: value index entries or a selected full raw result; no table-width dependency. |
| recipes results show RESULT_ID [--html NEW_FILE] | Return raw JSON or export an escaped field table. RESULT_ID is storage-relative, never an arbitrary path. |
| recipes artifact RESULT_ID NAME | Verify a declared report artifact's path/size/digest and print its local path; do not launch/publish. |
| recipes pack RECIPE --file RELATIVE_FILE ... --output NEW_ZIP | Package one recipe from an explicit file allowlist with manifest/digests; exclude private/storage/hidden/link entries. |
| recipes unpack ZIP --destination NEW_DIRECTORY | Verify exact bundle inventory/digests/bounds and extract a review candidate; no installation, registration or execution. |
| recipes jobs save NAME RECIPE [run options] | Save private invocation/source bindings and reviewed recipe fingerprint; preserve existing definitions. No execution or schedule creation. |
| recipes jobs list / show NAME / run NAME | Inspect saved jobs or rerun their existing recipe, rejecting recipe-content drift. |

Successful metadata/package/save operations return 0. Catalog errors, partial raw indexes, invalid inputs/artifacts/jobs/storage and unsuccessful recipe statuses return 1; argparse usage errors return 2. Report generation success does not mean source operations are successful. stdout follows the terminal table/explicit JSON policy above for catalog/show/index/execution/jobs, while packages and artifacts remain JSON; diagnostics go to stderr. HTML export paths must not exist. Pack/unpack destinations must be new. No scheduler, remote Exchange, automatic installer, notification provider or graphical/MCP application is created by these commands.

## Recipe attribution defaults and reserved identity

`python -B tools/recipe_identity.py defaults [--json]` prints an author/license table on a terminal and JSON with --json or non-TTY output (0 on success, 1 with safe error type on invalid local settings; usage 2). `.opsfeast-author.yaml` is per installation and ignored by Git. Descriptor/catalog/Info metadata includes author name/contacts and license. External `recipes unpack` rejects reserved Bundle authors/contacts before extraction; MIT pack requires explicit LICENSE. See [attribution contract](recipe-attribution.md).

## Optional Textual display

Run `python -B tools/opsfeast.py` without arguments for a version/download Home, masked Hosts, persistent profile switching and bundled Help. Hosts follows the default profile; explicit recipe environments are preserved. Explicit commands remain CLI. Bare `python -B tools/opsfeast.py recipes` opens the recipes workbench; explicit subcommands stay CLI. The workbench starts with checkout-only discovery and provides action forms for catalog, run, results/artifacts, jobs and bundles. Writes/execution require an in-app argument review; opening alone performs no operation. Add `--tui` to supported inspection/configuration/diagnostic/recipe commands or `run_recipe.py` for an interactive terminal display. The UI consumes stdout, preserves final result states/storage and returns the existing command exit code after closing. It requires terminal stdin/stdout and optional Textual 8.2.8 (`requirements-tui.txt`); prerequisite failures occur before execution. Use ordinary CLI output for automation. See [terminal display](terminal-ui.md) for the exact supported commands, examples, live-stage behavior, shortcuts, failures and verification limits.

## tools/run_recipe.py: inventory execution

This section covers shared selection/execution options for inventory and general Python-session recipes. Use [the general execution/authoring contract](recipe-execution.md) for descriptor 0.3.0, execute, raw results and limits. Inventory-specific platform/retention behavior below applies only to inventory-system.

```text
python -B tools/run_recipe.py RECIPE
    (--host HOST ... | --group GROUP ... | --all [--exclude HOST ...])
    [--root ROOT | --profile NAME] [--timeout SECONDS] [--threads N] [--verbose | --quiet]
    [--vars-file JSON_FILE] [--var NAME=VALUE ...] [--dryrun | --force]

python -B tools/run_recipe.py --recipe DIRECTORY
    (--host HOST ... | --group GROUP ... | --all [--exclude HOST ...])
    [--root ROOT | --profile NAME] [--timeout SECONDS] [--threads N] [--verbose | --quiet]
    [--vars-file JSON_FILE] [--var NAME=VALUE ...] [--dryrun | --force]
```

`--host` and `--group` may be combined and repeated. `--all` cannot be combined with either.

| Argument/option | Behavior |
| --- | --- |
| RECIPE | Recipe directory as the first argument; required unless --recipe is supplied. |
| --recipe DIRECTORY | Explicit recipe directory at any option position; cannot combine with leading RECIPE. |
| --host HOST ... | One or more exact host IDs; repeatable. Never interpreted as groups. |
| --group GROUP ... | One or more exact group names; repeatable. Never interpreted as host IDs. |
| --all | Every enabled host in the merged configuration; exclusive with --host/--group. |
| --exclude HOST ... | Exact host IDs to exclude for this run; requires --all. Unknown IDs fail before execution. |
| --root ROOT | Management directory; otherwise use profile/default. Positional management roots are not accepted. |
| --profile NAME | Select an environment for this invocation; cannot combine with --root. |
| --var NAME=VALUE | Invocation input override; repeat with unique names. Strings stay literal; other declared types use JSON. Overrides --vars-file and configured values. |
| --vars-file JSON_FILE | One UTF-8 JSON object of invocation inputs; relative to the shell directory with ~ expansion. Reject duplicate keys/non-finite data; no configuration writes. |
| --timeout SECONDS | Positive finite per-stage/command budget, default 30; not a whole-run deadline. |
| --threads N | Positive integer for concurrent hosts; default min(8, local logical CPU count), fallback 1. Use 1 for sequential execution. |
| -v, --verbose | Force progress and waiting heartbeats on stderr, including when stdout is redirected. |
| -q, --quiet | Suppress progress and waiting heartbeats; final JSON and errors remain. Exclusive with --verbose. |

```sh
python -B tools/run_recipe.py system/inventory/overview --host host-01
python -B tools/run_recipe.py system/inventory/overview --host host-01 host-02 host-03 --root /srv/feasts/main
python -B tools/run_recipe.py system/inventory/overview --group web production --profile inventory
python -B tools/run_recipe.py system/inventory/overview --host smtp-01 --group nginx apache2
python -B tools/run_recipe.py --all --recipe system/inventory/overview
python -B tools/run_recipe.py system/inventory/overview --all --threads 4 --exclude host9 host10
python -B tools/run_recipe.py community:system/inventory/overview --group web
python -B tools/run_recipe.py --host host-01 --recipe ./recipes/custom-system --root /srv/feasts/main
```

Recipe and targets must both be explicit; omission is a usage error (exit 2), never an implicit all-host selection or fallback to hosts.yaml recipe settings. Put the positional recipe first, or use --recipe elsewhere, once only. For example, `--group web production system/inventory/overview` treats all three values as group names and fails because no recipe was specified; it never guesses which value is a recipe. `--all system/inventory/overview` is rejected with a hint to use --recipe. The spelling is `--recipe`.

Use the optional host-level `group: web` string or `group: [web, production]` list in hosts.yaml; see [host groups](hosts-yaml.md#host-groups). Names are exact and case-sensitive, with no comma splitting, glob expansion or host:/group: prefix interpretation. A host and group may share a name: --host web selects only that host, while --group web selects its members.

The runner resolves every selector before any execution. Unknown names, invalid configuration and an empty target set fail without executing any host. Expand repeated --host/--group options in argument order, with group members in merged YAML host order (includes first, then the declaring file). --all uses that merged order. Overlaps and repeated selectors execute each host once, preserving its first occurrence. Groups select a union, not an intersection; they do not inherit variables, connection settings or recipes. All targets use the selected environment and the existing per-host execution contract. Selection support here does not extend diagnostic commands to groups.

The CLI executes the explicitly named compatible inventory-system or Python-session recipe directory; matching host recipe vars apply, while unrelated recipe selectors are bypassed. Host/connection configuration must remain valid. A bad recipe fails without falling back to host selectors. The internal Python run(root, host, recipe=None) helper retains host-selector behavior for existing callers; this is not a CLI default. See [sources, inputs and controls](recipe-sources.md) for shorthand selections, default/source/host/file/CLI var precedence, enabled flags, excluded_hosts and skipped results.

The previous positional HOST/ROOT, --hosts and optional recipe syntax is replaced. Migrate `run_recipe.py host-01 ROOT --recipe system/inventory/overview --hosts host-02` to `run_recipe.py system/inventory/overview --root ROOT --host host-01 host-02`. Existing YAML recipes lists and registrations are preserved; configuration checking still validates those lists.

### Recipe locations and platform selection

`system/inventory/overview` (leading or --recipe) is relative to this checkout's recipes directory, independent of the management root/shell directory. Do not include `recipes/` in that CLI form. Explicit `./recipes/custom-system` is management-root-relative; absolute paths must remain in the repository recipes directory or management root. `:system/inventory/overview` resolves from the selected management root recipes/; `community:system/inventory/overview` uses recipe_sources.community.path registered in entry hosts.yaml. External named sources accept path/vars/enabled and can live outside the management root. Predefined recipe_sources.bundle/profile accept enabled/vars without path (an optional path must resolve exactly to the default root relative to entry hosts.yaml); they control bare checkout and :profile references respectively, including their legacy path forms. Omitted controls default enabled. Missing paths never fall back to another source. YAML selectors still use `recipe: recipes/system/inventory/overview` for checkout recipes. Include files remain management-root-bound.

For each host, execution follows:

1. Resolve environment/recipe, validate host connections and descriptor/entrypoint paths/version literals before connecting.
2. Connect to the target and required hops; reuse or discover platform facts.
3. Match declared implementations against available facts. Failed initialization skips collection; no match is unsupported; equally ranked top matches fail as ambiguous.
4. Load only the selected entrypoint, check its runtime VERSION, collect inventory and validate the seven observation fields/states.
5. Close the owning Session strictly, preserve errors/partial observations, atomically save raw JSON and attempt structured retention.

Allowed match fields are os_name, distribution_id, os_version, distribution_version, kernel_release and architecture. All conditions must match. Explicit priority ranks first, then number of conditions. Missing facts do not satisfy conditions. Version bounds compare dotted numeric components; vendor suffixes use exact conditions such as `=14.2-RELEASE`. File/list order does not break ties, and failed selected code does not trigger another implementation.

Batch hosts run independently in a thread pool, with concurrency set by --threads. The CPU-based default is a starting limit for SSH/command I/O, not a performance benchmark; tune it for the controller and targets. The actual worker count is capped at the selected host count. --threads 1 runs sequentially without a pool. Each worker creates, uses and closes its own Session and hops in that same thread; Sessions are not shared between hosts. Descriptor/implementation loading through runpy is serialized to protect process-wide import state, while collectors execute concurrently. Failed/skipped/unsupported hosts do not prevent other selected hosts from running. Final JSON retains target selection order even when completion order differs; host progress is emitted immediately and whole lines are serialized on stderr. The [index/total] progress prefix identifies selection position, not a completed-host counter. --threads limits active host tasks, not all internal threads or individual hop connections. Custom implementations that mutate shared process state or shared external files must be reviewed for concurrent use; use --threads 1 when that requirement is unknown. Separate invocations against the same management environment are not coordinated by this option. A per-host preflight/save error appears in the batch summary; a result file is not guaranteed for errors before collection or when saving fails.

### Saved results and stdout

Progress is enabled automatically when `sys.stdout.isatty()` is true. It shows target selection, host index/count, connection hops, cached/discovered platform facts, implementation selection, collection, validation, cleanup, and saving. Every five seconds during a waiting stage, a heartbeat reports the current stage and elapsed time in that stage. This is a controller-side waiting indicator, not proof of remote-process health or a whole-run deadline. Messages are flushed immediately to stderr; stdout is JSON with --json or non-TTY output; terminal summaries follow the table policy above. Redirected/piped stdout disables automatic progress; --verbose enables it explicitly and --quiet disables it in a terminal. The internal Python run helper is quiet unless a reporting context is supplied. Progress omits credentials, raw command output and third-party exception text.

```text
[1/3] "smtp-01": connecting hop 1/1 (per-stage timeout 30s)
[1/3] "smtp-01": still connecting hop 1/1 (per-stage timeout 30s) (5s in this stage)
[1/3] "smtp-01": collecting inventory with "linux"
[1/3] "smtp-01": completed: success (inventory_complete)
```

Each inventory-system run writes a new file without overwriting previous inventories or updating human records:

```text
<management-root>/observations/<YYYYMMDDTHHMMSSZ>-inventory-system-<uuid>.json
```

New inventory filenames prefix the run started_at normalized to UTC at whole-second precision, for example `20261014T083012Z-inventory-system-fbd357d1-1443-4372-9e57-b7fe57f11b47.json`. Name sorting orders new files by start second, not completion time; UUIDs keep same-second runs distinct but do not order them within that second. JSON timestamps retain their original precision. Existing `inventory-system-<uuid>.json` files are preserved and remain readable: result discovery scans `observations/*.json` and uses stored timestamps, so mixed old/new names do not imply chronological filename order. Use the returned result_path/result_id rather than constructing a filename.

The shared result schema is **0.2.0**, independent of host facts schema 0.1.0. Recipe descriptor remains 0.2.0; bundled recipe version is 0.3.0; implementations carry independent versions. Results contain host_id, timestamps, runtime/evidence kind, status/reason/message, observations, command sources, host-init provenance, hop states and execution/cleanup errors. Recipe metadata records recipe_version, implementation_id/version/path when selected, selected-file SHA-256, descriptor SHA-256, Python-bundle SHA-256, resolved location and CLI/hosts selection source. A pre-dispatch skip has no selected implementation version. Source/host-disabled skips do not load a runtime or write an inventory file; they return result_path: null. Completed reports include source_name/source_root/reference and variable_names, without input values.

Seven common observations cover hostname, platform, system name/version, kernel name/release and architecture. Each retains value, state, observed_at, source_ids and error. Missing/failed values remain null with explicit states. A command returning zero does not establish successful parsing or cleanup. Raw inventory command output may appear in private source records.

With --json or non-TTY stdout, single-host output is a JSON summary containing status, reason_code, message, detected_kernel, supported_platforms, recipe_id and result_path. Using --all or resolving more than one unique host produces batch stdout: an object with a hosts array; each entry records host/status/reason/result_path, or a sanitized error type when no saved report is available. A selection resolving to one host retains the single-host summary unless --all is used. Nonempty exclusions add excluded_hosts with host_disabled/cli_excluded reasons. Explicit disabled hosts remain skipped results; disabled group/all members are omissions. If filtering removes every target, return 1 with empty hosts plus exclusion evidence and an error on stderr.

See the [inventory guide](../recipes/system/inventory/overview/README.md), [recipe descriptor](../recipes/system/inventory/overview/recipe.yaml), [result schema](../recipes/system/inventory/overview/schema.json) and [synthetic example](../recipes/system/inventory/overview/examples/result.synthetic.json) for authoring and data consumers. Copied inventory descriptors require descriptor 0.2.0, explicit access_mode, the inventory-observations retention declaration and matching retention.schema.json; removed output adapter/version keys are rejected. Reviewed custom inventory entrypoints and compatible Python-session recipes can execute; there is no arbitrary backend loader, extension-overlay installer or execution sandbox. General recipes return data in stdout summaries and save observations/recipe-run-<UUID>.json; declared host-values are retained, while undeclared datasets report no_retention_adapter; read [general result semantics](recipe-execution.md#results-failure-states-and-storage).

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

Completed recipe execution on a terminal prints one table with exactly three columns:
`host`, `collection identity`, and `result`. This applies to run_recipe.py, recipes run
and saved-job execution, for both single and batch targets. It does not append field/value
access, data, artifact, count or path tables. Excluded hosts appear as SKIP rows in the
same table. Progress/errors remain on stderr; --quiet suppresses runner progress.

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
python -B tools/opsfeast.py recipes results list --host HOST --recipe-id inventory-system --root ROOT
python -B tools/opsfeast.py recipes results show RESULT_ID --root ROOT
```

Select a displayed short ID (or the complete JSON result_id) from the newest-first list; HOST and ROOT identify the
original management environment. Each saved result contains host_id. show returns the
complete raw JSON, including access/collection evidence and saved data. For a basic
HTML view, add --html NEW_FILE; it writes a new escaped file without launching a viewer.
Use --json with list for agent automation. These commands do not connect, recollect,
change sudo state or infer a latest result from a filename. Missing/invalid results
remain explicit errors. Source-disabled or blocked preflight attempts may have no saved
result; inspect the original --json diagnostic output in that case.

Verification uses synthetic single/batch states, unknown identities, root/user actors,
retention failures, exclusions and unchanged JSON, plus real local saved-result lookup
by host without any Session. No remote recipe execution is needed for this display change.

## Saved-result collection user

Human `recipes results list` tables, redirected list text and list HTML show **user**
in place of identity quality. Use --json or results detail/show to inspect preserved
identity_quality and identity warnings. Existing warning display remains unchanged:
the compact TTY table omits warnings, while redirected text and list HTML retain them.

The result index adds nullable `collection_user`; JSON consumers keep identity_quality
and identity_warnings with their existing meanings. Index detail includes all three.
Explicit raw-result detail/show and saved files are unchanged. Python consumers can
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

## Vertical result details

Use recipes results detail for long result IDs, similar to MySQL's vertical \G view.
Without RESULT_ID, it reads the same newest-first index as results list and accepts
--host, --recipe-id and --status. It prints a numbered record separator and one
field: value line per index field, including the complete result_id and host_id.
It does not load every result's full collection payload into the display.

```sh
python -B tools/opsfeast.py recipes results detail --host HOST --recipe-id inventory-system --root ROOT
python -B tools/opsfeast.py recipes results detail RESULT_ID --root ROOT
```

With RESULT_ID, detail reads one complete raw result. Nested object fields use dotted
names (for example access.actual_identity.username); arrays remain JSON values on a
single line. Null/Boolean values remain explicit and strings retain leading zeroes.
Newlines and terminal controls in keys/values are escaped. No value is truncated or
horizontally combined with other fields. This explicit human view stays vertical for
both terminal and redirected stdout and does not require tabulate. It is not a parser
contract: add --json for the existing index envelope or complete raw-result JSON,
respectively. No new result schema or storage is introduced.

No matches prints No saved results. and returns zero; malformed index files remain
visible as invalid-result records and return one while preserving readable records.
Missing/unsafe result IDs return an error. RESULT_ID cannot be combined with index
filters; --html is rejected (use results list/show --html instead). Existing show JSON is unchanged; list now uses the short IDs described below. Use the original --root or --profile; detail performs no host
connection, sudo, collection, file rewrite or viewer launch. Synthetic tests cover
TTY/pipe/JSON, long names, escaped controls, filters, empty/partial indexes, unsafe IDs,
option errors and operation without table dependencies.

## Short result IDs

Human results list output (terminal, redirected text and HTML rows) uses short IDs,
for example a73c91e2, instead of long storage-relative filenames. Use them directly:

```sh
python -B tools/opsfeast.py recipes results list --host HOST --root ROOT
python -B tools/opsfeast.py recipes results show a73c91e2 --root ROOT
python -B tools/opsfeast.py recipes results detail a73c91e2 --root ROOT
```

The ID above is illustrative; use a displayed value from the same management root.
Full storage-relative result IDs still work, and show JSON remains the unchanged raw
document. detail displays the resolved complete result_id; detail without an ID shows
both result_id and short_id vertically. Index JSON (results version 0.1.0) adds short_id
to records and invalid-file errors while preserving the complete result_id. Use full
result_id in durable automation and --json for machine parsing. Short IDs also work
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

Formatting copies data at the view boundary. --json, raw results show JSON, TUI Original
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

_Last modified: 2026-10-19 16:05:57_
