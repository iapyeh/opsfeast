# OpsFeast and OpsBuffet

**Agent-Driven IT Operations. Human-Authorized.**

People define goals, target systems and authorization. Agents drive daily operations using reusable recipes, verify outcomes, and request human judgment or additional authorization when needed. Repeatable recipe steps can execute as code without requiring a model to generate every command.

## Concepts and roles

| Name | Technical meaning | Responsibility |
| --- | --- | --- |
| Feast | Private management instance | Configuration, selected recipes, observations, execution records and results. A profile registers and selects a Feast; it is not the Feast itself. |
| Buffet | Exchange instance | Discover, acquire and share recipes. Exchange services are planned. |
| Recipe | Versioned operational procedure and implementation | Inputs, dependencies, targets, privileges, side effects, outputs and verification evidence. |
| Dish | Execution result and supporting evidence | Retain complete, partial, failed and unknown states. The metaphor never implies success. Technical interfaces continue to use result/report. |
| Chef | AI agent | Plan and perform authorized work, interpret evidence and handle exceptions. This is a role, not a bundled agent product. |
| Kitchen | Execution environment | Tools, dependencies, connection capabilities, credentials/permissions and execution controls. Multiple managed runners or isolated kitchens are future architecture, not implemented capabilities. |
| Host | Business owner or delegated sponsor | Set purpose, resources and overall policy. |
| Feast Organizer | System administrator | Establish the environment, targets and operational authorization rules. |
| Guest | User or beneficiary | Request services, use outcomes and provide feedback. |

Host, organizer and guest are responsibilities, not hard-coded permissions tied to job titles. Actual authority follows explicit delegation and policy. In connection settings, `host` retains its technical machine meaning; the banquet role does not rename configuration fields.

The story is: acquire a recipe from an authorized Buffet, prepare it in an authorized Kitchen, and retain the resulting Dish in the user's Feast. Use the metaphor for orientation and branding; use instance, exchange, agent, execution environment, run and result for precise operational interfaces.

## Product and repository boundaries

| Repository | Responsibility | Status |
| --- | --- | --- |
| `iapyeh/opsfeast` | Local management tools, recipe inspection/execution, results, contracts and agent guidance | This repository, formerly `iapyeh/sshscript-ops`. |
| `iapyeh/opsbuffet` | Deployable Exchange service: discovery, acquisition, publication and source/version management | Planned; not created by the OpsFeast rename. |
| `iapyeh/opsfeast-recipes` | Independently released official recipe collection | Optional future split. Built-in recipes remain under this repository's recipes/. |

Community recipes can live in independent repositories or archives. Contributions do not require a fork of OpsFeast. Shared contracts currently live in schemas/ and the recipe guides; a separate contracts repository is not required now.

OpsBuffet Public Exchange will be the maintainer-operated public service. An enterprise can deploy its own instance, for example Acme OpsBuffet. Both should use the same Exchange product with separate storage, credentials, policy and administration. Public and private catalogs are deployment data, not service source code.

One Feast may eventually use multiple authorized Buffets. Enterprise review and import of a public recipe is a separate step from execution. Acquiring, installing, executing and publishing are distinct authorization scopes. Internal recipes and operational data must not automatically flow to a public Buffet. Public/private identifies an administrative boundary, not a verification or safety rating.

## Execution tools and present limits

SSHScript is the currently supported execution foundation. Future recipes may use CLIs, SDKs, HTTP APIs or other tools when their dependencies, behavior and evidence contracts are defined and verified. A name change does not implement additional backends.

OpsFeast currently provides profiles, configuration checks, explicit host/account diagnostics, static recipe inspection and a dedicated inventory-system runner. A general runner, Exchange client/server, installer, publication CLI, general sandbox and machine-enforced authorization records are not implemented. See the [README status](../README.md#status), [CLI reference](cli.md), [recipe catalog](../recipes/README.md) and [vision](vision.md).

## Naming and compatibility

Use OpsFeast and OpsBuffet as complete public brands; Feast and Buffet are internal concepts. Prefer opsfeast for the local repository and tools/opsfeast.py for new commands. Existing CLI and configuration compatibility is documented in the [migration guide](migration.md).

_Last modified: 2026-10-12_
