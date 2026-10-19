# Recipe authoring guide

Before choosing a directory, read [recipe classification and location](recipe-taxonomy.md). Default user recipes go in `<selected-profile-root>/recipes/<domain>/<optional-subdomains>/<action>/<name>/`; shared recipes use an explicitly registered external root. The corresponding selectors are :classified/path and company:classified/path. Intermediate folders are categories, not recipes; only leaves carry recipe.yaml. Keep descriptor identity stable across a classification-only move and review dependent selectors/jobs/consumers.

For retained-data handlers and converters, use [retention consumers](retention-consumers.md). Declare consumer subscriptions separately from the producing recipe, reuse the read-only retention reader and existing output/artifact interfaces, and enable reviewed local programs explicitly. Multi-recipe content belongs in a consumer or offline report, with preserved source/status/quality context. No runner edits or recipe-side subscriber list is needed.

Develop retention against saved raw with [retention ingest and explicit read-only deletion](retention-replay.md). New general runs capture a data-definition snapshot before execution; --recipe-dir explicitly tests revised definitions without importing recipe code. Declare access_mode accurately before collection: changing a descriptor later cannot make old write/unknown results deletable. Source UUID and raw digest have separate roles.

## Host-centered retention and state pages

Recipe creators define and produce retention; they do not embed vault presentation in it. Declare [host-values 0.2.0](retention.md#recipe-owned-data-declarations) for safe scalar fields with explicit units and meaningful dataset/field descriptions. Declare access_mode accurately; runner snapshots contain data declarations only. system/inventory/overview 0.3.2 owns its [inventory-observations declaration, schema and normalizer](../recipes/system/inventory/overview/README.md#recipe-owned-retention-contract); all inventory descriptors must declare access_mode and retention, independently of raw output. New structured contracts need reviewed registry support, not arbitrary candidate-code loading. Keep credentials out of both field values and descriptions.

Content authors use `context.retention.query/show` in offline python-report programs to combine multiple recipe/host/time selections. The [bundled example](../recipes/feast/report/retention-summary/README.md) writes Markdown and HTML, preserving full evidence and source times. Vault uses the same public data interface; `markdown_template` is removed from recipe retention. Update public tests, schemas, discovery metadata, capability catalogs and relevant skills with usable contract changes.

## Reuse product capabilities before authoring new machinery

Start with the [agent capability map](agent-capabilities.md), catalog/list/show and static inspection before writing new code. Prefer a compatible reviewed recipe or CLI workflow for the complete task, and applicable modules for in-process composition. Reuse configuration loading, typed inputs, session/cleanup/result handling, report/artifact contracts, retained export/validation, attribution defaults, packaging and saved reruns. Record the concrete gap when existing functionality is unsuitable, then implement only that missing logic. User-selected tools and operational boundaries still apply; capability discovery does not authorize execution.

For new Core recipes use [python-recipe 0.1.0](core-api.md#runner-integration-and-migration) and execute(recipe). Reuse its supplied session and scoped su/sudo; prefer the [Core skill](../skills/opsfeast-core/SKILL.md) for standalone programs. Existing python-session contracts and examples below remain compatible.

## Bind configuration at runtime

For standalone operational Python tools, use the [existing configuration loader](hosts-yaml.md#read-host-configuration-from-python), supplying a Feast root/profile and host ID at invocation time. Reuse its include and validation behavior; do not independently parse hosts.yaml or freeze private connection values into generated code. For runner-managed recipes, consume the borrowed Session and `context.host_id`/`context.vars` from the [execution contract](recipe-execution.md#entrypoint-and-available-capabilities); declare task inputs rather than reconnecting or assuming the context carries complete host settings. Keep portable recipe code separate from private bindings and credentials.

## Design for the shared vision

Read the [vision and design principles](vision.md) before creating or changing a recipe. Recipe authors and product developers contribute to the same ecosystem with distinct responsibilities: DevOps users express operational intent and author specialized recipes using existing capabilities, while product developers broaden and stabilize reusable product support to reduce that authoring burden. Both preserve reviewed logic as code for repeatable execution under human authorization.

- Create a focused recipe with explicit inputs and documented results that another administrator can review and adapt.
- Keep routine execution independent of an LLM where possible. If model inference is necessary, explain the dependency, data disclosure, cost implications and output verification.
- Provide enough context for an agent to explain purpose, target scope and consequences without asking the human to learn APIs or skill syntax.
- Use the least necessary privileges, document side effects and recovery limits, and keep secrets out of code, examples and shared artifacts.
- Preserve partial, failed and unknown results; publish evidence and compatibility limits instead of unsupported assurances.
- Include dependencies, versions, licensing and attribution so individual recipes and collections can be shared responsibly.
- Follow [agent operations through open contracts and skills](vision.md#enable-agent-operations-through-open-data-contracts-and-skills): document data and storage contracts and provide actionable skills for relevant inspection, transformation and maintenance tasks, including tasks without a bundled tool. State actual prerequisites and verification limits rather than inventing a CLI or claiming unsupported behavior.

Use the vision document's delivery questions to identify gaps. These principles do not create a generic runner interface or authorize installing, connecting or executing code.

When selecting services for a recipe, consult the recipe skill's service capability references and verify support for the intended runner/API version and configuration in the selected Feast. Reuse applicable services and document the capabilities used, required configuration/providers and failure handling. Service contributors must update these discoverable skill references with each new or changed service before delivery; see the [knowledge-transfer requirement](vision.md#enable-agent-operations-through-open-data-contracts-and-skills). The service catalog and APIs remain future deliverables until services are implemented.

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

Include `schemas/`, assets and supporting files when needed. The layout above is a Python example; other tools may use different entrypoints. Follow public SSHScript guidance when using Python with SSHScript or .spy. For inventory-system, use the documented descriptor 0.2.0 platform entrypoints and shared output contract, including its SSHScript Session requirement; other Python recipe IDs use [descriptor 0.3.0 and Python-session 0.1.0](recipe-execution.md). The [inventory-system descriptor](../recipes/system/inventory/overview/recipe.yaml) provides useful documentation fields; use that ID only for system inventory and review custom implementation code before execution.

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

## Report recipes and reusable visualization

For requests to produce a recurring report or visualization, follow [the accumulation and presentation principles](vision.md#accumulate-reusable-reports-and-keep-visualization-flexible). Let the user's agent select the view that fits the question and available tools. Prefer useful tables or simple charts for default views, with room for user-selected renderers and richer presentations. Preserve repeatable executable work instead of delivering only an image or asking a model to recreate the analysis on every refresh.

Within the user's authoring scope:

1. Inspect the actual [result-data contracts](result-data.md), schema versions and available sources. Establish the question, selected hosts/observations/time range, output format/location and permitted local processing. Use retained/exchange contracts for inventory; [general recipe raw data](recipe-execution.md#results-failure-states-and-storage) has its own recipe-owned schema and no inventory retention adapter. Do not guess a parser for undocumented data.
2. Save the data-selection query, transformations, interpretation rules, input parameters, templates/assets and required renderer versions with the report recipe. Keep private dataset locations and source bindings in user-selected configuration. Document units, source observation times/freshness, generation time, identity quality, exclusions and partial/unknown states. A generated dashboard should not replace observation evidence.
3. Provide a concrete reviewed invocation for rerunning the same report from existing data, with synthetic input/output examples and tests for normal, empty, stale, partial and invalid data. Use suitable ordinary tools for repeatable work. Keep outputs separate from source observations and preserve human notes. State when a renderer, model or external service is required and whether generation/sharing sends data elsewhere.
4. Match the actual execution interface. Offline reports use descriptor 0.3.0, runner python-report 0.1.0 and execute(*, context, timeout), with selected JSON inputs and declared artifacts. Read [the report contract](recipe-experience.md#offline-report-contract). Python-session operations retain explicit hosts and a borrowed Session. Use recipes run for either kind; do not create dummy host connections for reports. Incompatible platform-native dashboards still need reviewed standalone integration instructions.
5. Package portable code/templates/dependencies and synthetic tests through [report sharing](recipe-sharing.md#share-report-recipes-across-feasts). Recipients supply their own data bindings. Saving a report recipe does not establish a schedule, publish a report or authorize new collection; agreed recurring operation should rerun the reviewed program, with agents used for changes or unhandled exceptions.

The [implemented recipe experience](recipe-experience.md) delivers versioned catalog/report/artifact/bundle/job contracts and linked operational guidance. Future extensions must update those contracts, discovery/execution/storage behavior, skills and reproducible tests together. No arbitrary renderer sandbox, platform-native dashboard integration or measured token savings is claimed.

## Deliver a reviewable draft first

Use synthetic data for normal, permission-denied, unsupported, timeout, command-failure and parsing-failure cases. Preserve unknown values and actual sources; failure must not become zero or success, and old observations must not appear current. Follow public guidance for finite command budgets and cleanup. Report command completion, remote termination and outcome verification separately.

Static review is not execution evidence. New code and tests are executable content; run them within the authorized test scope. A request to create a recipe does not implicitly authorize connections, proxy commands, su/sudo or target changes. Keep real credentials out of tests and private trial records out of public fixtures.

## Explain how it can be used today

Use `tools/run_recipe.py` for inventory-system descriptor 0.2.0 or [Python-session descriptor 0.3.0](recipe-execution.md). For the latter, define execute(session, *, context, timeout), typed inputs.variables and the status/reason_code/message/data result. Use --var or --vars-file for invocation inputs; main.py need not define its own host/configuration CLI. Preserve runner-owned connection/cleanup. Other backends or incompatible standalone programs still need reviewed usage instructions and their own verifiable input/result protocol; do not claim automatic adaptation.

Directory selection only establishes configuration selection, not executability. Adapt compatible Python operations to the implemented versioned execute interface; do not automatically rewrite incompatible standalone programs. Report files, public learning sources, environment, verification evidence, compatibility and pending actions. For distribution, follow the [sharing guide](recipe-sharing.md).


## Declared recipe inputs

For inventory and Python-session recipes, use the [source/input contract](recipe-sources.md#variables-and-implementation-context). Declare accepted names/types/defaults under inputs.variables, and accept collect(session, report, timeout, facts, *, context=None) when vars are supplied. Access context.vars and pass context to helpers explicitly. Each invocation receives a deep copy after shallow default/source/host overlay; do not use process globals, automatic environment injection or secret-bearing logs. Invocation inputs overlay default/source/host values through --vars-file then --var; see [execution inputs](recipe-execution.md#select-a-recipe-and-provide-inputs). General recipes access context.vars in execute; legacy inventory implementations remain supported without vars. Source registration and static validation do not establish trust or execution authorization.

_Last modified: 2026-10-19 17:04:30_
