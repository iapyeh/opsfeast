# 3. Set up and take over an environment

[Book home](README.md) · Previous: [Architecture](02-architecture.md) · Next: [Hosts and access](04-hosts-and-access.md)

Setup establishes a local environment for future operations. It should leave you knowing the checkout, selected interpreter, profile root, `hosts.yaml` location and current readiness. It does not establish that a remote host can be reached.

## Ask for a concrete local plan

> Read the repository guidance and first-use guide. Inspect this workspace and existing Python environments without changing them. Explain OpsFeast's capabilities and propose the actual local setup: checkout, interpreter, dependency files, management root and skill status. Offer to perform that plan. Do not connect to hosts.

The first-use workflow allows cloning into the active project directory. In an empty workspace the checkout can occupy that directory; in a nonempty workspace use an `opsfeast/` child. Reuse an existing checkout only after verifying repository identity and its guidance. Preserve existing files and changes; clone-only scope does not permit pulling, resetting, installing packages or initializing profiles.

## Check the selected interpreter

From the actual checkout, these checks inspect readiness without installing dependencies or connecting:

```sh
python -B tools/check_environment.py
python -B tools/check_environment.py --scope init
python -B tools/opsfeast.py --help
```

Use a working selected Python 3.11+ before proposing another distribution. The initialization requirements include PyYAML and tabulate; full operational requirements add the supported SSHScript distribution. Optional Textual belongs to `requirements-tui.txt`. The current execution environment expects matching SSHScript import/distribution 7.0.0 and version-matched guidance. A different interpreter's missing package does not prove that the selected environment lacks it.

If installation is needed, review the actual interpreter, paths and relevant requirements file. Once that concrete local plan is approved, the agent should execute it without repeating the same approval. Do not rebuild an existing working venv merely for convenience. The canonical [setup guide](../../getting-started.md) provides installation commands and dependency evidence rules.

Skill sources in `skills/` can be read directly. Their presence or an agent reading them is not proof that they were installed into a particular agent product or automatically loaded.

## Initialize or attach

After local initialization is within scope:

```sh
python -B tools/opsfeast.py init main --json
python -B tools/opsfeast.py profiles
python -B tools/opsfeast.py check --profile main --json
```

Init creates the management scaffold and registers its root. New named profiles normally live under `feasts/`; an explicit path can select another location. New initialization establishes a retention namespace and operational Vault. Existing configuration and namespace are preserved. Use the returned root and `hosts.yaml` path rather than guessing from the profile name.

For an existing management root, attach registers and validates it without recreating the scaffold:

```sh
python -B tools/opsfeast.py attach /absolute/path/to/existing-feast --profile team
python -B tools/opsfeast.py check --profile team --json
```

`--profile team` selects one invocation. `use team` changes the persisted default; it is a deliberate local configuration change. `detach team` removes a registration while preserving data. Main cannot be detached; detaching the current non-main default requires a usable registered main. Read the [profile guide](../../profiles.md) before changing registrations.

## Take over an inherited environment

> Identify this OpsFeast installation and its registered management roots. Read current guidance and inspect configuration, recipe sources, service adapters, schedules and recent saved outcomes without connecting, dispatching or initializing. Preserve instance identity, private settings and human notes. Report missing dependencies and ambiguous ownership before proposing changes.

Do not initialize merely because you have not seen this environment before. `profiles`, `check`, saved-result browsing and static service inspection reveal different aspects of readiness. Basic profile availability does not validate the whole configuration; a passing configuration check does not establish connectivity.

When moving an installation, preserve identity according to the Core guide. A copied checkout needs its own installation UUID; do not casually regenerate identity on a legitimate move. The user agent must reread current object schemas and data contracts after a release update, even if it remembers an earlier release. No reading receipt or enforcement mechanism is required.

## Start using the CLI or current TUI

With an approved checkout `.venv`, Bash/Zsh users can enter the actual checkout and run:

```sh
source tools/activate.sh
python -B tools/opsfeast.py check --profile main
python -B tools/opsfeast.py
```

Activation affects this shell. The final command opens the Textual Home only when Textual is available in the selected environment. Opening Home does not connect; choosing a host operation can. Ask the agent to check Textual and supply an installation plan if absent. Users of another environment can invoke its selected Python directly.

The [current terminal guide](../../terminal-ui.md) documents implemented screens. This edition does not assume TUI coverage for every chapter; fuller walkthroughs follow verified TUI development.

**Checkpoint:** Record the actual checkout, interpreter, profile/root and `hosts.yaml`, whether full execution dependencies and optional Textual are available, and which host operations have been authorized.

*Last modified: 2026-10-26 12:55:26*
