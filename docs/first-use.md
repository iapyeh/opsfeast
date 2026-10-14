# Your first experience with OpsFeast

Open a project directory in your AI coding tool and give its agent the single prompt below to clone OpsFeast, read its guidance and propose a setup. After you authorize the plan, the agent can initialize your environment. You do not need to learn every Python tool's arguments first. This walkthrough uses an AI coding tool, such as Codex, Antigravity or Claude Code, whose agent can read local files and run commands. Project/workspace means the directory opened in that tool; UI labels vary. If the agent runs on another machine, choose the project directory on that machine and ensure it can access GitHub.

The goal is to create a management environment and understand where to configure hosts. After initialization, choose the hosts to test and the collection tasks to run.

For complete tool syntax, defaults, behavior, output and exit codes, see the [CLI reference](cli.md). It covers both tools/opsfeast.py and tools/run_recipe.py for administrators and agents.

## 1. Create a project/workspace

Choose a local directory, open it as a project/workspace in an AI coding tool with local file/command and GitHub network access, and start a fresh conversation. You do not need to run Git commands or replace a path in the prompt. An empty directory is convenient; existing workspace files are preserved.

## 2. Let your agent learn about the project

Paste this unchanged into the new conversation:

```text
Help me get started with OpsFeast in this project's directory. I authorize cloning https://github.com/iapyeh/opsfeast.git here; use an opsfeast subdirectory if the current directory is not empty, and preserve existing files. Reuse an existing OpsFeast checkout if present.

Read the checkout's README.md, AGENTS.md and docs/getting-started.md, then follow their first-use guidance. Check prerequisites without making changes, propose a local setup you can perform for me, and ask for my approval. Do not install software, create environments or initialize profiles until I agree.
```

The agent first performs the authorized clone: directly into an empty directory, or into a new `opsfeast/` subdirectory if the workspace is nonempty. A verified existing checkout is reused without pulling, resetting or overwriting it. A conflicting destination or missing Git/access is a blocker to explain, not permission to delete files or install software. After acquisition, the agent explicitly reads the checkout's guidance, including its reply-language and setup-approval rules; automatic reloading of newly cloned instructions is not assumed. It uses the checkout for subsequent commands and environment placement even if the workspace is its parent. See [the bootstrap procedure](getting-started.md#agent-led-checkout-bootstrap).

An English app interface does not determine the language of the agent's replies. You can append `Reply to me in Traditional Chinese (Taiwan).` to make that preference explicit. When the system display language is unavailable or ambiguous, the agent should ask rather than assume English.

The agent should find the project guidance, explain the Python 3.11+ requirement and the dependencies for initialization or the full toolset, and report:

- The complete public skill snapshot is included in Git and can be read directly. A fresh download is usually unnecessary for first use.
- The project can initialize and validate configuration, query settings, test a specified host connection, and run the currently supported inventory-system recipe.
- Which Python interpreter it will use, whether it will create an environment, which dependencies it will install, and where management data will be stored.

The proposal should prefer an existing working Python and distinguish OpsFeast packages from the chosen Python distribution's system dependencies. An extra system package needs a concrete error or official distribution/OS dependency evidence, with an explanation of what requires it; a generic list such as “install expat first” is insufficient. Normal package-manager dependency resolution should not be duplicated as speculative manual installation steps. See [dependency evidence](getting-started.md#dependency-evidence-and-python-reuse).

If the agent cannot find the files, confirm that it can access the directory you provided. If Python is unavailable, have it report the gap and an installation proposal appropriate to your computer.

## 3. Review the plan and authorize local initialization

The agent should finish its proposal by offering to perform the work and asking whether to proceed, in your preferred language. For example:

> I can carry out this local setup for you. Shall I proceed with the plan above? You can simply reply “I agree”.

If the concrete plan is suitable, replying `I agree` (or its equivalent in your language) is enough to authorize that local setup. The agent should execute the approved plan and report the results; the listed steps are not a requirement for you to run commands yourself. Existing authorization should not be requested again. If a tool/access limitation requires your help, the agent should identify that specific step.

No second prompt is required for the normal flow. As an optional alternative, if you want to specify a separate Python environment inside the checkout explicitly, paste:

> Create an isolated `.venv` at the confirmed OpsFeast repository root, install the full dependencies, read the included skill, and run the default init and check commands. Do not connect to remote hosts or execute recipes. When finished, tell me what to configure next.

If you already have a Python environment, provide its interpreter path instead. Ask the agent to reuse it and report missing dependencies first. The [getting-started guide](getting-started.md) defines the installation procedure.

After successful setup, the layout should include:

```text
opsfeast/
├── .venv/
├── .opsfeast.yaml
├── recipes/
└── feasts/
    └── main/
        ├── feast.yaml
        ├── hosts.yaml
        ├── hosts/
        ├── observations/
        ├── records/
        └── runs/
```

`.venv/` exists only if you chose to create a new environment. `feasts/` and `recipes/` are siblings. `.opsfeast.yaml` records profiles and the default environment, allowing later commands to omit the directory argument. The agent should report the actual interpreter, package and documentation versions, initialization/check results, and the full path to `hosts.yaml`.

### Use the CLI or try the interactive Home

The agent should finish setup by offering both interfaces with your actual checkout/interpreter paths. For Bash/Zsh with a checkout `.venv`, run these in the checkout's terminal:

```sh
source tools/activate.sh
python -B tools/opsfeast.py
```

