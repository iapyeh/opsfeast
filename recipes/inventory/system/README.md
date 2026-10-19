# inventory-system

Downstream handlers/converters declare their own [consumer subscriptions](../../../docs/retention-consumers.md). Discover associated programs with `opsfeast.py recipes show inventory/system --profile NAME --json` or `consumers list --recipe inventory/system`. The bundled reference is inventory/system and its retention contract/version is inventory-observations 0.1.0. Registered external clones retain their exact source-qualified references. This recipe does not maintain a subscriber list or invoke consumers; the shared retention transaction creates events and the dispatcher notifies enabled consumers.

Recipe version 0.3.1 provides Linux, FreeBSD, macOS and ESXi implementations under one recipe ID, using descriptor 0.2.0 and a shared result schema 0.2.0 in [schema.json](schema.json). Platform selection is automatic; users select the recipe directory, not a Python file. Linux/FreeBSD/ESXi have synthetic verification only. macOS has synthetic and local read-only verification. Real SSH and native FreeBSD/Linux collection remain unverified.

For complete tool syntax, defaults, behavior, output and exit codes, see the [CLI reference](../../../docs/cli.md). It covers both tools/opsfeast.py and tools/run_recipe.py for administrators and agents.

## Implementation choice

This recipe uses Python and SSHScript ==5.0.0 to collect host commands through the runner's local or SSH Session. SSHScript fits the command-oriented inventory task and reuses the configured connection and jump-host workflow. Platform implementations share the same Session interface and result contract; platform-specific parsing and report construction remain ordinary Python.

The [runner](../../../tools/run_recipe.py) creates the Session, connects through the configured hops when needed, passes it to the selected collector and requests strict cleanup. The shared [command probe](main.py) uses `session.exec_command` with a command timeout and records command output and failure states; the [macOS collector](implementations/macos.py) demonstrates platform-specific commands using that probe. This is a practical example of Session-based collection and bounded command execution, not a demonstration of su/sudo or interactive consoles.

