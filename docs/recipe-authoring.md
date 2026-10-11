# Recipe authoring guide

For humans and AI agents creating custom recipes. Start with the [user guide](recipes.md) and [recipes skill](../skills/sshscript-ops-recipes/SKILL.md). A general recipe API, complete descriptor schema and authoring CLI do not exist yet. The following requirements and layout recommendations are not an implemented execution protocol.

## Obtain knowledge and define the task

Use the [skill update guide](skill-updates.md) to locate the complete public SSHScript skill. Read SKILL.md, the Agent Guide, version policy and relevant API sections before using SSHScript. Use version-matched, attributable sources rather than assuming API behavior from memory or unrelated versions. Record public URLs, documentation contract and snapshot digest; when consulting the public repository, also record its branch/tag/commit.

Choose the interpreter and use the existing `tools/check_environment.py` to identify Python, SSHScript import/distribution versions and the documentation contract. The check does not create environments or install packages. Report missing documentation or version mismatches and wait for update instructions; do not upgrade automatically.

Establish purpose, platforms and versions, inputs, outputs, privileges, local and remote side effects, timeouts, sensitive data and test scope. Ask only for missing information that affects the result; retain requirements and authorization already provided.

## Create a complete recipe directory

Place custom content in the user's designated working directory. To select it with existing configuration tools, it must reside within the management root and follow the [path rules](hosts-yaml.md). Creating a recipe does not authorize changes to the SSHScript library.

Suggested layout:

```text
my-recipe/
  recipe.yaml
  main.py
  README.md
  examples/result.synthetic.json
  tests/
```

Include `schemas/`, assets and supporting files when needed. Follow public SSHScript guidance for Python or .spy usage. `main.py` is a layout recommendation, not a dynamically supported runner entrypoint. The [inventory-system descriptor](../recipes/inventory/system/recipe.yaml) provides useful documentation fields; do not impersonate its id or version to bypass runner checks.

Document at least the following:

| Area | Deliverable |
| --- | --- |
| Identity and publication | id, version, author/namespace, license and source; namespace is currently a documentation convention, not a selector field |
| Applicability | Planned, implemented and actually tested platforms separately; Python, SSHScript and dependency requirements |
| Operations | Entrypoint and concrete usage; local/remote commands, privilege changes, file writes and network access |
| Inputs | Fields, types, required values, defaults and sensitivity; no real embedded credentials |
| Results | Fields, types, units, timestamps, sources and schema version; complete, partial, failed and unknown states |
| Verification | Separate synthetic/mock, local and SSH evidence, with dates, environments, methods and limitations |
| Maintenance | Version changes, upgrade differences and incompatibilities; outcome verification and recovery limits for recipes that make changes |

Currently, `ops.py check` validates configuration, paths and limited descriptor properties, not all these requirements. Identify additional fields as custom documentation data; do not claim a general schema exists.

## Deliver a reviewable draft first

Use synthetic data for normal, permission-denied, unsupported, timeout, command-failure and parsing-failure cases. Preserve unknown values and actual sources; failure must not become zero or success, and old observations must not appear current. Follow public guidance for finite command budgets and cleanup. Report command completion, remote termination and outcome verification separately.

Static review is not execution evidence. New code and tests are executable content; run them within the authorized test scope. A request to create a recipe does not implicitly authorize connections, proxy commands, su/sudo or target changes. Keep real credentials out of tests and private trial records out of public fixtures.

## Explain how it can be used today

The current runner accepts only the exact inventory-system bundle. Other recipes may be delivered as standalone SSHScript programs, but must supply and validate their own concrete CLI/input/result protocol. Execute them according to their reviewed README only within authorization; do not claim `tools/run_recipe.py` supports them. Without a working standalone entrypoint, report a draft.

Directory selection only establishes configuration selection, not executability. Migrate to a versioned general interface when one is implemented. Report files, public learning sources, environment, verification evidence, compatibility and pending actions. For distribution, follow the [sharing guide](recipe-sharing.md).
