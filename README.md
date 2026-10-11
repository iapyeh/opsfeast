# SSHScript Ops

Tools, recipes, and workflows for building and maintaining IT operations with SSHScript.

## Getting started with your AI agent

Start by cloning the repository:

```sh
git clone https://github.com/iapyeh/sshscript-ops.git
```

Open a new conversation with an agent that can read your local files, such as Codex or Hermes, and send this prompt after replacing the path with your clone's absolute directory:

> I am using SSHScript Ops for the first time. The repository is at `/absolute/path/to/sshscript-ops`. Read README.md, AGENTS.md and the getting-started guide, explain what the project can do and what environment it needs, and propose an initial setup. Do not install dependencies or initialize anything yet.

Review the proposal, then authorize setup. The agent should initialize your management directory and tell you where to configure host addresses, login accounts, authentication and recipes.

**[First-use walkthrough / 人類使用者的第一次體驗](docs/first-use.md)** provides copyable prompts for setup and skill update checks, expected results, and an optional isolated trial. The [getting-started guide](docs/getting-started.md) contains the detailed setup procedure for agents. The same Markdown workflow applies across agents; automatic skill discovery is optional.

The agent can inspect prerequisites with `python3 -B tools/check_environment.py`, explain the supported tools and propose a concrete setup. After authorization, it can install the dependencies in `requirements.txt` (or `requirements-init.txt` for initialization only), read the included skills, and run `tools/ops.py init` and `check`. It then reports where to configure your hosts, accounts, authentication and recipe selection. Remote connection tests and collection require their own authorized scope.

The full SSHScript skill snapshot is included in Git. [Skill download and update instructions](docs/skill-updates.md) explain how to check the public bundle, stage a complete candidate and review compatibility. A user-authorized schedule may check for changes; checks never automatically replace skills or upgrade packages.

SSHScript Ops aims to help IT staff, with assistance from AI agents, build an orderly operations environment from their existing hosts and maintain it as systems change and problems arise.

SSHScript provides the foundation for readable, flexible local and remote execution. This repository will bring together reusable recipes, management data formats, operational procedures, and documentation templates.

## Status

This repository is an initial project scaffold. It provides a Python utility for management-directory initialization, configuration inspection and validation, and explicit host connection tests. It also provides an initial inventory-system Linux collector and a minimal runner; Linux collection has synthetic coverage, while real Linux/SSH validation remains pending.

## Host configuration

See the [hosts.yaml user guide](docs/hosts-yaml.md) for the proposed management-directory format, includes, jump hosts, host variables, and recipe selection. AI agents can use the repository skill [sshscript-ops-hosts](skills/sshscript-ops-hosts/SKILL.md) to help maintain these settings. Use `python tools/ops.py init` to create the `main` profile at `my-ops/main/`, and `python tools/ops.py check` to validate it (Python 3.11+ and PyYAML required). Use `python tools/ops.py test-connection <host-id>` to connect and run `hostname` and `date` (SSHScript 4.0.1+ also required). The ignored `.my-ops.yaml` records all profiles and the selected default; each initialized directory contains a `my-ops.yaml` definition. Use `init inventory` to create `my-ops/inventory`, `add /existing/directory` to register existing settings, `profiles` to list environments, and `use inventory` to switch the default. Adding profiles preserves an existing default. See the [profile guide](docs/profiles.md). Use `--profile NAME` on either tool for one invocation without changing the default, or pass an explicit directory. Registered relative paths are located from the tool checkout; relative CLI directory paths use the shell directory. Initialization, dumps and configuration checks do not connect. Use `python -B tools/run_recipe.py <host-id>` to run the explicitly selected inventory-system recipe directly from this checkout. No copying into the instance is needed after updating this repository. Add `--recipe recipes/inventory/system` to select a recipe directory for this run instead of the host's recipe settings; see [its guide](recipes/inventory/system/README.md) for runtime requirements and validation limits.

## Find, create and share recipes

The [recipe catalog](recipes/README.md) lists available content, supported platforms and actual verification evidence. The [recipe user guide](docs/recipes.md) provides copyable prompts for asking your AI agent to create a recipe, share one or several recipes through GitHub or ZIP/tar.gz, and review someone else's recipes before installation.

Agents should read the repository [recipes skill](skills/sshscript-ops-recipes/SKILL.md) and its task-specific guides. [Skill sources and updates](docs/skill-updates.md) explain where to obtain the complete SSHScript knowledge bundle and Ops guidance. Third-party content is checked for integrity, publisher evidence and behavior before a concrete installation plan is authorized; installation does not authorize execution. These are documented agent workflows. A general runner, third-party installer, pack/publish CLI and lockfile are not yet implemented.

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

[SSHScript](https://github.com/iapyeh/sshscript) remains a separate execution library. SSHScript Ops builds operational content and a management framework on that foundation. Recipes initially live in this repository so their contracts, documentation, and workflows can evolve together.
