# Documentation

This directory will contain architecture, getting-started instructions, and project decisions.

## Configuration guide

- [人類使用者的第一次體驗](first-use.md): clone the repository, give its path to an agent, review and authorize setup, and see what to configure next; includes copyable prompts and an isolated trial.
- [初次使用 SSHScript Ops](getting-started.md): shared human/agent entry point, prerequisites, authorized setup and next steps.
- [Skill 下載與更新檢查](skill-updates.md): public download source, comparison, candidate staging and authorized periodic checks.
- [管理環境與 profiles](profiles.md): named and external directories, registration, default selection and legacy locator compatibility.
- [管理 hosts.yaml 與主機設定](hosts-yaml.md): proposed configuration rules for users and AI agents; includes initialization and configuration checks; a minimal inventory-system runner is documented in the [recipe guide](../recipes/inventory/system/README.md).

## Initial decisions

- The central project is named SSHScript Ops; its repository is `sshscript-ops`.
- Built-in recipes live under `recipes/`; users may author and share their own recipes in separate repositories or archives. Generic execution and distribution tooling remain planned.
- SSHScript remains the separate execution foundation.
- Obsidian, AI agent workflows, and compliance evidence collection are integrations or functional areas, not restrictions on the project name.
- The public repository contains tools and examples. User operational data stays in the user's environment.
- Initial target platforms are Linux, FreeBSD, and macOS. Actual support will be declared per recipe after verification.

## Recipe ecosystem guides

- [Use, create and share recipes](recipes.md): available content and copyable human prompts.
- [Recipe authoring](recipe-authoring.md): knowledge sources, deliverable requirements, evidence and current runner limits.
- [Share and package recipes](recipe-sharing.md): one or many recipes, GitHub and ZIP/tar.gz, allowlists, provenance and signature preparation.
- [Acquire, review and install recipes](recipe-acquisition.md): candidate acquisition, integrity and publisher verification, behavior review, authorized installation and use.
- [Recipes skill](../skills/sshscript-ops-recipes/SKILL.md): agent routing to these guides and the full SSHScript skill.

## Next design work

Version the generic recipe contract and runner interface, then implement candidate acquisition, installation records and distribution tools according to the guides above. The current guides do not claim those tools exist. Continue real Linux/SSH validation and the collect-record-repeat-compare workflow, including preservation of human notes.
