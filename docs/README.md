# Documentation

This directory will contain architecture, getting-started instructions, and project decisions.

## Configuration guide

- [初次使用 SSHScript Ops](getting-started.md): shared human/agent entry point, prerequisites, authorized setup and next steps.
- [Skill 下載與更新檢查](skill-updates.md): public download source, comparison, candidate staging and authorized periodic checks.

- [管理 hosts.yaml 與主機設定](hosts-yaml.md): proposed configuration rules for users and AI agents; includes initialization and configuration checks; a minimal inventory-system runner is documented in the [recipe guide](../recipes/inventory/system/README.md).

## Initial decisions

- The central project is named SSHScript Ops; its repository is `sshscript-ops`.
- Recipes are a component under `recipes/`, rather than a separate repository initially.
- SSHScript remains the separate execution foundation.
- Obsidian, AI agent workflows, and compliance evidence collection are integrations or functional areas, not restrictions on the project name.
- The public repository contains tools and examples. User operational data stays in the user's environment.
- Initial target platforms are Linux, FreeBSD, and macOS. Actual support will be declared per recipe after verification.

## Next design work

Define the first inventory recipe, its output contract, the user's local management directory, and the record update rules. Then verify the full collect-record-repeat-compare workflow before broadening the scope.
