# Recipe catalog

This catalog lists recipes currently supplied by SSHScript Ops. To ask your AI agent to create a recipe, share content or acquire someone else's work, start with the [user guide](../docs/recipes.md).

## Available recipes

| Recipe | Purpose | Implemented platform | Verification evidence | Usage |
| --- | --- | --- | --- | --- |
| [inventory-system](inventory/system/README.md) 0.1.0 | Seven fields covering hostname, system name/version, kernel and architecture | Linux | Synthetic tests; macOS unsupported-platform path tested locally; real Linux/SSH collection unverified | Dedicated runner, SSHScript ==5.0.0; see recipe README |

No other recipes are currently supplied, and there is no third-party catalog yet. FreeBSD/macOS support and other inventory types are future directions, not available collectors. Update this catalog when adding recipes, including purpose, version, platforms, evidence and usage. Author declarations are not substitutes for actual testing.

## Custom and third-party content

Users may create recipes in their own working directories or repositories without forking Ops. Custom recipes within a management directory can be selected through explicit `./recipes/...` paths. However, the current runner accepts only the exact built-in inventory-system bundle, not arbitrary custom code. A general execution interface and third-party installer are not implemented.

- [Create a custom recipe](../docs/recipe-authoring.md)
- [Share one or multiple recipes](../docs/recipe-sharing.md)
- [Acquire, review, verify and authorize installation](../docs/recipe-acquisition.md)
- [Recipes skill for AI agents](../skills/sshscript-ops-recipes/SKILL.md)

## Recipe documentation requirements

Recipe authors should follow the shared [vision and design principles](../docs/vision.md) and [authoring guide](../docs/recipe-authoring.md). Design for human intent, repeatable execution with less model work, community reuse, clear authorization and outcomes supported by evidence.

Each recipe should document its purpose, supported and tested platforms, SSHScript compatibility, dependencies, required permissions, inputs, outputs, side effects and verification method.

Collection recipes should retain observation sources and timestamps and distinguish success, permission denial, unsupported operations, timeouts and parsing failures.

The first result contract and synthetic example live with inventory-system. The runner currently supports only the exact inventory-system bundle, not arbitrary recipe execution.
