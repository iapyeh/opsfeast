For login-to-river handoff, use [browser readiness 0.1.0](browser-events.md): open the exact river so login retains its scoped next URL, then continue already-authorized work without waiting for a "logged in" reply. The reader reports `reader.opened` and the owner controller pushes `browser_event` on its existing stdout; this is readiness evidence, never approval or automatic model wakeup. Separate installations use namespaced authentication/editing cookies.

For the agreed product boundaries, Host ID/history/deletion decisions and staged
daemon direction, read [system profiling architecture](system-profiling.md).
For shipped capability discovery and saved host Web/CLI/Python views, read
[profiling 0.1.0](profiling.md).

For per-installation Web ports and agent ownership, follow [Web endpoint 0.1.0](web-server.md): `.opsfeast.yaml` stores `web.port`; first launch allocates it, `--port N` persists an explicit choice, and the returned URL is authoritative. Reuse `opsfeast.web_settings.read_port/configure_port/bind_server` for checkout-level operations; occupied ports never authorize stopping an unidentified process.

For agent website operations, use the [memory-only owner controller](agent-owner.md): independent highest Web capability, administrator/password setup, API requests and Console workers without token files. Human authorization remains required.

# Documentation

For shared multi-host investigations, see [shared task river 0.1.0](shared-console.md): independent connections, host-tagged blocks, per-host TAB focus and one chronological river.

For chat-owned live SSHScript execution and streamed Console output, use [Console worker 0.3.0](console-agent.md).


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

## Host experience

[Host notes](host-notes.md): review/edit private host knowledge on the Web, share CLI/Python/API operations, resolve conflicts and confirm experience extraction.



For actual local Web data pages, Profile scope and public source readers, see [saved-data workspace](web-workspace.md).

For official version comparisons and the human-confirmed Agent update instruction,
see [version checks](web-updates.md). Settings scope and ownership are described in
[Settings hierarchy](web-settings.md).


For incomplete-property causes, Web/CLI inspection and reference-IP recovery, see [result diagnostics](result-diagnostics.md) and [reference addresses](host-reference-ips.md).


For the bundled recipe audit and delivered/remaining profiling acquisition gaps,
read [coverage review](profiling-coverage.md). New Linux account and process
snapshots use separate recipes and shared retention/views; see the profiling guide.


For SSH/sudo/firewall policy, time synchronization and logging configuration
collection, read [Linux policy profiling](linux-policy-profiling.md): five independent
recipes, contexts, native/configured/runtime boundaries, omissions and verification.

## Recipe menu and execution

[Choose dishes and run recipes in Web](web-recipe-menu.md): purposes, suggested
combinations, the full profiling target, explicit host/identity review, typed
inputs, confirmation, progress/stop, receipts and shared agent interfaces.

[Web inventory scope and report artifacts](web-recipe-menu.md) now covers the
complete browser workflow for jobs/individual sensors and saved report viewing,
including preview/download, provenance and verification limits.


## Inventory composition design rationale

The [inventory routine/meal design](inventory-routine-design.md) records the agreed rationale for independent recipes, host-owned connection reuse and verified login/root phases. These are now implemented; use [the current routine contract](recipe-routines.md) for invocation, retention and limits.


## Recipe routines and meals

Use [routines and shared-connection meals 0.1.0](recipe-routines.md) for current standalone/composed inventory, permission grouping, scope borrowing, selectors, durable checkpoints, independent retention and Web execution. The original design document remains rationale; it is no longer a proposed-only feature.

## Inventory child consumers and reports

Use [the inventory dependency map](inventory-consumers.md) for current
child references, exact report filters, subscription/read-filter updates and
unchanged historical ownership. Vault already subscribes to all observations;
backup-check has no inventory dependency. Retention-summary keeps exact filters;
execution-summary 0.1.3 preserves child/meal outcomes and routine/connection evidence.
Saved-result collection_user is unknown for mixed/unverified routine actors. Existing
Overview-only filters are not aliases for children; private configuration and
historical records are never rewritten automatically. These read/presentation
interfaces require no host access; explicit report, dispatch or rebuild writes
need the human's corresponding scope.

*Last modified: 2026-11-10 17:31:30*
