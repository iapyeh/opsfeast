# Documentation

This directory contains architecture, getting-started instructions, diagnostic procedures and project decisions.

Start with the shared [vision and design principles](vision.md): human intent, lower learning burden, token efficiency through reusable recipes, community collaboration, explicit authorization and verifiable outcomes. Project contributors and recipe authors follow the same direction.

- [Ecosystem and naming](ecosystem.md): OpsFeast, OpsBuffet, roles and repository boundaries.
- [Rename compatibility and migration](migration.md): old CLI, configuration preservation and optional migration.

## Command-line tools

- **[Recipe sources and inputs](recipe-sources.md)**: checkout/profile/registered roots, shorthand selections, variable contracts, enabled flags and per-run exclusions.
- **[Complete CLI reference](cli.md)**: opsfeast.py subcommands, run_recipe.py options, defaults, platform dispatch, cache behavior, outputs, storage and exit codes for humans and agents.
- [Host initialization and diagnostics](host-diagnostics.md): detailed platform/credential semantics and su/sudo verification limits.

## Configuration guide

- [First-use walkthrough](first-use.md): clone the repository, give its path to an agent, review and authorize setup, and see what to configure next; includes copyable prompts and an isolated trial.
- [Getting started with OpsFeast](getting-started.md): shared human/agent entry point, prerequisites, authorized setup and next steps.
- [Skill sources and updates](skill-updates.md): public download source, comparison, candidate staging and authorized periodic checks.
- [Management environments and profiles](profiles.md): named and external directories, registration, default selection and legacy locator compatibility.
- [Connect your first host](first-host.md): minimal YAML, copyable checks and connection commands, then practical authentication, jump, sudo and su cases.
- [Host configuration and hosts.yaml](hosts-yaml.md): proposed configuration rules for users and AI agents; includes initialization and configuration checks; a minimal inventory-system runner is documented in the [recipe guide](../recipes/inventory/system/README.md).

## Initial decisions

- The central project is named OpsFeast; its repository is `opsfeast`.
- Built-in recipes live under `recipes/`; users may author and share their own recipes in separate repositories or archives. Generic execution and distribution tooling remain planned.
- SSHScript remains the currently supported execution foundation; other backends are a design direction, not implemented support.
- Obsidian, AI agent workflows, and compliance evidence collection are integrations or functional areas, not restrictions on the project name.
- The public repository contains tools and examples. User operational data stays in the user's environment.
- Initial target platforms are Linux, FreeBSD, and macOS. Actual support will be declared per recipe after verification.

## Agent instructions

- [Public and local agent guidance](agent-guidance.md): shared tracked instructions, optional private settings, discovery behavior and checks before publication.

## Recipe ecosystem guides

- [Use, create and share recipes](recipes.md): available content and copyable human prompts.
- [Recipe authoring](recipe-authoring.md): knowledge sources, deliverable requirements, evidence and current runner limits.
- [Share and package recipes](recipe-sharing.md): one or many recipes, GitHub and ZIP/tar.gz, allowlists, provenance and signature preparation.
- [Acquire, review and install recipes](recipe-acquisition.md): candidate acquisition, integrity and publisher verification, behavior review, authorized installation and use.
- [Recipes skill](../skills/opsfeast-recipes/SKILL.md): agent routing to these guides and the full SSHScript skill.

## Next design work

Version the generic recipe contract and runner interface, then implement candidate acquisition, installation records and distribution tools according to the guides above. The current guides do not claim those tools exist. Continue real Linux/FreeBSD/SSH and native su/sudo validation and the collect-record-repeat-compare workflow, including preservation of human notes.

_Last modified: 2026-10-13_
