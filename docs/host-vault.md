# Host vault, retention and operation journals

Host-vault contract **0.1.0** provides local, host-centered annual history,
rebuildable cumulative records, recent fleet observations, and plain Markdown views.
The selected profile root itself is the vault; `feasts/main` is the usual main root,
not a required location. Open it in Obsidian or any Markdown reader. No Obsidian
plugin, server, model, connection or running TUI is required for reading.

See [offline raw replay, stable source IDs and explicit read-only deletion](retention-replay.md) for recovery and author iteration. Write/unknown observations and operation journals are protected.

## Identity and configuration

The logical management identity is the pair **(namespace, host_id)**. Hardware
replacement, VM relocation and OS reinstall preserve history when the user retains
that pair. Native machine IDs, serials and the older retained `host_key` are captured
environment evidence, not rules for splitting or merging logical hosts.

`feast.yaml` extends the existing profile definition:

```yaml
schema_version: 1
kind: opsfeast
namespace: example-production
overview_months: 3
```

Namespace requires 1–63 lowercase letters/digits/hyphens/underscores, beginning with
a letter or digit. It is user-selected; different independent Feasts should choose
different namespaces. A replacement installation may explicitly reuse one. Profile
names and filesystem paths can change without changing namespace. Instance UUIDs
continue to identify the installation that produced an event; missing instance
identity remains the documented all-zero placeholder. Namespaces are assertions,
not authenticated publisher identities. Do not edit an existing namespace to relabel
archives: rebuild detects the mismatch. Namespace/host renaming requires a future
explicit identity migration; it is not implemented by changing configuration.

## Enable or migrate

Initialize a new profile through the normal setup workflow first. New and existing
profiles explicitly select their namespace with the same local migration command:

```sh
python -B tools/opsfeast.py vault migrate --profile main \
  --namespace example-production --overview-months 3 --json
python -B tools/opsfeast.py vault rebuild --profile main --json
python -B tools/opsfeast.py vault groups --profile main --json
python -B tools/opsfeast.py vault inspect --profile main --json
```

Each command also accepts `--root /absolute/feast` instead of `--profile`. JSON is
the output in terminals and pipes; `--json` is accepted explicitly. Success exits 0,
configuration/storage failures exit 1 with a sanitized error type, argparse errors
exit 2. Commands do no remote work. `inspect` is read-only and returns settings and
archived records. `migrate` requires an existing Feast definition and hosts.yaml.

Migration validates legacy inventory payloads, preserves observation IDs, source
UUIDs and raw business data, wraps them with namespace identity and writes annual
archives. Legacy retained payloads never attested an installation UUID: their origin
instance is explicitly all-zero. The original `records/observations.sqlite3` is not
modified or deleted. An interrupted migration can be rerun with the same namespace.
There is no cross-database transaction; already committed archive records remain
valid after a projection/migration failure. Repair with the same migrate command or
rebuild as appropriate. The old database is a historical backup after migration;
new observations are written only to the vault. Profiles without namespace keep
legacy retention behavior until explicitly migrated.

## Directory and ownership

```text
<profile-root>/
  feast.yaml
  hosts.yaml
  HOSTS.md
  .vault-source.json
  .vault.lock
  hosts/
    <encoded-host-id>/
      README.md
      records/
        observations.sqlite3
        README.md
        <encoded-recipe-reference>.md
      2026/
        observations.sqlite3
        reports/<record-digest>.md
        operations/<record-digest>.md
  groups/
    .generated.json
    <encoded-group-id>/
      README.md
      <encoded-host-id>.md
  overview/
    observations.sqlite3
    README.md
```

IDs use reversible UTF-8 percent encoding. Ordinary lowercase IDs such as web-01
remain unchanged. Digits, hyphens and underscores remain visible; reserved device
names, uppercase characters and punctuation are encoded to avoid traversal and
case-insensitive collisions.
Markdown URL targets encode these filesystem components once more as URLs.
host IDs themselves are unchanged in records. Namespace is stored in the Feast
definition and each record; one vault contains one namespace.

Annual databases are authoritative. Years use UTC observation completion time;
operation result events stay in the intent year even when completion crosses a year.
`records` accumulates all years and does not expire. It can be deleted and rebuilt
from archive SQLite files. Its latest-state pages select the newest whole observation
per source-qualified recipe reference, breaking equal times by record ID. A partial
latest snapshot stays partial: older values are never silently filled in. Source
timestamps/statuses and generation time are distinct. Annual Markdown is also a
reproducible view of each archived record.

