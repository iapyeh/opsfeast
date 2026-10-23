# Execute and author Python-session recipes

New raw adds source_observation_id and execution_access_mode; general results also capture retention_snapshot before connection/code execution. These are additive [replay context fields](../schemas/raw-retention-context.schema.json). [Offline replay](retention-replay.md) uses the original snapshot by default, preserving execution classification independently of an author override.

## Retention and operation journals

[Namespace-enabled profiles](retention.md) add opt-in typed host-values 0.2.0 retention with dataset/field descriptions and explicit units to general recipes. Write/unknown general recipes persist intent before connections/code and append outcome after cleanup. Missing access_mode means unknown; read skips the operation journal. Retention/audit failure yields explicit failure; content update has a separate receipt and never changes recipe status, and no automatic raw cleanup occurs. Profiles without namespace retain the legacy raw-only general-recipe behavior described below.

Use `tools/opsfeast.py recipes run` to execute one explicitly selected recipe on explicitly selected hosts. Inventory uses descriptor 0.3.0 with inventory-jobs 0.1.0; general recipes use the Python-session/Core contracts described here. The [recipes list/show/run surface](recipe-experience.md) uses the internal recipe_runner module; offline python-report 0.1.0 uses recipes run without Session/host selection. Both use the selected interpreter, Python 3.11+, PyYAML 6.0.3 and matching SSHScript import/distribution 6.0.0. Review the actual recipe and dependencies before authorized execution; this interface is not a sandbox or approval mechanism.

