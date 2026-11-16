# Profile management in Settings (0.1.0)

Use **Settings → Profiles** for installation-level Profile lifecycle work. Daily
Web pages (Recipes, Hosts, workspace, retained data and logs) use the persisted
**default Profile** and do not offer another Profile selector. Settings may still
inspect a particular Profile's owned configuration. CLI `--profile` and explicit
Core/HTTP Profile parameters remain available to agents; this change concerns the
human Web workflow, not removal of explicit automation scope.

## Human workflow

| Action | Effect |
| --- | --- |
| Create | New root at installation-data `profiles/NAME`; refuses existing names/directories |
| Attach | Validate and register an existing absolute management directory in place; no copy or reinitialization |
| Detach | Remove registration only, leaving all files in place; detach of the current non-main default atomically falls back to available main |
| Set default | Persist the installation-wide default for subsequent daily Web/CLI work |
| Export | Download a private full Profile ZIP, including any credentials stored inside it; no host connections |
| Import | Verify that ZIP and create/register a new management directory under a fresh name; preserve Namespace/history/data rather than rewriting identity |
| Delete | Remove registration and rename the whole root into installation-data `profile-trash/NAME-UUID`; no permanent purge |

Vacuum is deferred and has no button or endpoint. Main remains protected from
detach/delete. The current default cannot be deleted: switch first. Missing roots
can be detached; deletion requires an existing valid root. Delete rejects roots
that overlap installation storage or another registered Profile. Cross-filesystem
rename fails without copying or changing registration; detach such a root instead.
The UI requires the exact Profile name before export, detach or delete. Cancel
performs no action. Recovery paths appear after deletion; recover with Attach
using that path and a free registration name. There is no automatic trash purge.

These actions never authorize connections, recipes, privilege changes or package
installation. All lifecycle HTTP endpoints require administrator/owner access and
same-origin checks. Their settings revision is checked; conflicts require reload
and review rather than automatic retry. Existing new-directory init failures can
leave candidates, as documented in [Profiles](profiles.md).

## Default Profile boundaries

Daily pages show a default Profile label and a link to Settings rather than a
selector. An old link naming another Profile is returned to the default page,
with its host/recipe/result/run selections cleared and a visible explanation;
it never reuses a same-named host from another environment. Links naming the
current default retain their other query parameters, while `profile` is removed
from the address. Retained data itself is never rebound or rewritten.

Daily browser requests pin their original default using
`X-OpsFeast-Default-Profile`, URI-encoded to support Unicode names. If the saved
default changes in another tab, administrator APIs return 409
`default_profile_changed_reload`. The page disables further controls and asks for
reload, without replaying a mutation. This is a stale-page guard, not a permission
boundary or a globally atomic transaction with external registry editors.
Existing running jobs and scoped Console/history rivers keep their original
identity; default switching does not reconnect or replay them. Daily views of an
old run require returning to its Profile through Settings first.

## Private backup scope and consistency

A backup includes regular files **inside the selected Profile root**: host
configuration and in-root credentials, user recipes/settings, raw observations,
retention, notes/document attachments, reports and generated Vault files. It does
not copy product code, the installation registry/administrator/port settings,
external SSH keys, external recipe-source roots or other external dependencies.
Absolute external references remain unchanged; inspect and supply dependencies
separately before any authorized execution. No source is downloaded or executed
by import. Profile roots containing installation storage or other registered
Profiles are rejected rather than exporting a wider scope.

Keep ZIPs private. They are not sanitized sharing artifacts and are not encrypted
by this service. The UI warns before download. Do not paste them or their secrets
into chat. The server returns `application/zip`, `Cache-Control: no-store` and a
fixed download filename; the browser supplies the Profile-specific filename.

