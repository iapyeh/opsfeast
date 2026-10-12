# Recipe catalog

This catalog lists recipes currently supplied by OpsFeast. To ask your AI agent to create a recipe, share content or acquire someone else's work, start with the [user guide](../docs/recipes.md).

## Available recipes

| Recipe | Purpose | Implemented platform | Verification evidence | Usage |
| --- | --- | --- | --- | --- |
| [inventory-system](inventory/system/README.md) 0.2.0 | Seven fields covering hostname, system name/version, kernel and architecture | Linux, FreeBSD, macOS | Synthetic tests; macOS read-only initialization/inventory tested locally; real Linux/FreeBSD/SSH collection unverified | Dedicated runner, SSHScript ==5.0.0; see recipe README |

No other recipes are currently supplied, and there is no third-party catalog yet. Other inventory types remain future directions. Update this catalog when adding recipes, including purpose, version, platforms, evidence and usage. Author declarations are not substitutes for actual testing.

## Custom and third-party content

Users may create recipes in their own working directories or repositories without forking Ops. Custom recipes within a management directory can be selected through explicit `./recipes/...` paths. However, the current runner supports only the documented inventory-system descriptor/implementation contract; reviewed custom platform implementations can execute within it. A general execution interface and third-party installer are not implemented.

- [Create a custom recipe](../docs/recipe-authoring.md)
- [Share one or multiple recipes](../docs/recipe-sharing.md)
- [Acquire, review, verify and authorize installation](../docs/recipe-acquisition.md)
- [Recipes skill for AI agents](../skills/opsfeast-recipes/SKILL.md)

## Recipe documentation requirements

Recipe authors should follow the shared [vision and design principles](../docs/vision.md) and [authoring guide](../docs/recipe-authoring.md). Design for human intent, repeatable execution with less model work, community reuse, clear authorization and outcomes supported by evidence.

Each recipe should document its purpose, supported and tested platforms, SSHScript compatibility, dependencies, required permissions, inputs, outputs, side effects and verification method.

Collection recipes should retain observation sources and timestamps and distinguish success, permission denial, unsupported operations, timeouts and parsing failures.

The first result contract and synthetic example live with inventory-system. The runner supports inventory-system implementations with a shared schema, not arbitrary recipe IDs.

_Last modified: 2026-10-12_
