# Profiling discovery and retained host views 0.1.0

## Purpose and implemented scope

Use profiling to discover bundled integrations, identify gaps and read existing
host evidence through shared Python/CLI/Web interfaces. The eight-domain taxonomy
is product-owned. Ten reviewed providers integrate foundational inventory, disks/RAID, configured
MySQL replication, local accounts/process snapshots and five Linux policy families.
See [architecture and delivery sequence](system-profiling.md) for the broader
coverage, daemon, Host ID and deletion design. Those later-stage behaviors are not
implemented by these read interfaces.

The catalog routes 104 properties across 39 capabilities (72 unchanged inventory
properties plus specialized projections). Twenty-seven capabilities have partial
integrations; twelve still have none.
Integrated capabilities are labeled **partial**, never full system support. Other
capabilities are `not_integrated`: another bundled specialized tool may exist but
has no read adapter here yet. Seven explicit Linux collection recipes are supplied; this delivery does not
automatically assemble/run specialized recipes. Linux has the broadest existing source coverage;
actual applicability/permissions come from collection evidence, not discovery.

## Human workflow

In Web, select the intended Profile, open **Hosts -> host -> 系統全貌**. Expand a
domain/capability to inspect saved values, source timestamps, reasons and record
IDs. Categories without integration stay visible. Opening this page does not
connect, refresh collection, enable jobs or send notifications. A disabled host
still has readable history. If there is no retained evidence, inspect the host's
relevant recipe result: collection or retention may have failed before any
property observation was saved. A raw-only failure is not a new retained value.

Example human requests:

- “Show this host's saved storage values and what has not been collected; do not connect.”
- “Which account, firewall and process capabilities are already integrated?”
- “Explain the missing fields from saved evidence before proposing new collection.”

Refresh is a separate operation. Read [inventory execution](inventory-jobs.md),
select the target/properties and reuse the existing human authorization. Missing
coverage is not permission to install tools, escalate, scan other hosts or collect
credentials.

## CLI

```sh
python -B tools/opsfeast.py profiling describe --json
python -B tools/opsfeast.py profiling describe --domain identity --json
python -B tools/opsfeast.py profiling show --profile main --host HOST --json
python -B tools/opsfeast.py profiling show --profile main --host HOST --domain storage --limit 100 --offset 0 --json
```

`describe` requires no Profile and reads only product JSON; it imports no recipe or
candidate normalizer. `show` requires a registered host in the selected Profile
(or `--root DIRECTORY` instead of `--profile`) and initialized retention. It reads
saved observations only. Both accept the optional domain ID; invalid IDs fail.
`--limit` is 1–250 properties (default 100); `--offset` is nonnegative. Follow
`next_offset` until null. TTY output uses shared tables; use `--json` explicitly for
agents. Redirected output is JSON. Exit 0 means the read succeeded, not healthy or
complete coverage. Invalid input/storage/configuration errors return nonzero.

Full retained evidence remains available through:

```sh
python -B tools/opsfeast.py retention show RECORD_ID --profile main --json
```

## Checkout-level Python interfaces

```python
from opsfeast import Instance
from opsfeast.profiling import catalog, provider_catalog, inspect_host

capabilities = catalog(domain="storage")  # optional domain
native_jobs = provider_catalog("system-inventory")
profile = Instance.open().profile("main")
evidence = inspect_host(profile, "HOST", domain="storage", offset=0, limit=100)
# Inside a Python recipe, reuse its supplied recipe.profile for inspect_host.
```

Python 3.11+ and normal OpsFeast dependencies are required. No SSHScript import or
runtime verification is required for these local reads. These are documented
checkout/package interfaces, not an external provider/plugin registration API.
Do not import internal Web modules, parse raw files or scan SQLite to reproduce
this read model. Use `profile.retention.query/show` for full/general datasets.

## HTTP

- `GET /api/v1/profiling/catalog?domain=storage`: profile-independent discovery.
- `GET /api/v1/profiling/host?profile=main&host_id=HOST&domain=storage&offset=0&limit=100`:
  selected Profile's registered host and retained evidence.

Both require administrator authentication or the existing owner agent capability.
They perform no writes. Invalid selection is 422, missing authentication 401;
storage I/O/SQLite failures are 503 without private paths. Do not create a new
anonymous operational view. The existing Web server must load the updated Python
routes; refreshing browser assets alone cannot update an old server process.

## Data contract and interpretation

Catalog responses have `schema_version: 0.1.0`, `status`, `domains`, `providers`,
`capabilities` and `limits`. Domain IDs are hardware, storage, software, network,
workloads, identity, observability and analysis. Each capability declares its ID,
domain, title, observation kind, scope note, partial/not-integrated status and
explicit property/provider bindings. Property definitions retain native IDs, jobs,
types, units and YANG mappings. Provider metadata is static evidence, not a target
dependency check or grant to execute it.

Host responses add Profile/Host ID, read time, retained record count, per-capability
`evidence_counts`, paged property `items`, `total` and `next_offset`. A property's
state is:

