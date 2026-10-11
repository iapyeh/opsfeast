# Your first experience with SSHScript Ops

Clone SSHScript Ops, give its directory to your AI agent, and ask it to explain the requirements and propose a setup. After you authorize the plan, the agent can initialize your environment. You do not need to learn every Python tool's arguments first. This walkthrough assumes an agent such as Codex or Hermes that can read local files and run commands. If the agent runs on another machine, the repository must be accessible there.

The goal is to create a management environment and understand where to configure hosts. After initialization, choose the hosts to test and the collection tasks to run.

## 1. Clone the project

On a computer with Git installed:

```sh
git clone https://github.com/iapyeh/sshscript-ops.git
cd sshscript-ops
```

Record the directory's absolute path. On macOS/Linux, use `pwd`; in PowerShell, use `Get-Location`. Replace `/absolute/path/to/sshscript-ops` in the prompts below with that path. On Windows, use the full Windows path.

## 2. Let your agent learn about the project

Start a new conversation and paste:

> I am using SSHScript Ops for the first time. The repository is at `/absolute/path/to/sshscript-ops`. Read README.md, AGENTS.md and docs/getting-started.md. Explain what the project can do, what environment it needs, and propose an initial setup. Do not install dependencies or initialize anything yet.

The agent should find the project guidance, explain the Python 3.11+ requirement and the dependencies for initialization or the full toolset, and report:

- The complete public skill snapshot is included in Git and can be read directly. A fresh download is usually unnecessary for first use.
- The project can initialize and validate configuration, query settings, test a specified host connection, and run the currently supported inventory-system recipe.
- Which Python interpreter it will use, whether it will create an environment, which dependencies it will install, and where management data will be stored.

If the agent cannot find the files, confirm that it can access the directory you provided. If Python is unavailable, have it report the gap and an installation proposal appropriate to your computer.

## 3. Review the plan and authorize local initialization

If you agree to a separate Python environment inside the project, paste:

> Create an isolated `.venv` in this project, install the full dependencies, read the included skill, and run the default init and check commands. Do not connect to remote hosts or execute recipes. When finished, tell me what to configure next.

If you already have a Python environment, provide its interpreter path instead. Ask the agent to reuse it and report missing dependencies first. The [getting-started guide](getting-started.md) defines the installation procedure.

After successful setup, the layout should include:

```text
sshscript-ops/
├── .venv/
├── .my-ops.yaml
├── recipes/
└── my-ops/
    └── main/
        ├── my-ops.yaml
        ├── hosts.yaml
        ├── hosts/
        ├── observations/
        ├── records/
        └── runs/
```

`.venv/` exists only if you chose to create a new environment. `my-ops/` and `recipes/` are siblings. `.my-ops.yaml` records profiles and the default environment, allowing later commands to omit the directory argument. The agent should report the actual interpreter, package and documentation versions, initialization/check results, and the full path to `hosts.yaml`.

## 4. Configure your hosts

Open the reported `my-ops/main/hosts.yaml`. The initial template includes localhost and a remote example with the synthetic address `host.example`. Replace the example host ID and address, set the login account and authentication method, and configure `via` if a jump host is needed. Recipe lists start empty; add selections as needed.

Your agent can help organize settings, but do not paste passwords or private keys into chat. See the [host configuration guide](hosts-yaml.md) for fields and authentication rules. The default management directory is ignored by Git; keep real settings and observations in your management environment.

After editing, paste:

> Validate the current default management environment's configuration. Do not connect or execute recipes. If validation fails, identify the source file and what needs correction.

This also checks that the agent uses the same interpreter and can run `ops.py check` without a directory argument. Successful configuration validation does not establish connectivity. When ready, specify a host ID for a connection test. For inventory collection, separately specify the recipe and execution scope.

## Optional: initialize and test a configured host

For platform discovery without account-switch tests, paste after replacing the host ID:

> Read docs/host-diagnostics.md and the Ops hosts skill. Run host-init for host-01 in my default profile to refresh its platform facts. I authorize the configured connection and read-only platform queries. Do not run su, sudo or recipes. Report the result and saved facts path.

For the configured host diagnostic suite, paste:

> Read docs/host-diagnostics.md and the Ops hosts skill. Run test-host for host-01 in my default profile. I authorize its configured connection, read-only login/platform checks, connection-account sudo shell/identity testing only when an explicit sudo password is configured, and independent su shell/identity testing to other accounts declared for that host. Do not test chains, passwordless sudo or recipes. Report each test, skipped reasons and whether facts were reused or freshly collected; do not disclose credentials.

Test-host reuses successful target-matching facts; direct host-init always refreshes. A zero test-host exit code may include skipped tests. Platform facts do not prove recipe compatibility or complete account privileges. Native SSH/su/sudo validation is still pending; the tool reports actual outcomes without assuming success. Inventory is a separately authorized operation: one inventory/system recipe can dispatch mixed-platform hosts automatically. See its [guide](../recipes/inventory/system/README.md).

## 5. Try a skill update check

Paste:

> Check whether the public SSHScript skill has changed. Compare and report only; do not apply updates, upgrade packages or create a schedule.

The agent should follow the [skill update guide](skill-updates.md), compare the public bundle, and report equality, the candidate documentation contract and compatibility. No change is a normal result. A failed check must be reported as a failure, not as no update. If you later want periodic checks, agree on scope, frequency and notifications, then use the agent platform's scheduling capability.

## Use multiple environments or take over existing data

To organize another group of hosts, ask your agent to create a named environment, such as `ops.py init inventory`. Its data resides in `my-ops/inventory/`. `ops.py profiles` lists environments, and `ops.py use inventory` changes the default. In an interactive terminal, `ops.py use` lets you select one.

When moving computers, handing over work or receiving a colleague's management directory, use `ops.py add /path/to/existing-profile` to validate and register it. This does not create a scaffold or rewrite the directory's files. Choose a new profile name if there is a conflict. See the [profile guide](profiles.md) for naming and path rules.

## Try it without reusing existing management data

Clone into a new directory, for example:

```sh
git clone https://github.com/iapyeh/sshscript-ops.git sshscript-ops-trial
```

Give the trial directory's absolute path to the agent and follow the steps above. A new clone does not include ignored management settings, Python environments or locator files.

Maintainers can test committed local changes that have not been pushed by cloning their local repository into a new directory. Replace these paths with your own:

```sh
git clone "/absolute/path/to/sshscript-ops" "/absolute/path/to/sshscript-ops-trial"
```

A local clone includes committed content only. To compare another agent's experience, start a fresh conversation and trial directory so it uses the repository documentation for setup. Check whether it finds the getting-started guide, reads the included skill correctly, and clearly reports the next steps.

_Last modified: 2026-10-11_
