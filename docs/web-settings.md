# Shared settings area

The Web settings area is separate from operational/result views. It must eventually
cover all supported human configuration needs while retaining CLI and agent APIs.
Build one service/validation contract per settings domain; Web and CLI are adapters,
not separate configuration stores or independent interpretations of defaults.

## Current availability

| Route | Scope | Current delivery |
| --- | --- | --- |
| `/settings` | Discovery | Settings hub driven by the server capability catalog |
| `/settings/site` | Installation | Site name/slogan/logo/avatar plus administrator setup/change |
| `/settings/profiles` | Installation | Admin-only basic status, create, attach and default switch via Core |
| `/hosts` (also linked from `/settings/hosts`) | Selected profile | Real host create/basic connection/metadata/group edit and confirmed delete; [contract](web-hosts.md) |
| `/settings/recipes` | Selected profile | Planning page; no new recipe configuration writer |
| `/settings/parameters` | Selected profile | Planning page; no new default/override writer |
| `/settings/retention` | Selected profile | Planning page; no new policy/content writer |

The recipes/parameters/retention planning pages do not load private configuration or perform operations. Host settings require administrator login and use the shared configuration-only service. Existing CLI/Core/recipe/retention capabilities
remain usable within their existing contracts. The catalog's empty interfaces for
planned categories mean the new settings surface is not delivered, not that every
related existing tool is unavailable. A [single-administrator login](web-administrator.md) is implemented; the site's
local capability can bootstrap only the first account and cannot manage profiles,
hosts or retention. Multiple users/per-agent credentials remain future work.

`GET /api/v1/settings/catalog`, `opsfeast.settings.catalog()` and
`python -B -m opsfeast.settings catalog` return the same static JSON 0.1.0 catalog, defined by
[settings-catalog.schema.json](../schemas/settings-catalog.schema.json).
It lists category IDs, scope (`installation|profile`), availability
(`available|planned`), UI route, implemented interface entrypoints and canonical
guide path. Discovery reads no private configuration, initializes no data and imports
no user program. UI copy is in the Traditional Chinese authoring catalog; English
translation waits for the operator's request.

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

*Last modified: 2026-11-01 23:27:07*