| State | Meaning |
| --- | --- |
| `not_collected` | No matching retained attempt; does not prove no raw run exists. |
| `complete` | All selected source scopes report complete for that declared property. |
| `partial` | Some successful evidence exists but not every selected scope is complete. |
| `unavailable` | Attempts exist but no successful value/complete enumeration is available. |

Each evidence entry preserves namespace, exact recipe reference, definition digest,
record/probe IDs, original coverage time, saved property definition, counts and
reason codes. Namespace/reference/definition variants remain separate; the view
does not infer that imported or different-source identities are equivalent. The
existing inventory latest-attempt reducer wins per property/scope; newer failures
do not fall back to older success. Successful empty table enumeration is complete,
not missing. Absence claims still require the original enumeration scope.

Sample previews retain keys, status, reasons, source IDs and times. `value_preview`
is a JSON rendering (including zero/false/null), bounded to 2,000 characters, not a
replacement typed value. `value_truncated` marks text truncation. At most 20 samples
per property/source are previewed; `samples_truncated` and total/success counts
explain omitted instances. Follow record IDs with retention show for full values.
Inventory retains its saved property definition/unit. Specialized sources expose
the saved contract name/version/digest plus the current data-only projection path
and unit; this projection is not presented as an original producer field catalog.

`status: success` means projection/read success. Complete property coverage says
nothing about freshness, health, missing fields outside the declaration or baseline
quality. Compare original sample times, not `read_at`. This model reads the registered versions listed below, including source-qualified
implementations of those contracts. Legacy snapshots, unregistered versions and
raw-only failures remain
available through retention/result diagnosis; they are not silently converted.
Queries currently read matching retention history before reducing/paging it;
pagination bounds responses, not history scan cost. No scale benchmark is claimed.

## Provider extension and inventory integration

The data-only `opsfeast/profiling-catalog.json` owns domain/capability bindings.
`opsfeast.profiling.provider_catalog` reads reviewed native provider definitions;
`tools/inventory_jobs.catalog` delegates to it. Inventory collection.json and its
schema-bound retained property definitions remain unchanged. Historical digests,
records and manual/scheduled execution semantics are preserved; no migration,
identity rebinding or new compatibility layer is added.

The catalog validator rejects duplicate IDs/property bindings, unknown/unrouted
properties, unsupported adapters and escaping/symlink resources. Add a provider by
reviewing its read adapter, native contract and mappings with tests, not by loading
arbitrary user modules from metadata. Adding a provider today is a product change.
Non-recipe execution providers and automatic collection planning remain later work.

## Specialized providers and acquisition batches

| Provider / contract | Source and scope | Coverage interpretation |
| --- | --- | --- |
| disks-raid / 0.4.0 | Existing physical/controller/virtual/MD/OS rows, saved summary and findings. | Each array uses its saved coverage; unknown/not-applicable empty arrays are not complete enumeration. Summary completeness is not health. |
| mysql-replication / 0.1.0 | Existing configured instance server identity and replica-side channels/health/reason/cleanup. | Fixed successful query/parse evidence determines completeness independently of health. Instance names and times remain separate. |
| linux-local-accounts / 0.1.0 | New local passwd/group recipe, portable final data. | Local-file enumeration only; excludes hashes/GECOS and does not establish effective login/sudo or directory-service coverage. |
| linux-process-snapshot / 0.1.0 | New visible procfs snapshot recipe, portable final data. | PID/start ticks/optional boot ID, source resources and executable metadata; no argv/environment or complete event history. |

Use the [coverage review](profiling-coverage.md),
[local accounts recipe](../recipes/system/account/inventory/local-users/README.md)
and [process snapshot recipe](../recipes/system/process/inventory/snapshot/README.md).
Existing specialized acquisition is reused, not rewritten. New recipes require
Linux/target Python 3.8+, selected account read access, and controller Python
3.11+/SSHScript 7.0.1. They never install or automatically escalate.

Recipe-author interface: `opsfeast.linux_profile.collect(recipe, "accounts")` or
`collect(recipe, "processes")`, using the supplied Core Recipe session, timeout and
vars (max_items, command_timeout_seconds). The body returns the ordinary recipe
result and final schema-bound portable data. `linux_profile_schema.schema(kind)`
provides the matching definition; the two descriptors embed it. This is a bundled
product service 0.1.0, not an independently installed target agent or stable
third-party provider loader. Missing Python/transport/malformed responses fail;
valid platform metadata with dataset gaps is partial and can be retained.

Specialized records select the latest retained attempt per namespace, Host ID,
exact recipe reference and saved definition digest. A newer unavailable field
never falls back to an older success. Account/process array rows have name or
PID/start keys; other arrays may use explicitly observation-local source_row
positions, which are not stable entity identifiers. MySQL additionally separates
configured instance labels. Source timestamps remain the producer timestamps;
Linux target times and controller acquisition intervals are independent.

These recipes produce no global scheduler registration; run them explicitly via
recipes run after authorization. A full probe/transport failure not retained by
the current runner is still a raw-only failure; the viewer cannot label old
retention as a new failed attempt. Inspect raw recipe history as well.