Stop other writers before transfer or deletion. The Web service serializes these
actions against its recipe-run controller and rejects them while a recipe run is
active; it does not stop jobs or prove that external CLI agents/Console workers
are idle. Export checks the ordinary-file set, sizes and modification times before
and after copying. SQLite files are recognized by their header and exported with
SQLite transaction backups; their WAL/SHM/rollback-journal sidecars are omitted.
Other `.lock`/similarly named documents are preserved. The resulting archive is a
stable ordinary-file set plus per-database snapshots, **not one atomic snapshot
across all databases and files**. External writers and database time/size limits
can cause failure; never infer a frozen installation from successful export.

Bounds: 256 MiB ZIP, 512 MiB expanded bytes, 128 MiB per file, 25,000 files,
8 MiB manifest; each SQLite backup is bounded to 30 seconds and the file-size
limit. Symlinks, special files, encrypted ZIPs, duplicate/unlisted archive members,
path traversal, digest mismatches, unsupported versions and occupied destinations
are rejected. Import uses a private staging directory, verifies the exact file
set/hashes and statically validates configuration before registering. Existing
Profiles are never merged or overwritten. Failed owned candidates are cleaned up
when they are not registered. File contents and executable intent are preserved;
new directories are private and files use owner-only read/write, plus owner execute
when declared by the export. No original broad permissions/setuid are restored.

## Contracts and shared interfaces

The [backup manifest schema](../schemas/profile-backup.schema.json) describes ZIP
`manifest.json`, kind `opsfeast-profile-backup`, version `0.1.0`. Files are stored
under `profile/RELATIVE_PATH`; manifest rows record relative path, size, SHA-256
and Boolean executable intent. SHA-256 detects modification, not publisher trust.
Only this backup format is imported; arbitrary ZIPs are not Profile backups.

Checkout APIs (not standalone SDKs):

```python
from opsfeast import profile_settings, profile_transfer

state = profile_settings.inspect(installation)
# Use only within the human's authorized lifecycle/backup scope:
raw = profile_transfer.export(installation, name="lab",
                              expected_revision=state["revision"])
state = profile_transfer.import_archive(installation, installation_data, raw,
                                        name="restored", expected_revision=state["revision"])
```

`profile_settings.create/attach/use/update/detach` return the current settings
snapshot. Core `instance.profiles.detach(name, expected_revision=...)` now accepts
an optional optimistic revision. `profile_transfer.delete` requires installation,
data root, name, exact `confirm_name`, expected revision; it returns that snapshot
plus `deleted: {name, recovery_root, permanently_removed: false}`. Reuse these
services rather than implementing independent registry parsing or deletion.
Direct Python callers must establish writer quiescence themselves; the Web idle
guard is an adapter behavior. The normal Core/CLI explicit-profile rules remain.

| New endpoint | Input/output |
| --- | --- |
| `POST /api/v1/profiles/detach` | JSON `name`, `expected_revision`; settings snapshot |
| `POST /api/v1/profiles/delete` | JSON `name`, `confirm_name`, `expected_revision`; settings plus recovery receipt |
| `POST /api/v1/profiles/export` | JSON `name`, `expected_revision`; private ZIP bytes |
| `POST /api/v1/profiles/import?name=NAME&expected_revision=REV` | Bounded binary ZIP request body; settings snapshot |

Existing create/attach/default/description endpoints remain as documented in the
[administrator guide](web-administrator.md#profile-state-and-changes). Invalid input
or filesystem/database failure is a sanitized 422, oversized upload 413,
unauthenticated 401, foreign origin 403, revision conflict 409. An active Web recipe
run returns 409 `profile_management_requires_idle_recipes`; do not retry writes
or stop work automatically. No arbitrary server path is accepted for archive
extraction. Import does not change an existing default selection.

Focused public tests: `test_profile_transfer.py`, `test_profile_settings.py`,
`test_profile_description_web.py`, `test_profiles.py`, `test_default_profile.mjs`,
`test_profile_navigation.mjs`, `test_recipe_menu_layout.mjs`, `test_workspace.mjs`
and `test_host_manager.mjs`. All use synthetic local data; no live Profile was
created, detached, imported, deleted or switched for testing.

*Last modified: 2026-11-13 15:53:30*
