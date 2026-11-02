# Persistent installation data 0.1.0

Keep user-owned installation identity and Web presentation outside replaceable
product checkouts. Product code, bundled frontend assets and documentation can
be upgraded or cloned independently; the operator explicitly attaches the new
checkout to the same persistent data root.

## Boundaries and selection

```text
product-checkout/
  opsfeast/                  product code
  web/                       bundled frontend
  .opsfeast-storage.json     ignored local data-root binding

installation-data/           independently preserved sibling or external directory
  .opsfeast-data.json        versioned root marker
  .opsfeast-instance.json    authoritative installation identity
  .opsfeast-site.json        authoritative site presentation
  .opsfeast-site-assets/     user-uploaded logo/avatar images
  .opsfeast-admin.json       private single-administrator credentials
  profiles/                 default location for newly Web-created profiles
  .opsfeast-web-edit-PORT.token   temporary per-launch edit capability
```

The data root must be outside the product directory and cannot contain the product
directory. These are separate ownership boundaries even when physically located
on the same disk. External storage is not a backup: back up the whole persistent
root, including settings and image references. Stop the Web server and other
writers for a consistent filesystem backup; do not copy an active edit token into
a running replacement deployment.

This delivery separates **identity, site settings, images and administrator
credentials**. New Web-created profile roots also live under the external root. Existing profile
registrations, management roots, recipes, observations, retention and Vault content
are not moved or re-registered. If a profile's management root is under the product
checkout, deleting that checkout can still delete its data. Preserve those roots
separately before any destructive product replacement. Existing profile commands
retain their path semantics. User presentations and extension registration will
need contracts under persistent/external locations when delivered; this does not
implement a presentation loader or move arbitrary user directories.

The binding follows [installation-storage.schema.json](../schemas/installation-storage.schema.json).
It contains `schema_version: "0.1.0"` and an absolute `data_root`.
The root marker follows [installation-data.schema.json](../schemas/installation-data.schema.json).
It contains `schema_version: "0.1.0"` and
`kind: "opsfeast-installation-data"`. Neither duplicates the UUID: the existing
instance identity remains authoritative.

Core identity calls resolve this binding before locating identity metadata. Profile
switches do not change it. An unbound Core installation retains its existing
identity contract; Web and site presentation APIs require an initialized data
root. An invalid/dangling binding fails; it never falls back to old product-local
site files. There is no dual write or automatic old-layout compatibility layer.

## First separation of an existing prototype

Stop all site/identity writers, including the Web server. From the trusted product
checkout, use the selected Python with an **absent absolute destination** whose
parent exists:

```sh
.venv/bin/python -B -m opsfeast.storage init --data-root /absolute/path/to/installation-data
```

This explicit initialization:

1. Validates source identity, existing site settings and every normalized image
   filename/digest, including unreferenced images.
2. Creates the destination with mode 0700 and copies the known installation data.
   Source files stay intact; unknown/symlinked files or missing image references
   stop initialization rather than being silently discarded.
3. Keeps an assigned UUID/name/description and records the data directory as the
   identity location. An unassigned source receives a UUID during this explicit
   initialization.
4. Verifies copied settings and image bytes, then writes the checkout binding
   atomically under a cooperating-writer lock. Metadata/assets are created 0600.

Existing destinations and existing bindings are refused. A failure after destination
creation leaves the candidate for inspection and preserves source data; do not
assume it is complete or retry by deleting it. There is no automatic merge,
replacement, source deletion or general import/migration mechanism.

After binding, product-local originals are recovery copies, not active settings.
Do not edit them expecting Web changes. The data root is now the location to
inspect, configure and back up. The operation does not modify historical source
IDs, namespace or operational records.

## Upgrade or use a fresh product checkout

For an in-place normal source update, the ignored binding still selects the same
data. For a fresh checkout, attach the existing data **before initializing a new
identity or starting Web**:

```sh
.venv/bin/python -B -m opsfeast.storage attach --data-root /absolute/path/to/installation-data
.venv/bin/python -B -m opsfeast.storage show
.venv/bin/python -B -m opsfeast.web
```

`attach` validates the marker and assigned/location-consistent identity, then writes
only the new checkout's local binding. It refuses to overwrite a different existing
binding. A fresh checkout without that binding can alternatively start Web with:

```sh
.venv/bin/python -B -m opsfeast.web --data-root /absolute/path/to/installation-data
```

The flag selects data for that Web invocation; it does not attach Core/CLI calls.
Use `attach` when the whole checkout should share that identity. All commands accept
`--installation /absolute/product/path` on `opsfeast.storage` to avoid relying on
the working directory. JSON output reports the selected data root; nonzero means
failure. No command connects, executes recipes, starts consumers or changes profiles.

Replaceable product versions must support the stored contract versions. Unsupported
metadata fails visibly without rewriting it. Physical preservation is implemented;
automatic future schema conversion, downgrade compatibility and version recovery
are not promised. Back up data and read release compatibility notes before upgrade.

## Moves, copies and recovery

A product checkout can move or be replaced while attached data stays at the same
location; its assigned UUID remains unchanged. Copying product code alone does not
copy the ignored binding or create a new data root. Explicitly attaching several
checkouts to one data root represents the **same installation**, not independent
instances. Site writes retain revision/lock checks; a per-port token file prevents
two launched servers from sharing that edit capability slot.

Moving the persistent data root itself still needs the existing explicit identity
relocation procedure, followed by updating/recreating the checkout binding. Copying
it for an independent installation needs a renewed UUID. A moved/copy-detected root
is rejected by `attach` rather than quietly becoming an apparently valid instance.
No automatic binding repair is implemented.

For rollback after separation, stop writers first and retain the authoritative
persistent root. An old product that does not understand storage bindings must
not resume writing its stale product-local recovery copies. Reattaching a supported
product is the supported recovery path in this delivery.

## Checkout Python interfaces

```python
from opsfeast.storage import resolve_data_root, initialize_data_root, bind_data_root
from opsfeast import site

# Explicit authorized setup; not part of a read-only inspection.
initialize_data_root(product_path, absent_external_destination)
# On a replacement checkout:
bind_data_root(new_product_path, existing_data_root)
root = resolve_data_root(new_product_path, required=True)
settings = site.read_site(root)
```

Read APIs never initialize directories. `opsfeast.site` accepts a marked data root
or a bound product path and uses that one authority. `create_app(installation,
data_root=..., edit_token=...)` also supports explicit selection. None of these
interfaces relocates profile roots or claims OS-user isolation.

## Verification

`tests/test_installation_storage.py` covers preserved source copies, same UUID,
Core identity writes to bound data, product removal/replacement, surviving images,
invalid/missing destinations, missing assets, broken bindings and moved data.
`test_site.py`, `test_web_preview.py` and Core tests verify the shared identity and
presentation behavior. Synthetic replacement tests do not prove backup integrity,
remote storage suitability or compatibility with future releases.

*Last modified: 2026-11-01 13:20:29*
