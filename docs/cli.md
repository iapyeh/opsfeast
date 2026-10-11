# Ops command-line reference

SSHScript Ops provides two command-line entrypoints:

- **`tools/ops.py` prepares and diagnoses the host environment.** It inspects recipe metadata and platform coverage, manages profiles, validates host configuration, discovers platform facts, and tests configured login/su/sudo capabilities.
- **`tools/run_recipe.py` collects system inventory.** Select one recipe for a mixed Linux, FreeBSD and macOS fleet; the runner selects each host's implementation automatically and saves results with version and source evidence.

Platform-specific entrypoints share one result contract. Administrators do not need to maintain a separate recipe selection for every OS. Routine probing, dispatch and collection run as Python code without an LLM in the execution path. Agents can use this reference to choose the right command and explain its actual outcome.

## Conventions and prerequisites

Run examples from the repository checkout. `python` means the interpreter selected for your environment; `-B` avoids writing Python bytecode. Replace synthetic host IDs, account names and `/srv/my-ops` with your settings. Host/configuration commands read `hosts.yaml` from the chosen management environment; a host ID is a configuration key, not necessarily its hostname.

| Operation | Controller requirements |
| --- | --- |
| Profiles, init, add, use, check, dump, inspect-recipe | Python 3.11+ and PyYAML; no SSHScript Session |
| Standalone test-connection | Python 3.11+, PyYAML and the supported SSHScript command contract (documented minimum 4.0.1) |
| Host-init, test-host, test-su, test-sudo, test-connection --host-init, inventory | Python 3.11+, PyYAML and matching SSHScript import/distribution **5.0.0** |

The full environment check expects PyYAML 6.0.3 and SSHScript 5.0.0:

```sh
python -B tools/check_environment.py
python -B tools/check_environment.py --scope init
python -B tools/ops.py --help
python -B tools/run_recipe.py --help
```

Environment checks only report readiness. Tools do not automatically create Python environments, install dependencies, upgrade SSHScript or download skills. See [getting started](getting-started.md) for setup and [host configuration](hosts-yaml.md) for connection/key/jump-host rules.

## Choose the management environment

For most commands, omit the location to use the selected default profile in the checkout's `.my-ops.yaml`, or pass `--profile NAME` for one invocation. This does not change the default. An explicit management root and `--profile` cannot be combined for execution/configuration commands. Missing or invalid profiles fail without searching other environments.

The CLI has two forms for an explicit root:

| Entrypoint/subcommands | Root argument |
| --- | --- |
| ops.py check, dump, test-connection | Optional positional `ROOT` |
| ops.py host-init, test-host, test-su, test-sudo | Optional `--root ROOT` |
| run_recipe.py | Optional positional `ROOT` |
| ops.py init | Optional name or path; `--profile` names the registration |
| ops.py add | Required existing directory; `--profile` names the registration |

Explicit relative directory paths use the current shell directory; registered relative locations use the checkout. `init inventory` is a name under the checkout's `my-ops/`; `init ./inventory` is a path under the shell directory. See [profiles](profiles.md) for registration conflicts, legacy directories and locator migration.

## tools/ops.py: command reference

Run `python -B tools/ops.py COMMAND --help` for that command's parser help. Brackets below mean optional arguments; usernames use spaces, not commas.

