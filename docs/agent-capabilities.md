# Reuse OpsFeast tools and Python modules

This guide is for **DevOps users and their agents** operating OpsFeast or authoring specialized recipes. OpsFeast product developers have the complementary mission to reduce user-side development by providing complete, broad and stable tools/modules; see [the two roles](vision.md#distinguish-product-developers-from-devops-users). Both roles use reviewed programs for repeated work so AI can focus on new needs, judgment, changes and exceptions.

OpsFeast accumulates reusable operational knowledge and executable capabilities. Before writing a parser, connection wrapper, discovery scanner, result store, exporter or recurring script, look for an existing tool, recipe or module here. Start with the [skill index](../skills/README.md), select the relevant skill, then use the [CLI reference](cli.md) and the task's canonical guide. This reference describes the current checkout; it does not make every internal Python function a stable public SDK.

Inventory raw files now use UTC start-second prefixes with UUIDs; old files remain valid. Reuse recipes results list/show or recipe_reports results/show_result, which read both naming formats and sort by stored timestamps, instead of writing a filename-specific scanner. See [raw result names](cli.md#saved-results-and-stdout).

Console presentation uses the checkout-level [console_output helpers](../tools/console_output.py): TTY tables, explicit --json precedence and preserved non-TTY/raw-data contracts. See [the command-specific policy](cli.md#terminal-tables-and-json) before choosing agent invocations. Rendering does not authorize operations, and is not a versioned Core API.

## Decide what to reuse

1. Identify the requested outcome, selected Feast/targets/data and existing authorization. Discover relevant capabilities without running operations: recipe catalog/inspection, published contracts and implementation sources are the starting points.
2. Prefer an existing compatible recipe or CLI command for the complete task. Use structured JSON output for automation; do not scrape human text or replace the command's validation and result interpretation.
3. When developing Python that needs in-process data or composition, reuse an applicable module below. Inspect its current signature, dependencies, return values and caller/tests. For runner-managed recipes, use supplied Sessions/contexts rather than implementing a second configuration/connection lifecycle.
4. Check actual environment, configuration and input readiness. Static compatibility is not proof of execution readiness. A listed write/connection interface is not permission to run it.
5. Implement only the missing task-specific logic. If an existing capability is unsuitable, explain the concrete gap (contract, behavior, dependency, platform, user-selected tool or authorization constraint), reuse the parts that fit, and preserve a reviewed recipe/helper for repetition. Do not require an LLM to recreate working code on ordinary reruns.

Reuse is a default decision rule, not a requirement to force an unsuitable tool. User-selected tools and environment constraints take precedence. Do not independently recreate established include rules, recipe selectors, typed-input overlays, identity semantics, storage schemas, archive validation or artifact checks merely because the agent can generate code for them.

## Task-to-tool catalog

Commands below are command families, not permission grants or complete copyable invocations. Consult the linked guide for exact arguments, defaults, exit codes and effects. Use the selected interpreter with `-B` from the trusted checkout.

| Need | Existing interface to try first | Evidence and limits |
| --- | --- | --- |
| Check interpreter/dependencies and skill snapshot | `tools/check_environment.py` | Read-only readiness check; no installation or connection. [Setup](getting-started.md) |
| Create/select/register a Feast | `tools/opsfeast.py init`, `profiles`, `attach`, `detach`, `use` | Registry/scaffold changes are distinct from host operations. [Profiles](profiles.md) |
| Load/validate/query host settings | `opsfeast.py check`, `dump`; `opsfeast.Validator` | Includes/path/duplicate checks; dump exposes raw selected values. [Configuration Python interface](hosts-yaml.md#read-host-configuration-from-python) |
| Find recipes and inspect compatibility | `opsfeast.py recipes list/show`, `inspect-recipe` | Static metadata/signatures only; no recipe import, connection or dependency installation. [Catalog](recipe-experience.md#discovery-and-selection) |
| Initialize facts or test configured access | `opsfeast.py host-init`, `test-connection`, `test-host`, `test-su`, `test-sudo`, `check-access` | Real local/SSH operations and possible privilege attempts; use the appropriate narrow scope. check-access tests login plus independent su/enabled sudo for other declared users, using Boolean sudo policy (false disables; true/omission enables; strings rejected), with a tabulate per-test status/host/test/user/reason table (configured host icon or default 🍎; ❌ on failure; tabulate[widechars] 0.10.0 supplies Unicode alignment) and stderr progress; inventory preflight/dryrun stays login-only; add --json --quiet for full machine-readable evidence. [Diagnostics](host-diagnostics.md), [inventory access](inventory-access.md) |
| Run an operation with inputs/targets | `opsfeast.py recipes run`, `tools/run_recipe.py` | Existing selection, typed vars, sessions, cleanup and results; inventory dryrun makes connections. [Execution](recipe-execution.md), [sources](recipe-sources.md) |
| Author identity/license defaults | `tools/recipe_identity.py defaults`; `recipe_identity.defaults()` | Read installation-level defaults; reserved Bundle attribution remains protected. [Attribution](recipe-attribution.md) |
| Generate offline reports/basic HTML | `opsfeast.py recipes run report/summary`, catalog/results `--html` | Local report execution writes artifacts; renderer code requires review. No dummy host needed. [Reports](recipe-experience.md#offline-report-contract) |
| Find saved results/verify artifacts | `opsfeast.py recipes results list/show`, `recipes artifact` | Read-only lookup and digest/path checks; no viewer launch or publication. [Results](recipe-experience.md#results-and-artifacts) |
| Recover/export/validate/combine observations | `tools/observation_store.py ingest/export/validate/combine` | Ingest writes; JSON/CSV export reads retained data; combination preserves history. No transmission or foreign raw ingestion. [Data contracts](result-data.md), [CSV](inventory-access.md) |
| Package/review a portable recipe candidate | `opsfeast.py recipes pack/unpack` | Explicit allowlist and integrity/path checks; creates files/candidate, no installation or publisher authentication. [Bundles](recipe-experience.md#portable-recipe-bundles) |
| Save/rerun reviewed work | `opsfeast.py recipes jobs save/list/show/run` | Private bindings and content verification; run executes again. No bundled scheduler. [Jobs](recipe-experience.md#saved-jobs-and-recurring-work) |
| Check/stage public SSHScript skill updates | `tools/skill_bundle.py check/download` | Authorized network download/check only; no activation or package upgrade. [Skill updates](skill-updates.md) |

The shared loader resolves host/account icons using entry hosts.yaml `default.icon.user`, `default.icon.host`, per-group `default.groups.<name>.icon.user/host`, and named-account `default.users.<account>.icon` (built-ins 👤/🍎). Explicit host/account icons override defaults; named-account defaults then precede group user defaults. For each remaining field independently, the first configured value in host group order precedes the global default. Optional default.users.<account>.email is readable source metadata (CLI dump), without host-account inheritance or notification behavior. Icons must be one Unicode Symbol code point. Core/CLI/runner share effective values without rewriting YAML. See [host icon contract](hosts-yaml.md#host-icon); it is display metadata, not host identity.

## Public Core Python API

Prefer [Core API 0.1.0](core-api.md) and the [Core skill](../skills/opsfeast-core/SKILL.md) for installation identity/profiles, hosts snapshots, standalone sessions and scoped Recipe su/sudo, and read-only inspection. From the checkout root or an authorized installed package use `from opsfeast import Instance`; select `Instance.open(installation=...).profile(...)`. Core replaces the need for caller-managed tools import paths for these capabilities. Existing python-session recipes remain compatible; python-recipe entrypoints receive execute(recipe). Logging/notifications remain deferred. See canonical examples, dependencies, error/lifecycle rules and copy/UUID policy in that guide.

## Python reuse map

These modules live in `tools/` and use sibling imports. Put the selected trusted checkout's `tools/` on `sys.path` or `PYTHONPATH`; these legacy modules are compatibility interfaces rather than the versioned Core API. The bundled package is installable; prefer Core for its supported operations. Use Python 3.11+ and the selected environment's dependencies. Configuration/catalog/results/exchange processing need PyYAML; operational interfaces additionally require matching SSHScript 5.0.0. Extra renderers/providers have their own dependencies. Pass filesystem arguments as `pathlib.Path` where the implementation expects paths.

| Module and current interface | Reusable result or behavior | Caller responsibility |
| --- | --- | --- |
| `opsfeast.resolve_root(root=None, profile=None)`; `Validator(root).load(path)` / `.check_connections()` / `.check()` | Feast selection and merged, validated settings | See the [complete loading example](hosts-yaml.md#read-host-configuration-from-python). Secrets remain raw; do not log settings. |
| `recipe_catalog.catalog(root=None, query=None, kind=None)`; `choose(root, selector)` | Catalog dict with sources/recipes/status; selected recipe dict | `root=None` scans checkout only. Inspect errors and selected `runnable`; ambiguous IDs fail. `choose` alone does not enforce execution readiness. |
| `recipe_inspection.inspect_recipes(value=None, requested=())` | Static recipe/platform inspection report | Check report errors/coverage, not merely the presence of a descriptor. See [inspection](cli.md#inspect-recipes-and-platform-gaps). |
| `recipe_inputs.cli_variables(metadata, values=None, assignments=())`; `prepare_vars(metadata, source_vars, host_vars, cli_vars=None)` | Parsed assignments and validated independent effective-vars dict | Preparation overlays defaults/source/host/CLI; caller passes the right layers. Runner already does this for recipes. `RecipeContext` has only `host_id` and `vars`. |
| `recipe_identity.defaults(root=ROOT)` | Normalized author/contacts/license dict | `root` is the installation checkout, not the Feast. Preserve reserved attribution and packaging obligations. |
| `recipe_reports.results(root, recipe=None, host=None, status=None)`; `show_result(root, identifier)`; `show_artifact(root, identifier, name)` | Result index, raw document or verified artifact metadata/path | Inspect partial/errors and source times; obtain identifiers from the index. Artifact names are declared relative paths. These reads do not execute or publish. |
| `observation_store.export(root, *, recipe=None, hosts=None, since=None, until=None)`; `validate_exchange(bundle)`; `combine(bundles)` | Exchange dict; validated record count; validated deduplicated union | Export reads the existing database, missing storage fails. Time filters use observation completion time. Preserve identity quality and conflicts. JSON values are input objects, not filenames. CSV is a CLI presentation surface. |
| `management_view.masked(value)`; `hosts_snapshot()`; `profiles_snapshot()` | Masked local UI read models | Snapshots use this checkout's registry/default profile, not a supplied root. Inspect message/status fields; masking recognizes key names and is not a guarantee against arbitrary secret content. Do not substitute masked settings for execution configuration. |
| `inventory_values.validate_inventory(data)` | Validation of the partitioned inventory-values contract | Use the [inventory access/results contract](inventory-access.md); this does not validate a complete raw or exchange envelope. |
| `recipe_jobs.listing(root)`; `load(root, name, verify=True)` | Saved names/definition with default content verification | `verify=False` is inspection only, not permission to execute changed content. Use CLI jobs save/run for invocation preparation and execution. |

For writes and host operations, prefer the complete CLI/runner workflow: `run_recipe.py`, `recipe_reports.run_report`, `recipe_packages.pack/unpack`, `recipe_jobs.save`, `observation_store.retain`, `host_runtime` and `access_check` are implementation owners, not interchangeable task shortcuts. Direct composition must preserve their prerequisites, caller preparation, target selection, enabled flags, cleanup, storage and failure rules. For example, CLI ingest validates an eligible batch before a transaction; calling `retain` in a loop does not provide that batch guarantee. Do not bypass the workflow merely to import a lower-level function. Use the canonical task contracts and public synthetic tests before proposing a new adapter.

## Minimal read-only composition example

After adding the checkout's tools directory as in the [configuration example](hosts-yaml.md#read-host-configuration-from-python), a standalone program can reuse discovery and result lookup without generating scanners:

```python
from opsfeast import resolve_root
from recipe_catalog import catalog
from recipe_reports import results

available = catalog(query="port", kind="operation")  # Checkout-only discovery.
if available["status"] != "success":
    raise RuntimeError("Recipe discovery needs review")

root = resolve_root(profile="main").resolve()  # Select an existing registered Feast.
index = results(root, status="success")
if index["errors"]:
    raise RuntimeError("Some saved results could not be read")
# Consume available["recipes"] and index["results"] locally.
# A recorded success is execution evidence, not proof that a service is healthy.
```

Choose profile/root from invocation inputs in reusable programs; `main` here illustrates an explicit selection. This example neither runs a recipe nor verifies live host readiness. Check each function's result states and catch `ConfigError`/filesystem or database failures at the application's boundary with secret-safe messages. Missing files, failed inspection and unsupported contracts must not silently fall back to a homemade parser or stale embedded configuration.

## Extend and maintain the learning path

For a DevOps user needing an unimplemented capability, describe the gap and a concrete workflow within scope rather than inventing commands. For product developers, assess that gap as a candidate for reusable product support that reduces future user-side development; documenting a workaround alone does not fulfill that mission. Logging/notification services, additional execution backends, a live exchange, automatic installation/publication and a scheduler remain planned. Recipient-selected analysis and richer report renderers can use documented data/report contracts; no general recipient database importer is bundled.

Every added or changed usable capability must update its canonical guide, this map where applicable, relevant skill routing and examples in the same delivery. Include supported versions, availability/dependency checks, exact CLI and/or Python interface, inputs/outputs, effects, failure/skipped states, extension points and verification limits. Record when a module is internal or an interface has changed. Remove obsolete “planned” claims when implementation is delivered, and do not confuse recipe version, descriptor version and result/data-contract version.

The [development principle](vision.md#make-existing-capabilities-the-first-choice-for-agents) and [contributor gate](../AGENTS.md#before-every-commit) make agent knowledge transfer part of functionality delivery. Documentation is a procedure, not an automatic loader or enforcement mechanism; agents must read the current sources and installation copies need the [update procedure](skill-updates.md).

Connection-only batch diagnostics are available through `test-connection --all --profile NAME` or `test-connection --group web database --profile NAME`; reuse this CLI before writing a connection loop. It preserves the existing single-host report, returns versioned batch JSON with --json, excludes disabled group/all members, validates selection before connections, and supplies automatic TTY progress/per-host tables. Combine --json --quiet for machine consumption. See [canonical syntax and result interpretation](cli.md#select-and-monitor-connection-tests) and the [hosts skill](../skills/opsfeast-hosts/SKILL.md#connection-selection-and-progress). This is a checkout CLI capability, not a new Core API or permission to connect.

## ESXi login identity

Reuse `check-access --host HOST --profile NAME --json --quiet` for login/root readiness; the shared `host_runtime.identity(session, timeout, console=False, target=None, verification=None, evidence=None)` checkout helper supplies OS-derived username/effective_uid and optional backend evidence on an already-authorized Session. Standard id is preferred; only missing id plus verified VMkernel selects the fixed system Python adapter. This adds no Core API/configuration field, installation or permission to connect/enter privileges. The access gate, diagnostics and existing Core identity checks reuse the helper. Read [prerequisites, canonical CLI/import examples, fields, errors, backend extension and verification limits](host-diagnostics.md#esxi-login-identity-without-id). Public tests are in tests/test_esxi_identity.py. One ESXi 7.0 root login passed; other releases/non-root access and native su/sudo/inventory remain unverified. Do not write a second ESXi identity probe in each recipe.

_Last modified: 2026-10-16_