## Verification

Public tests: `test_profiling.py`, `test_profiling_web.py` and `test_profiling.mjs`.
They cover data-only discovery, schema-bound property parity, invalid registrations,
empty/failed/partial evidence, successful empty enumeration, scope separation,
preview limits, pagination, HTTP authentication/Profile selection, safe failures,
UI escaping and retry. Synthetic collector -> raw -> retention -> HTTP values and
original timestamps are tested without managed-host connections. This delivery
adds no native SSH, hardware or baseline-detection verification.


### Local delivery checks (2026-11-09)

- Python 3.14.4 checkout environment: 1,325 tests passed. The initial sandbox run
  had 10 localhost-socket permission errors; the complete rerun with local socket
  access passed. No managed-host connections were made by this delivery.
- JavaScript: 74 tests passed; the later unit-display assertion also passed in the
  focused four-test viewer suite.
- Wheel build/extraction smoke: installed resource lookup and shared catalog /
  inventory provider imports passed outside the checkout import path.
- Changed-document local links/timestamps and skill YAML frontmatter checked.
- Chrome desktop: a separate temporary synthetic installation verified login
  destination, host tab, saved values/units/source times and uncollected fields.
  The QA server was stopped afterward. Mobile layout was not separately verified.
- The existing user-facing service was restarted with explicit human approval,
  preserving checkout, interpreter, port and installation data; homepage, profiling
  asset and authenticated catalog returned HTTP 200. No host commands were replayed.
- Native platform probes and statistical anomaly detection were not added/tested.
  YANG definitions/schema bindings were unchanged; the optional pyang check was not
  rerun (pyang/jsonschema are absent from the shared maintenance environment).


## Acquisition batch verification (2026-11-09)

- Complete local Python 3.14.4 regression: 1,340 tests passed. An initial stale
  recursive bundle-selection expectation was updated for nine recipes. A transient
  existing Console initialization error passed on its six-test rerun and in the
  final complete run; no Console/library behavior was changed.
- JavaScript suite: 74 passed. Targeted profile renderer checks also passed after
  adding explicit instance labels and distinguishing saved definitions/projections.
- New collection tests use temporary passwd/group and procfs fixtures. Both recipe
  bodies pass through the real runner, portable retention, default consumer update
  and shared HTTP projection, with synthetic transport. No managed-host collection
  or native Linux/SSH applicability is claimed.
- Extracted-wheel smoke verified five provider catalogs, nine recipe descriptors,
  shared service imports and strict portable schemas. The target probe parses using
  Python 3.8 grammar; this is syntax evidence, not a Python 3.8 native runtime test.
- Source schemas and normalizers for existing inventory, disks/RAID and MySQL were
  preserved. Historical observations and profile settings were not rewritten.
- The task-owned Web controller reported no active workers on graceful shutdown;
  original checkout/interpreter/8741 port/installation data were reused. Homepage
  and authenticated five-provider catalog returned HTTP 200 after reload.


## Linux policy/settings providers

The [policy acquisition guide](linux-policy-profiling.md) documents five new
contracts/providers: linux-ssh-policy, linux-sudo-policy, linux-firewall-policy,
linux-time-sync and linux-logging-config (all 0.1.0, portable). They reuse
`opsfeast.linux_profile.collect(recipe, kind)` with reviewed kind IDs ssh-policy,
sudo-policy, firewall-policy, time-sync and logging-config. The supplied session,
account, timeout and final portable data flow stay shared. Seven Linux recipe
kinds are supported in total; no arbitrary probe or target package installation
is enabled.

Policy sample previews optionally carry basis configured/effective/runtime/context;
Web labels it explicitly. Evidence also carries source_scope and safe commands
metadata (argv, interval, exitcode, termination/reason); command streams and source
file dumps are absent. The generic adapter still preserves namespace/reference/
definition boundaries and newest unavailable attempts. A complete query returning
NTPSynchronized=no is not a synchronization-success claim. Sudo projections omit
Defaults/arguments and remain partial; SSH context does not establish login success.
The canonical guide lists dependencies, limits, exact invocation/context examples,
unsupported forms, sensitive-field omissions and public verification.

## Recipe menu and human-confirmed execution

The [recipe menu 0.1.0](web-recipe-menu.md) now delivers the planned
Web selection workflow: recipe purpose/limits, suggested combinations, the shared
39-capability blueprint, exact targets and inputs, review/confirmation, serial
runner progress/stop and saved receipts. This is separate from read-only saved-data
and profiling views. Opening a viewer or history never collects or retries work.
The original profiling blueprint remains the Bundle target, not a claim that all
current capabilities are complete.


## Independent inventory sources

The system-inventory provider now points to the product-owned shared property catalog and Overview meal. Its current records use inventory-routine-observations 0.1.0 under child references; historical job records remain separately readable. No new fields or broad coverage claims are inferred from the split. Property evidence includes matching routine actors/permissions and connection warnings; complete data does not imply restored identity or current host health.

*Last modified: 2026-11-10 15:57:34*
