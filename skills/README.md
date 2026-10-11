# AI Agent Guidance

This directory contains AI agent entry points and skills for establishing and maintaining a user's operations environment.

Guidance should help agents discover recipes, check compatibility and prerequisites, interpret execution status, maintain records, and verify outcomes. General Markdown guidance should remain usable without a skill loader.

SSHScript execution semantics belong to the SSHScript project. Guidance here should reference the appropriate SSHScript version rather than duplicate its API documentation.

## Available repository skills

- [sshscript-ops-hosts](sshscript-ops-hosts/SKILL.md): create, edit, and review a user management directory's `hosts.yaml` and included YAML, using the [configuration guide](../docs/hosts-yaml.md); initialize platform facts and perform requested connection/su/sudo diagnostics through the [diagnostic guide](../docs/host-diagnostics.md).
- [sshscript-ops-recipes](sshscript-ops-recipes/SKILL.md): discover, author and execute supported inventory implementations across platforms, share one or many recipes, and acquire, verify and review third-party candidates before authorized installation. Start with the [recipe user guide](../docs/recipes.md).

These skills rely on the repository layout and can be read directly by any agent. The full public SSHScript skill snapshot lives in `.agents/skills/sshscript/`, including references and SOURCE.json; its presence does not imply installation or automatic loading by a particular agent.

Start with the [getting-started guide](../docs/getting-started.md). The `tools/ops.py` utility initializes and validates management configuration. [Skill download and update checks](../docs/skill-updates.md) use `tools/skill_bundle.py` to compare or stage complete public SSHScript bundles; they do not activate skills or install them into agent-specific locations. The Ops hosts skill above is updated with this repository. The minimal inventory-system runner is described in the [recipe guide](../recipes/inventory/system/README.md).

_Last modified: 2026-10-11_