| Command syntax after tools/ops.py | Purpose and behavior |
| --- | --- |
| `init [NAME_OR_PATH] [--profile NAME]` | Create a management scaffold, validate it, then register it. Default: my-ops/main, profile main. Preserve existing configuration. |
| `add ROOT [--profile NAME]` | Validate/register an existing directory without creating or changing its scaffold. |
| `profiles` | List registrations and show the selected default. No registrations is a normal result. |
| `use [NAME]` | Change the default to a registered environment. Omitted NAME opens an interactive selector; noninteractive use requires a name. |
| `check [ROOT] [--profile NAME]` | Validate YAML, duplicate definitions, connections/users/vars, include/jump cycles, recipe selections and path boundaries. Does not connect or validate complete recipe execution contracts. |
| `inspect-recipe [RECIPE] [--platform OS_NAME ...] [--json]` | Read recipe metadata, declared platform coverage, entrypoint/version status and verification evidence. Omitted RECIPE discovers checkout recipes; repeat --platform for desired OS names. No management profile, SSHScript import or connection. |
| `dump SETTING [ROOT] [--profile NAME]` | Print a dot-separated mapping path from loaded configuration as JSON, including merged hosts. This performs loading checks, not a complete check. List indexes are unsupported. |
| `test-connection HOST [ROOT] [--profile NAME]` | Connect to the host and required hops, then independently run hostname and date. Does not switch accounts or run recipes. |
| `host-init HOST [--root ROOT] [--profile NAME]` | Connect and freshly discover platform facts, updating saved initialization data on every explicit invocation. |
| `test-host HOST [--root ROOT] [--profile NAME]` | Test login, reuse or initialize facts, then test the configured account capabilities described below. |
| `test-sudo HOST [USER ...] [--run-as TARGET] [--root ROOT] [--profile NAME]` | Independently test each sudo actor; omitted USER means the actual connection identity. Default TARGET: root. |
| `test-su HOST USER ... [--root ROOT] [--profile NAME]` | Independently test connection-user → each target. At least one target is required. |
| `test-su HOST --chain USER ... [--chain USER ...] [--root ROOT] [--profile NAME]` | Test each ordered chain from a fresh connection identity. Repeat --chain for separate chains. |

Profile/configuration commands and inspect-recipe do not connect or execute recipes. Init/add preserve an existing default; the first successful registration becomes the default. Use changes only the selected profile. In interactive registration, a conflicting name may prompt for another name; noninteractive conflicts fail without waiting. Init failure may leave newly created scaffold files for correction, but does not register a failed setup.

### Inspect recipes and platform gaps

```sh
# Discover every recipe.yaml under this checkout's recipes directory.
python -B tools/ops.py inspect-recipe

# Inspect a recipe and compare desired OS names against its declarations.
python -B tools/ops.py inspect-recipe inventory/system --platform linux --platform openbsd

# Obtain the complete descriptor and inspection report for an agent.
python -B tools/ops.py inspect-recipe recipes/inventory/system --json
python -B tools/ops.py inspect-recipe ./my-custom-recipe --json
```

Short paths such as `inventory/system` or `recipes/inventory/system` resolve under this checkout's recipes directory. Absolute paths and explicit `./`, `../` or `~` paths use the shell directory/home, **not a management root**. A supplied path selects one recipe directory containing recipe.yaml; omit it for recursive checkout discovery. This command does not use hosts.yaml, the profile registry, host-init caches or SSHScript. Python 3.11+ and PyYAML suffice.

Human output shows description, planned/implemented/tested platforms, implementation IDs/versions/entrypoints, all match conditions (including OS/distribution versions), priority, dependencies, privileges, side effects, inputs, output contract and recorded verification. JSON includes the complete `descriptor`, per-entrypoint static checks, `coverage`, `runner_contract`, errors and inspection report version 0.1.0. No report file is saved.

Coverage compares declarations: `not_declared_implemented` lists requested OS names absent from platforms.implemented; `planned_not_implemented` lists pending declared platforms; `implemented_not_declared_tested` lists implementations without a tested-platform declaration. For the current inventory recipe, requesting openbsd exposes that missing declaration, while Linux/FreeBSD remain implemented but lack local/SSH execution evidence. Requested values are exact os_name labels such as linux, freebsd or macos; repeat the option, rather than using commas. A platform gap is informational and does not change the exit code.

Inspection reads YAML and parses Python VERSION literals without importing or executing entrypoints. Missing files, invalid syntax, version mismatches and escaping descriptor/entrypoint symlinks are reported. For inventory-system, it also uses the current runner's descriptor validator; other recipe IDs are inspectable but report `unsupported-recipe-id`, since no general runner or descriptor schema exists. One bad discovered recipe does not hide the others; any inspection error returns 1, and a completed inspection returns 0. Command/path errors use stderr; completed reports use stdout, including failed per-recipe reports in JSON mode.

These are declared capabilities and static checks. They do not establish publisher authenticity, installed dependencies, actual host applicability, platform detection or successful execution. Match conditions may restrict OS/distribution/version/architecture even when a platform name is listed. Read recorded verification and review code before authorized execution.

### Connection diagnostics and options

