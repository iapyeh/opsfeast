# Shared settings area

Profile cards display editable registration descriptions. Use **編輯說明** to
save or clear plain text; create/attach also accept descriptions. Reuse the
revision-checked `PATCH /api/v1/profiles` adapter rather than writing the registry
from UI code. See [description limits, CLI/Core examples and failure behavior](profiles.md#profile-descriptions).


The Web settings area is separate from operational/result views. It must eventually
cover all supported human configuration needs while retaining CLI and agent APIs.
Build one service/validation contract per settings domain; Web and CLI are adapters,
not separate configuration stores or independent interpretations of defaults.

## Settings hierarchy and availability

The hub has four installation-level peers: **Site**, **Profiles**, **Bundle
Recipes** and **Execution**. Within Profiles, select the owning Profile to open its Hosts, user
Recipes, parameters and Retention policies. Selection changes the displayed scope,
not the default Profile. The Profiles management page also nests these links under
each registered Profile, preserving the exact name in the destination URL.

| Route | Scope | Current delivery |
| --- | --- | --- |
| `/settings` | Installation | Version checks and hierarchical capability discovery |
| `/settings/site` | Installation | Presentation and administrator configuration |
| `/settings/profiles` | Installation | Profile status/create/attach/default switch, with owned child links |
| `/settings/bundle-recipes` | Installation | Read-only checkout Bundle catalog, independent of a selected Profile |
| `/settings/execution` | Installation | Default recipe execution threads (8), with revision-checked saving |
| `/settings/hosts?profile=NAME` | Selected Profile | Entry to the real host editor, retaining Profile scope |
| `/settings/recipes?profile=NAME` | Selected Profile | Read-only custom/registered external Recipe catalog, excluding Bundle recipes |
| `/settings/parameters?profile=NAME` | Selected Profile | Parameter/policy guidance; Web writer remains planned |
| `/settings/retention?profile=NAME` | Selected Profile | Retention-policy guidance; Web writer remains planned |

Bundle definitions belong to the product checkout. This layout does not move
execution enablement or variable overrides out of Profiles: those settings still
follow [source/policy inheritance](recipe-sources.md). No configuration migration,
global enablement default or independent Bundle code editor is introduced.

Recipe settings views reuse the shared static catalog and provide inspection,
not source registration, install, enablement, parameter editing or execution.
Private data requires the existing administrator/owner authority; the site-edit
capability alone does not manage Profiles or private Recipe catalogs.

`GET /api/v1/settings/catalog`, `opsfeast.settings.catalog()` and
`python -B -m opsfeast.settings catalog` share catalog **0.2.0**, defined by
[the schema](../schemas/settings-catalog.schema.json). Every category has `parent`:
null for installation peers, `profiles` for Profile-owned children. Scope remains
`installation|profile`; availability remains `available|planned`. Implemented APIs,
CLI routes and guide paths describe actual reads/writes. The catalog is static:
it reads no Profile data and never imports user programs.

The previous flat 0.1.0 catalog is replaced. Clients must consume parent hierarchy;
`recipes` now means Profile user/external Recipes, while `bundle-recipes` is the
installation peer. Read-only inspection availability does not imply a writer.

### Where Bundle Recipe parameters are set

Bundle Recipe code is shared by Profiles; each Profile owns its execution
configuration. On `/settings/profiles`, open the owning card's **預設參數與執行政策**
link. `/settings/parameters?profile=NAME` identifies that Profile's actual
`hosts.yaml` for authenticated users, explains `default.recipes.<reference>.vars`
and group/host overrides, and links to [the complete merge rules](recipe-sources.md).
The Bundle and user Recipe lists also link to this guidance, retaining Profile
scope. Bundle parameters do not belong in the replaceable bundled descriptor/code.

This page is guidance, not a Web editor: ask the Agent to make an authorized
configuration change, or edit the selected Profile's `hosts.yaml`. Its illustrative
YAML changes only parameters and does not enable or run a Recipe. No file is
written by reading the guide. The Profile cards distinguish their own settings
with a full-height border/background; creation/attachment stays in a separate
installation-management section.

## Version checks and confirmed Agent handoff

The version panel reads installed evidence locally. Explicit checks consult official
OpsFeast GitHub `main`/VERSION and SSHScript PyPI releases, distinguish new/current/
locally-newer/diverged/unknown/failed evidence, and ask before producing an update
instruction. The human sends that instruction to their Agent; the website does
not run an installer or send a message. See [checks and handoff](web-updates.md)
for module/CLI/HTTP use, dependencies, error states, compatibility and limits.

## Configuration principles for future domains

- Select installation/profile/source scope explicitly. Present the actual owning
  data/file and effective values, including inherited/default/group/host origins.
- Reuse the [hosts configuration](hosts-yaml.md), [recipe source/policy](recipe-sources.md)
  and [retention](retention.md) contracts. Preserve includes, human notes and
  credentials; do not create a Web-only copy of hosts.yaml or recipe defaults.
- Separate inspection, validation and saving from connections, execution, consumer
  dispatch, publication or external delivery. Saving configuration does not imply
  any of those effects.
- Provide reviewable changes, revision/digest conflict detection, bounded validated
  inputs, typed errors and post-save reads through shared interfaces. Redacted
  credentials need explicit preserve/replace/clear semantics, not blank overwrite.
- Separate recipe acquisition, source registration, installation, enablement and
  execution. Preserve user code outside replaceable product directories.
- Distinguish recipe-owned retained-data definitions, platform storage policy and
  user data/content operations. Replay/rebuild/import/delete are separate actions;
  destructive requests need scope previews and evidence-protection checks through
  existing services, not SQL or parallel file deletion tools.
- Keep module/API/CLI documentation, capability catalog and agent skills current
  with each usable feature. Availability must not be inferred from a planning card.

These are requirements for subsequent domain implementations, not claims that the
host/recipe/retention editing services or universal authorization are implemented.

## Current site CLI and shared module

For account CLI and profile APIs/permissions, read [administrator/profile settings](web-administrator.md). Existing profile CLI remains available.


All commands below emit JSON on stdout; failures exit nonzero and explain the
failure on stderr. They are separate module entrypoints, not opsfeast.py subcommands.
`catalog` needs no data root. Site commands use an attached checkout or explicit
marked `--data-root`, as described in [installation storage](installation-storage.md).
They perform local presentation changes, never connect or execute operational code.

```sh
.venv/bin/python -B -m opsfeast.settings catalog
.venv/bin/python -B -m opsfeast.settings site show
# Replace 7 with the revision just read; the name below is synthetic.
.venv/bin/python -B -m opsfeast.settings site update --expected-revision 7 --name "My lab" --slogan "Reviewed operations"
.venv/bin/python -B -m opsfeast.settings site update --expected-revision 8 --avatar /absolute/path/to/avatar.png
.venv/bin/python -B -m opsfeast.settings site update --expected-revision 9 --inherit-name --default-logo --default-avatar
```

Updates change only selected fields. `--name` overrides the site display name;
`--inherit-name` clears that override without editing instance name/UUID.
`--slogan ""` restores neutral default text. `--logo/--avatar FILE` accepts the same
PNG/JPEG limits/normalization as Web; `--default-logo/--default-avatar` saves null
custom references and preserves old uploaded files. CLI access follows the OS
account's filesystem authority; it does not need a Web token or grant a new role.

`opsfeast.settings.update_site(root, expected_revision=REV, changes={...}, images={...})`
composes the same `opsfeast.site` validation/upload/revision services. `changes`
accepts selected site_name/slogan/logo/avatar fields; `images` maps logo/avatar to
PNG/JPEG bytes and cannot also set the same role in changes. A stale revision fails
before uploading; a later concurrent change still fails at save. As with Web, an
uploaded image can remain unpublished after a failed save. Reread/reconcile rather
than blindly retrying stale updates. Image/private data are not part of catalog JSON.

## Bundled image defaults

Null logo/avatar references select the bundled OpsFeast mark at `/assets/mark.svg`.
This is a replaceable default in a slot owned by the installation's human owner.
Saved user images always take precedence. Default resources are product-owned;
custom images/settings remain in external installation data and survive product
replacement. Restoring defaults changes the reference, never deletes a user image.
A product upgrade may update the bundled default mark; it must not replace a custom
reference. The frontend helper `siteAssetUrl` is prototype-private, not a public
presentation SDK. No external image downloads or AI-generated artwork are required.

## Verification

Public `test_settings.py` covers availability, selected-field preservation, stale
revisions, CLI discovery/update and rejected conflicting inputs. `test_site_assets.mjs`
covers bundled defaults and persistent custom references. Web tests cover the shared
catalog, category routes, and absent write endpoints for planned domains. Existing
site/storage tests own image normalization, protected edits and upgrade persistence.



## Recipe execution defaults

Use [execution throttle 0.1.0](web-recipe-menu.md#execution-throttle-and-defaults-010) for the implemented `/settings/execution` page, shared `opsfeast.execution_settings.inspect/save` facade, JSON CLI and GET/PUT `/api/v1/recipe-execution/settings`. The default is 8 concurrent host lanes; temporary per-run threads are sent with confirmed Start, need no new preview and do not save defaults. Selected host counts are not capped. Same-host recipes remain serial. Storage uses versioned installation data, never bundled code or private hosts.yaml. Invalid/stale saves fail; reads/saves do not execute work.

*Last modified: 2026-11-11 16:11:57*