The second command opens the Textual Home, with Profiles, Recipes, Hosts, Help and Actions. Textual is optional and not part of `requirements.txt`; the agent must check its availability in the selected environment. If it is missing, ask for an installation proposal using `requirements-tui.txt` before launching. Do not infer TUI readiness from the ordinary environment check. The [terminal interface guide](terminal-ui.md) covers prerequisites and navigation.

Use `source`, not `sh tools/activate.sh`; activation affects the shell where it is sourced. The helper preserves your current directory, so the agent should provide the actual checkout `cd` command when needed. Other environments can run their selected Python directly with `-B`; no shell activation is required. If activation reports a missing file, inspect the **Expected activation file** path before creating or replacing any environment.

After configuring a host, you can use the CLI examples below or open **Hosts**, select that host and press Enter → **test-connection**. Opening Home does not connect; selecting test-connection performs the explicit host/jump checks. CLI output and TUI results follow the same result semantics and authorization scope.

## 4. Configure your hosts

Follow [Connect your first host](first-host.md). It starts with the smallest usable settings and provides exact validation/connection commands, expected results and common failure checks. Ask the agent to help prepare one host using your address, login account and chosen authentication method; enter secrets locally. Preserve existing data and comments. The initial host.example is synthetic, not ready to connect.

After editing, paste:

> Validate profile main without connecting or executing recipes. Correct only the intended host settings within my configuration scope. Report the actual source file and result, then provide copyable commands and agent prompts using my checkout path, interpreter, profile and host ID. Explain which next steps connect, test privileges or collect inventory. Do not execute steps beyond my authorization.

For a new main profile with a checkout .venv, the first local check is:

```sh
cd "/absolute/path/to/opsfeast"
.venv/bin/python -B tools/opsfeast.py check --profile main
```

Replace the path with your clone. The agent must supply your actual values, rather than leave placeholders in its handoff. After this passes, the first-host guide provides a narrow hostname/date connection test and optional inventory. Its su/sudo cases are separate later choices; test-host may include configured privilege tests.

For manual Bash/Zsh use, you may activate the existing environment:

```sh
source tools/activate.sh
python -B tools/opsfeast.py check --profile main
```

The helper exports PYTHONDONTWRITEBYTECODE=1, locates this checkout's .venv even when sourced from another directory, and leaves your working directory unchanged. Source it rather than run it with bash; see [manual environment use](cli.md#manual-environment-use). Agents should use the selected interpreter directly.

## Optional: initialize and test a configured host

For platform discovery without account-switch tests, paste after replacing the host ID:

> Read docs/host-diagnostics.md and the Ops hosts skill. Run host-init for host-01 in my default profile to refresh its platform facts. I authorize the configured connection and read-only platform queries. Do not run su, sudo or recipes. Report the result and saved facts path.

For the configured host diagnostic suite, paste:

> Read docs/host-diagnostics.md and the Ops hosts skill. Run test-host for host-01 in my default profile. I authorize its configured connection, read-only login/platform checks, connection-account sudo shell/identity testing only when the credential precedence rule selects a configured password (including the account password), and independent su shell/identity testing to other accounts declared for that host. Do not test chains, passwordless sudo or recipes. Report each test, skipped reasons and whether facts were reused or freshly collected; do not disclose credentials.

Test-host reuses successful target-matching facts; direct host-init always refreshes. A zero test-host exit code may include skipped tests. Platform facts do not prove recipe compatibility or complete account privileges. Native SSH/su/sudo validation is still pending; the tool reports actual outcomes without assuming success. Inventory is a separately authorized operation: one inventory/system recipe can dispatch mixed-platform hosts automatically. See its [guide](../recipes/inventory/system/README.md).

## 5. Try a skill update check

Paste:

> Check whether the public SSHScript skill has changed. Compare and report only; do not apply updates, upgrade packages or create a schedule.

The agent should follow the [skill update guide](skill-updates.md), compare the public bundle, and report equality, the candidate documentation contract and compatibility. No change is a normal result. A failed check must be reported as a failure, not as no update. If you later want periodic checks, agree on scope, frequency and notifications, then use the agent platform's scheduling capability.

## Use multiple environments or take over existing data

To organize another group of hosts, ask your agent to create a named environment, such as `opsfeast.py init inventory`. Its data resides in `feasts/inventory/`. `opsfeast.py profiles` lists environments, and `opsfeast.py use inventory` changes the default. In an interactive terminal, `opsfeast.py use` lets you select one.

When moving computers, handing over work or receiving a colleague's management directory, use `opsfeast.py attach /path/to/existing-profile` to validate and register it. This does not create a scaffold or rewrite the directory's files. Choose a new profile name if there is a conflict. Detach NAME removes a registration while preserving data; main is protected, and removing the current default first validates main and switches to it. Profiles shows basic missing/invalid status without automatically deleting entries. See the [profile guide](profiles.md) for lifecycle, naming and path rules.

## Try it without reusing existing management data

Clone into a new directory, for example:

```sh
git clone https://github.com/iapyeh/opsfeast.git opsfeast-trial
```

Give the trial directory's absolute path to the agent and follow the steps above. A new clone does not include ignored management settings, Python environments or locator files.

Maintainers can test committed local changes that have not been pushed by cloning their local repository into a new directory. Replace these paths with your own:

```sh
git clone "/absolute/path/to/opsfeast" "/absolute/path/to/opsfeast-trial"
```

A local clone includes committed content only. To compare another agent's experience, start a fresh conversation and trial directory so it uses the repository documentation for setup. Check whether it finds the getting-started guide, reads the included skill correctly, and clearly reports the next steps.

_Last modified: 2026-10-14_
