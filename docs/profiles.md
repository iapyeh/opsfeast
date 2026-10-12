# Feasts and profiles

A **Feast** is a private management instance with hosts.yaml, recipe selections, observations, records and runs. A **profile** registers a Feast under a name and selects it for a command. Built-in recipes are shared from the tool checkout's recipes/. Initialization and registration do not connect or execute recipes.

Use the [CLI reference](cli.md) for exact interfaces and the [migration guide](migration.md) for former SSHScript Ops names.

## Initialize a Feast

| Command | New root on a fresh checkout | Profile |
| --- | --- | --- |
| python -B tools/opsfeast.py init | <checkout>/feasts/main | main |
| python -B tools/opsfeast.py init inventory | <checkout>/feasts/inventory | inventory |
| python -B tools/opsfeast.py init /srv/team/inventory | /srv/team/inventory | inventory |
| python -B tools/opsfeast.py init ./inventory | <shell-directory>/inventory | inventory |

Named init reuses the registered root for that name, including a legacy my-ops/ or external root. No-argument init reuses the registered main root. If main is absent, it creates feasts/main; an existing default selection is preserved. default is the selection role, not the fixed name of a new Feast. Schema-1 locators still expose a profile named default.

A new instance receives feast.yaml with schema_version: 1 and kind: opsfeast. Reinitialization preserves existing host settings and valid legacy definitions. No recipes directory is created inside a new Feast; custom recipes are optional.

An explicit path containing / or a backslash is relative to the shell directory unless absolute; a bare name selects the checkout's feasts/ location or an existing named profile. Tilde paths are expanded. Use ./inventory when you mean a shell-relative path. --profile NAME sets an explicit registration name. Name conflicts require an explicit different name; terminal prompts may offer a suggestion, but noninteractive commands fail without waiting.

## Attach an existing environment

```sh
python -B tools/opsfeast.py attach /path/to/existing-feast
python -B tools/opsfeast.py attach ./inventory --profile team.inventory
```

attach always takes a path, validates the instance and its hosts/includes/connections/recipe selections, and registers it without changing its files or creating missing scaffold entries. Legacy directories containing only hosts.yaml remain valid; any present definition must be valid. It does not create a Session. The first registration becomes the default; subsequent registrations preserve the selected default.

The same resolved root, including a symlink alias, keeps its existing profile name. Asking to register it under another name fails. Duplicate registered roots are invalid.

## Detach a registration

```sh
python -B tools/opsfeast.py detach inventory
```

Detach removes exactly one named registration, preserves the management directory and all of its files, and prints the removed name/root and resulting default. A missing directory does not prevent detaching a nondefault profile. Reattach with attach PATH; no files are restored or recreated by detach.

Main is a protected name: detach main always fails, without a force option. Detaching a nondefault profile leaves the default unchanged. Detaching the current default requires main to be registered and usable: its directory must exist, any present current/legacy definition must be valid, and hosts.yaml must be a file whose resolved path remains inside the management root. A legacy hosts-only main is accepted. These are basic location checks, not full configuration/recipe or connection validation.

The validated fallback and removal are saved in one atomic registry replacement. Missing/unregistered/invalid main, unknown names and failed writes leave the original registry/default intact; no directory is deleted, created or auto-attached. If main is unavailable, repair its directory/registration or explicitly use another available profile before detaching a nondefault registration. Init without NAME remains equivalent to init main; existing registrations/contents remain preserved.

## Select and inspect profiles

```sh
python -B tools/opsfeast.py profiles
python -B tools/opsfeast.py use inventory
python -B tools/opsfeast.py check --profile inventory
python -B tools/opsfeast.py dump hosts.localhost --profile inventory
```

profiles is read-only and shows available/missing/invalid/unavailable based on directory, definition and entry-file checks. This basic status does not validate YAML content, recipes, connectivity or privileges. Missing entries remain registered; nothing is automatically removed. use changes the default; without a name it offers selection only in an interactive terminal, and noninteractive use requires an explicit name. Cancellation preserves the registry. --profile selects a Feast for one invocation on either CLI without changing the default. Explicit roots and --profile cannot be combined for execution/configuration commands. Diagnostics and recipe execution require their own authorization.

## Registry and boundaries

New checkouts use .opsfeast.yaml:

```yaml
schema_version: 2
default_profile: main
profiles:
  main:
    root: feasts/main
  inventory:
    root: feasts/inventory
  team.inventory:
    root: /srv/team/inventory
```

Checkout-relative roots are saved as relative paths; external roots are absolute. Writes atomically replace the active registry. An existing .my-ops.yaml remains active until an explicit migration. If both registry names exist, commands fail; definitions follow the same single-generation rule. Legacy schema 1 becomes a default profile in memory and is written as schema 2 only when registration, detach or use requires a write.

Each Feast is the boundary for includes and saved results; custom recipes remain inside their selected profile root or explicitly registered external source. See [recipe sources](recipe-sources.md). Sibling profiles cannot escape into each other. Missing or invalid registered directories fail without falling back to another profile. Existing paths, profile names and default selection are preserved.

Both generations of default data directories, registry files and temporary files are ignored by Git. Other custom directories inside a checkout need their own ignore rules. Keep real operational data, credentials, notes and results outside public commits and recipe bundles.

_Last modified: 2026-10-12_
