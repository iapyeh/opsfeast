# Recipe catalog

This catalog lists recipes currently supplied by OpsFeast. To ask your AI agent to create a recipe, share content or acquire someone else's work, start with the [user guide](../docs/recipes.md).

## Available recipes

| Recipe | Purpose | Implemented platform | Execution tools and showcase | Verification evidence | Usage |
| --- | --- | --- | --- | --- | --- |
| [inventory-system](inventory/system/README.md) 0.2.2 | Seven fields covering hostname, system name/version, kernel and architecture | Linux, FreeBSD, macOS, ESXi | SSHScript ==5.0.0 for local/SSH Session command collection; [implementation choice](inventory/system/README.md#implementation-choice) | Synthetic tests; macOS read-only initialization/inventory tested locally; real Linux/FreeBSD/ESXi/SSH collection unverified | run_recipe.py; see recipe README |
| [check-port](check/port/README.md) 0.1.0 | One TCP IP/port check from the selected host | Linux, FreeBSD, macOS with target python3 | SSHScript 5.0.0 borrowed Session/argv/command budget; Python socket probe | Synthetic tests only; real target/SSH unverified | run_recipe.py check/port --host HOST --var port=8888 |
| [report-summary](report/summary/README.md) 0.1.0 | Plain offline execution-result table/JSON | Controller Python; no host connection | Python stdlib rendering and HTML escaping; python-report 0.1.0 | Synthetic tests and isolated synthetic local report generation; no real data | opsfeast.py recipes run report/summary --input RESULT.json |

The bundled port check and offline report are listed above; there is no third-party catalog yet. Other inventory types remain future directions. Update this catalog when adding recipes, including purpose, version, platforms, execution tools, actual showcased capabilities, evidence and usage. Author declarations are not substitutes for actual testing.

## Custom and third-party content

Users may create recipes in their own working directories or repositories without forking Ops. Custom recipes within a management directory can be selected through explicit `./recipes/...` paths. run_recipe.py supports the inventory-system descriptor/implementation contract and [general Python-session execution](../docs/recipe-execution.md) (descriptor 0.3.0, contract 0.1.0). Reviewed compatible custom recipes use its connection/input/result lifecycle. The [recipe experience](../docs/recipe-experience.md) provides offline python-report 0.1.0, catalog/result/artifact views, explicit-file bundle candidates and saved reruns. An automatic third-party installer and arbitrary operational backend loader are not implemented.

- [Create a custom recipe](../docs/recipe-authoring.md)
- [Share one or multiple recipes](../docs/recipe-sharing.md)
- [Acquire, review, verify and authorize installation](../docs/recipe-acquisition.md)
- [Recipes skill for AI agents](../skills/opsfeast-recipes/SKILL.md)

## Recipe documentation requirements

Recipe authors should follow the shared [vision and design principles](../docs/vision.md) and [authoring guide](../docs/recipe-authoring.md). Design for human intent, repeatable execution with less model work, community reuse, clear authorization and outcomes supported by evidence.

Each recipe should document its purpose, supported and tested platforms, selected tools and compatibility, dependencies, required permissions, inputs, outputs, side effects and verification method. Follow the [tool selection workflow](../docs/recipe-authoring.md#choose-execution-tools) and explain the implementation choice. SSHScript recipes should link actual capabilities to code and evidence; other tools and mixed recipes are welcome, with their own reviewed standalone usage where the current runner does not apply.

Collection recipes should retain observation sources and timestamps and distinguish success, permission denial, unsupported operations, timeouts and parsing failures.

The first result contract and synthetic example live with inventory-system. Inventory-system retains its shared observation schema; other compatible Python recipes return the versioned general result envelope and recipe-owned data.

Retained inventory and JSON exchange are implemented through [result-data tools and contracts](../docs/result-data.md), with the [agent skill](../skills/opsfeast-result-data/SKILL.md). Identity/sudo probes and ESXi have synthetic coverage only; prior macOS local tests cover the older collection path.

_Last modified: 2026-10-13_
