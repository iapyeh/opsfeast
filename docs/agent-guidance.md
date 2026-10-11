# Public and local agent guidance

SSHScript Ops separates shared project instructions from each user's private environment and maintenance preferences.

## Public guidance

The repository root `AGENTS.md` is tracked in Git and distributed when users clone the project. It contains shared entrypoints, environment checks, knowledge sources, authorization boundaries, recipe status and contribution conventions. It must remain portable: use repository-relative paths and avoid personal accounts, absolute checkout paths, private infrastructure and task-specific permission grants.

Different agents discover instructions differently. Codex discovers project guidance along the path from the project root to its working directory; other agents may need an explicit request to read AGENTS.md. See the [official Codex guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md). Reading instructions is not permission to install dependencies or perform remote operations.

## Learning path and documentation principles

The [README's For AI agents section](../README.md#for-ai-agents) provides the learning order, task-to-skill routing, included SSHScript references and complete skill acquisition/update entrypoints. Use it when starting with a fresh agent; direct Markdown reading works even without automatic guidance or skill discovery. The [skill update guide](skill-updates.md) owns the detailed candidate review and application procedure.

Future documentation and skills follow the shared [AI-friendly documentation principles](vision.md#write-ai-friendly-documentation-for-humans-and-agents). Keep them understandable to humans and actionable by agents: expose the relevant learning path, exact interfaces and interpretation, sources and update procedures, and verification limits without requiring prior chat context. These are contributor requirements, not a claim of machine-enforced documentation checks.

## Shared tool reference

The [CLI reference](cli.md) is the complete human/agent entrypoint for tools/ops.py and tools/run_recipe.py. Use it to identify the implemented command, required arguments, location form, defaults, side effects and result interpretation. Follow its links for detailed configuration, diagnostics or recipe authoring; do not infer capability from an isolated example.

## Route operational requests

Use the [hosts skill](../skills/sshscript-ops-hosts/SKILL.md) for settings, platform initialization and requested host/account diagnostics. Use the [recipes skill](../skills/sshscript-ops-recipes/SKILL.md) for inventory execution, platform implementations and recipe sharing/review. Both link to executable interfaces and their limits; reading a skill does not execute it.

The [host diagnostic guide](host-diagnostics.md) distinguishes fresh host-init from test-host cache reuse and explains independent versus chained su, sudo actors versus targets, credentials and skipped states. The [inventory guide](../recipes/inventory/system/README.md) owns descriptor/result schema 0.2.0 and platform selection. Record actual source/version/digest and verification evidence; do not equate a zero diagnostic exit code or matching metadata with complete host capability verification or safe custom code.

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

_Last modified: 2026-10-11_