Start with the [recipes skill](../skills/opsfeast-recipes/SKILL.md), [CLI reference](cli.md#operational-recipe-execution) and [source/input rules](recipe-sources.md). Check the selected Feast and environment with `check` and `check_environment.py`; these checks do not execute recipes or install missing dependencies. Inspect the descriptor and entrypoint statically with `inspect-recipe /absolute/recipe/path --json`. Compatible metadata does not prove target dependencies, safety or successful operation.

## Select a recipe and provide inputs

From the checkout, using the selected interpreter:

```sh
python -B tools/opsfeast.py recipes run system/network/check/port --host rms3 --root ~/Download/testops --var port=8888
python -B tools/opsfeast.py recipes run :system/network/check/port --host rms3 --profile main --vars-file /path/to/inputs.json
python -B tools/opsfeast.py recipes run company:system/network/check/port --group web --var port=443 --threads 2
python -B tools/opsfeast.py recipes run system/inventory/overview --host rms3 --var command_timeout_seconds=10
```

The second example requires a reviewed compatible recipe already present at the Feast's `recipes/system/network/check/port`; the third requires a registered reviewed company source. Source forms, enabled flags and host/group/all/exclude selection are shared with inventory. A recipe need not be listed under a host for explicit --host execution. Exact-reference settings merge default/group/host vars; bulk/group execution additionally requires the resolved enabled flag. Existing selection lists keep first-matching overrides; see the [policy guide](recipe-sources.md). There is no fallback to another source or recipe. The internal recipe_runner.run(root, host, recipe=REFERENCE) requires an explicit recipe and routes inventory through inventory_jobs.collect_host; there is no snapshot fallback.

`--var NAME=VALUE` may repeat with unique names. Declared string inputs are literal text, including empty text, `true`, leading zeros and additional equals signs. Other types use JSON syntax: `port=8888`, `enabled=false`, `scale=1.5`, `'items=[1,2]'`, `'options={"mode":"basic"}'`. Use shell quoting for spaces, arrays and objects. No shell interpolation is performed by the input parser. Duplicate --var names are errors; supply the final value once.

`--vars-file` accepts one readable UTF-8 JSON file containing an object, for example `{"port":8888}`. Its path is relative to the shell directory, with `~` expansion; it is explicit local input data and need not be inside the Feast. Duplicate object keys, non-finite values, invalid JSON and non-object roots are rejected. CLI assignments override file values regardless of option order. Required/type/range/unknown-key validation follows the [typed input contract](recipe-sources.md#variables-and-implementation-context).

Precedence is recipe defaults → source vars → resolved default/group/host recipe vars → invocation inputs. Nested mappings merge and lists/scalars replace, with an independent copy per host. Within invocation inputs, --var replaces the same variable from --vars-file before that merge; see [exact precedence](recipe-sources.md#variables-and-implementation-context). Invalid effective inputs are rejected before that host's Session is created or entrypoint is loaded. Batch hosts remain independent: one host's preflight failure does not cancel others; target-name/configuration selection errors and invalid vars-file syntax fail before any host executes. Bulk targets honor host/source/recipe enabled gates; explicit --host overrides all three for that target, without allowing a disabled jump host or bypassing input/path validation. Per-invocation overrides do not rewrite hosts.yaml. Namespace-enabled CLI operations persist one [explicit observation run](observation-runs.md), including preflight failures and skipped target evidence; collection, retention and content receipts remain independent. Parameter values may be sensitive: use a private input file for secrets rather than shell arguments/history; provenance records arbitrary variable names rather than values (inventory separately saves its nonsecret validated Attention policy), while recipe-owned output must avoid disclosure.

## Core Recipe execution 0.1.0

New recipes may declare runner.contract python-recipe, runner.version 0.1.0 and define synchronous execute(recipe). This is a separate explicit contract; [Core API](core-api.md#runner-integration-and-migration) defines Recipe fields, session ownership, root/su/sudo scopes, instance metadata and cleanup evidence. Descriptor 0.3.0, typed inputs, selection, common results and storage behavior are shared. See [system/account/check/identity](../recipes/system/account/check/identity/README.md) for a complete example. Existing python-session/python-report/inventory contracts remain unchanged.

For authorized root-only work, call `with recipe.root() as root:` then `root("id -u", check=True)`. It uses the shared ordered account policy and raises RootUnavailableError if root is unavailable after safe restoration. The yielded value is a callable console, not a Recipe. See [the full example, prerequisites and failure rules](core-api.md#automatic-root-console). Generic recipes never acquire root merely by being invoked.

## Descriptor 0.3.0 and Python-session 0.1.0

A general recipe uses a simple unique ID other than the reserved inventory-system ID, one Python entrypoint, a literal matching VERSION and typed inputs:

```yaml
descriptor_version: 0.3.0
id: my-check
version: 1.0.0
runner:
  contract: python-session
  version: 0.1.0
  entrypoint: main.py
inputs:
  variables:
    port: {type: integer, required: true, minimum: 1, maximum: 65535}
output:
  schema_version: 1.0.0
```

`output.schema_version` versions the recipe-owned data; the runner validates the common result envelope, not a recipe-specific JSON Schema. `runner` accepts only contract/version/entrypoint; `output` accepts only schema_version. Entrypoints are .py files inside their own recipe directory, without absolute/traversing paths or escaping symlinks. Python helpers must also remain there. The runner statically validates VERSION, the execute signature and input definitions without importing the recipe. It records descriptor, entrypoint and Python bundle hashes; these establish provenance, not publisher trust or immutability during execution. Avoid modifying recipe files during a run.

Optional platforms.planned/implemented/tested lists are declarations for inspection, not dispatch rules. This contract uses one entrypoint and rejects inventory-style implementations. It does not probe host facts or select platform code automatically. Recipe authors check needed platform/dependency capabilities through their reviewed code and return unsupported/failed when unavailable. Use the existing [inventory implementation contract](../recipes/system/inventory/overview/README.md) for system inventory; do not convert its seven-field output to this contract.

Declare dependencies, permissions, side effects, implementation choice, applicability and verification evidence as described in [authoring](recipe-authoring.md). Additional descriptive fields are documentation data, not automatically enforced permission or dependency-installation rules. [Explicit-file pack/unpack](recipe-experience.md#portable-recipe-bundles) prepares verified recipe candidates. There is no automatic installer, extension overlay or alternative operational backend loader.

## Entrypoint and available capabilities

```python
VERSION = "1.0.0"

def execute(session, *, context, timeout):
    result = session.exec_command(
        ["some-reviewed-program", str(context.vars["port"])],
        check=False, command_timeout=timeout,
    )
    if result.exitcode != 0:
        return {"status": "failed", "reason_code": "command_failed",
                "message": "The check command failed.", "data": {}}
    return {"status": "success", "reason_code": "check_complete",
            "message": "The check completed.", "data": {"output": result.stdout}}
```

The runner passes the already selected local or SSH Session, `RecipeContext(host_id, vars)` and a positive timeout. It owns connection plans/jumps and strict Session cleanup. The recipe must not close the borrowed Session or reconnect by loading credentials itself. Remote settings retain the existing host-key/authentication semantics. This interface remains SSHScript-based; recipes may invoke reviewed CLIs/SDKs inside their implementation, but there is no independent backend runner.

Only a synchronous execute accepting the Session positional argument and context/timeout keywords is supported; other required arguments are rejected statically. Runtime VERSION and callable presence are checked again after loading. Entrypoint loading is serialized because runpy changes process import state; executions can run concurrently with separate Sessions and contexts. Avoid mutable shared state, process-wide settings and conflicting file writes. Sibling imports are not automatically added to sys.path: keep a small recipe self-contained, or load explicit reviewed helpers relative to `__file__` using standard Python facilities. Review all dependencies and helpers.

The timeout controls connection stages and is supplied as the per-command budget; it is not a whole-recipe deadline. Recipes must apply it to their operations and clean up their own jobs/resources. Arbitrary Python executes in the controller process without isolation, and no forced interruption or process-termination guarantee is provided. Print diagnostics to stderr, keep stdout reserved for runner result output (terminal tables, or JSON with --json/non-TTY output), and avoid secret-bearing exception/output text. Read the [SSHScript skill](../skills/sshscript/SKILL.md) and task-relevant references before using its APIs.

## Results, failure states and storage

execute returns exactly four fields:

| Field | Contract |
| --- | --- |
| status | success, partial, failed, skipped or unsupported |
| reason_code | Nonempty machine-readable string, defined by the recipe |
| message | Nonempty human-readable explanation |
| data | Object of finite plain JSON data with string object keys, defined and tested by the recipe |

A successful diagnostic may observe an unhealthy service. For system/network/check/port, a refused connection is a completed check with status success, data.reachable false and reason_code port_refused; read the observation as well as execution status. Timeout/network errors remain failed with reachable null. Each recipe must document how to interpret its outcomes.

The runner adds `run_contract: 0.1.0`, recipe-owned schema_version, host_id, started_at/completed_at UTC timestamps, runtime/evidence_kind, source/version/digest provenance, variable names, hops, host metadata and execution_errors. Result-validation failure produces failed/invalid_result and discards the invalid returned payload. Loading/connection/execute exceptions produce failed/execution_failed with exception type/stage, without custom exception text. Cleanup failure produces failed/cleanup_failed while preserving valid collected data. Recipe-returned partial/skipped/unsupported states remain explicit. Preflight failures do not fabricate a raw report.

Completed attempts are atomically saved at `<management-root>/observations/recipe-run-<UUID>.json`; with --json or non-TTY stdout, output provides result_path, status/reason/message and data for a single host, or ordered per-host summaries including data for batches. Saved batch completion also prints a shared Observation ID, inspectable with observation ID/latest and host --status filters. Terminal completion shows host, collection identity, result and result id (a short ID accepted by observation result; a dash for unsaved/excluded targets); use the [saved-result viewing workflow](cli.md#inspect-one-hosts-saved-execution) for details. Output/save errors return nonzero. Arbitrary recipe code can still write or print beyond these conventions: this is not an output sandbox.

General recipes without a retention declaration carry `retention: {status: skipped, reason_code: no_retention_adapter}`. Declared host-values use the [retention interface](retention.md), independent of inventory storage/exchange. General retention does not run inventory identity/sudo probes or enter the inventory exchange payload; inventory retains its current raw → retained flow. Recipes requiring new retention adapters must define reviewed versioned data contracts before support is added. Use ordinary JSON tools to inspect general raw results; observation_store inventory ingest does not accept them.

Exit 0 requires every attempted host's status to be success, with no retention/content failure or degraded access. Partial/failed/skipped/unsupported returns 1; usage errors return 2. No automatic retry or fallback implementation runs after failure.

## Verification and extension

[Public synthetic tests](../tests/test_general_recipes.py) cover CLI/file precedence, input types/bounds/isolation, descriptor/signature/path validation, static inspection, general execution, connection/loading/result/cleanup failure, result storage and inventory coexistence. The bundled [port recipe](../recipes/system/network/check/port/README.md) has synthetic probe/command tests; no real SSH, native su/sudo or target TCP probe was performed for this change. A fresh agent should inspect, review and execute through the documented CLI within the user's scope, without inventing a standalone --host interface for main.py.

To add another Python-session recipe, use a new ID, implement this entrypoint/result contract, declare typed inputs and target dependencies, publish synthetic success/failure/boundary tests, and register a reviewed source when external. If this interface cannot express a required backend, platform dispatch or result capability, document the gap and propose an explicitly versioned extension rather than guessing support.

Terminal presentation does not change recipe return values or saved reports. See
[compact execution summaries](cli.md#compact-execution-summaries) for unknown actors,
retention/fallback outcomes and existing offline host-specific inspection.

## Unified entrypoint verification (2026-10-20)

The complete suite passed 763 tests on CPython 3.11.15, 3.13.13 and 3.14.4. test_recipe_runner.py verifies the removed standalone CLI, explicit recipe requirement, job delegation without a second access gate, rejection of snapshot/write inventory descriptors before connection, registered-path resolution, independent UTC filenames and durable raw preservation on receipt failure. Existing suites cover general Python-session/Core execution, concurrency/progress, reports, results, saved jobs, retention/replay and Vault.

Native macOS with SSHScript 5.0.0 verified selective utility queries without profile writes and two independent saved observations with retention/Vault delivery. No remote SSH or native Linux/FreeBSD/ESXi/su/sudo result follows from this evidence. Wheel/sdist builds and installed-package tests are local checks, not publication. No private host was enabled for cron.

_Last modified: 2026-10-23 08:11:44_
