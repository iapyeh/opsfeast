# Recipe catalog

[system/inventory/overview 0.3.2](system/inventory/overview/README.md#recipe-owned-retention-contract) declares inventory-observations 0.1.0 independently of raw output. The recipe owns its schema and normalization; registered-contract selection and storage remain platform services.


This catalog lists recipes currently supplied by OpsFeast. To ask your AI agent to create a recipe, share content or acquire someone else's work, start with the [user guide](../docs/recipes.md).

The bundled [system/account/check/identity](system/account/check/identity/README.md) demonstrates python-recipe 0.1.0 with the Core Recipe scoped session. It observes the login account without su/sudo; local and synthetic evidence do not prove remote applicability.

The bundled [feast/report/retention-summary](feast/report/retention-summary/README.md) reads declared retention through the offline report reader and produces Markdown/HTML, including cross-recipe selections. Operation recipe creators own their retention declarations; content is a downstream application.

## Classification

Use [domain/subdomains/action/name](../docs/recipe-taxonomy.md) for new recipes. Paths can have more than two levels. Bundle recipes live here; user-authored recipes normally live under the selected profile's recipes/ and use :references. Shared user repositories use registered source references. Classification-only moves retain IDs and historical evidence; see the guide's relocation table and required configuration/job/consumer updates.

## Available recipes

| Reference | Stable ID / version | Purpose | Runtime/platform | Verification evidence | Invocation |
| --- | --- | --- | --- | --- | --- |
| [system/inventory/overview](system/inventory/overview/README.md) | inventory-system / 0.3.2 | Common system facts plus hardware, storage, network, software and services sections | SSHScript 5.0.0; Linux, FreeBSD, macOS, ESXi | Synthetic; historical local macOS evidence does not verify new native access/retention behavior | run_recipe.py system/inventory/overview --host HOST |
| [system/network/check/port](system/network/check/port/README.md) | check-port / 0.1.0 | One bounded TCP connection from the selected host | SSHScript Session plus target Python socket; Linux, FreeBSD, macOS | Synthetic; no native target/SSH verification | run_recipe.py system/network/check/port --host HOST --var port=8888 |
| [system/account/check/identity](system/account/check/identity/README.md) | check-identity / 0.1.0 | Observe the supplied session's effective account without escalation | Core Recipe and SSHScript; Linux, FreeBSD, macOS | Synthetic and earlier local Core evidence; remote applicability unverified | run_recipe.py system/account/check/identity --host HOST |
| [feast/report/execution-summary](feast/report/execution-summary/README.md) | report-summary / 0.1.2 | Render selected saved execution results as HTML and JSON | Offline controller Python; python-report 0.1.0 | Synthetic and isolated local report generation | opsfeast.py recipes run feast/report/execution-summary --input RESULT.json |
| [feast/report/retention-summary](feast/report/retention-summary/README.md) | report-retention / 0.1.0 | Combine retained observations as Markdown and HTML | Offline controller Python; python-report 0.1.0 | Synthetic and installed-wheel retention/report tests | opsfeast.py recipes run feast/report/retention-summary --profile NAME --json |

This checkout ships these five recipes. Catalog discovery also includes enabled profile and registered external sources; publisher trust, dependencies and host applicability remain separate evidence. No live exchange or automatic third-party installer is implemented. Update this catalog with actual coverage and verification when adding recipes.

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

_Last modified: 2026-10-19 17:04:30_
