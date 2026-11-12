# Preserve an installation during updates

This is the shared agent procedure for an authorized update. It is not an automatic
updater or permission to initialize another installation. Reuse the existing Web
port, administrator credentials, identity, Profile roots and user settings. A clone
or package replacement supplies product code; it must not supply replacement user
configuration.

## Record and preserve the existing state

Before applying an update, identify the actual product checkout/interpreter,
installation-data binding and assigned UUID, current Web origin/port, launch options,
controller/process, active work and every Profile's resolved management root. Keep
the default Profile, names, descriptions and registered recipe-source roots. Do not
run Git in a data directory or infer an installation from a port alone.

Make the appropriate private backups or local hash inventory before changing state.
Keep credential contents out of chat, command arguments, public fixtures and commits.
Protect these separate locations:

| Location | Preserve |
| --- | --- |
| External installation-data | Identity, `.opsfeast-admin.json`, site settings/images, `web-server.json`, execution defaults, recipe-run and Console records |
| Checkout-local bindings/registry | `.opsfeast-storage.json`, `.opsfeast.yaml`, Profile registrations and resolved paths |
| Every Profile root | `hosts.yaml` and includes, recipe defaults, `feast.yaml`, `recipe-menu.json`, host notes, user recipes/skills, saved jobs, observations, retention, Vault and operational records |
| Registered external sources | User recipe code, descriptors and their independent source/configuration |

`recipe-menu.json` owns custom categories, assignments, saved meals/nested meal
references and selected fields. Recipe defaults remain in `hosts.yaml`; installation
execution defaults are separate. Do not regenerate any of them from product examples.
If a Profile root is under the old product directory, keep that actual directory
intact until its data has been preserved through an explicitly authorized plan.
A new checkout must point to the same resolved roots; copying relative registry
paths into a different directory is not proof of preservation.

## Apply code without reinitializing data

For an in-place update, perform only the applicable authorized fast-forward/package
change, preserving local edits and ignored bindings. Do not stash/reset/clean/delete
user state automatically. Reload the updated instructions and contracts before
resuming operation; unsupported data remains a visible blocker rather than a reason
to overwrite it with defaults.

For a replacement checkout, attach the existing marked installation-data **before**
initializing identity or starting Web. Restore/register the existing Profile roots
using the [Profile attach workflow](profiles.md), preserving their exact identities,
contents, default selection and descriptions. Do not call installation/profile
`init` to reconnect an existing installation. No administrator bootstrap/reset,
`--port` override, new data-root allocation or recipe execution belongs in an
ordinary update. Reuse the original selected interpreter unless environment changes
are separately authorized.

```sh
# From the replacement product checkout, with the selected existing interpreter:
python -B -m opsfeast.storage attach --data-root /absolute/path/to/existing-installation-data
python -B -m opsfeast.storage show
python -B -m opsfeast.web_settings show
```

Use the actual quoted interpreter/checkout/data paths in the agent handoff. The
binding itself remains checkout-local and is not distributed by Git/packages.

## One-time move of a checkout-local Web port

Web endpoint 0.2.0 stores the port in external `web-server.json`; normal startup does
not read a port from `.opsfeast.yaml`. When updating an installation with the former
`web: {port: N}` entry, record that value and perform the explicit transfer from
that existing checkout after loading the updated code:

```sh
python -B -m opsfeast.web_settings migrate-port
python -B -m opsfeast.web_settings show
```

Use `--installation /absolute/old-checkout` if invoked elsewhere; `--data-root`
selects the already identified installation data explicitly. The transfer copies
only the port, backs up the original registry bytes privately under installation-data
`web-port-backups/`, removes only its `web` entry with comment-preserving YAML, and
preserves the rest of the registry. It requires the selected Web environment's
`requirements-host-settings.txt` dependency. It never initializes data or changes
administrator, Profile, menu, recipe or retention files.

A different external port, invalid file or concurrent registry change fails without
silently overwriting either choice. If interrupted after the port copy, the old
registry/backup remains available; reconcile and rerun only when the recorded values
agree. Do not delete a candidate or invent a new port to conceal an incomplete move.
Normal startup refuses an outstanding old registry port instead of silently choosing
another one. If the old port cannot be established, stop and report the missing
information. This is a narrow, explicit configuration transfer authorized as part
of preserving an existing port, not a general data-schema migration service.

Complete this transfer **before discarding or replacing the old checkout**. A new
checkout attached to the same installation-data then reads the same port without
copying the former Web setting. If the external port already exists and there is
no old registry entry, no transfer is needed. Never run `set --port` during an update
unless the human actually requested a port change.

## Verify before handoff

Reconcile active work before a necessary restart; wait or obtain the genuinely
missing operational decision instead of killing active work. Preserve the same
checkout/interpreter/data binding, Web origin and port. Start the updated service
using its saved external port, verify HTTP at its actual URL, and keep the agreed
process/controller running. Do not replay host commands. Browser sessions may need
a new login after restart; that does not mean the administrator account was reset.

Compare the private before/after inventory: same UUID, port, administrator metadata,
site configuration, Profile roots, category/assignment/meal definitions, recipe
sources/defaults, execution defaults and saved data. Apart from the documented port
transfer, update validation must not change their contents. Show only nonsecret
status/digests or comparison results to the human. Do not claim a compatible contract
or unchanged data when reads fail. Preserve originals and report the exact gap.

Unsaved plates are currently tab-local browser `sessionStorage`, not saved server
objects. Keep the same browser tab, origin (scheme/hostname/port) and Profile root;
the draft key is based on that root. Do not clear browser storage or change origin
as a routine update step. Closing the tab/browser can discard the draft independently
of product updates. Save a reusable meal before an update when selections must be
durable; meals deliberately do not save host choices or runtime threads. Do not
claim persistence across browser closure or a change from localhost to 127.0.0.1.

Saved user meal/category definitions remain byte-for-byte unchanged. References to
Bundle recipes/meals still resolve to the updated product definitions, so their
effective contents can change as designed; report material changes without rewriting
user definitions. Unknown schemas or incompatible overrides require a concrete
follow-up decision, not automatic reinitialization or silent conversion.

Preserve Profile `.host-note-attachments/` together with `.host-notes.json`; [document bundle](host-note-attachments.md) UUIDs, manifests, original file bytes and note relationships must stay unchanged. They are private Profile data, not replaceable product assets. Never reconstruct attachments from report examples or repeat an uncertain upload on update. Preview grants/auxiliary ports are transient and are recreated on demand; they are not installation identity or the main Web port.

*Last modified: 2026-11-12 12:30:01*
