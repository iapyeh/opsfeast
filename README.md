# OpsFeast

**Agent-Driven IT Operations. Human-Authorized.**

OpsFeast helps AI agents manage IT systems through reusable, verifiable and shareable recipes. People define goals, targets and authorization; agents handle planning and routine work within that scope and request human input for exceptions or decisions beyond it.

A **Feast** is your private management instance: configuration, selected recipes, execution records and results. **OpsBuffet** is the planned exchange platform for discovering, acquiring and sharing recipes, with separately operated public and enterprise instances. See [the ecosystem and naming guide](docs/ecosystem.md) for roles, repository responsibilities and implementation limits.

OpsFeast welcomes recipes built with different execution tools. When SSHScript fits the task and the authorized environment, prefer it for command execution and session orchestration. The project also serves as a practical showcase of SSHScript through reusable recipes and verifiable examples. User-selected tools and operational constraints take precedence; see the [tool selection workflow](docs/recipe-authoring.md#choose-execution-tools).

SSHScript is the currently supported execution foundation for the host diagnostics and recipe execution. Other tools require explicit dependencies and verifiable contracts; the open ecosystem direction does not implement additional runner backends.

Previously named **SSHScript Ops** (`sshscript-ops`), this repository now uses **OpsFeast** (`opsfeast`). The CLI is `tools/opsfeast.py`; the former `tools/ops.py` entrypoint and `import ops` are removed. Existing management directories and registrations remain usable without being moved or rewritten. See [the migration guide](docs/migration.md).

Read the **[command-line reference](docs/cli.md)** for every opsfeast.py command and run_recipe.py option, execution behavior, output, saved data and exit codes. It is the shared tool manual for administrators and AI agents. Agents should start with [For AI agents](#for-ai-agents) below for the learning order and complete skill sources.

## Why OpsFeast matters in the AI era

AI makes it easier to generate commands and scripts. Running real infrastructure still requires context: which host and account to use, what permissions are needed, what a command may change, and how to tell whether it worked. That context must survive beyond a single conversation.

OpsFeast gives you a place to organize that context and a common workflow for turning a request into a documented recipe. Your agent can help prepare the work; you define the goal and authorize the operations. Versioned code, explicit inputs and recorded evidence make the result easier to revisit, hand over and improve.

For a system administrator, the value is continuity: fewer repeated explanations, a clearer connection between scripts and the hosts they serve, and useful operational knowledge that can be shared with a colleague or another agent.

## What makes it useful

- **Bring order to your hosts.** Keep connection settings, jump hosts, accounts and recipe selections in your own management environment. Use named profiles to work with different groups of systems.
- **Run one inventory across different systems.** Select inventory/system for a mixed Linux, FreeBSD, macOS and ESXi fleet; the runner discovers needed platform facts, chooses each implementation and saves a common result with versions and digests.
- **Check configured access before collection.** Use test-host for login/platform/account diagnostics, or test-su/test-sudo for explicit account tests, including independent su targets and repeated chains. Reports retain skipped and failed states.
- **Build recipes for your needs.** Give your agent a task and use the authoring guides to develop a recipe with documented inputs, outputs, permissions and verification evidence.
- **Describe the goal; let your agent handle the details.** The design aims to let administrators explain what they need and set operational boundaries while their agent learns the relevant skills, prepares the recipe and explains the result. You should not need to learn SSHScript APIs to request a workflow.
- **Spend fewer tokens on repeated work.** Use AI to develop, review and adapt recipes, then run their defined operations as code. Routine recipe execution does not require an LLM to generate each command again. Agent planning, reviews and interpretation can still consume tokens; minimum token usage is a design goal, not a measured guarantee.
- **Build through community collaboration.** Administrators can contribute their expertise as individual recipes or collections, share them in repositories or archives, and help each other improve documentation, compatibility and verification. The documented sharing workflows support this direction; automated distribution tools are still planned.
- **Keep knowledge you can share.** Package one recipe or a collection with its documentation, dependencies and synthetic examples. Others can review the content and adapt it to their environments.
- **Make evidence part of the workflow.** Distinguish observations from interpretations, configuration checks from execution, and successful commands from verified outcomes. Missing information stays unknown.
- **Keep control of your environment.** Real host data and credentials stay in your management environment. Third-party recipes follow a review and authorization workflow before installation; execution has its own scope.

The project is growing toward a recipe ecosystem. Today, it provides management-directory setup, configuration checks, explicit connection tests, and a system inventory recipe with automatic Linux/FreeBSD/macOS/ESXi implementation selection and a shared recipe execution tool. It also includes skills and guides for authoring, sharing and reviewing recipes. Python-session recipes can also run through `run_recipe.py` with typed invocation inputs; see the [execution contract](docs/recipe-execution.md) and [port check](recipes/check/port/README.md). A third-party installer remains planned; real Linux/SSH inventory validation is pending.

**[Take the first-use walkthrough](docs/first-use.md)** or **[explore the recipe catalog](recipes/README.md)** to get started.

## Safety and operational control

Managing infrastructure requires more than generating a plausible command. OpsFeast emphasizes reviewable recipes, explicit targets and permissions, and evidence that distinguishes success, failure, partial results and unknowns. Existing tools provide configuration and path checks; the inventory recipe defines its operations and records results with bounded command execution and cleanup handling.

Third-party recipes should be acquired as candidates, checked for integrity and publisher evidence, and reviewed for behavior before you authorize a concrete installation plan. Installation does not authorize execution. A matching checksum establishes consistency with that checksum; protection against source replacement requires trusted publisher evidence. Even a valid signature does not prove safe behavior. See the [acquisition and review guide](docs/recipe-acquisition.md).

These safeguards combine implemented checks with documented agent procedures. The project does not yet provide a general execution sandbox, machine-enforced approval records or a complete supply-chain verification system. Keeping operational files outside the public repository also does not prevent an agent from reading them; agents must avoid exposing secrets in prompts, reports and shared artifacts.

## A lower learning curve, with informed decisions

Our goal is for you to describe the desired result in ordinary language while your agent handles skills, configuration and execution details. You still define the systems in scope, provide authentication through an appropriate private channel, and authorize actions that may affect them. The agent should ask only for missing information that matters, explain consequences clearly and reuse context already supplied.

Today, that approach is supported by setup and connection tools, agent guides and recipe execution through run_recipe.py. Arbitrary requests may require a new recipe, compatibility work and validation before use. We are building toward this experience; it is not yet a general system that can safely perform every IT task from a single sentence.

Read the [vision and design principles](docs/vision.md) for the shared direction followed by project contributors and recipe authors.

## Getting started with your AI agent

Use an **AI coding tool** that can read your local project files and run commands, such as Codex, Antigravity or Claude Code. This guide uses **project/workspace** for the directory opened in that tool; the exact UI labels vary. An ordinary chat without local file access is not enough for these steps. No particular agent product or skill loader is required.

### 1. Create a project/workspace

Choose the local directory where you want OpsFeast to live, then create or open a project/workspace pointing to that directory in your AI coding tool. It can be empty; you do not need to clone OpsFeast yourself. Start a new agent conversation in that project with local file/command access and network access to GitHub. If the agent runs on another machine, choose the directory on that machine.

### 2. Paste the single first-use prompt

Paste this unchanged. “This project's directory” means the active workspace; no path replacement or separate clone/setup prompt is needed.

```text
Help me get started with OpsFeast in this project's directory. I authorize cloning https://github.com/iapyeh/opsfeast.git here; use an opsfeast subdirectory if the current directory is not empty, and preserve existing files. Reuse an existing OpsFeast checkout if present.

Read the checkout's README.md, AGENTS.md and docs/getting-started.md, then follow their first-use guidance. Check prerequisites without making changes, propose a local setup you can perform for me, and ask for my approval. Do not install software, create environments or initialize profiles until I agree.
```

The agent clones into an empty workspace, or into a new `opsfeast/` subdirectory when the workspace already contains files. It verifies and reuses an existing OpsFeast checkout rather than cloning again, preserving its changes and configuration. It uses the actual checkout as its working directory; you do not need to reopen the project just because the checkout is a subdirectory. A conflicting destination, missing Git, denied access or failed download is reported with the specific help needed; the agent does not overwrite files or install software to resolve those blockers without approval.

The cloned `AGENTS.md` and getting-started guide provide the reply-language rules and setup approval handoff, so they do not need to be repeated in the prompt. To explicitly request Traditional Chinese, append `Reply to me in Traditional Chinese (Taiwan).` Automatic language detection depends on what your agent can access; an explicit language request takes priority.

The setup proposal should reuse a compatible, working Python when available and install project packages from the relevant requirements files. Extra system packages need actual failure evidence or the chosen Python distribution's official dependency metadata, with their purpose explained; they are not presumed OpsFeast requirements. See [dependency evidence and Python reuse](docs/getting-started.md#dependency-evidence-and-python-reuse).

After cloning and reading the project guidance, expect a setup proposal identifying the checkout, interpreter (or missing Python), dependencies and management directory, rather than an already completed installation. If the agent cannot read the project, correct the project path/access before continuing. The agent should explicitly offer to perform the proposed local setup and ask whether to proceed. Reply `I agree` (or the equivalent in your language) to approve that concrete plan; the agent then carries it out and reports results. Host connections and recipe execution require their own scope. Continue in the same conversation with your agreement; there is no second required prompt. See the [first-use handoff](docs/first-use.md#3-review-the-plan-and-authorize-local-initialization) for details.

**Start with the [skills/ index](skills/README.md).** All bundled OpsFeast and SSHScript skill sources live there. Ask your agent to read the index and task-relevant skills; files being present does not mean its loader has activated them. New skills specific to your Feast belong in that management directory's `skills/`, so they remain portable when you change agents. If existing agent skills or loading rules conflict, the agent should explain the conflict and agree on a solution with you before changing files or choosing between conflicting instructions. See [storage and integration](docs/agent-guidance.md#skill-storage-and-conflict-resolution).

For your first host, follow the [first-host guide](docs/first-host.md): minimal settings, validation, connection testing and practical SSH/su/sudo cases before the full reference.

After authorized setup, the agent should tell you where to configure host addresses, login accounts, authentication and recipes, and offer both CLI and Textual Home next steps. For a checkout .venv in Bash/Zsh, it should provide `source tools/activate.sh` and `python -B tools/opsfeast.py` with the actual checkout path. Textual readiness must be checked separately; if missing, the agent can propose installing `requirements-tui.txt`. See [the interface handoff](docs/first-use.md#use-the-cli-or-try-the-interactive-home).

**[First-use walkthrough](docs/first-use.md)** explains the single-prompt setup handoff, optional explicit instructions and skill update checks, expected results, and an optional isolated trial. The [getting-started guide](docs/getting-started.md) contains the detailed setup procedure for agents. The same Markdown workflow applies across agents; automatic skill discovery is optional.

The agent can inspect prerequisites with `python3 -B tools/check_environment.py`, explain the supported tools and propose a concrete setup. After authorization, it can install the dependencies in `requirements.txt` (or `requirements-init.txt` for initialization only), read the included skills, and run `tools/opsfeast.py init` and `check`. It then reports where to configure your hosts, accounts, authentication and recipe selection. Remote connection tests and collection require their own authorized scope.

The full SSHScript skill snapshot is included in Git. [Skill download and update instructions](docs/skill-updates.md) explain how to check the public bundle, stage a complete candidate and review compatibility. A user-authorized schedule may check for changes; checks never automatically replace skills or upgrade packages.

## Optional terminal display

Run `python -B tools/opsfeast.py` without arguments for a version/download Home, masked Hosts, persistent profile switching and bundled Help. Hosts follows the default profile; explicit recipe environments are preserved. Explicit commands remain CLI. Bare `python -B tools/opsfeast.py recipes` opens the recipes workbench; explicit subcommands stay CLI. The workbench starts with checkout-only discovery and provides action forms for catalog, run, results/artifacts, jobs and bundles. Writes/execution require an in-app argument review; opening alone performs no operation. Add `--tui` to supported commands for a Textual table of progress and results, with row details and original output. Install the optional `requirements-tui.txt` in your selected environment. Read the [terminal display guide](docs/terminal-ui.md) for supported commands, setup, exit codes and limits. Ordinary CLI/JSON use remains available without Textual.

## Recipe author defaults

Configure public author name, contacts and intended recipe license in the local `.opsfeast-author.yaml`; Home displays them. New recipe authoring uses these defaults, with Unknown until configured. Built-ins are Bundle/MIT, and external imports cannot claim Bundle. See [attribution and defaults](docs/recipe-attribution.md).

## For AI agents

Read the [skill index](skills/README.md) first, select the relevant skills and check task-relevant integration conflicts as described in [agent guidance](docs/agent-guidance.md#skill-storage-and-conflict-resolution). Start here when a user asks you to use OpsFeast. Read the linked Markdown directly if your agent does not automatically discover project guidance or skills; no particular agent product or skill loader is required.

### Learn Ops and choose the relevant skill

1. Read [AGENTS.md](AGENTS.md) for project instructions, then any user-maintained `AGENTS.local.md` in this checkout. Local guidance is optional, private and not supplied by a clone; see [public and local guidance](docs/agent-guidance.md).
2. Read the [getting-started guide](docs/getting-started.md) for prerequisites and setup, and the [CLI reference](docs/cli.md) before selecting commands. It documents `tools/opsfeast.py` and `tools/run_recipe.py`, including arguments, defaults, side effects, saved data, results and exit codes. Use the interpreter selected by the user.
3. Select the task-specific skill below and follow its linked guides. Reuse already-read material when it remains applicable. Before designing features or writing recipes or documentation, read the [vision and design principles](docs/vision.md).

| Task | Start with |
| --- | --- |
| Manage profiles, hosts.yaml, platform facts or connection/su/sudo diagnostics | [Ops hosts skill](skills/opsfeast-hosts/SKILL.md), then [host diagnostics](docs/host-diagnostics.md) for tests |
| Discover, execute, author, share or review recipes | [Ops recipes skill](skills/opsfeast-recipes/SKILL.md), then the [recipe catalog](recipes/README.md) and selected recipe guide |
| Read, recover, export or combine retained result data | [Result-data skill](skills/opsfeast-result-data/SKILL.md), then [result workflow](docs/result-data.md) |
| Write or adapt SSHScript commands and sessions | [Included SSHScript skill](skills/sshscript/SKILL.md), its [Agent Guide](skills/sshscript/references/agent-guide.md), [version policy](skills/sshscript/references/versioning.md) and relevant [API guide](skills/sshscript/references/api-guide.md) sections |

Ops skills describe the management workflow; the SSHScript skill describes the execution library. The complete public SSHScript snapshot is included at `skills/sshscript/` and can be read offline. Its [SOURCE.json](skills/sshscript/SOURCE.json) records provenance, documentation contract and bundle digest. Verify the actual interpreter and SSHScript import/distribution versions against that contract before use. Bundled files do not imply installation or automatic loading by your agent.

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

This repository is an initial project scaffold. It provides a Python utility for management-directory initialization, configuration inspection and validation, and explicit host connection tests. It also provides inventory-system collectors for Linux, FreeBSD, macOS and ESXi, automatic host initialization and account diagnostics. Linux/FreeBSD/ESXi have synthetic coverage; macOS has local read-only validation. Real SSH and native su/sudo validation remain pending.

See [host diagnostics](docs/host-diagnostics.md) for `host-init`, `test-host`, independent/chained `test-su` and multi-account `test-sudo`. Setup alone does not authorize these connection or privilege tests.

## Host configuration

See the [hosts.yaml user guide](docs/hosts-yaml.md) for the proposed management-directory format, includes, jump hosts, host variables, and recipe selection. AI agents can use the repository skill [opsfeast-hosts](skills/opsfeast-hosts/SKILL.md) to help maintain these settings. On a fresh checkout, use `python tools/opsfeast.py init` to create the `main` profile at `feasts/main/`, and `python tools/opsfeast.py check` to validate it (Python 3.11+ and PyYAML required). Use `python tools/opsfeast.py test-connection <host-id>` to connect and run `hostname` and `date` (SSHScript 4.0.1+ also required). New checkouts use the ignored `.opsfeast.yaml` registry and new instances contain `feast.yaml`. Existing `.my-ops.yaml` registries and `my-ops.yaml` definitions remain supported; existing named profiles are reused by init. Use `init inventory` to create `feasts/inventory`, `attach /existing/directory` to register existing settings, `profiles` to list environments, and `use inventory` to switch the default. Adding profiles preserves an existing default. See the [profile guide](docs/profiles.md). Use `--profile NAME` on either tool for one invocation without changing the default, or pass an explicit directory. Registered relative paths are located from the tool checkout; relative CLI directory paths use the shell directory. Initialization, dumps and configuration checks do not connect. Use `python -B tools/run_recipe.py inventory/system --host <host-id>` to run system inventory directly from this checkout. No copying into the instance is needed after updating this repository. Recipe and targets are required; put the recipe first or use `--recipe DIRECTORY` elsewhere, and select hosts/groups with `--host`/`--group` or every configured host with `--all`. Use `--root` for an explicit management directory. Register external clones in entry hosts.yaml recipe_sources, select profile content with :inventory/system or named content with community:inventory/system, and attach vars to matching recipe selectors. Source/host enabled flags and --all --exclude support temporary selection controls; see [sources and inputs](docs/recipe-sources.md); see [its guide](recipes/inventory/system/README.md) for runtime requirements and validation limits.

## Explore, run and reuse recipes

```sh
python -B tools/opsfeast.py recipes list --checkout-only
python -B tools/opsfeast.py recipes list --profile main --json
python -B tools/opsfeast.py recipes show check/port --profile main
python -B tools/opsfeast.py recipes run check/port --profile main --host rms3 --var port=8888
python -B tools/opsfeast.py recipes run report/summary --profile main --input /path/to/raw-result.json
```

The catalog combines checkout, Feast and registered external sources with explicit references; compatibility is static evidence, not a connection/dependency test. Reports run offline and save declared artifacts. Basic HTML views remain plain and usable; agents can extend them through documented data/report contracts. [Recipe experience](docs/recipe-experience.md) covers results, artifacts, portable bundles and saved jobs for ordinary reruns. A saved job is not an installed schedule or execution authorization.

## Run a recipe with invocation inputs

Use `run_recipe.py` for inventory and compatible Python-session recipes. Inputs declared in recipe.yaml are supplied with `--var NAME=VALUE` or a JSON `--vars-file`, without editing hosts.yaml. For example, within authorized connection/probe scope:

```sh
python -B tools/run_recipe.py check/port --host rms3 --root ~/Download/testops --var port=8888
```

This checks TCP 127.0.0.1:8888 from rms3 itself; read the [recipe's interpretation and prerequisites](recipes/check/port/README.md). General recipes use execute(session, *, context, timeout), save raw JSON and report skipped inventory retention. See [authoring/execution](docs/recipe-execution.md) and the [CLI reference](docs/cli.md#toolsrun_recipepy-inventory-execution). Existing inventory platform dispatch and retention remain supported.

## Initialize and diagnose a host

After configuring a host and authorizing its tests, use the selected interpreter from this checkout:

```sh
python -B tools/opsfeast.py test-host host-01
python -B tools/opsfeast.py host-init host-01
python -B tools/opsfeast.py test-su host-01 --chain user2 user3 --chain user3 user2
python -B tools/opsfeast.py test-sudo host-01 user2 user3 --run-as root
python -B tools/run_recipe.py inventory/system --host host-01 host-02 host-03
```

Test-host checks login, reuses or initializes platform facts, tests the login account's sudo only when the credential precedence rule selects a password (including the account password), and independently tests su to other declared accounts. Direct host-init always refreshes facts. For inventory-system, run_recipe.py automatically initializes facts when needed, dispatches each host to its platform implementation, and records recipe/implementation/schema versions. Read the [diagnostic guide](docs/host-diagnostics.md) for credentials, skipped states, cache limits and management-root arguments, and the [inventory guide](recipes/inventory/system/README.md) before executing custom code. Python-session recipes use the [general execution contract](docs/recipe-execution.md); extension installation remains planned.

## Find, create and share recipes

The [recipe catalog](recipes/README.md) lists available content, supported platforms and actual verification evidence. Use `python -B tools/opsfeast.py inspect-recipe` to discover checkout recipes, or `python -B tools/opsfeast.py inspect-recipe inventory/system --platform freebsd --platform openbsd` to view a focused summary of requested platform support and gaps. Default output is concise; add `--details` for full human-readable content or `--json` for the complete descriptor and agent-readable report. Inspection reads files without running recipes or connecting; see the [CLI reference](docs/cli.md#inspect-recipes-and-platform-gaps) for paths, evidence limits and exit codes. The [recipe user guide](docs/recipes.md) provides copyable prompts for asking your AI agent to create a recipe, share one or several recipes through GitHub or ZIP/tar.gz, and review someone else's recipes before installation.

Agents should read the repository [recipes skill](skills/opsfeast-recipes/SKILL.md) and its task-specific guides. [Skill sources and updates](docs/skill-updates.md) explain where to obtain the complete SSHScript knowledge bundle and Ops guidance. Third-party content is checked for integrity, publisher evidence and behavior before a concrete installation plan is authorized; installation does not authorize execution. These are documented agent workflows. Catalog list/show/run, offline reports, results/artifact views, single-recipe pack/unpack and saved jobs are implemented; see [the recipe experience](docs/recipe-experience.md). An automatic third-party installer, publisher, lockfile and scheduler are not yet implemented. The [Python-session contract](docs/recipe-execution.md) supports other reviewed recipe IDs.

## Planned workflow

1. Register hosts and define connection settings in the user's own environment.
2. Collect inventory and state using versioned recipes.
3. Organize host and service records, retaining the sources and timestamps of observations.
4. Identify changes and investigate problems using operational skills and their linked procedures.
5. Perform authorized maintenance and verify its outcome.
6. Update records while preserving human notes and operational history.

## Repository structure

| Directory | Purpose |
| --- | --- |
| [recipes/](recipes/README.md) | Reusable collection, inspection, maintenance, and repair tools |
| [schemas/](schemas/README.md) | Contracts for host records, observations, and execution results |
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

## Retained observations and sharing

Inventory execution automatically saves operational success/partial observations in each Feast records/observations.sqlite3 after saving raw JSON. Check both collection and retention status. Use tools/observation_store.py to recover selected raw results, export filtered JSON, validate exchanges or combine A/B exports. Host identity is best-effort and source-scoped fallback warnings must be preserved. Read the [workflow and contracts](docs/result-data.md), [CLI](docs/cli.md#retained-observations-and-exchange) and [result-data skill](skills/opsfeast-result-data/SKILL.md). Recipient analysis storage is independent; no transport or stage-4 importer is bundled. Identity probes may use supplied explicit sudo capability; set recipe input identity_sudo false to disable, or true for authorized passwordless sudo. Old raw files are not automatically backfilled.

Host identity_key, label and description are now supported. An explicit identity_key takes precedence and is shared across Feasts as user-assigned identity; change it after OS reinstall/replacement and coordinate its namespace. label/description are captured human text, never identity keys, and are preserved through retention/exchange. See [the canonical host configuration](docs/hosts-yaml.md#explicit-host-identity-and-human-readable-metadata) and [identity/metadata rules](docs/result-data.md#explicit-identity-and-display-metadata). MAC is not an automatic key.

_Last modified: 2026-10-14_
