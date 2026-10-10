# AI Agent Guidance

This directory will contain AI agent entry points and skills for establishing and maintaining a user's operations environment.

Guidance should help agents discover recipes, check compatibility and prerequisites, interpret execution status, maintain records, and verify outcomes. General Markdown guidance should remain usable without a skill loader.

SSHScript execution semantics belong to the SSHScript project. Guidance here should reference the appropriate SSHScript version rather than duplicate its API documentation.

## Available repository skill

- [sshscript-ops-hosts](sshscript-ops-hosts/SKILL.md): create, edit, and review a user management directory's `hosts.yaml` and included YAML, using the [configuration guide](../docs/hosts-yaml.md).

This skill currently relies on the repository layout and can be read directly by an agent. The `tools/my_ops.py` utility initializes and validates management configuration. No automatic skill installer is provided. The minimal inventory-system runner is described in the [recipe guide](../recipes/inventory/system/README.md).
