# Documentation

For chat-owned live SSHScript execution and streamed Console output, use [Console worker 0.1.0](console-agent.md).


- [Web host configuration](web-hosts.md): real host creation, connection/groups, revision checks and confirmed deletion.

## Interactive Console

For the real opt-in Web Console, server-push serialization, confirmation controls, recovery and agent CLI, read [interactive Console protocol 0.1.0](interactive-console.md). Synthetic host-page drafts remain separate.

[Local administrator and profiles](web-administrator.md) covers owner-entered
credentials, login/session limits and Core-backed profile configuration.


Use [shared settings](web-settings.md) for the Web area, current site CLI/API,
bundled defaults and planned hosts/recipes/defaults/retention configuration.


For Web personalization and upgrade-preserved installation identity/site assets,
read [presentation](site-presentation.md), [persistent storage](installation-storage.md)
and the [Web preview](../web/README.md). Profile management roots are separate.

Use [recipe classification and location](recipe-taxonomy.md) for the current bundled paths, variable-depth domain/action convention, user profile/shared-source placement and relocation effects on configuration, jobs, consumers and historical evidence.

For agents operating OpsFeast or developing Python integrations, start with [the existing tool/module capability map](agent-capabilities.md) and [skill index](../skills/README.md). Reuse suitable capabilities before creating new implementations.

This directory contains architecture, getting-started instructions, diagnostic procedures and project decisions.

Start with the shared [vision and design principles](vision.md): human intent, lower learning burden, token efficiency through reusable recipes, community collaboration, explicit authorization and verifiable outcomes. Project contributors and recipe authors follow the same direction.

- [Ecosystem and naming](ecosystem.md): OpsFeast, OpsBuffet, roles and repository boundaries.
- [Rename compatibility and migration](migration.md): old CLI, configuration preservation and optional migration.

## Command-line tools

- **[Recipe sources and inputs](recipe-sources.md)**: checkout/profile/registered roots, shorthand selections, variable contracts, enabled flags and per-run exclusions.
- **[Complete CLI reference](cli.md)**: opsfeast.py subcommands, opsfeast.py recipes run options, defaults, platform dispatch, cache behavior, outputs, storage and exit codes for humans and agents.
- [Host initialization and diagnostics](host-diagnostics.md): detailed platform/credential semantics and su/sudo verification limits.

## Configuration guide

- [First-use walkthrough](first-use.md): clone the repository, give its path to an agent, review and authorize setup, and see what to configure next; includes copyable prompts and an isolated trial.
- [Getting started with OpsFeast](getting-started.md): shared human/agent entry point, prerequisites, authorized setup and next steps.
- [Skill sources and updates](skill-updates.md): public download source, comparison, candidate staging and authorized periodic checks.
- [Management environments and profiles](profiles.md): named and external directories, registration, default selection and legacy locator compatibility.
- [Connect your first host](first-host.md): minimal YAML, copyable checks and connection commands, then practical authentication, jump, sudo and su cases.
- [Host configuration and hosts.yaml](hosts-yaml.md): proposed configuration rules for users and AI agents; includes initialization and configuration checks; a minimal inventory-system runner is documented in the [recipe guide](../recipes/system/inventory/overview/README.md).

## Initial decisions

- The central project is named OpsFeast; its repository is `opsfeast`.
- Built-in recipes live under `recipes/`; users may author and share their own recipes in separate repositories or archives. Python-session execution is implemented through opsfeast.py recipes run; distribution tooling remains planned.
- SSHScript remains the currently supported execution foundation; other backends are a design direction, not implemented support.
- Obsidian, AI agent workflows, and compliance evidence collection are integrations or functional areas, not restrictions on the project name.
- The public repository contains tools and examples. User operational data stays in the user's environment.
- Initial target platforms are Linux, FreeBSD, and macOS. Actual support will be declared per recipe after verification.

## Agent instructions

For Python composition, read the [Core API contract](core-api.md) and
[authorized temporary operation guide](core-agent-operations.md): host-ID
dictionaries, literal shell text, per-command deadlines, failure evidence and
the route from exploration to reusable recipes.

- [Public and local agent guidance](agent-guidance.md): shared tracked instructions, optional private settings, discovery behavior and checks before publication.

## Recipe ecosystem guides

- [Use, create and share recipes](recipes.md): available content and copyable human prompts.
- [Recipe catalog, reports and reuse](recipe-experience.md): list/show/run, raw-result queries, offline reports/artifacts, basic HTML, explicit-file bundles and saved jobs.
- [Parameterized recipe execution](recipe-execution.md): Python-session 0.1.0, descriptor 0.3.0, --var/JSON input files, entrypoints, results and limits.
- [Recipe authoring](recipe-authoring.md): knowledge sources, deliverable requirements, evidence and current runner limits.
- [Share and package recipes](recipe-sharing.md): one or many recipes, GitHub and ZIP/tar.gz, allowlists, provenance and signature preparation.
- [Acquire, review and install recipes](recipe-acquisition.md): candidate acquisition, integrity and publisher verification, behavior review, authorized installation and use.
- [Recipes skill](../skills/opsfeast-recipes/SKILL.md): agent routing to these guides and the full SSHScript skill.

## Next design work

Extend the implemented Python-session contract only with versioned, tested capabilities. Implement candidate acquisition, installation records and distribution tools according to the guides above. The current guides do not claim those tools exist. Continue real Linux/FreeBSD/SSH and native su/sudo validation and the collect-record-repeat-compare workflow, including preservation of human notes.

## Host reference IP addresses

[Host reference IPs](host-reference-ips.md) explains automatic updates from saved
inventory, read-only hosts list/show and Core queries, source times, unknown/empty
states, reference-only use and current platform limits.

For interpreter/package failures before a host connection, start with [SSHScript runtime diagnosis and repair](runtime-troubleshooting.md): version mismatch, duplicate metadata, source checks, CLI/TUI evidence and selected-environment repair.


For the independent agent-written Console transcript reader, see [console records](console-records.md): 0.2.0 block append, bounded snapshot/SSE, paged content, human form replies and agent wait; login only, no remote execution adapter.

*Last modified: 2026-11-02 17:03:25*