`overview` contains observation records within the configured rolling calendar-month
window, default three months (1–1200 supported). Rebuild prunes only this copy; it
never removes annual history or cumulative records. The host list is the union of
configured hosts and archived hosts, so old, disabled and never-observed hosts remain
visible. The initial viewer does not infer online status or a health score.

Generated Markdown has an overwrite notice and modification date. Editing generated
files is unsupported; rebuild overwrites them. The initial host README is a human
landing page and is preserved on later rebuilds. User files elsewhere are preserved.
Do not put private credentials in human notes or declared retained fields if the
vault may be shared. Existing hosts.yaml/raw files may contain private data: the
entire profile is not automatically a sanitized sharing package.

Group refresh is explicitly requested; it reads current hosts.yaml membership and
creates relative Markdown links, never symlinks. Its manifest tracks generated
files. Removed memberships remove only managed files still carrying the generated
notice; human files and host histories remain. A collision with an unmanaged output
fails. Group refresh does not collect data or refresh host state.

## Record and SQLite contracts

[Vault record schema](../schemas/host-vault-record.schema.json) wraps the existing
inventory contract or general host-values data. Each envelope carries a stable
`record_id`, kind, current namespace/host ID, recipe ID/source-qualified reference,
UTC time, immutable origin, business data and a mappings list. Optional retention_provenance carries source identity, raw digest, execution mode and snapshot/version. Origin retains its
original namespace/host ID, instance UUID, source UUID and record ID. Native identity
evidence remains inside the inventory payload; legacy exchange consumers continue
to see the original retained 0.1.0 payload.

Each SQLite has `PRAGMA user_version=1` and:

```sql
CREATE TABLE records (
  record_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  namespace TEXT NOT NULL,
  host_id TEXT NOT NULL,
  recipe_id TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  payload TEXT NOT NULL
);
CREATE INDEX record_selection ON records(kind, recipe_id, observed_at);
```

`payload` is the canonical full envelope. Identical IDs/content deduplicate; different
content for an existing ID fails. Changing management identity in a future import
must preserve origin/record ID and append a mapping with from/to namespace/host,
mapped_at and basis. [Package manifest schema](../schemas/host-vault-package.schema.json)
defines future package members, byte lengths and SHA-256 digests. The checkout-level `validate_package_manifest(value)` validates this structure and path syntax without reading or extracting any files. Mapping/package
structures are defined now; **new import, export, package construction, mapping,
transport and merging workflows are deferred**. Namespace changes do not retrieve
historical data. The existing inventory export/validate/combine interface remains
compatible and exports underlying inventory payloads from archives, not the recent
overview; general observations and operations are not included in that legacy format.

## Recipe retention and Markdown

Inventory uses the existing trusted extraction adapter automatically. Other
python-session/python-recipe descriptors may opt into a constrained scalar adapter:

```yaml
access_mode: read
retention:
  contract: host-values
  version: 0.1.0
  fields:
    reachable: {type: boolean, unit: ""}
    port: {type: integer, unit: "tcp-port"}
  markdown_template: state.md
```

The adapter reads only declared top-level keys of result.data. Types are string,
number, integer or boolean; an explicit unit is required (empty means unitless).
Missing/null remains unavailable, false/zero remain values, and wrong types fail
retention. Only local/SSH success/partial results are retained. Mock, failed, skipped
and unsupported outcomes are excluded. Undeclared data, commands, input values and
raw errors are not retained. Authors must declare only safe business fields and
agree on field meanings/units across compatible recipes; this is not an automatic
semantic reconciliation service.

The optional recipe-relative template is reviewed recipe content. `{{field_name}}`
substitutions escape field text; templates may contain ordinary Markdown and must
not embed secrets or unsafe active content. It runs no template code. The standard
page always includes provenance, original times/statuses, fields and inventory;
recipe Markdown adds a domain-specific view. Regeneration uses archived content,
not recipe execution or loading a new template. Retention failure preserves raw
results and returns failed retention/nonzero execution, with archive replay/rebuild
where applicable. General results do not use the legacy inventory ingest adapter; vault ingest uses
saved snapshots or an explicitly selected descriptor/template without loading code.

The scalar payload is defined by [host-values 0.1.0](../schemas/host-values.schema.json).

## Long-lived operation journal

The [operation-event schema](../schemas/operation-event.schema.json) defines intent and result data.

Declare `access_mode: read`, `write` or `unknown`; omission means unknown. General
runner recipes in namespace-enabled vaults persist write/unknown intent before any
connection or recipe code is loaded. Persistence failure prevents execution. Read
recipes skip the operation journal. Inventory defaults to the legacy read collection
path; an explicit write/unknown inventory declaration is honored and journals before
collection, after access preflight. Its bundle digest is recorded separately from
a general recipe entrypoint digest.
Descriptor declarations are reviewed assertions, not a sandbox or command classifier.

