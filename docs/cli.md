# Ops command-line reference

OpsFeast provides two command-line entrypoints:

- **`tools/opsfeast.py` prepares and diagnoses the host environment.** It inspects recipe metadata and platform coverage, manages profiles, validates host configuration, discovers platform facts, and tests configured login/su/sudo capabilities.
- **`tools/run_recipe.py` executes inventory and compatible Python-session recipes.** Inventory automatically selects each host's platform implementation. General recipes use one execute entrypoint. Both accept typed invocation inputs and save versioned raw results; only inventory has structured retention. See [the general contract](recipe-execution.md).

Platform-specific entrypoints share one result contract. Administrators do not need to maintain a separate recipe selection for every OS. Routine probing, dispatch and collection run as Python code without an LLM in the execution path. Agents can use this reference to choose the right command and explain its actual outcome.

## Conventions and prerequisites

Run examples from the repository checkout. `python` means the interpreter selected for your environment; `-B` avoids writing Python bytecode. Replace synthetic host IDs, account names and `/srv/feasts/main` with your settings. Host/configuration commands read `hosts.yaml` from the chosen management environment; a host ID is a configuration key, not necessarily its hostname.

| Operation | Controller requirements |
| --- | --- |
| Profiles, init, attach, detach, use, check, dump, inspect-recipe | Python 3.11+ and PyYAML; no SSHScript Session |
| Standalone test-connection | Python 3.11+, PyYAML and the supported SSHScript command contract (documented minimum 4.0.1) |
| Host-init, test-host, test-su, test-sudo, test-connection --host-init, run_recipe.py | Python 3.11+, PyYAML and matching SSHScript import/distribution **5.0.0** |

The full environment check expects PyYAML 6.0.3 and SSHScript 5.0.0:

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
| `init [NAME_OR_PATH] [--profile NAME]` | Create a management scaffold, validate it, then register it. Default: feasts/main, profile main. Preserve existing configuration. |
| `attach ROOT [--profile NAME]` | Validate/register an existing directory without creating or changing its scaffold. |
| `profiles` | List registrations, basic directory status and selected default. Missing entries remain registered; no registrations is a normal result. |
| `detach NAME` | Remove one registration while preserving its directory/data. Main is protected; removing the current default validates and switches to main in one registry write. |
| `use [NAME]` | Change the default to a registered environment. Omitted NAME opens an interactive selector; noninteractive use requires a name. |
| `check [ROOT] [--profile NAME]` | Validate YAML, duplicate definitions, connections/users/vars, include/jump cycles, recipe selections and path boundaries. Does not connect or validate complete recipe execution contracts. |
| `inspect-recipe [RECIPE] [--platform OS_NAME ...] [--details | --json]` | Read recipe metadata, declared platform coverage, entrypoint/version status and verification evidence. Omitted RECIPE discovers checkout recipes; repeat --platform for desired OS names. No management profile, SSHScript import or connection. |
| `dump SETTING [ROOT] [--profile NAME]` | Print a dot-separated mapping path from loaded configuration as JSON, including merged hosts. This performs loading checks, not a complete check. List indexes are unsupported. |
| `test-connection HOST [ROOT] [--profile NAME]` | Connect to the host and required hops, then independently run hostname and date. Does not switch accounts or run recipes. |
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
python -B tools/opsfeast.py inspect-recipe inventory/system --platform linux --platform openbsd

