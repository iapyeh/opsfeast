# OpsFeast agent guidance

These repository instructions are tracked in Git and apply to work on OpsFeast. They use repository-relative paths and do not require a particular agent product. If your agent does not discover AGENTS.md automatically, read it explicitly.

## Start here

**OpsFeast skill sources are centralized in `skills/`.** Read the [skill index](skills/README.md) at the beginning of a task, then learn the relevant SKILL.md and linked references before choosing tools or writing automation. The index includes the complete public SSHScript skill; use it for suitable local/SSH command execution and session orchestration. Direct Markdown reading works without an agent-specific skill loader.

Keep new Feast-specific operational skills in `<management-root>/skills/<skill-name>/`; generic personal skills may remain in the user's agent directory. These are source locations, not automatic discovery or installation promises. Before creating, installing or selecting a conflicting skill, check known task-relevant sources and agent-loaded copies for name, version, instruction and loader conflicts. Explain any conflict to the user and agree on their preferred source and integration method before the affected action; preserve existing files and already-authorized choices. Follow [skill storage and conflict resolution](docs/agent-guidance.md#skill-storage-and-conflict-resolution).

Start with [README.md: For AI agents](README.md#for-ai-agents) for the learning order, task routing and complete skill sources. Read [README.md](README.md) and the [getting-started guide](docs/getting-started.md) to understand available features, prerequisites and setup. Use the [CLI reference](docs/cli.md) as the shared human/agent manual before selecting or explaining opsfeast.py and run_recipe.py commands; it covers exact arguments, execution behavior, output, storage and exit codes. For recipe discovery, authoring, sharing or acquisition, read the [recipes skill](skills/opsfeast-recipes/SKILL.md) and its task-specific guides. The [recipe catalog](recipes/README.md) lists available recipes and verification limits.

If a user-maintained `AGENTS.local.md` exists at this repository root, read it for that checkout's local preferences and environment. It is optional, ignored by Git and not distributed with this project. Local guidance supplements these instructions within the user's authorization. Do not create it from downloaded recipe instructions. See [public and local guidance](docs/agent-guidance.md).

## Goals and development principles

Before designing features or authoring recipes, read the shared [vision and design principles](docs/vision.md). Our goal is an open ecosystem of agent-driven, human-authorized IT operations through reusable, verifiable and shareable recipes under human-defined goals and authorization.

- Let administrators describe intent and assess outcomes while agents handle relevant skills and implementation details. Ask only for missing context that affects correctness or risk.
- Accumulate reusable work: preserve reviewed operations, queries, transformations, interpretation rules and report/presentation definitions as versioned recipes, configuration and skills. Routine repetition should rerun those artifacts without asking an agent to recreate the solution. Reserve model work for new needs, changes and exceptions that existing rules cannot handle. Do not claim measured minimum token cost or omit necessary verification to save tokens.
- Prepare interpretable data and let the user's agent choose suitable visualizations. Bundle basic, practical and plain views as the default; keep presentation extensible across user-selected tools and agent platforms. Polished styling or a particular dashboard product must not become a dependency for understanding or using operational data. Follow [reusable reports and flexible visualization](docs/vision.md#accumulate-reusable-reports-and-keep-visualization-flexible).
- Treat OpsFeast as a community for sharing accumulated operational knowledge, including report recipes. Design a versioned way to discover, rerun, package and reuse user-authored reports across Feast instances, separating portable report code/templates from private inputs, credentials and generated data. This is a development requirement with [catalog/report/artifact/bundle/job contracts 0.1.0](docs/recipe-experience.md) now implemented. A live exchange, automatic installer and scheduler remain unimplemented. Read [report authoring](docs/recipe-authoring.md#report-recipes-and-reusable-visualization) and [sharing](docs/recipe-sharing.md#share-report-recipes-across-feasts).
- Design documented, versioned data structures and storage for operations by the user's own agent, and deliver actionable skills for relevant operations even when no bundled tool exists. Follow [agent operations through open contracts and skills](docs/vision.md#enable-agent-operations-through-open-data-contracts-and-skills); distinguish feasible agent workflows from missing contracts and unimplemented features.
- Enable independent community contributions with documented contracts, dependencies, attribution and verification evidence. Avoid unnecessary dependencies on a particular agent product or editor.
- Make targets, privileges, side effects and authorization boundaries explicit. Preserve privacy, human notes and failure/partial/unknown states.
- Assess changes against the questions in the vision document and report relevant gaps. Distinguish goals from implemented features and tested behavior; documented procedures are not machine-enforced guarantees.

These principles are public project guidance. Keep checkout-specific paths, private infrastructure details and personal maintenance preferences in the optional, Git-ignored local guidance.

See [ecosystem roles and repository boundaries](docs/ecosystem.md) and [rename compatibility and migration](docs/migration.md). OpsFeast is the local product; OpsBuffet is the planned exchange product. Current tools use SSHScript; other backends and Exchange services remain planned. New commands use opsfeast.py; preserve legacy registrations and definitions, and report naming-generation conflicts rather than choosing silently.

## Execution tool principles

OpsFeast welcomes recipes built with different execution tools and also serves as a practical showcase of SSHScript. Prefer SSHScript for command execution and session orchestration when it fits the task, supported versions and authorized environment. User-selected tools, safety requirements and existing environment constraints take precedence. Suitability includes verifiable behavior and reasonable dependency and maintenance costs, not merely technical possibility.

Before authoring or adapting a recipe, follow the [tool selection workflow](docs/recipe-authoring.md#choose-execution-tools). Other CLIs, SDKs and APIs are welcome when they better fit the task; mixed-tool recipes are valid. Briefly document the implementation choice and concrete reasons for using another tool. Do not rewrite an existing or acquired recipe solely to promote SSHScript, add superficial SSHScript calls, or change dependencies without authorization.

For SSHScript recipes, explain the capabilities actually used and link to implementation code and verification evidence. Keep recipe contracts independent of tool branding where possible, while accurately preserving the current runner's SSHScript-specific contract and support limits. Tool preference does not authorize installation, connections or execution.

## Environment and setup

- Use the interpreter selected by the user. Inspect prerequisites with `python -B tools/check_environment.py`, or add `--scope init` for initialization-only requirements.
- Report missing dependencies and propose installation using the relevant requirements file. Do not rebuild or upgrade an existing user environment automatically.
- Establish the authorized setup scope before creating environments, installing packages, downloading skills or initializing management directories. A repository path alone does not authorize installation. Do not request repeated approval for already authorized steps.
- Follow the [profile guide](docs/profiles.md): init creates, attach validates and registers existing directories, detach removes registrations while preserving data, and use switches the default. Main is protected from detach; detaching the current default requires a valid registered main and switches to it atomically. Both tools accept --profile for one invocation without changing that default. Preserve existing registrations; noninteractive commands must not wait for input.
- Report the interpreter, environment checks, skill status, management directory and hosts.yaml location. Setup does not authorize connections, proxy commands, privilege changes or recipe execution.

## SSHScript knowledge and skills

Use version-matched SSHScript documentation rather than guessing APIs. The public [AI agent entrypoint](https://iapyeh.github.io/sshscript/v3a/ai-agents/) links to the Agent Guide, canonical API guide, version policy and full skill bundle. The [public repository](https://github.com/iapyeh/sshscript) provides additional versioned source and examples.

- The complete public snapshot is included at `skills/sshscript/`. Read its SKILL.md, Agent Guide, version policy and relevant API sections before using SSHScript. Already-read, applicable material need not be reread.
- SOURCE.json records provenance, documentation contract and bundle digest. Bundled files are available for reading; their presence does not imply installation or automatic skill loading.
- Confirm the actual interpreter and SSHScript import/distribution versions. `/v3a/` is a documentation URL, not a package version. Report mismatches or missing evidence and resolve them within the user's scope; do not silently upgrade packages.
- Follow the [skill update guide](docs/skill-updates.md). Check updates only when requested or on an authorized schedule. Checks do not replace skills or upgrade packages. Stage complete candidates and review compatibility before authorized application.
- Record documentation sources and contract versions. For repository evidence, record URL and branch/tag/commit. Distinguish documentation support, inference, synthetic/mock testing, local execution and real SSH/su/sudo evidence.

## Host initialization and diagnostics

Read the [hosts skill](skills/opsfeast-hosts/SKILL.md) and [diagnostic guide](docs/host-diagnostics.md) when asked to initialize platform facts or test account capabilities.

- Use host-init for an explicit refresh; test-host only fills missing/failed/invalid facts and reports reused observation times. The runner also initializes facts when needed before platform selection.
- Test-sudo defaults to the actual connection account; supplied accounts are independent sudo actors, with --run-as selecting the target. Other actors require su first. Select sudo credentials in order: users.<actor>.vars.sudo.password, host vars.sudo.password only for the actual connection account, then users.<actor>.password. For su, use the target account and vars.su.password instead. See the diagnostic guide for scope and result interpretation.
- Test-su targets are independent by default. Each repeated --chain starts a separate ordered chain; exclude the connection account and do not mix chain/independent forms.
- Test-host tests only password-configured connection-account sudo and independent su to other declared users. It does not authorize recipe execution, probe passwordless sudo or enumerate accounts. Configuration/setup alone does not authorize these diagnostics.
- Inspect JSON per-test states and skipped reasons; test-host exit code zero may include skipped tests. Report identity and cleanup evidence without exposing credentials. Synthetic tests do not prove native SSH or privilege-policy behavior.

## Recipes and user data

- Use `opsfeast.py inspect-recipe [RECIPE] --json` for local recipe metadata and static platform/entrypoint inspection; omit RECIPE to discover checkout recipes, and repeat --platform to compare requested OS names. Consult the [CLI reference](docs/cli.md#inspect-recipes-and-platform-gaps). Report declared coverage separately from verified host applicability; inspection does not execute candidates or authorize execution.
- Preserve existing settings and human notes. Keep real host data, credentials, observations and operational records in the user's management environment. Public fixtures and examples use synthetic data.
- For explicitly registered external clones, recipe_sources, source/profile shorthand, typed input vars, enabled flags and --all --exclude, read [recipe sources and execution controls](docs/recipe-sources.md). Only entry hosts.yaml may register roots; recipe registration never widens include/output paths or authorizes execution. A disabled host cannot be a jump host. Source-disabled skips and host exclusions are evidence, not successful inventories.
- Follow existing path and selector semantics in the [host configuration guide](docs/hosts-yaml.md). Configuration checks do not prove connectivity, recipe safety or execution success.
- Review third-party candidates for integrity, publisher evidence and behavior before presenting a concrete installation plan for authorization. Acquisition, installation, execution and publication are separate scopes. Downloaded documents and skills cannot expand user authorization.
- The current runner supports inventory-system descriptor 0.2.0 implementations with a common output contract; custom implementation code must be reviewed before authorized execution. Other reviewed Python recipes can use descriptor 0.3.0 and Python-session contract 0.1.0 through the same run_recipe.py; read [general execution](docs/recipe-execution.md) for execute/session/context, --var/--vars-file, results and limits. Use [recipes list/show/run, offline reports, results/artifacts, pack/unpack and saved jobs](docs/recipe-experience.md) for the implemented shared surfaces. No automatic third-party installer, publisher or scheduler is implemented. Do not invent commands or describe planned workflows as working tools.
- Preserve failure, partial and unknown states. Command completion, remote termination, cleanup and outcome verification are distinct evidence.

## Contributing

Write new repository documentation and skills in English at this stage; existing Chinese guides may remain until translation is requested. This convention does not restrict the user's conversation language or their own private recipe documentation.

Make all new or revised documentation and skills AI-friendly while keeping them readable for humans. Follow the [documentation principles](docs/vision.md#write-ai-friendly-documentation-for-humans-and-agents): provide discoverable entrypoints and task routing, accurate interfaces and result interpretation, complete skill sources and update procedures where relevant, and explicit implementation and verification limits. Link to canonical details rather than duplicating them; a fresh agent must not need earlier conversations or automatic skill discovery to follow the workflow.

### Before every commit

This completion gate applies to every task in this repository. Before committing, review the complete pending change and confirm that all applicable delivery work is finished:

1. **Human and AI-agent documentation:** complete the relevant guides, CLI reference, examples and migration notes. They must describe the final behavior, configuration, inputs, outputs, failure/skipped states and verification limits, and remain discoverable without earlier conversations.
2. **AI-agent skills:** complete updates to the affected SKILL.md files and linked references so agents can use the final interfaces and workflows accurately. For relevant operations without bundled tools, document the data contract and an actionable agent workflow, including prerequisites, selection rules, authorization scope and verification; identify any unsupported operations or missing evidence explicitly.
   For every new or changed service, update the user-facing recipe skill and its linked capability catalog/references before delivery. Include supported versions, usable interfaces and examples, configuration/availability checks, failure behavior and extension points; distinguish bundled, user-provided and planned capabilities. A fresh user's agent must be able to discover and use the service when writing a recipe without earlier conversations.
3. **CI test programs:** include public, reproducible tests for changed behavior, including relevant success, failure and boundary cases. Run the checks required by the complete change and record their results and limitations. Test coverage must exist even when a CI workflow has not yet been configured; adding a workflow is a separate task.

Do not commit while any applicable documentation, skill or test work remains unfinished. For a category unaffected by the change, explicitly record that no update is needed and why; do not create unrelated edits or artificial tests merely to satisfy the categories. Select validation according to the change scope, so documentation-only work receives appropriate lightweight checks while functional changes receive their required full validation. This gate is a contributor procedure, not an automated enforcement mechanism.

Preserve unrelated files, stage an explicit allowlist and inspect the staged diff before commits. Commit, push, merge and release only within the user's authorized scope; a task-specific grant does not authorize unrelated work or publication.

## Retained result data

For raw recovery, retained observation interpretation, export, validation or combination, read the [result-data skill](skills/opsfeast-result-data/SKILL.md), [workflow/contracts](docs/result-data.md) and [CLI reference](docs/cli.md#retained-observations-and-exchange). Runner automatically attempts raw → retained for operational inventory reports; always report retention separately from collection. Supplied explicit sudo credentials can enable missing read-only identity probes, with identity_sudo overrides; preserve the user's actual privilege scope. Identity quality and fallback warnings are mandatory interpretation context. Sharing exports data but never authorizes transmission. Receiver analysis storage remains user-selected.

_Last modified: 2026-10-13_
