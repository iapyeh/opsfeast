# Feasts and profiles

## Profile descriptions

Each registration in `.opsfeast.yaml` can include an optional `description` string.
It belongs to the installation registry, independently of the registration name,
management root, Namespace and default selection. Existing entries without it read
as empty text; no migration or management-directory rewrite is needed.

In Settings → Profiles, choose **編輯說明** on a Profile card, edit and save.
Create/attach also accept a description. Empty text in the editor clears it;
empty attach input preserves an existing registration description. Text supports
multiple lines and up to 1,000 Unicode characters; control characters other than
tab/newline and invalid Unicode are rejected. Descriptions are plain text, not
Markdown, and appear only in authenticated Profile views; do not store secrets.
Cancellation writes nothing. Revision conflicts return 409 and retain the draft;
reload the page, review the current description and reapply the intended edit.
An unavailable management root does not prevent editing registration metadata.
These changes do not connect to hosts or change default selection.

For agents, run `python -B tools/opsfeast.py profiles show --json` to obtain the
registry `revision`, then run:

```sh
python -B tools/opsfeast.py profiles set-description main --description 'Production hosts' --expected-revision REVISION --json
```

Pass `--description ''` to clear. Stale revisions fail without overwriting changes.
The result uses the same profile-settings snapshot as `profiles show`, including
`description` in every row. The ordinary `profiles --json` list also includes it.
The checkout-level helper is
`opsfeast.profile_settings.update(installation, name=..., description=..., expected_revision=...)`.
Core callers can use `instance.profiles.set_description(name, text, expected_revision=revision)`;
`profiles.list()` returns description text, and `attach`/`init_profile` accept
optional `description`. Omitting description preserves it on reattachment/reinit.
An explicit Core `None` on create/attach means omission; HTTP `null` is invalid.

`PATCH /api/v1/profiles` requires exactly `name`, `description`, and
`expected_revision`. Administrator/owner capability and same-origin rules match
other Profile writes; site-edit tokens are insufficient. POST create/attach accept
optional description. Invalid requests return 422, stale revisions 409, and
unauthenticated requests 401. See [Web administrator boundaries](web-administrator.md).


User-authored recipes normally live under the selected profile's actual management root at recipes/domain/subdomains/action/name, for example feasts/main/recipes/database/mysql/check/replication. Use a :classified/path selector. Profiles can point to arbitrary registered directories; a profiles/ parent is not required. For code shared across profiles, register one external recipe source. See [classification, placement and relocation](recipe-taxonomy.md).

## Profile roots, retention and vault content

A profile's optional host vault is the dedicated `vault/` child of its management root, including external attached roots. Init enables it automatically; see [namespace and vault initialization](host-vault.md). Renaming a profile or moving its root does not change namespace. Authoritative retained data lives under retention/; generated content lives under vault/hosts, vault/groups and vault/overview; raw observations, configuration and execution records remain outside vault/. Profile selection chooses both locations; CLI --root always means the profile root. Retained data and notes may be private, so a vault is not automatically a sanitized sharing artifact.

Console summaries use tables when stdout is a terminal; add `--json` to supported inspection/diagnostic/check/profile commands for structured output. Non-TTY formats, execution scope and stored data remain unchanged. See [the command-specific console policy](cli.md#terminal-tables-and-json).

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

A new instance receives feast.yaml with schema_version: 1, kind: opsfeast, namespace
and overview_months (default 3), plus independent retention/ storage and vault/ host/group indexes. Namespace
defaults to the profile registration name; use `init NAME --namespace VALUE` when
that name does not satisfy namespace syntax or a different identity is intended.
The saved namespace is preserved on subsequent init and profile renaming; a different
override fails before writing. Reinitialization preserves host settings, definition
comments, human notes and archives while refreshing generated views. Init performs
no host operations. `init ... --json` returns profile/root/namespace/vault_directory
and normal configuration status as one JSON object. A separate vault migrate is not
needed for new profiles; first operational inventory success/partial is retained automatically. No recipes directory is created inside a new Feast; custom recipes are optional.

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

## Web profile settings

`/settings/profiles` provides administrator-only basic status, create, attach and
switch through Core. New Web-created roots use the persistent installation data
root's `profiles/NAME`; existing registered roots are unchanged. Reads do not prove
connectivity. Mutations carry registry digest checks, and initialization can leave
a candidate directory after late failure. Profile registration storage remains
checkout-local and must be preserved separately on replacement. See
[administrator/profile interfaces](web-administrator.md) for exact APIs, permissions
and verification. No Web rename, detach or deletion is implemented.

The Web list gives every Profile its own bordered card, with its name, status,
management-root path and owned settings inside that card. Only the card whose name
matches `default_profile` receives the current-default badge; it has no switch
button. The same rule is reapplied after a successful switch. Switch actions stay
in their card header, avoiding floating controls that can overlap another Profile.
There is no separate pinned current-default summary.

Creation and attachment are installation-level actions below the Profile cards.
**Attach existing environment** registers an already present Feast management
root (containing `hosts.yaml`) under a Profile name. It reuses settings, recipes,
observations, Retention and Vault in place; it does not copy, move or rebuild those
files. Already registered Profiles do not need to be attached again. Attachment
is not a way to add a child object to a Profile.

## TUI profile selection

Bare `python -B tools/opsfeast.py` includes a Profiles table with the same availability checks. Enter or Switch selected profile updates the persisted default and refreshes Hosts; cursor movement is read-only. Invalid/unavailable rows and failed writes preserve the default. Explicit recipe root/profile form values remain unchanged. See [terminal UI](terminal-ui.md#profiles) for navigation, execution boundaries and limits.

## Registry and boundaries

The optional top-level `web: {port: 18741}` stores this checkout’s persistent Web
endpoint. See [Web endpoint 0.1.0](web-server.md) for validation, first allocation,
launch precedence and conflict handling. Profile mutations preserve this setting.

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

*Last modified: 2026-11-06 09:23:54*