All host-test/init commands accept `--timeout SECONDS`, default 30, a positive finite number. It bounds connection stages/commands and authenticated entry/exit where applicable, **not the complete run**. SSHScript base-shell/capability setup and recovery have separate contract limits.

Only test-connection additionally accepts:

| Option | Behavior |
| --- | --- |
| `-v`, `--verbose` | Progress on stderr. |
| `--debug` | Safe effective connection details on stderr, implying verbose; does not enable SSHScript's raw DEBUG log. |
| `--traceback` | Exception frames without source text, locals or exception messages. |
| `--host-init` | Also perform a fresh host-init after connecting; currently uses a separate connection. |

Test-connection JSON includes host, connected, hops, commands and success. Each hop records its connection result; key_source identifies where identity_file is read. Commands retain stdout/stderr/exitcode or error. Success requires both commands and strict cleanup to succeed; connected alone is insufficient. With --host-init, initialization must also succeed.

```sh
python -B tools/ops.py init inventory
python -B tools/ops.py check --profile inventory
python -B tools/ops.py dump hosts.host-01.connection --profile inventory
python -B tools/ops.py test-connection host-01 --profile inventory --debug
python -B tools/ops.py test-connection host-01 /srv/my-ops --host-init
```

Dump emits selected values unchanged, including passwords if the selected mapping contains them. Keep real configuration, command output and saved reports in your management environment.

### Host-init: fresh observations and reusable facts

Host-init queries uname for OS/kernel/architecture. Linux distribution information comes from os-release; FreeBSD userland version and macOS product version are separate from kernel release. Missing fields retain their state; sufficient OS evidence can still permit a generic implementation.

```sh
python -B tools/ops.py host-init host-01 --profile inventory
python -B tools/ops.py host-init host-01 --root /srv/my-ops
```

Facts include os_name, kernel_name, kernel_release, architecture and available OS/distribution names/versions. The JSON includes schema/probe version **0.1.0**, host_id, status, reason_code, observed_at, facts, per-field states, command sources and target_fingerprint. Explicit initialization also returns result_path. The file is atomically replaced at:

```text
<management-root>/observations/host-init/<sha256-of-host-id>.json
```

Test-host and the runner reuse successful facts with the expected schema, matching host/target fingerprint and observation timestamp. Missing, malformed, failed or target-mismatched facts require a new probe. The runner also reprobes once if cached facts cannot select an implementation. Direct host-init and test-connection --host-init always refresh. A failed explicit refresh retains previous_success as historical evidence, but the latest failure prevents cache reuse. Cleanup failure makes fresh initialization fail.

There is no age expiry. Changes to an external SSH config or an OS reinstallation at the same endpoint are not detected by the configuration fingerprint; explicitly refresh after known changes. Cached observations keep their original timestamp and never become a fresh measurement merely by reuse.

### Sudo: actor versus target

```sh
python -B tools/ops.py test-sudo host-01 --profile inventory
python -B tools/ops.py test-sudo host-01 user2 user3 --run-as service-user --profile inventory
```

USER is the account **executing sudo**. TARGET is the identity sudo should enter. Other actors first require verified su entry from the connection account. Results identify whether failure happened at su entry/identity or sudo entry/identity. Independent actors use fresh connections.

Sudo uses `users.<actor>.vars.sudo.password`; host `vars.sudo.password` is fallback only for the actual connection identity. It never implicitly borrows users.<actor>.password. `--run-as` selects the diagnostic target; `vars.sudo.user` is not used. Standalone test-sudo can attempt passwordless sudo when no sudo password is set. These tests establish authenticated shell/identity access, not permissions for every command. Success does not prove password consumption: policy or authentication cache can avoid a prompt.

### Su: independent targets and ordered chains

```sh
python -B tools/ops.py test-su host-01 user2 user3 --profile inventory
python -B tools/ops.py test-su host-01 --chain user2 user3 --chain user3 user2 --profile inventory
```

The first command tests connection-user → user2 and connection-user → user3. The second tests two independent chains:

```text
connection-user → user2 → user3
connection-user → user3 → user2
```

Each --chain group starts a fresh connection. A failed/skipped prerequisite prevents remaining steps in that chain, while other groups continue. Independent lists and chain groups cannot be mixed. The connection account cannot be a target; independent duplicates and adjacent chain duplicates are rejected, while nonadjacent chain repeats are allowed.