Intent includes stable ID, logical target, recipe/version, source reference, descriptor
and implementation hashes, purpose, controller OS username, variable names and an
explicit indication that caller invocation is not a verified authorization receipt.
Variable values/credentials are omitted. These records establish provenance, not
cryptographic authentication or tamper resistance. Result is an independent append-only
event referring to intent; successful execution never means verified changed state.
Results default to not_observed, with an optional observation-ID evidence link for
reviewed callers. A crash leaves an unresolved intent. Retries/rollback are new
invocations and new intents; no failure is overwritten. Final audit-write failure
preserves raw result, marks runner failed and leaves the intent unresolved. No
automatic operation deletion or raw/debug cleanup is implemented.

Runner coverage includes general runner recipes and explicit write/unknown inventory
declarations. Direct Core/session commands,
diagnostics and arbitrary external processes are not automatically journaled. A
standalone authorized write program must use the explicit journal functions below;
do not claim all shell activity is audited.

## Checkout module interfaces

These are checkout-level interfaces available through the bundled tools path, not
new Core API promises. Use selected profile.root or the CLI root resolver, never
freeze credentials or construct private paths from an agent's earlier observations.

```python
from host_vault import settings, records, rebuild, refresh_groups
configuration = settings(profile.root)  # None for a legacy Feast
history = records(profile.root)         # validates authoritative envelopes
rebuild(profile.root)                   # local views only
refresh_groups(profile.root)            # explicit membership refresh
```

For general recovery prefer `vault ingest FILE --profile NAME --json`, using a saved snapshot by default. An explicit --recipe-dir tests revised definitions without executing recipe code. `retain_general` also accepts saved_snapshot and dry_run keyword arguments; see [replay interfaces](retention-replay.md#modules-and-schemas). For standalone writes use
`operation_intent(root, host, metadata, descriptor_digest, variable_names,
reference=..., implementation_digest=..., source_observation_id=...,
bundle_digest=...)` before work, and
`operation_result(root, intent, report, observation_ids=())` after cleanup. Do not
swallow intent failures. Persisting a failed result does not establish safe remote
termination/restoration. `envelope`/`validate_record` expose the versioned envelope
construction/validation rules; no arbitrary adapter code is loaded.

## Consistency and verification limits

POSIX cooperating writers serialize through `.vault.lock`. SQLite uses a 30-second
lock timeout and transactions. Annual commit precedes view writes; view failure
does not undo history. Markdown uses atomic replacement. Readers can see different
projection generations across files during rebuild; there is no whole-vault atomic
snapshot. Rebuild currently scans history, favoring correctness and simplicity over
large-fleet optimization. Live cloud-synchronized/network SQLite and concurrent
noncooperating editors are unsupported. Stop writers or use consistent SQLite backup
procedures before copying. Symlink paths/SQLite sidecars are rejected.

Synthetic tests cover migration/replay, native identity change, old-data preservation,
partial snapshots, projection failure/repair, expiry, groups/human files, path safety,
concurrent writers, scalar/template extraction, audit intent/results and mappings.
No real host writes, transport, Obsidian application automation, automatic cleanup,
import/export implementation or cryptographic audit guarantee is claimed.

Delivery verification (2026-10-17): Python 3.11.15, 3.13.13 and 3.14.4 each passed 625 tests, including headless Textual checks and 17 vault-specific tests. Older interpreters reused the selected maintenance environment's Python dependencies; this does not establish native SSHScript readiness on those interpreters. Wheel/sdist builds, temporary no-dependency pip installation, installed-wheel migration/retention/Markdown/group smoke checks, Python 3.11 grammar, schema syntax/references, skill frontmatter and changed-document checks passed. No real host connection/write, automatic private-data migration, commit, push or release was performed.

Verification (2026-10-19): Python 3.11.15, 3.13.13 and 3.14.4 each passed 639 tests, including 14 new replay/deletion regressions. The older interpreters reused the maintenance environment's Python dependencies, which does not prove native SSHScript readiness. Wheel/sdist builds, temporary no-dependency installation, installed-wheel snapshot replay/dedup/write protection and legacy migration/provenance-upgrade/deletion smoke checks passed. Python 3.11 grammar, schema syntax/references, skill frontmatter and Markdown link/date checks passed. No real host connection/write, automatic private-data migration, commit, push or release was performed.

_Last modified: 2026-10-19_