# Read full details, or obtain the complete descriptor/report for an agent.
python -B tools/opsfeast.py inspect-recipe inventory/system --details
python -B tools/opsfeast.py inspect-recipe recipes/inventory/system --json
python -B tools/opsfeast.py inspect-recipe ./my-custom-recipe --json
```

Short paths such as `inventory/system` or `recipes/inventory/system` resolve under this checkout's recipes directory. Absolute paths and explicit `./`, `../` or `~` paths use the shell directory/home, **not a management root**. A supplied path selects one recipe directory containing recipe.yaml; omit it for recursive checkout discovery. This command does not use hosts.yaml, the profile registry, host-init caches or SSHScript. Python 3.11+ and PyYAML suffice.

Default human output is a short recipe summary: identity/version, purpose and implemented/declared-tested/planned-only platforms. With --platform, it focuses on the requested OS names: implemented, planned but missing, or not declared supported; relevant entrypoint health, additional match conditions and recorded verification are shown only for those OS names. Inspection errors and unsupported runner IDs remain visible in either view. Use --details for full human-readable metadata, paths, all implementations, dependencies, privileges, side effects, inputs, output contract and verification. --details and --json are mutually exclusive; --details shows the full report even when --platform is supplied. JSON includes the complete `descriptor`, per-entrypoint static checks, `coverage`, `runner_contract`, errors and inspection report version 0.1.0. No report file is saved.

Coverage compares declarations: `not_declared_implemented` lists requested OS names absent from platforms.implemented; `planned_not_implemented` lists pending declared platforms; `implemented_not_declared_tested` lists implementations without a tested-platform declaration. For the current inventory recipe, requesting openbsd exposes that missing declaration, while Linux/FreeBSD remain implemented but lack local/SSH execution evidence. Requested values are exact os_name labels such as linux, freebsd or macos; repeat the option, rather than using commas. A platform gap is informational and does not change the exit code.

Inspection reads YAML and parses Python VERSION literals without importing or executing entrypoints. Missing files, invalid syntax, version mismatches and escaping descriptor/entrypoint symlinks are reported. For inventory-system, it also uses the current runner's descriptor validator; Python-session descriptors are statically validated (entrypoint path, literal VERSION, execute signature and input definitions) and report valid-python-session or invalid-python-session. Other contracts remain unsupported-recipe-id; there is no arbitrary backend loader. One bad discovered recipe does not hide the others; any inspection error returns 1, and a completed inspection returns 0. Command/path errors use stderr; completed reports use stdout, including failed per-recipe reports in JSON mode.

These are declared capabilities and static checks. They do not establish publisher authenticity, installed dependencies, actual host applicability, platform detection or successful execution. Match conditions may restrict OS/distribution/version/architecture even when a platform name is listed. Read recorded verification and review code before authorized execution.

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

Sudo selects the first non-null password in this order: `users.<actor>.vars.sudo.password`, host `vars.sudo.password` (only for the actual connection identity), then `users.<actor>.password`. Explicit overrides take precedence; a failed authentication never triggers retries with lower-priority sources. `--run-as` selects the diagnostic target; `vars.sudo.user` is not used. Standalone test-sudo can attempt passwordless sudo when no sudo password is set. These tests establish authenticated shell/identity access, not permissions for every command. Success does not prove password consumption: policy or authentication cache can avoid a prompt.

To investigate a failed test, add `--debug --traceback`. JSON steps include `password_source` and `password_supplied` when su/sudo credentials are selected; no password value is emitted. A PermissionError during authenticated entry is categorized as `authentication_rejected_or_password_required`: the public SSHScript contract includes explicit rejection, a second password request, or a password request when none was supplied. This category does not identify the exact host-policy cause or prove an incorrect password. Review the failed stage and selected credential source first. Tracebacks contain frames only; exception messages and raw privileged output remain omitted. Progress/debug/traceback output goes to stderr; stdout remains JSON.

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

Test-host always tests login/hostname/date. It then reuses or initializes facts, tests sudo **only for the connection identity and only with a password selected by the precedence rule (including the account password)**, and independently tests su to other accounts declared in users. It does not enumerate accounts, test chains, attempt passwordless sudo or execute recipes.

If connection establishment fails, remaining tests are skipped. Host-init failure does not prevent account diagnostics. One account-test failure does not stop other independent groups. Test-host uses separate connections for the diagnostic phases/groups; it is not one atomic remote transaction.

Its JSON contains host, overall status, and tests keyed by test-connection, host-init, test-sudo and test-su. Inspect their individual status, skipped reason, initialization cache/probe source and original observation time. Overall partial means some tests were skipped, rather than all capabilities having been verified.

## tools/run_recipe.py: inventory execution

This section covers shared selection/execution options for inventory and general Python-session recipes. Use [the general execution/authoring contract](recipe-execution.md) for descriptor 0.3.0, execute, raw results and limits. Inventory-specific platform/retention behavior below applies only to inventory-system.

```text
python -B tools/run_recipe.py RECIPE
    (--host HOST ... | --group GROUP ... | --all [--exclude HOST ...])
    [--root ROOT | --profile NAME] [--timeout SECONDS] [--threads N] [--verbose | --quiet]
    [--vars-file JSON_FILE] [--var NAME=VALUE ...]

