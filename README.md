# OpsFeast

**Agent-Driven IT Operations. Human-Authorized.**

OpsFeast helps AI agents manage IT systems through reusable, verifiable and shareable recipes. People define goals, targets and authorization; agents handle planning and routine work within that scope and request human input for exceptions or decisions beyond it.

A **Feast** is your private management instance: configuration, selected recipes, execution records and results. **OpsBuffet** is the planned exchange platform for discovering, acquiring and sharing recipes, with separately operated public and enterprise instances. See [the ecosystem and naming guide](docs/ecosystem.md) for roles, repository responsibilities and implementation limits.

OpsFeast welcomes recipes built with different execution tools. When SSHScript fits the task and the authorized environment, prefer it for command execution and session orchestration. The project also serves as a practical showcase of SSHScript through reusable recipes and verifiable examples. User-selected tools and operational constraints take precedence; see the [tool selection workflow](docs/recipe-authoring.md#choose-execution-tools).

SSHScript is the currently supported execution foundation for the host diagnostics and dedicated inventory runner. Other tools require explicit dependencies and verifiable contracts; the open ecosystem direction does not implement additional runner backends.

Previously named **SSHScript Ops** (`sshscript-ops`), this repository now uses **OpsFeast** (`opsfeast`). The CLI is `tools/opsfeast.py`; the former `tools/ops.py` entrypoint and `import ops` are removed. Existing management directories and registrations remain usable without being moved or rewritten. See [the migration guide](docs/migration.md).

Read the **[command-line reference](docs/cli.md)** for every opsfeast.py command and run_recipe.py option, execution behavior, output, saved data and exit codes. It is the shared tool manual for administrators and AI agents. Agents should start with [For AI agents](#for-ai-agents) below for the learning order and complete skill sources.

## Why OpsFeast matters in the AI era

AI makes it easier to generate commands and scripts. Running real infrastructure still requires context: which host and account to use, what permissions are needed, what a command may change, and how to tell whether it worked. That context must survive beyond a single conversation.

OpsFeast gives you a place to organize that context and a common workflow for turning a request into a documented recipe. Your agent can help prepare the work; you define the goal and authorize the operations. Versioned code, explicit inputs and recorded evidence make the result easier to revisit, hand over and improve.

For a system administrator, the value is continuity: fewer repeated explanations, a clearer connection between scripts and the hosts they serve, and useful operational knowledge that can be shared with a colleague or another agent.

## What makes it useful

- **Bring order to your hosts.** Keep connection settings, jump hosts, accounts and recipe selections in your own management environment. Use named profiles to work with different groups of systems.
- **Run one inventory across different systems.** Select inventory/system for a mixed Linux, FreeBSD and macOS fleet; the runner discovers needed platform facts, chooses each implementation and saves a common result with versions and digests.
- **Check configured access before collection.** Use test-host for login/platform/account diagnostics, or test-su/test-sudo for explicit account tests, including independent su targets and repeated chains. Reports retain skipped and failed states.
- **Build recipes for your needs.** Give your agent a task and use the authoring guides to develop a recipe with documented inputs, outputs, permissions and verification evidence.
- **Describe the goal; let your agent handle the details.** The design aims to let administrators explain what they need and set operational boundaries while their agent learns the relevant skills, prepares the recipe and explains the result. You should not need to learn SSHScript APIs to request a workflow.
- **Spend fewer tokens on repeated work.** Use AI to develop, review and adapt recipes, then run their defined operations as code. Routine recipe execution does not require an LLM to generate each command again. Agent planning, reviews and interpretation can still consume tokens; minimum token usage is a design goal, not a measured guarantee.
- **Build through community collaboration.** Administrators can contribute their expertise as individual recipes or collections, share them in repositories or archives, and help each other improve documentation, compatibility and verification. The documented sharing workflows support this direction; automated distribution tools are still planned.
- **Keep knowledge you can share.** Package one recipe or a collection with its documentation, dependencies and synthetic examples. Others can review the content and adapt it to their environments.
- **Make evidence part of the workflow.** Distinguish observations from interpretations, configuration checks from execution, and successful commands from verified outcomes. Missing information stays unknown.
- **Keep control of your environment.** Real host data and credentials stay in your management environment. Third-party recipes follow a review and authorization workflow before installation; execution has its own scope.

The project is growing toward a recipe ecosystem. Today, it provides management-directory setup, configuration checks, explicit connection tests, and a system inventory recipe with automatic Linux/FreeBSD/macOS implementation selection and a dedicated runner. It also includes skills and guides for authoring, sharing and reviewing recipes. A general recipe runner and third-party installer are still planned; real Linux/SSH inventory validation is pending.

**[Take the first-use walkthrough](docs/first-use.md)** or **[explore the recipe catalog](recipes/README.md)** to get started.

## Safety and operational control

Managing infrastructure requires more than generating a plausible command. OpsFeast emphasizes reviewable recipes, explicit targets and permissions, and evidence that distinguishes success, failure, partial results and unknowns. Existing tools provide configuration and path checks; the inventory recipe defines its operations and records results with bounded command execution and cleanup handling.

Third-party recipes should be acquired as candidates, checked for integrity and publisher evidence, and reviewed for behavior before you authorize a concrete installation plan. Installation does not authorize execution. A matching checksum establishes consistency with that checksum; protection against source replacement requires trusted publisher evidence. Even a valid signature does not prove safe behavior. See the [acquisition and review guide](docs/recipe-acquisition.md).

These safeguards combine implemented checks with documented agent procedures. The project does not yet provide a general execution sandbox, machine-enforced approval records or a complete supply-chain verification system. Keeping operational files outside the public repository also does not prevent an agent from reading them; agents must avoid exposing secrets in prompts, reports and shared artifacts.

## A lower learning curve, with informed decisions

Our goal is for you to describe the desired result in ordinary language while your agent handles skills, configuration and execution details. You still define the systems in scope, provide authentication through an appropriate private channel, and authorize actions that may affect them. The agent should ask only for missing information that matters, explain consequences clearly and reuse context already supplied.

Today, that approach is supported by setup and connection tools, agent guides and the dedicated inventory runner. Arbitrary requests may require a new recipe, compatibility work and validation before use. We are building toward this experience; it is not yet a general system that can safely perform every IT task from a single sentence.

Read the [vision and design principles](docs/vision.md) for the shared direction followed by project contributors and recipe authors.

## Getting started with your AI agent

Start by cloning the repository:

```sh
git clone https://github.com/iapyeh/opsfeast.git
```

Open a new conversation with an agent that can read your local files, such as Codex or Hermes, and send this prompt after replacing the path with your clone's absolute directory:

> I am using OpsFeast for the first time. The repository is at `/absolute/path/to/opsfeast`. Read README.md, AGENTS.md and the getting-started guide, explain what the project can do and what environment it needs, and propose an initial setup. Do not install dependencies or initialize anything yet.

Review the proposal, then authorize setup. The agent should initialize your management directory and tell you where to configure host addresses, login accounts, authentication and recipes.

**[First-use walkthrough](docs/first-use.md)** provides copyable prompts for setup and skill update checks, expected results, and an optional isolated trial. The [getting-started guide](docs/getting-started.md) contains the detailed setup procedure for agents. The same Markdown workflow applies across agents; automatic skill discovery is optional.

The agent can inspect prerequisites with `python3 -B tools/check_environment.py`, explain the supported tools and propose a concrete setup. After authorization, it can install the dependencies in `requirements.txt` (or `requirements-init.txt` for initialization only), read the included skills, and run `tools/opsfeast.py init` and `check`. It then reports where to configure your hosts, accounts, authentication and recipe selection. Remote connection tests and collection require their own authorized scope.

The full SSHScript skill snapshot is included in Git. [Skill download and update instructions](docs/skill-updates.md) explain how to check the public bundle, stage a complete candidate and review compatibility. A user-authorized schedule may check for changes; checks never automatically replace skills or upgrade packages.

## For AI agents

Start here when a user asks you to use OpsFeast. Read the linked Markdown directly if your agent does not automatically discover project guidance or skills; no particular agent product or skill loader is required.

### Learn Ops and choose the relevant skill

1. Read [AGENTS.md](AGENTS.md) for project instructions, then any user-maintained `AGENTS.local.md` in this checkout. Local guidance is optional, private and not supplied by a clone; see [public and local guidance](docs/agent-guidance.md).
2. Read the [getting-started guide](docs/getting-started.md) for prerequisites and setup, and the [CLI reference](docs/cli.md) before selecting commands. It documents `tools/opsfeast.py` and `tools/run_recipe.py`, including arguments, defaults, side effects, saved data, results and exit codes. Use the interpreter selected by the user.
3. Select the task-specific skill below and follow its linked guides. Reuse already-read material when it remains applicable. Before designing features or writing recipes or documentation, read the [vision and design principles](docs/vision.md).

| Task | Start with |
| --- | --- |
| Manage profiles, hosts.yaml, platform facts or connection/su/sudo diagnostics | [Ops hosts skill](skills/opsfeast-hosts/SKILL.md), then [host diagnostics](docs/host-diagnostics.md) for tests |
| Discover, execute, author, share or review recipes | [Ops recipes skill](skills/opsfeast-recipes/SKILL.md), then the [recipe catalog](recipes/README.md) and selected recipe guide |
| Write or adapt SSHScript commands and sessions | [Included SSHScript skill](.agents/skills/sshscript/SKILL.md), its [Agent Guide](.agents/skills/sshscript/references/agent-guide.md), [version policy](.agents/skills/sshscript/references/versioning.md) and relevant [API guide](.agents/skills/sshscript/references/api-guide.md) sections |

Ops skills describe the management workflow; the SSHScript skill describes the execution library. The complete public SSHScript snapshot is included at `.agents/skills/sshscript/` and can be read offline. Its [SOURCE.json](.agents/skills/sshscript/SOURCE.json) records provenance, documentation contract and bundle digest. Verify the actual interpreter and SSHScript import/distribution versions against that contract before use. Bundled files do not imply installation or automatic loading by your agent.

### Obtain and update complete skills

The [official SSHScript AI agent entrypoint](https://iapyeh.github.io/sshscript/v3a/ai-agents/) provides the public guides and [complete skill ZIP](https://iapyeh.github.io/sshscript/v3a/ai-agents/downloads/sshscript-skill.zip). The `/v3a/` URL is not a package version; inspect the candidate's documentation contract.

When the user requests a check or authorizes downloading a candidate, run the applicable command from the Ops checkout with the selected interpreter:

```sh
# Compare the official bundle with the included snapshot; do not replace it.
python -B tools/skill_bundle.py check

# Download and validate a complete candidate into a directory that does not exist.
python -B tools/skill_bundle.py download .skill-downloads/sshscript-candidate
```

`check` downloads into memory and reports `unchanged` or `review_required`; a difference does not necessarily mean a newer version, and a failed check does not mean no update. `download` saves a candidate without activating it. Review compatibility and local changes before authorized application, replacing the complete snapshot including references and SOURCE.json. Downloading only `SKILL.md` is incomplete. Neither command installs or upgrades SSHScript. Follow the [skill download and update guide](docs/skill-updates.md) for result interpretation, review, application and authorized scheduled checks.

The **Ops hosts and recipes skills** ship with the [Ops repository](https://github.com/iapyeh/opsfeast), together with `docs/` and AGENTS.md; they are not part of the SSHScript ZIP. Obtain a trusted full clone or snapshot, preserve relative paths and record the actual commit. For updates, compare an isolated candidate's skills, accompanying guides and tool changes before authorized application. There is currently no separate Ops skill ZIP or automatic Ops skill update command. Direct reading is supported; installing into an agent requires its platform-specific procedure and the accompanying documents, as described in the update guide.

Reading these materials does not authorize installation, connections, privilege tests or recipe execution. Work within the user's requested scope and distinguish documented support, implemented behavior and actual verification evidence.

## Status

This repository is an initial project scaffold. It provides a Python utility for management-directory initialization, configuration inspection and validation, and explicit host connection tests. It also provides inventory-system collectors for Linux, FreeBSD and macOS, automatic host initialization and account diagnostics. Linux/FreeBSD have synthetic coverage; macOS has local read-only validation. Real SSH and native su/sudo validation remain pending.

See [host diagnostics](docs/host-diagnostics.md) for `host-init`, `test-host`, independent/chained `test-su` and multi-account `test-sudo`. Setup alone does not authorize these connection or privilege tests.

## Host configuration

See the [hosts.yaml user guide](docs/hosts-yaml.md) for the proposed management-directory format, includes, jump hosts, host variables, and recipe selection. AI agents can use the repository skill [opsfeast-hosts](skills/opsfeast-hosts/SKILL.md) to help maintain these settings. On a fresh checkout, use `python tools/opsfeast.py init` to create the `main` profile at `feasts/main/`, and `python tools/opsfeast.py check` to validate it (Python 3.11+ and PyYAML required). Use `python tools/opsfeast.py test-connection <host-id>` to connect and run `hostname` and `date` (SSHScript 4.0.1+ also required). New checkouts use the ignored `.opsfeast.yaml` registry and new instances contain `feast.yaml`. Existing `.my-ops.yaml` registries and `my-ops.yaml` definitions remain supported; existing named profiles are reused by init. Use `init inventory` to create `feasts/inventory`, `attach /existing/directory` to register existing settings, `profiles` to list environments, and `use inventory` to switch the default. Adding profiles preserves an existing default. See the [profile guide](docs/profiles.md). Use `--profile NAME` on either tool for one invocation without changing the default, or pass an explicit directory. Registered relative paths are located from the tool checkout; relative CLI directory paths use the shell directory. Initialization, dumps and configuration checks do not connect. Use `python -B tools/run_recipe.py inventory/system --host <host-id>` to run system inventory directly from this checkout. No copying into the instance is needed after updating this repository. Recipe and targets are required; put the recipe first or use `--recipe DIRECTORY` elsewhere, and select hosts/groups with `--host`/`--group` or every configured host with `--all`. Use `--root` for an explicit management directory. Register external clones in entry hosts.yaml recipe_sources, select profile content with :inventory/system or named content with community:inventory/system, and attach vars to matching recipe selectors. Source/host enabled flags and --all --exclude support temporary selection controls; see [sources and inputs](docs/recipe-sources.md); see [its guide](recipes/inventory/system/README.md) for runtime requirements and validation limits.

## Initialize and diagnose a host

After configuring a host and authorizing its tests, use the selected interpreter from this checkout:

```sh
python -B tools/opsfeast.py test-host host-01
python -B tools/opsfeast.py host-init host-01
python -B tools/opsfeast.py test-su host-01 --chain user2 user3 --chain user3 user2
python -B tools/opsfeast.py test-sudo host-01 user2 user3 --run-as root
python -B tools/run_recipe.py inventory/system --host host-01 host-02 host-03
```

Test-host checks login, reuses or initializes platform facts, tests the login account's sudo only when the credential precedence rule selects a password (including the account password), and independently tests su to other declared accounts. Direct host-init always refreshes facts. Runner automatically initializes facts when needed, dispatches each host to its platform implementation, and records recipe/implementation/schema versions. Read the [diagnostic guide](docs/host-diagnostics.md) for credentials, skipped states, cache limits and management-root arguments, and the [inventory guide](recipes/inventory/system/README.md) before executing custom code. A general recipe runner and extension installer remain planned.

## Find, create and share recipes

The [recipe catalog](recipes/README.md) lists available content, supported platforms and actual verification evidence. Use `python -B tools/opsfeast.py inspect-recipe` to discover checkout recipes, or `python -B tools/opsfeast.py inspect-recipe inventory/system --platform freebsd --platform openbsd` to view a focused summary of requested platform support and gaps. Default output is concise; add `--details` for full human-readable content or `--json` for the complete descriptor and agent-readable report. Inspection reads files without running recipes or connecting; see the [CLI reference](docs/cli.md#inspect-recipes-and-platform-gaps) for paths, evidence limits and exit codes. The [recipe user guide](docs/recipes.md) provides copyable prompts for asking your AI agent to create a recipe, share one or several recipes through GitHub or ZIP/tar.gz, and review someone else's recipes before installation.

Agents should read the repository [recipes skill](skills/opsfeast-recipes/SKILL.md) and its task-specific guides. [Skill sources and updates](docs/skill-updates.md) explain where to obtain the complete SSHScript knowledge bundle and Ops guidance. Third-party content is checked for integrity, publisher evidence and behavior before a concrete installation plan is authorized; installation does not authorize execution. These are documented agent workflows. A general runner, third-party installer, pack/publish CLI and lockfile are not yet implemented.

## Planned workflow

1. Register hosts and define connection settings in the user's own environment.
2. Collect inventory and state using versioned recipes.
3. Organize host and service records, retaining the sources and timestamps of observations.
4. Identify changes and investigate problems using runbooks.
5. Perform authorized maintenance and verify its outcome.
6. Update records while preserving human notes and operational history.

## Repository structure

| Directory | Purpose |
| --- | --- |
| [recipes/](recipes/README.md) | Reusable collection, inspection, maintenance, and repair tools |
| [schemas/](schemas/README.md) | Contracts for host records, observations, and execution results |
| [runbooks/](runbooks/README.md) | Procedures for investigation, maintenance, and outcome verification |
| [templates/](templates/README.md) | Example configuration and management document templates |
| [skills/](skills/README.md) | Guidance for AI agents using the management framework |
| [docs/](docs/README.md) | Architecture, getting started, and project decisions |
| [tests/](tests/README.md) | Reproducible verification of recipes and workflows |

## Design direction

- Target Linux, FreeBSD, and macOS initially; each recipe will declare its own supported and tested environments.
- Keep observations separate from AI interpretations. Missing or failed observations must not become zero values or claims of success.
- Describe prerequisites, permissions, side effects, and limitations for each operational tool.
- Keep actual host inventories, credentials, collected data, and operational records in the user's own environment.
- Support documentation integrations such as Obsidian without making a specific editor mandatory.
- Allow future mapping of observations to audit controls and compliance evidence requirements.

## First milestone

Complete one workflow for a small set of hosts: collect basic inventory, create host records, repeat collection, and record changes while preserving human notes.

## Relationship to SSHScript

[SSHScript](https://github.com/iapyeh/sshscript) remains a separate execution library. OpsFeast builds operational content and a management framework on that foundation. Recipes initially live in this repository so their contracts, documentation, and workflows can evolve together.

_Last modified: 2026-10-12_
