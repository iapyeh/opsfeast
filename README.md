# SSHScript Ops

Tools, recipes, and workflows for building and maintaining IT operations with SSHScript.

SSHScript Ops aims to help IT staff, with assistance from AI agents, build an orderly operations environment from their existing hosts and maintain it as systems change and problems arise.

SSHScript provides the foundation for readable, flexible local and remote execution. This repository will bring together reusable recipes, management data formats, operational procedures, and documentation templates.

## Status

This repository is an initial project scaffold. It provides a Python utility for management-directory initialization, configuration inspection and validation, and explicit host connection tests. It also provides an initial inventory-system Linux collector and a minimal runner; Linux collection has synthetic coverage, while real Linux/SSH validation remains pending.

## Host configuration

See the [hosts.yaml user guide](docs/hosts-yaml.md) for the proposed management-directory format, includes, jump hosts, host variables, and recipe selection. AI agents can use the repository skill [sshscript-ops-hosts](skills/sshscript-ops-hosts/SKILL.md) to help maintain these settings. Use `python tools/my_ops.py init` to create `my-ops/` beside `recipes/`, and `python tools/my_ops.py check` to validate it (Python 3.11+ and PyYAML required). Use `python tools/my_ops.py test-connection <host-id>` to connect and run `hostname` and `date` (SSHScript 4.0.1+ also required). Each successful `init [DIRECTORY]` remembers its directory for both tools in the ignored checkout locator `.my-ops.yaml`; the directory itself contains a `my-ops.yaml` definition. Explicit directory arguments override the remembered path. Paths are located relative to the tool checkout, independent of the shell directory. Initialization, dumps and configuration checks do not connect. Use `python -B tools/run_recipe.py <host-id>` to run the explicitly selected inventory-system recipe directly from this checkout. No copying into the instance is needed after updating this repository. Add `--recipe recipes/inventory/system` to select a recipe directory for this run instead of the host's recipe settings; see [its guide](recipes/inventory/system/README.md) for runtime requirements and validation limits.

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