python -B tools/run_recipe.py --recipe DIRECTORY
    (--host HOST ... | --group GROUP ... | --all [--exclude HOST ...])
    [--root ROOT | --profile NAME] [--timeout SECONDS] [--threads N] [--verbose | --quiet]
    [--vars-file JSON_FILE] [--var NAME=VALUE ...]
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
python -B tools/run_recipe.py inventory/system --host host-01
python -B tools/run_recipe.py inventory/system --host host-01 host-02 host-03 --root /srv/feasts/main
python -B tools/run_recipe.py inventory/system --group web production --profile inventory
python -B tools/run_recipe.py inventory/system --host smtp-01 --group nginx apache2
python -B tools/run_recipe.py --all --recipe inventory/system
python -B tools/run_recipe.py inventory/system --all --threads 4 --exclude host9 host10
python -B tools/run_recipe.py community:inventory/system --group web
python -B tools/run_recipe.py --host host-01 --recipe ./recipes/custom-system --root /srv/feasts/main
```

Recipe and targets must both be explicit; omission is a usage error (exit 2), never an implicit all-host selection or fallback to hosts.yaml recipe settings. Put the positional recipe first, or use --recipe elsewhere, once only. For example, `--group web production inventory/system` treats all three values as group names and fails because no recipe was specified; it never guesses which value is a recipe. `--all inventory/system` is rejected with a hint to use --recipe. The spelling is `--recipe`.

Use the optional host-level `group: web` string or `group: [web, production]` list in hosts.yaml; see [host groups](hosts-yaml.md#host-groups). Names are exact and case-sensitive, with no comma splitting, glob expansion or host:/group: prefix interpretation. A host and group may share a name: --host web selects only that host, while --group web selects its members.

The runner resolves every selector before any execution. Unknown names, invalid configuration and an empty target set fail without executing any host. Expand repeated --host/--group options in argument order, with group members in merged YAML host order (includes first, then the declaring file). --all uses that merged order. Overlaps and repeated selectors execute each host once, preserving its first occurrence. Groups select a union, not an intersection; they do not inherit variables, connection settings or recipes. All targets use the selected environment and the existing per-host execution contract. Selection support here does not extend diagnostic commands to groups.

The CLI executes the explicitly named compatible inventory-system or Python-session recipe directory; matching host recipe vars apply, while unrelated recipe selectors are bypassed. Host/connection configuration must remain valid. A bad recipe fails without falling back to host selectors. The internal Python run(root, host, recipe=None) helper retains host-selector behavior for existing callers; this is not a CLI default. See [sources, inputs and controls](recipe-sources.md) for shorthand selections, default/source/host/file/CLI var precedence, enabled flags, excluded_hosts and skipped results.

The previous positional HOST/ROOT, --hosts and optional recipe syntax is replaced. Migrate `run_recipe.py host-01 ROOT --recipe inventory/system --hosts host-02` to `run_recipe.py inventory/system --root ROOT --host host-01 host-02`. Existing YAML recipes lists and registrations are preserved; configuration checking still validates those lists.

### Recipe locations and platform selection

`inventory/system` (leading or --recipe) is relative to this checkout's recipes directory, independent of the management root/shell directory. Do not include `recipes/` in that CLI form. Explicit `./recipes/custom-system` is management-root-relative; absolute paths must remain in the repository recipes directory or management root. `:inventory/system` resolves from the selected management root recipes/; `community:inventory/system` uses recipe_sources.community.path registered in entry hosts.yaml. External named sources accept path/vars/enabled and can live outside the management root. Predefined recipe_sources.bundle/profile accept enabled/vars without path (an optional path must resolve exactly to the default root relative to entry hosts.yaml); they control bare checkout and :profile references respectively, including their legacy path forms. Omitted controls default enabled. Missing paths never fall back to another source. YAML selectors still use `recipe: recipes/inventory/system` for checkout recipes. Include files remain management-root-bound.

For each host, execution follows:

1. Resolve environment/recipe, validate host connections and descriptor/entrypoint paths/version literals before connecting.
2. Connect to the target and required hops; reuse or discover platform facts.
3. Match declared implementations against available facts. Failed initialization skips collection; no match is unsupported; equally ranked top matches fail as ambiguous.
4. Load only the selected entrypoint, check its runtime VERSION, collect inventory and validate the seven observation fields/states.
5. Close the owning Session strictly, preserve errors/partial observations, atomically save raw JSON and attempt structured retention.

Allowed match fields are os_name, distribution_id, os_version, distribution_version, kernel_release and architecture. All conditions must match. Explicit priority ranks first, then number of conditions. Missing facts do not satisfy conditions. Version bounds compare dotted numeric components; vendor suffixes use exact conditions such as `=14.2-RELEASE`. File/list order does not break ties, and failed selected code does not trigger another implementation.

Batch hosts run independently in a thread pool, with concurrency set by --threads. The CPU-based default is a starting limit for SSH/command I/O, not a performance benchmark; tune it for the controller and targets. The actual worker count is capped at the selected host count. --threads 1 runs sequentially without a pool. Each worker creates, uses and closes its own Session and hops in that same thread; Sessions are not shared between hosts. Descriptor/implementation loading through runpy is serialized to protect process-wide import state, while collectors execute concurrently. Failed/skipped/unsupported hosts do not prevent other selected hosts from running. Final JSON retains target selection order even when completion order differs; host progress is emitted immediately and whole lines are serialized on stderr. The [index/total] progress prefix identifies selection position, not a completed-host counter. --threads limits active host tasks, not all internal threads or individual hop connections. Custom implementations that mutate shared process state or shared external files must be reviewed for concurrent use; use --threads 1 when that requirement is unknown. Separate invocations against the same management environment are not coordinated by this option. A per-host preflight/save error appears in the batch summary; a result file is not guaranteed for errors before collection or when saving fails.

### Saved results and stdout

Progress is enabled automatically when `sys.stdout.isatty()` is true. It shows target selection, host index/count, connection hops, cached/discovered platform facts, implementation selection, collection, validation, cleanup, and saving. Every five seconds during a waiting stage, a heartbeat reports the current stage and elapsed time in that stage. This is a controller-side waiting indicator, not proof of remote-process health or a whole-run deadline. Messages are flushed immediately to stderr; stdout remains JSON. Redirected/piped stdout disables automatic progress; --verbose enables it explicitly and --quiet disables it in a terminal. The internal Python run helper is quiet unless a reporting context is supplied. Progress omits credentials, raw command output and third-party exception text.

```text
[1/3] "smtp-01": connecting hop 1/1 (per-stage timeout 30s)
[1/3] "smtp-01": still connecting hop 1/1 (per-stage timeout 30s) (5s in this stage)
[1/3] "smtp-01": collecting inventory with "linux"
[1/3] "smtp-01": completed: success (inventory_complete)
```

Each inventory-system run writes a new file without overwriting previous inventories or updating human records:

```text
<management-root>/observations/inventory-system-<uuid>.json
```

The shared result schema is **0.2.0**, independent of host facts schema 0.1.0. Recipe descriptor remains 0.2.0; bundled recipe version is 0.2.2; implementations carry independent versions. Results contain host_id, timestamps, runtime/evidence kind, status/reason/message, observations, command sources, host-init provenance, hop states and execution/cleanup errors. Recipe metadata records recipe_version, implementation_id/version/path when selected, selected-file SHA-256, descriptor SHA-256, Python-bundle SHA-256, resolved location and CLI/hosts selection source. A pre-dispatch skip has no selected implementation version. Source/host-disabled skips do not load a runtime or write an inventory file; they return result_path: null. Completed reports include source_name/source_root/reference and variable_names, without input values.

Seven common observations cover hostname, platform, system name/version, kernel name/release and architecture. Each retains value, state, observed_at, source_ids and error. Missing/failed values remain null with explicit states. A command returning zero does not establish successful parsing or cleanup. Raw inventory command output may appear in private source records.

Single-host stdout is a JSON summary containing status, reason_code, message, detected_kernel, supported_platforms, recipe_id and result_path. Using --all or resolving more than one unique host produces batch stdout: an object with a hosts array; each entry records host/status/reason/result_path, or a sanitized error type when no saved report is available. A selection resolving to one host retains the single-host summary unless --all is used. Nonempty exclusions add excluded_hosts with host_disabled/cli_excluded reasons. Explicit disabled hosts remain skipped results; disabled group/all members are omissions. If filtering removes every target, return 1 with empty hosts plus exclusion evidence and an error on stderr.

See the [inventory guide](../recipes/inventory/system/README.md), [recipe descriptor](../recipes/inventory/system/recipe.yaml), [result schema](../recipes/inventory/system/schema.json) and [synthetic example](../recipes/inventory/system/examples/result.synthetic.json) for authoring and data consumers. Old copied descriptors must be migrated to 0.2.0. Reviewed custom inventory entrypoints and compatible Python-session recipes can execute; there is no arbitrary backend loader, extension-overlay installer or execution sandbox. General recipes return data in stdout summaries and save observations/recipe-run-<UUID>.json with skipped no_retention_adapter; read [general result semantics](recipe-execution.md#results-failure-states-and-storage).

## Exit codes, output and side effects

Su/sudo JSON includes per-step `identity_verification` (expected/actual username and effective UID, matched/status/message) and per-group `parent_identity_verification` for return to the original connection identity. See [identity evidence](host-diagnostics.md#read-the-identity-evidence) for failed/incomplete/not-run states and separate prerequisite su evidence. --verbose/--debug adds readable successful identity/restoration explanations on stderr; stdout remains JSON.

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

Profiles/init/attach/detach/use/check print human-readable text. Dump and host diagnostics print JSON. Recipe execution prints summary JSON and saves full reports; inventory additionally saves eligible retained observations. Python-session results include data and explicit skipped no_retention_adapter. Diagnostic progress/errors go to stderr where supported; preflight errors may produce no JSON report. Init writes the scaffold/registry; attach/detach/use write the registry. Host-init writes facts; test-host and inventory can initialize facts; inventory writes new results and retained data. Standalone test-connection/su/sudo do not automatically save their reports. Redirect stdout if you need to retain a diagnostic report.

Setup/checks do not authorize connections, proxy commands, account switches or recipes. Explicit diagnostics may create authentication/audit records and execute login-shell startup; configured proxies can execute locally. The built-in inventory performs read-only queries; missing identity probes may use supplied explicit sudo capability or identity_sudo true. It does not su to alternate actors. Custom recipe code must be reviewed within its execution scope; path/version/digest checks do not authenticate a publisher or confine code. Channel closure is not proof of remote-process termination.

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

Host identity refers to an OS installation. Linux uses a hashed machine-id candidate with clone/reinstall caveats. FreeBSD/macOS/ESXi lack a verified installation identifier in this implementation and use source UUID plus local host_id fallback, even with valid hardware serials. Fallback emits a warning with remediation and does not establish replacement detection or cross-source equality. Sudo credential selection and identity_sudo controls are documented in the canonical workflow. Unknown cleanup fails collection; no historical keys are automatically reassigned. No receiver database importer, automatic latest-state/conflict resolver, transmission or cleanup tool is implemented.

Host identity_key, label and description are now supported. An explicit identity_key takes precedence and is shared across Feasts as user-assigned identity; change it after OS reinstall/replacement and coordinate its namespace. label/description are captured human text, never identity keys, and are preserved through retention/exchange. See [the canonical host configuration](../docs/hosts-yaml.md#explicit-host-identity-and-human-readable-metadata) and [identity/metadata rules](../docs/result-data.md#explicit-identity-and-display-metadata). MAC is not an automatic key.

_Last modified: 2026-10-13_
