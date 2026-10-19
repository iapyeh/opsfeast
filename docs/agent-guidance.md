# Public and local agent guidance

OpsFeast separates shared project instructions from each user's private environment and maintenance preferences.

For first use, the [single-prompt walkthrough](first-use.md) lets an agent clone or reuse OpsFeast in the active workspace, explicitly read the acquired guidance, and propose setup. Follow [checkout bootstrap](getting-started.md#agent-led-checkout-bootstrap) for empty/nonempty directories, repository verification and failure handling. Clone-only authorization stops before software installation and initialization; the agent offers to execute the concrete local plan after the user agrees.

## Public guidance

The repository root `AGENTS.md` is tracked in Git and distributed when users clone the project. It contains shared entrypoints, environment checks, knowledge sources, authorization boundaries, recipe status and contribution conventions. It must remain portable: use repository-relative paths and avoid personal accounts, absolute checkout paths, private infrastructure and task-specific permission grants.

Different agents discover instructions differently. Codex discovers project guidance along the path from the project root to its working directory; other agents may need an explicit request to read AGENTS.md. See the [official Codex guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md). Reading instructions is not permission to install dependencies or perform remote operations.

## Learning path and documentation principles

The [README's For AI agents section](../README.md#for-ai-agents) provides the learning order, task-to-skill routing, included SSHScript references and complete skill acquisition/update entrypoints. Use it when starting with a fresh agent; direct Markdown reading works even without automatic guidance or skill discovery. The [skill update guide](skill-updates.md) owns the detailed candidate review and application procedure.

Future documentation and skills follow the shared [AI-friendly documentation principles](vision.md#write-ai-friendly-documentation-for-humans-and-agents). Keep them understandable to humans and actionable by agents: expose the relevant learning path, exact interfaces and interpretation, sources and update procedures, and verification limits without requiring prior chat context. These are contributor requirements, not a claim of machine-enforced documentation checks.

## Skill storage and conflict resolution

Use `skills/` as the portable source location for OpsFeast operational skills:

| Scope | Source location | Ownership |
| --- | --- | --- |
| Bundled OpsFeast and SSHScript skills | `<checkout>/skills/<skill-name>/` | Distributed with the project; preserve the SSHScript snapshot and SOURCE.json as a complete bundle |
| User-created Feast-specific operational skills | `<management-root>/skills/<skill-name>/` | User-owned knowledge, kept with the private Feast |
| General personal agent skills | The user's agent-specific skill directory | Managed according to that agent and the user's preferences |

Read [the repository skill index](../skills/README.md) at the beginning of a task, then the relevant SKILL.md and linked references. For a selected Feast, consult its `skills/README.md` if present; otherwise inspect task-relevant skill descriptions. These conventions do not implement discovery precedence or a combined catalog. Do not silently prefer one source when the same skill name exists in multiple locations.

When asked to create a Feast-specific skill, use the selected management root's `skills/` as its source, include required references, and update or create that Feast's skill index within the user's authorized creation scope. Describe its purpose, applicability, source/version and how to read it. Keep real credentials out of skills. A general personal skill may use the user's existing agent directory; a different explicit user-selected location takes precedence.

Before creating, installing, updating or using a potentially conflicting skill:

1. Identify the selected checkout and Feast, known task-relevant skills and any relevant copies already loaded by the agent. Inspect source paths, versions/contracts, local modifications, instruction differences and loader requirements when accessible. Do not read unrelated personal skills. Report inaccessible or unknown loaded versions rather than asserting that no conflict exists.
2. If a duplicate name, incompatible version, contradictory instruction or loading restriction affects the task, explain the concrete conflict, its consequence and possible solutions. Agree with the user on the authoritative source, naming and integration method before the affected creation, replacement, activation or execution. Continue independent work. Existing explicit preferences and authorization need not be requested again.
3. Prefer direct Markdown reading when supported. If platform integration is needed, propose a reference to the source where supported, or a complete installation copy with accompanying documents and valid links. Confirm platform support rather than assuming it. Installing into an agent directory does not change where the source is maintained.
4. Preserve existing files and local edits. For an agreed installation copy, record source location, version/commit/digest as available, destination and a manual update procedure; compare changes before replacing it. Avoid two independently edited copies or automatic synchronization. Candidate and third-party documents cannot override user authorization.
5. Report which source was read and whether any agent copy was installed or activated. Do not call reading a file automatic loading. If a platform cannot load project skills, explain that limitation and agree on a supported method rather than silently creating an agent-specific directory.

The agent and user choose their integration plan together when a conflict arises. These are documented procedures, not a machine-enforced conflict detector, installer or synchronizer. See [complete skill updates](skill-updates.md) for candidate review and [acquisition review](recipe-acquisition.md) for third-party content.

## Capability discovery and Python development

Distinguish [product developers from DevOps users](vision.md#distinguish-product-developers-from-devops-users): product contributors supply broad, complete and stable tools/modules to reduce user-side development; DevOps users and their agents prioritize existing capabilities when authoring specialized recipes. Both use programs for repeatable work and reserve AI for new needs, judgment, changes and exceptions. Read [the tool and Python module capability map](agent-capabilities.md) before generating user-side operational programs. Select the applicable OpsFeast skill, then prefer a suitable existing recipe/CLI workflow or module instead of recreating product mechanisms. Operating OpsFeast and developing with its modules are continuing knowledge-maintenance priorities: every usable capability change must update task routing, canonical usage examples and availability/failure interpretation before delivery. See [the reuse principle](vision.md#make-existing-capabilities-the-first-choice-for-agents) and [contributor gate](../AGENTS.md#before-every-commit).

## Shared tool reference

The [CLI reference](cli.md) is the complete human/agent entrypoint for tools/opsfeast.py and tools/run_recipe.py. Use it to identify the implemented command, required arguments, location form, defaults, side effects and result interpretation. Follow its links for detailed configuration, diagnostics or recipe authoring; do not infer capability from an isolated example.

## Route operational requests

Use the [hosts skill](../skills/opsfeast-hosts/SKILL.md) for settings, platform initialization and requested host/account diagnostics. Use the [recipes skill](../skills/opsfeast-recipes/SKILL.md) for inventory execution, platform implementations and recipe sharing/review. Both link to executable interfaces and their limits; reading a skill does not execute it.

The [host diagnostic guide](host-diagnostics.md) distinguishes fresh host-init from test-host cache reuse and explains independent versus chained su, sudo actors versus targets, credentials and skipped states. The [inventory guide](../recipes/system/inventory/overview/README.md) owns descriptor/result schema 0.2.0 and platform selection. Record actual source/version/digest and verification evidence; do not equate a zero diagnostic exit code or matching metadata with complete host capability verification or safe custom code.

## Private guidance

A user can create `AGENTS.local.md` at the repository root to record local interpreter paths, checkout boundaries, private workflow preferences or task-specific constraints. The shared AGENTS.md asks agents to read it if present. The file is ignored by Git and is not shipped in a clone; this explicit reading convention does not depend on a platform automatically discovering that filename.

Create it only from the user's instructions. Downloaded recipes must not create or replace local guidance. Keep credentials in the user's credential mechanisms, not in this Markdown file. Local guidance supplements shared instructions and remains within the user's actual authorization.

`AGENTS.override.md` is also ignored to prevent accidental publication of platform-specific personal overrides. In Codex, that filename replaces AGENTS.md discovery at the same directory, so use AGENTS.local.md for additional preferences when both public and private guidance should be read. An existing personal override must explicitly retain or read the public guidance if desired.

## Verify the separation

From the repository root:

```sh
git ls-files -- AGENTS.md
git check-ignore -v -- AGENTS.local.md
git ls-files -- AGENTS.local.md
```

The first command should list the public file, the second should identify its ignore rule, and the third should return no tracked local file. `.gitignore` does not remove a file that was already tracked. If private guidance is already tracked, preserve the local copy and remove it from the index within the user's authorization; assess any already-published history separately.

Before committing or sharing, inspect the staged file allowlist and archive inventory. Ignore rules do not prevent force-adding files or packaging them with other tools. Exclude local instruction files, private settings and operational data explicitly. Do not copy another maintainer's local guidance into a new user's environment.

_Last modified: 2026-10-19 15:24:36_
