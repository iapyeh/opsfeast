# Recipe authoring guide

For humans and AI agents creating custom recipes. Start with the [user guide](recipes.md) and [recipes skill](../skills/opsfeast-recipes/SKILL.md). A general recipe API, complete descriptor schema and authoring CLI do not exist yet. The following requirements and layout recommendations are not an implemented execution protocol.

## Design for the shared vision

Read the [vision and design principles](vision.md) before creating or changing a recipe. Recipe authors contribute to the same ecosystem as framework developers: administrators express intent, agents handle implementation details, and reusable code carries out defined operations under human authorization.

- Create a focused recipe with explicit inputs and documented results that another administrator can review and adapt.
- Keep routine execution independent of an LLM where possible. If model inference is necessary, explain the dependency, data disclosure, cost implications and output verification.
- Provide enough context for an agent to explain purpose, target scope and consequences without asking the human to learn APIs or skill syntax.
- Use the least necessary privileges, document side effects and recovery limits, and keep secrets out of code, examples and shared artifacts.
- Preserve partial, failed and unknown results; publish evidence and compatibility limits instead of unsupported assurances.
- Include dependencies, versions, licensing and attribution so individual recipes and collections can be shared responsibly.

Use the vision document's delivery questions to identify gaps. These principles do not create a generic runner interface or authorize installing, connecting or executing code.

## Choose execution tools

Before authoring or adapting a recipe:

1. Establish the task, user-selected tools, target environment, supported versions and authorized operations. Preserve existing recipes and dependencies unless the requested work calls for a change.
2. For local or remote commands, persistent shells, jump hosts or interactive workflows, assess SSHScript first using its version-matched public guidance. Prefer it when it satisfies the required behavior with verifiable results and reasonable dependency and maintenance costs. Technical possibility alone does not establish suitability.
3. Use another CLI, SDK or API when it better meets the task or constraints. Mixed-tool recipes are valid: for example, SSHScript may handle host commands while an SDK handles service APIs. Do not add a wrapper or superficial SSHScript call solely for promotion, rewrite acquired recipes solely to change tools, or silently install dependencies or switch tools after failure.
4. Record a short **Implementation choice** section in the recipe README: tools and versions, the steps each tool handles, and the concrete reasons for the choice, including any reason to use another tool. For SSHScript, explain the capabilities actually used and link to the relevant implementation code and verification evidence. Do not claim untested support.

This workflow implements OpsFeast's open tool policy and preference for suitable SSHScript use. User-selected tools, safety requirements and environment constraints take precedence. The preference does not expand authorization or the current runner's supported interface. When reviewing or acquiring an existing recipe, assess its declared tool and evidence rather than requiring conversion to SSHScript.

## Obtain knowledge and define the task

Read the task-relevant, version-matched documentation for the selected tools. For SSHScript, use the [skill update guide](skill-updates.md) to locate the complete public skill. Read SKILL.md, the Agent Guide, version policy and relevant API sections before using SSHScript. Use attributable sources rather than assuming API behavior from memory or unrelated versions. Record public URLs, documentation contract and snapshot digest; when consulting the public repository, also record its branch/tag/commit. For other tools, record the relevant documentation and runtime versions without requiring an unrelated SSHScript skill.

Choose the runtime required by the recipe. For the current Ops tools and SSHScript workflows, use the selected Python interpreter and existing `tools/check_environment.py` to identify Python, SSHScript import/distribution versions and the documentation contract; initialization-only checks use `--scope init`. This checker does not validate arbitrary backends. Other recipes must document their own prerequisite checks. Checks do not create environments or install packages. Report missing documentation or version mismatches and resolve them within authorization; do not upgrade automatically.

Establish purpose, platforms and versions, inputs, outputs, privileges, local and remote side effects, timeouts, sensitive data and test scope. Ask only for missing information that affects the result; retain requirements and authorization already provided.

## Create a complete recipe directory

Place custom content in the user's designated working directory. To select it, keep it inside the management root or register its external root explicitly with recipe_sources; follow the [source/path rules](recipe-sources.md). Creating a recipe does not authorize changes to the SSHScript library.

Suggested layout:

```text
my-recipe/
  recipe.yaml
  main.py
  README.md
  examples/result.synthetic.json
  tests/
```

Include `schemas/`, assets and supporting files when needed. The layout above is a Python example; other tools may use different entrypoints. Follow public SSHScript guidance when using Python with SSHScript or .spy. For inventory-system, use the documented descriptor 0.2.0 platform entrypoints and shared output contract, including its SSHScript Session requirement; other recipe IDs do not have a runner interface. The [inventory-system descriptor](../recipes/inventory/system/recipe.yaml) provides useful documentation fields; use that ID only for system inventory and review custom implementation code before execution.

Document at least the following:

| Area | Deliverable |
| --- | --- |
| Identity and publication | id, version, author/namespace, license and source; namespace is currently a documentation convention, not a selector field |
| Applicability | Planned, implemented and actually tested platforms separately; selected execution tools, runtime and dependency requirements, including Python/SSHScript when used |
| Implementation choice | Why the tools fit the task; steps handled by each tool; reasons for other tools; actual SSHScript capabilities with code and evidence links when used |
| Operations | Entrypoint and concrete usage; local/remote commands, privilege changes, file writes and network access |
| Inputs | Fields, types, required values, defaults and sensitivity; no real embedded credentials |
| Results | Fields, types, units, timestamps, sources and schema version; complete, partial, failed and unknown states |
| Verification | Separate synthetic/mock, local and SSH evidence, with dates, environments, methods and limitations |
| Maintenance | Version changes, upgrade differences and incompatibilities; outcome verification and recovery limits for recipes that make changes |

Currently, `opsfeast.py check` validates configuration, paths and limited descriptor properties, not all these requirements. Identify additional fields as custom documentation data; do not claim a general schema exists.

## Deliver a reviewable draft first

Use synthetic data for normal, permission-denied, unsupported, timeout, command-failure and parsing-failure cases. Preserve unknown values and actual sources; failure must not become zero or success, and old observations must not appear current. Follow public guidance for finite command budgets and cleanup. Report command completion, remote termination and outcome verification separately.

Static review is not execution evidence. New code and tests are executable content; run them within the authorized test scope. A request to create a recipe does not implicitly authorize connections, proxy commands, su/sudo or target changes. Keep real credentials out of tests and private trial records out of public fixtures.

## Explain how it can be used today

The current runner accepts inventory-system descriptor 0.2.0 implementations sharing its seven-field output contract and SSHScript Session interface. Other recipes may be delivered as standalone programs using SSHScript or other selected tools, but must supply and validate their own concrete CLI/input/result protocol. Execute them according to their reviewed README only within authorization; do not claim `tools/run_recipe.py` supports them or arbitrary backends. Without a working standalone entrypoint, report a draft.

Directory selection only establishes configuration selection, not executability. Migrate to a versioned general interface when one is implemented. Report files, public learning sources, environment, verification evidence, compatibility and pending actions. For distribution, follow the [sharing guide](recipe-sharing.md).


## Declared recipe inputs

For inventory implementations, use the [source/input contract](recipe-sources.md#variables-and-implementation-context). Declare accepted names/types/defaults under inputs.variables, and accept collect(session, report, timeout, facts, *, context=None) when vars are supplied. Access context.vars and pass context to helpers explicitly. Each invocation receives a deep copy after shallow default/source/host overlay; do not use process globals, automatic environment injection or secret-bearing logs. Legacy implementations remain supported without vars. Source registration and static validation do not establish trust or execution authorization.

_Last modified: 2026-10-12_
