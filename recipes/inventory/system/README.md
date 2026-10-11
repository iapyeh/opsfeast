# inventory-system

Recipe version 0.2.0 provides Linux, FreeBSD and macOS implementations under one recipe ID, using descriptor 0.2.0 and a shared result schema 0.2.0 in [schema.json](schema.json). Platform selection is automatic; users select the recipe directory, not a Python file. Linux/FreeBSD have synthetic verification only. macOS has synthetic and local read-only verification. Real SSH and native FreeBSD/Linux collection remain unverified.

For complete tool syntax, defaults, behavior, output and exit codes, see the [CLI reference](../../../docs/cli.md). It covers both tools/ops.py and tools/run_recipe.py for administrators and agents.

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

No su/sudo, installation or target configuration changes are performed. Read access and the listed target commands are required. Controller requirements are Python 3.11+, PyYAML and matching SSHScript import/distribution 5.0.0. The runner preserves configured connections, jump hosts and SSHScript's default host-key trust; it never upgrades packages.

## Execute

```sh
python -B tools/run_recipe.py host-01 --recipe inventory/system
python -B tools/run_recipe.py host-01 /srv/my-ops --recipe inventory/system --hosts host-02 host-03
python -B tools/run_recipe.py host-01 --profile inventory
```

`--hosts` adds host IDs to the first positional host; duplicate IDs are executed once. Each host has independent initialization, selection, cleanup and result files; a failure/skip does not stop other hosts. Batch execution is sequential. Aggregate exit code is zero only when all inventories succeed.

The optional positional management root and `--profile` retain their existing mutually exclusive semantics. Without either, the selected default profile is used. Bare `--recipe inventory/system` selects this checkout's `recipes/inventory/system`; the CLI rejects the `recipes/` prefix. Explicit `--recipe ./recipes/custom-system` selects a directory relative to the management root. YAML `recipe: recipes/inventory/system` still selects the checkout, even from include files. Missing checkout content does not fall back to instance copies. Paths cannot escape their repository/management boundaries.

Without `--recipe`, exactly one selected recipe with ID `inventory-system` is required. With it, that host's recipe selectors are bypassed, but host/connection configuration is still validated. Other recipe IDs and general third-party interfaces remain unsupported.

## Host initialization and selection

The runner reuses successful, target-matching host facts from the management environment. Otherwise it performs the same read-only probe as `ops.py host-init`; cached facts that cannot select an implementation also trigger one fresh probe. A failed probe skips recipe execution and saves the reason. Unknown platforms produce unsupported. Missing distribution/version can still select a generic OS implementation.

See [host diagnostics](../../../docs/host-diagnostics.md) for refresh semantics, cache storage, limitations and su/sudo tests. Direct `host-init` always refreshes; `test-host` only fills missing/failed/invalid initialization. The original facts timestamp and cache/probe source remain in results.

Implementations are declared explicitly in `recipe.yaml`:

```yaml
implementations:
  - id: linux
    version: 0.1.1
    entrypoint: implementations/linux.py
    match: {os_name: linux}
  - id: ubuntu-24
    version: 0.1.0
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
def collect(session, report, timeout, facts):
    # Populate the seven observations, sources and execution_errors.
    ...
```

All implementations share the inventory input/output contract. `main.py` contains existing report/parser helpers and legacy Linux collection; it is not the runner-selected entrypoint. The new `implementations/*.py` files provide separate platform entrypoints. The runner validates manifest paths/version literals before connecting, loads only the selected entrypoint, checks its runtime version, and validates observation shape and states. It does not execute unselected implementation modules.

Custom inventory bundles are now executable through this contract; they no longer need identical bytes to the built-in bundle. Review the complete code/dependencies before authorizing execution. Manifest checks are not an execution sandbox, authenticity verification or permission grant. General recipe execution, extension-overlay installation, packaging and third-party installation remain unimplemented. Independent platform files reduce shared-code conflicts; contributors may still need to reconcile recipe.yaml/schema changes when updating Git.

## Results and verification

Every run saves a new `observations/inventory-system-<uuid>.json`; prior results and human records are preserved. Reports include recipe version, implementation ID/version/path, selected-file SHA-256, complete Python-bundle SHA-256, runtime versions, host-init facts/provenance, observations, command sources and execution/cleanup errors. The bundle digest covers all `.py` files in sorted relative-path order, including shared helpers. It is provenance, not publisher authentication.

Schema version and recipe/implementation versions are independent. Result schema 0.2.0 adds host-init provenance, implementation versions and skipped runs; migrate old copied descriptors to 0.2.0 before using this runner. A pre-dispatch skip has no selected implementation version. Source/schema versions and missing/error states are preserved; raw collector output may be present in inventory sources and must remain in the private management environment. The runner enforces observation shape without requiring a JSON Schema library; the JSON Schema is available to downstream consumers.

Single-host stdout summarizes status/reason/message/kernel/platforms/result path. Batch stdout summarizes each host. Success returns 0; partial, unsupported, skipped, failed and configuration/save errors return 1. A successful command is not sufficient if parsing or strict Session cleanup fails. `--timeout` bounds connection stages and each command, not the entire run; channel closure is not proof of remote termination.

Synthetic tests cover parsers, three platform collectors, specialization/ambiguity, version/paths, cache failure, selected-code failure without fallback, batch continuation, cleanup and preservation. Local macOS read-only initialization/inventory and the SSHScript credential-free command example are checked separately. Real Linux/FreeBSD, SSH/jump-host and native su/sudo remain unverified.

SSHScript source: bundled public documentation contract 5.0.0 and SOURCE.json bundle SHA-256 `e065bec4e7bd48791563412c5ca3bdaac5f46c5e09456ba5d24665a01ba79b4b`; public [API guide](https://iapyeh.github.io/sshscript/v3a/recommended-api/). FreeBSD userland semantics follow the [FreeBSD manual](https://man.freebsd.org/cgi/man.cgi?query=freebsd-version&sektion=1), consulted 2026-10-11. No private SSHScript source was used.

_Last modified: 2026-10-11_
