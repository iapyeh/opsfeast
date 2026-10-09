# Documentation

This directory will contain architecture, getting-started instructions, and project decisions.

## Initial decisions

- The central project is named SSHScript Ops; its repository is `sshscript-ops`.
- Recipes are a component under `recipes/`, rather than a separate repository initially.
- SSHScript remains the separate execution foundation.
- Obsidian, AI agent workflows, and compliance evidence collection are integrations or functional areas, not restrictions on the project name.
- The public repository contains tools and examples. User operational data stays in the user's environment.
- Initial target platforms are Linux, FreeBSD, and macOS. Actual support will be declared per recipe after verification.

## Next design work

Define the first inventory recipe, its output contract, the user's local management directory, and the record update rules. Then verify the full collect-record-repeat-compare workflow before broadening the scope.