Su uses each target's `users.<target>.password`. Missing required credentials produce skipped tests; passwordless su is not probed. Identity queries verify effective UID against the requested account. Context exit and strict Session cleanup are checked separately. Bash and id are required by the SSHScript authenticated-console contract. Ops does not prompt interactively for passwords.

Privilege-test JSON includes host, test, status, connection_user when identified, and groups. Each group contains its accounts, chain/independent mode, steps and status. Steps retain from_user, to_user, operation, verified identity or skipped reason/failure stage. Errors omit credential-bearing exception text and raw privileged output.

### Test-host: one configured-host check

```sh
python -B tools/ops.py test-host host-01 --profile inventory
```

Test-host always tests login/hostname/date. It then reuses or initializes facts, tests sudo **only for the connection identity and only with an explicit sudo password**, and independently tests su to other accounts declared in users. It does not enumerate accounts, test chains, attempt passwordless sudo or execute recipes.

If connection establishment fails, remaining tests are skipped. Host-init failure does not prevent account diagnostics. One account-test failure does not stop other independent groups. Test-host uses separate connections for the diagnostic phases/groups; it is not one atomic remote transaction.

Its JSON contains host, overall status, and tests keyed by test-connection, host-init, test-sudo and test-su. Inspect their individual status, skipped reason, initialization cache/probe source and original observation time. Overall partial means some tests were skipped, rather than all capabilities having been verified.

## tools/run_recipe.py: inventory execution

```text
python -B tools/run_recipe.py HOST [ROOT]
    [--profile NAME] [--recipe DIRECTORY]
    [--hosts HOST ...] [--timeout SECONDS]
```

| Argument/option | Behavior |
| --- | --- |
| HOST | First host ID; required. |
| ROOT | Optional positional management directory; otherwise use profile/default. |
| --profile NAME | Select an environment for this invocation; cannot combine with ROOT. |
| --recipe DIRECTORY | Override this host's recipe selectors with one inventory-system directory. |
| --hosts HOST ... | Additional host IDs; duplicate IDs execute once, preserving first occurrence. |
| --timeout SECONDS | Positive finite per-stage/command budget, default 30; not a whole-run deadline. |

```sh
python -B tools/run_recipe.py host-01 --recipe inventory/system
python -B tools/run_recipe.py host-01 /srv/my-ops --recipe inventory/system --hosts host-02 host-03
python -B tools/run_recipe.py host-01 --profile inventory
python -B tools/run_recipe.py host-01 /srv/my-ops --recipe ./recipes/custom-system
```

Without --recipe, exactly one selected inventory-system recipe is required for the host. Other selected recipe IDs are not executed. With --recipe, host recipe selectors are bypassed; host/connection configuration still must be valid. A bad override fails without falling back to host selectors.

### Recipe locations and platform selection

`--recipe inventory/system` is relative to this checkout's recipes directory, independent of the management root/shell directory. Do not include `recipes/` in that CLI form. Explicit `./recipes/custom-system` is management-root-relative; absolute paths must remain in the repository recipes directory or management root. Missing checkout paths do not fall back to instance copies. YAML selectors still use `recipe: recipes/inventory/system` for checkout recipes. Include files remain management-root-bound.

For each host, execution follows:

1. Resolve environment/recipe, validate host connections and descriptor/entrypoint paths/version literals before connecting.
2. Connect to the target and required hops; reuse or discover platform facts.
3. Match declared implementations against available facts. Failed initialization skips collection; no match is unsupported; equally ranked top matches fail as ambiguous.
4. Load only the selected entrypoint, check its runtime VERSION, collect inventory and validate the seven observation fields/states.
5. Close the owning Session strictly, preserve errors/partial observations and save a new result.

Allowed match fields are os_name, distribution_id, os_version, distribution_version, kernel_release and architecture. All conditions must match. Explicit priority ranks first, then number of conditions. Missing facts do not satisfy conditions. Version bounds compare dotted numeric components; vendor suffixes use exact conditions such as `=14.2-RELEASE`. File/list order does not break ties, and failed selected code does not trigger another implementation.

Batch hosts run sequentially and independently. Failed/skipped/unsupported hosts do not stop later hosts. A per-host preflight/save error appears in the batch summary; a result file is not guaranteed for errors before collection or when saving fails.