The [verification section](#results-and-verification) distinguishes synthetic tests and local macOS execution from unverified real SSH and native Linux/FreeBSD collection. Connection and cleanup code alone does not establish remote validation or prove remote-process termination. See the [tool selection workflow](../../../docs/recipe-authoring.md#choose-execution-tools) for other recipes; this runner still requires its documented SSHScript interface.

## Collection contract

| Field | Linux | FreeBSD | macOS |
| --- | --- | --- | --- |
| hostname | uname -n | uname -n | uname -n |
| platform | linux | freebsd | macos |
| system_name | os-release NAME | FreeBSD | sw_vers -productName |
| system_version | os-release VERSION_ID | freebsd-version -u (userland) | sw_vers -productVersion |
| kernel_name | uname -s | uname -s | uname -s |
| kernel_release | uname -r | uname -r | uname -r |
| architecture | uname -m | uname -m | uname -m |

Linux reads `/etc/os-release`, falling back to `/usr/lib/os-release` only when the first file is absent. It never executes file contents, merges files or substitutes kernel version for missing distribution version. Missing, denied, failed, truncated and unparseable values retain their own states. Observations describe the environment visible to the login account, including a container/jail, not necessarily physical hardware.

No installation or target configuration changes are performed. The runner prefers verified root through at most two accounts: login and the first other sudo-enabled users entry in YAML order. An eligible root second candidate gets su priority; otherwise login sudo is tried first, then second-account su/sudo. If neither route works safely, collect as login with explicit fallback evidence. Account sudo: false disables only that account's sudo and excludes it as a second candidate. Read the [canonical access policy, credential-presence rules, dryrun/force, field catalog and CSV guide](../../../docs/inventory-access.md) before execution. This includes real connections and possible su/sudo attempts. Controller requirements remain Python 3.11+, PyYAML and matching SSHScript import/distribution 5.0.0; SSH trust and jump settings are preserved.

## Execute

```sh
python -B tools/run_recipe.py inventory/system --host host-01
python -B tools/run_recipe.py inventory/system --host host-01 host-02 host-03 --root /srv/feasts/main
python -B tools/run_recipe.py inventory/system --group web production --profile inventory
python -B tools/run_recipe.py inventory/system --host smtp-01 --group nginx apache2
python -B tools/run_recipe.py --all --recipe inventory/system
```

Recipe and targets are required. Put the positional recipe first, or use --recipe DIRECTORY at any option position; using both is an error. --host selects exact host IDs and --group selects exact group names, with multiple/repeated values supported. Combine them for a union; duplicate hosts execute once. --all selects every enabled host (including local/jump/ungrouped hosts) and cannot be combined with either option. No target-kind guessing or recipe fallback is performed.

Each host has independent initialization, selection, cleanup and result files; a failure/skip does not stop other hosts. Batch execution uses a bounded thread pool: --threads N sets concurrent hosts, default min(8, local logical CPU count), fallback 1 and capped by the host count. --threads 1 runs sequentially. Each host creates, uses and closes its own Session in its worker; implementation loading is serialized, but collection runs concurrently. Final JSON keeps selection order; progress follows actual worker activity. Review custom implementations for shared state/file writes before parallel use. Aggregate exit code is zero only when all inventories succeed. Unknown targets fail before execution. One resolved host uses the single-host summary; multiple hosts or --all use the batch summary.

When stdout is a terminal, the runner automatically displays host/stage progress on stderr and a waiting heartbeat every five seconds. Use --verbose for progress when saving/piping stdout JSON, or --quiet to suppress progress. The waiting indicator does not establish remote health or completion; see [progress and output](../../../docs/cli.md#saved-results-and-stdout).

Use --root for the management directory or --profile for a registered environment; they are mutually exclusive. Without either, use the default profile. A bare recipe path such as inventory/system selects this checkout's recipes/inventory/system; the CLI rejects the recipes/ prefix. Explicit ./recipes/custom-system selects a directory relative to the management root. YAML recipe: recipes/inventory/system still selects the checkout, even from include files. Use :inventory/system for profile recipes/ or community:inventory/system for a registered source. Source/host enabled flags and --all --exclude control execution; see [sources and inputs](../../../docs/recipe-sources.md). Missing content never falls back to another source. Paths cannot escape their repository/management boundaries.

The CLI uses matching host recipe vars and bypasses unrelated selectors while validating host/connection configuration. Existing YAML selections remain usable by configuration checks and internal Python callers; other recipe IDs and general third-party interfaces remain unsupported. Migrate the former positional host/root and --hosts syntax using the [CLI reference](../../../docs/cli.md#toolsrun_recipepy-inventory-execution).

## Recipe variables

Bundled recipe 0.3.1 (descriptor/result schema 0.2.0) supports inputs.variables.command_timeout_seconds: a finite number greater than zero. Defaults come from the recipe declarations, then source vars, then the first matching host selector vars; first-level replacement and deep-copy isolation are used. This variable changes collection command budgets, while --timeout still controls connection/discovery. Each collector accepts a context keyword exposing host_id and vars; pass it explicitly to helpers. Legacy collectors without context work only when no effective vars are supplied. See the [input contract](../../../docs/recipe-sources.md#variables-and-implementation-context) for declared types, validation, defaults and secret-handling limits.

Source/host-disabled skips happen before runtime/connection and have result_path null. They are not fabricated inventory files and return nonzero. Completed results record source provenance and variable names without values. Prior macOS local evidence belongs to recipe 0.2.0; the current input/context changes have synthetic coverage, without new native SSH evidence.

## Host initialization and selection

The runner reuses successful, target-matching host facts from the management environment. Otherwise it performs the same read-only probe as `opsfeast.py host-init`; cached facts that cannot select an implementation also trigger one fresh probe. A failed probe skips recipe execution and saves the reason. Unknown platforms produce unsupported. Missing distribution/version can still select a generic OS implementation.

See [host diagnostics](../../../docs/host-diagnostics.md) for refresh semantics, cache storage, limitations and su/sudo tests. Direct `host-init` always refreshes; `test-host` only fills missing/failed/invalid initialization. The original facts timestamp and cache/probe source remain in results.

Implementations are declared explicitly in `recipe.yaml`:

```yaml
implementations:
  - id: linux
    version: 0.1.2
    entrypoint: implementations/linux.py
    match: {os_name: linux}
  - id: ubuntu-24
    version: 0.1.1
    entrypoint: implementations/ubuntu_24.py
    match:
      os_name: linux
      distribution_id: ubuntu
      distribution_version: ">=24.04,<25.04"
```

The second entry is an authoring example, not a supplied Ubuntu-specific implementation. Allowed match fields are `os_name`, `distribution_id`, `os_version`, `distribution_version`, `kernel_release` and `architecture`. Conditions are ANDed. Non-version fields compare exact strings. OS/distribution IDs use lower-case names; architecture remains the raw uname value. Version conditions use dotted numeric comparisons with comma-separated bounds; trailing zeros compare equally. Vendor-suffixed releases require exact matching such as `=14.2-RELEASE`; they are not silently coerced into numeric versions.

Matches rank by explicit integer `priority` (default 0), then number of conditions (more specific first). Equal top ranks are ambiguous and fail; file/list order never breaks ties. A selected implementation's runtime failure does not trigger another implementation.

## Authoring and execution boundaries

Each implementation is a recipe-relative `.py` file declaring one literal `VERSION` string matching its descriptor version, plus:

```python
def collect(session, report, timeout, facts, *, context=None):
    # Populate compatibility observations, sources and execution_errors.
    # The runner supplies the verified collection actor.
    ...
```

All implementations share the inventory input/output contract. Bundles declaring output.inventory_contract_version 0.1.0 must include details.py with collect/validate and the fixed six-section contract; the runner uses that reviewed helper under the same actor. New optional details use a separate shared budget and never turn unsupported optional fields into core failures. `main.py` contains existing report/parser helpers and legacy Linux collection; it is not the runner-selected entrypoint. The new `implementations/*.py` files provide separate platform entrypoints. The runner validates manifest paths/version literals before connecting, loads only the selected entrypoint, checks its runtime version, and validates observation shape and states. It does not execute unselected implementation modules.

Custom inventory bundles are now executable through this contract; they no longer need identical bytes to the built-in bundle. Review the complete code/dependencies before authorizing execution. Manifest checks are not an execution sandbox, authenticity verification or permission grant. General recipe execution and explicit-file packaging are implemented through their own contracts; extension-overlay installation and automatic third-party installation remain unimplemented. Independent platform files reduce shared-code conflicts; contributors may still need to reconcile recipe.yaml/schema changes when updating Git.

For complete synthetic extension examples, read [partitioned raw result](examples/result.partitioned.synthetic.json) and [partitioned exchange](examples/exchange.partitioned.synthetic.json). The original fixtures remain legacy compatibility examples.

## Results and verification

Every run saves a new `observations/<YYYYMMDDTHHMMSSZ>-inventory-system-<uuid>.json`; prior results and human records are preserved. Reports include recipe version, implementation ID/version/path, selected-file SHA-256, complete Python-bundle SHA-256, runtime versions, host-init facts/provenance, observations, command sources and execution/cleanup errors. The bundle digest covers all `.py` files in sorted relative-path order, including shared helpers. It is provenance, not publisher authentication.

Filename prefixes use started_at in UTC at whole-second precision; JSON times keep their original precision. Existing unprefixed files remain readable. See [raw filenames and result lookup](../../../docs/cli.md#saved-results-and-stdout) for sorting, same-second ties and old/new compatibility.

Schema version and recipe/implementation versions are independent. Result schema 0.2.0 adds host-init provenance, implementation versions and skipped runs; migrate old copied descriptors to 0.2.0 before using this runner. A pre-dispatch skip has no selected implementation version. Source/schema versions and missing/error states are preserved; raw collector output may be present in inventory sources and must remain in the private management environment. The runner enforces observation shape without requiring a JSON Schema library; the JSON Schema is available to downstream consumers.

Single-host stdout summarizes status/reason/message/kernel/platforms/result path. Batch stdout summarizes each host. Success returns 0; partial, unsupported, skipped, failed and configuration/save errors return 1. A successful command is not sufficient if parsing or strict Session cleanup fails. `--timeout` bounds connection stages and each command, not the entire run; channel closure is not proof of remote termination.

Synthetic tests cover parsers, three platform collectors, specialization/ambiguity, version/paths, cache failure, selected-code failure without fallback, batch continuation, cleanup and preservation. Local macOS read-only initialization/inventory and the SSHScript credential-free command example are checked separately. Real Linux/FreeBSD, SSH/jump-host and native su/sudo remain unverified.

SSHScript source: bundled public documentation contract 5.0.0 and SOURCE.json bundle SHA-256 `e065bec4e7bd48791563412c5ca3bdaac5f46c5e09456ba5d24665a01ba79b4b`; public [API guide](https://iapyeh.github.io/sshscript/v3a/recommended-api/). FreeBSD userland semantics follow the [FreeBSD manual](https://man.freebsd.org/cgi/man.cgi?query=freebsd-version&sektion=1), consulted 2026-10-11. No private SSHScript source was used.

## Recipe-owned retention contract

This recipe defines and produces `inventory-observations` **0.1.0**. Its [retention.schema.json](retention.schema.json) owns the retained payload, field meanings, units, nullable nested inventory sections and interpretation limits. Its [retention.py](retention.py) owns allowlisted normalization and semantic validation. The platform manages execution, registered-contract selection, record envelopes, storage, replay, queries and optional content updates. Vault and web/report content are downstream consumers; no Markdown or renderer belongs to this retention contract.

```yaml
access_mode: read
retention:
  contract: inventory-observations
  version: 0.1.0
  description: Allowlisted inventory and native identity evidence; preserve partial/unknown states and collection scope, not overall health.
  schema: retention.schema.json
```

`output` describes raw JSON only. The former output.retention_adapter, output.retained_contract_version and output.exchange_version keys are rejected. Descriptor/result schema remains 0.2.0; recipe version is 0.3.1; the nested retained inventory and legacy exchange payloads remain 0.1.0. Keep these independent versions distinct. Copied inventory descriptors now require explicit access_mode, the retention declaration and a matching local schema. There is no implicit declaration based on recipe ID.

OpsFeast registers this shipped normalizer by `(contract, version)` in `retention_contracts`. Static inspection reads metadata/schema/digests without importing normalizer or collection code. The runner snapshots the declaration plus normalizer code and canonical schema digests after inventory access preflight and before the collection connection/selected implementation loading. Access preflight may already have connected and attempted authorized privilege checks; this change does not move that boundary. Only operational local/SSH success/partial evidence qualifies; raw inputs, commands, execution errors and undeclared private fields are not retained.

Offline replay executes only the registered bundled pure data normalizer, never a candidate recipe's main.py, collector or retention.py. An external clone can reuse this contract/schema; changing a clone's normalizer does not replace the registered implementation. A new structured contract/version needs a reviewed product registration, reproducible tests and schema/skill documentation; arbitrary third-party normalizer loading is unsupported. Bundle digests remain provenance, not authentication or a Python sandbox. For portable user recipe bundles include retention.schema.json in the explicit file allowlist and declare the required OpsFeast registered contract; do not assume a copied Python file activates a new normalizer.

```sh
python -B tools/opsfeast.py recipes show inventory/system --checkout-only --json
python -B tools/opsfeast.py retention list --profile main --recipe inventory/system --json
python -B tools/opsfeast.py retention ingest /path/to/inventory-raw.json --profile main --dry-run --json
# Old raw without a current snapshot requires an explicit reviewed definition:
python -B tools/opsfeast.py retention ingest /path/to/old-inventory-raw.json --profile main \
  --recipe-dir /path/to/opsfeast/recipes/inventory/system --dry-run --json
```

Use the actual source-qualified recipe reference from discovery/results (for example company:inventory/system), not necessarily the bundled short path. Discovery exposes declaration, schema_path, schema_sha256 and registered normalizer source/digest. Retained envelopes include retention_definition plus snapshot/version provenance, precise source times, origin and quality warnings. Core `profile.retention.query(recipe=REFERENCE)` and offline `context.retention.query(...)` retrieve complete data for vault, HTML or cross-recipe analysis without another collection.

New inventory raw carries retention_snapshot 0.2.0 with normalizer_sha256 and schema_sha256. Missing snapshots or mismatched installed digests fail explicitly; select a reviewed --recipe-dir to authorize revised extraction, then preview with --dry-run. Original execution classification and producer identity remain evidence. Existing retained IDs with changed definition/content conflict rather than being silently rewritten: only explicitly deletable read observations can be removed and replayed; preserve protected write/unknown evidence. No automatic data migration or deletion occurs. Data/identity status, retention persistence and content_update are separate; a content failure does not undo saved data or change collection status.

Public [contract tests](../../../tests/test_inventory_retention_contract.py) cover recipe-owned discovery/schema semantics, missing/invalid declarations, schema/path/digest conflicts, candidate-code nonexecution, replay/dedup, privacy and partial states, and new private storage packaging boundaries. [Installed-package tests](../../../tests/test_core_delivery.py) exercise the same data contract and content reader without checkout imports. This is synthetic evidence, not native collection verification.

## Retained data and identity

After raw result saving, the runner uses this recipe's declared registered normalizer to produce operational success/partial retention under retention/ annual archives. It shares only allowlisted data through an explicit stage-3 export. Identity evidence is separate from the seven common observation fields. Hardware serial/UUID does not identify an OS installation; fallback and Linux machine-id limitations remain explicit. See [contracts, identity/sudo rules, recovery and sharing](../../../docs/result-data.md), [CLI interfaces](../../../docs/cli.md#retained-observations-and-exchange), [retained schema](../../../schemas/retained-observation.schema.json), [exchange schema](../../../schemas/observation-exchange.schema.json) and [synthetic exchange](examples/exchange.synthetic.json).

ESXi implementation 0.1.0 uses uname for hostname/kernel/architecture, a constant VMware ESXi system name, and the full vmware -v line for system version. Optional hardware identity comes from esxcli hardware platform get. The shared access adapter can verify an ESXi root login without id using an existing system Python; see [identity prerequisites and limits](../../../docs/host-diagnostics.md#esxi-login-identity-without-id). Native su/sudo still requires the existing SSHScript authenticated-console prerequisites. Supported interfaces are documented ESXi shell/ESXCLI interfaces, but ESXi inventory execution has not been tested; only direct root access verification on ESXi 7.0 has real-host evidence. vCenter/vSphere API collection and guest-to-hypervisor topology are not implemented. VMware guests use their OS collector; virtual hardware identifiers must not be equated with the physical host.

Result schema remains 0.2.0 with additive identity evidence 0.1.0 and retention receipt. Recipe/implementation version changes are independent. Existing raw reports require a saved current snapshot or explicit reviewed --recipe-dir for replay; no background migration occurs. A stage-2 failure makes runner exit nonzero while preserving collection evidence for replay. Current tests are synthetic; historical macOS collection verification does not verify the new identity/sudo/retention path.

Host identity_key, label and description are now supported. An explicit identity_key takes precedence and is shared across Feasts as user-assigned identity; change it after OS reinstall/replacement and coordinate its namespace. label/description are captured human text, never identity keys, and are preserved through retention/exchange. See [the canonical host configuration](../../../docs/hosts-yaml.md#explicit-host-identity-and-human-readable-metadata) and [identity/metadata rules](../../../docs/result-data.md#explicit-identity-and-display-metadata). MAC is not an automatic key.


Inventory-owned retention follow-up verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed all 678 public tests, including 13 new inventory-contract regressions and installed-wheel structured inventory retention assertions. Older interpreters reused the selected maintenance environment's Python dependencies. Wheel/sdist builds, temporary no-dependency pip installation and installed inventory normalization/query/replay/content smoke passed. Python 3.11 grammar, schema syntax/references, skill frontmatter, documentation links/footers and diff whitespace checks passed. This is synthetic/local-package evidence; no native host collection, private-data modification, commit, push or release occurred.

_Last modified: 2026-10-19 14:55:28_