### Saved results and stdout

Each run writes a new file without overwriting previous inventories or updating human records:

```text
<management-root>/observations/inventory-system-<uuid>.json
```

The shared result schema is **0.2.0**, independent of host facts schema 0.1.0. Recipe descriptor/version is currently 0.2.0; implementations carry independent versions. Results contain host_id, timestamps, runtime/evidence kind, status/reason/message, observations, command sources, host-init provenance, hop states and execution/cleanup errors. Recipe metadata records recipe_version, implementation_id/version/path when selected, selected-file SHA-256, Python-bundle SHA-256, resolved location and CLI/hosts selection source. A pre-dispatch skip has no selected implementation version.

Seven common observations cover hostname, platform, system name/version, kernel name/release and architecture. Each retains value, state, observed_at, source_ids and error. Missing/failed values remain null with explicit states. A command returning zero does not establish successful parsing or cleanup. Raw inventory command output may appear in private source records.

Single-host stdout is a JSON summary containing status, reason_code, message, detected_kernel, supported_platforms, recipe_id and result_path. Batch stdout is an object with a hosts array; each entry records host/status/reason/result_path, or a sanitized error type when no saved report is available.

See the [inventory guide](../recipes/inventory/system/README.md), [recipe descriptor](../recipes/inventory/system/recipe.yaml), [result schema](../recipes/inventory/system/schema.json) and [synthetic example](../recipes/inventory/system/examples/result.synthetic.json) for authoring and data consumers. Old copied descriptors must be migrated to 0.2.0. Reviewed custom inventory entrypoints can execute; there is no arbitrary-recipe runner, extension-overlay installer or execution sandbox.

## Exit codes, output and side effects

| Command/result | Exit code |
| --- | --- |
| Successful local profile/configuration operation | 0 |
| Interactive use cancellation; profiles with no registrations | 0 |
| Successful connection test, including initialization if requested | 0 |
| Host-init success | 0 |
| Su/sudo/test-host success, partial or skipped | 0; inspect JSON for skipped tests |
| Inventory: every selected host fully successful | 0 |
| Actual diagnostic failure; inventory partial/unsupported/skipped/failed; configuration/save error | 1 |
| Invalid CLI syntax/options rejected by argparse | 2 |

Profiles/init/add/use/check print human-readable text. Dump and host diagnostics print JSON. Inventory prints summary JSON and saves full reports. Diagnostic progress/errors go to stderr where supported; preflight errors may produce no JSON report. Init writes the scaffold/registry; add/use write the registry. Host-init writes facts; test-host and inventory can initialize facts; inventory writes new results. Standalone test-connection/su/sudo do not automatically save their reports. Redirect stdout if you need to retain a diagnostic report.

Setup/checks do not authorize connections, proxy commands, account switches or recipes. Explicit diagnostics may create authentication/audit records and execute login-shell startup; configured proxies can execute locally. The built-in inventory performs read-only queries without su/sudo. Custom recipe code must be reviewed within its execution scope; path/version/digest checks do not authenticate a publisher or confine code. Channel closure is not proof of remote-process termination.

## Human and agent workflow

Prepare/register an environment, edit hosts.yaml, and run check. For an authorized readiness check, use test-host and interpret every test state. Explicitly refresh host-init after known OS/endpoint changes. For authorized inventory, select the same recipe for the fleet and read each host's result, selected implementation/version and partial/error evidence. Keep configuration, credentials, observations and human notes in the management environment.

Agents should use --profile or an explicit root for unattended work, explicit profile names instead of interactive use, and the user's chosen interpreter. Read the [hosts skill](../skills/sshscript-ops-hosts/SKILL.md) for diagnostics and the [recipes skill](../skills/sshscript-ops-recipes/SKILL.md) for inventory. Reuse existing authorization and context; ask only for missing information that affects correctness or scope.

Synthetic tests cover configuration, dispatch, cache, account transitions, batch continuation and failure/cleanup handling. macOS local read-only initialization/inventory has been verified. Real Linux/FreeBSD collection, SSH and native su/sudo remain unverified; compatible metadata and synthetic success do not establish those outcomes.

_Last modified: 2026-10-11_
