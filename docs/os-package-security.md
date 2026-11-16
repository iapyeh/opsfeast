# OS package security, phase one (0.3.0)

Use this workflow for **version-based vulnerability analysis of OS-managed
packages**. It provides a new inventory recipe, explicit vendor-data acquisition
and an offline report recipe. It is not an SPDX/CycloneDX exporter, application
library/container SBOM, binary attestation, exploitability analysis or patch tool.
The old `system/inventory/software` overview remains a basic inventory; its data
is insufficient for this assessment and is not silently converted.

For a host-selected end-to-end run, use [the package-security meal](package-security-meal.md). It supplies the three steps below automatically, including explicit authorized controller HTTPS and linked reports. The separate collector, advisory CLI and offline report remain available.

## Availability and prerequisites

| Environment | New package inventory | Vendor assessment |
| --- | --- | --- |
| Debian Linux | dpkg binary/source names and versions, architecture, maintainer, state | Debian Security Tracker JSON; exact release and codename, source-version ordering |
| Ubuntu Linux | Same dpkg identities | Canonical CVE OSV, exact release/source version; Pro ecosystems require explicit declaration |
| RHEL | RPM full epoch:version-release, architecture, vendor, source RPM filename | Official Red Hat RHSA OSV; exact declared product stream required |
| Other RPM/dpkg Linux distributions | Database collection when the native manager is available | Unknown; do not substitute Debian/Ubuntu/RHEL advisories based on `ID_LIKE` |
| FreeBSD | pkg identities plus separate installed kernel, running kernel and userland patch versions | Official VuXML native pkg ranges plus release-specific base security advisories |
| Proxmox VE | Full dpkg database plus pve-manager/product, running kernel and component versions | Official Proxmox VE PSA package fix versions; Debian base coverage remains separate/unknown |
| ESXi 7+ | Native XML VIB/component lists, version/build and image profile; no target Python needed | Official Broadcom VMSA Response Matrix, exact update branch/build |
| macOS, other environments | Unsupported by this collector | Unknown |

Controller: OpsFeast with Python 3.11+, its normal dependencies and SSHScript
7.0.1 for collection. Linux/FreeBSD targets: `python3` 3.8+ standard library on PATH, readable
`/etc/os-release` on Linux, and `dpkg-query`, `rpm` or FreeBSD `pkg`. No automatic
installation, sudo, repository refresh or privilege acquisition occurs. The
collector uses the runner-provided `recipe.session.exec_command` with fixed argv
and stdin, as documented by the bundled version-matched SSHScript skill.
ESXi uses fixed native `uname`/`esxcli` commands with controller-side XML parsing.
Read [native platform details](os-package-platforms.md) for exact prerequisites,
commands, fields, failure handling and version limits.

The implementations are covered by synthetic parser, transport, version,
assessment and runner integration tests. Native platform/SSH execution is **not
verified** by those tests. Small official Ubuntu/Red Hat records were separately
normalized locally; the complete live archives were not downloaded for testing.

## Three separate authorization scopes

1. Inventory connects only to human-selected hosts using the existing execution
   policy. Confirm Profile/host identity and relevant saved host notes before
   requesting new collection. Existing notes are context, never authorization.
2. Vendor `fetch` downloads public data to the controller over HTTPS. It never
   contacts managed hosts. Review network/storage scope independently.
3. Report generation reads explicitly selected local JSON files and writes new
   local artifacts. It never connects, refreshes feeds, patches packages or retries.

For example, after the human authorizes the actual collection targets:

```sh
python -B tools/opsfeast.py inspect-recipe system/software/inventory/os-packages --json
python -B tools/opsfeast.py recipes run system/software/inventory/os-packages \
  --profile main --host node --timeout 60 --json
```

Use the raw result path returned by the runner as a report input. Collection and
portable-retention receipts are independent; verify both. Reading a successful
raw result alone does not prove retention/consumer delivery succeeded. `inventory
query` is the older inventory-jobs interface and is not an invocation for this
Python-recipe collector.

Inputs: `page_size` 200 (1–500), `command_timeout_seconds` 30 (1–120),
`collection_budget_seconds` 180 (1–900), `declared_ecosystems` `[]` (up to 100
exact nonempty strings, 256 characters each). Effective per-command timeout is
bounded by the recipe timeout and remaining collection budget. These controls
bound bytes/time rather than limiting hosts or silently stopping after 2,000
packages. They are distinct from the runner's host concurrency setting.

RHEL requires an operator-confirmed ecosystem such as the following, matching the
actual product/repository/subscription stream. Ubuntu Pro also requires explicit
scope. This declaration is saved with the snapshot; it does not establish
entitlement or verify repositories automatically.

```sh
python -B tools/opsfeast.py recipes run system/software/inventory/os-packages \
  --profile main --host rhel-node \
  --var 'declared_ecosystems=["Red Hat:enterprise_linux:9::baseos"]' --json
```

## Full collection and package identity

The target reads and sorts the visible native package database on each page. A
canonical SHA-256 over OS identity, manager, all native package rows, platform details and excluded
states must remain identical across pages and a final reread. The controller
reconstructs and checks that fingerprint. This detects observed package database
changes; it is not an atomic database lock and cannot prove that no transient
change occurred between reads. Each page retains query/output digest and source
time plus transport exit/truncation evidence. Native query failures retain their exit code and up to 16 KiB of stderr in page evidence; timeout/output-limit cleanup terminates only that owned query process. Duplicate identities, malformed
rows, byte limits, timeouts or changed fingerprints leave `complete: false` with
gaps. A partial snapshot is never sufficient for a clean finding.

Target native-query output and controller package data each have a 64 MiB limit;
pages hold up to 64 KiB of native rows and controller transport JSON up to 128 KiB.
No inventory row-count ceiling is imposed. The final check rereads the database,
so exceptionally large/slow databases may need a larger explicit budget. A limit
hit is reported as incomplete, never a successful truncated inventory.

`packages_complete` means the visible selected package database was enumerated consistently.
`complete` additionally requires complete platform identity evidence. Neither flag means
that every software component on the host was found. dpkg residual
`config-files`/`not-installed` entries are excluded with counts; unpacked or other
incomplete installation states remain rows and produce unknown judgments.

`os-package-inventory` 0.2.0 stores `host_id`, OS/release/codename, manager,
`packages`, declared ecosystems, completeness/counts, excluded states,
`snapshot_sha256`, acquisition times/pages and gaps. Rows retain native full
version, architecture, source name/version where provided, producer, RPM epoch,
release/source-RPM filename or FreeBSD ports origin. Missing fields remain null;
source identity is not guessed by splitting an RPM filename. See the
[portable schema](../schemas/os-package-inventory.schema.json), embedded in the
collector descriptor for retention. purl is a derived lookup identity, not proof
of repository origin. Repository/signature origin is not independently verified;
`repository_origin` is null and `provenance_status` explicitly says so.

## Immutable vendor snapshots

Use an operator-chosen directory outside replaceable product code, for example
`<Profile root>/security/advisories/`. The module CLI does not resolve or initialize
Profiles. Parent directories must already exist. Each output is exclusively
created; existing files are never overwritten. There is no implicit update,
"latest" lookup, background schedule or migration of old inventories.

```sh
python -B -m opsfeast.package_security fetch --vendor debian \
  --release 12 --codename bookworm --output /data/security/debian-12.json
python -B -m opsfeast.package_security fetch --vendor ubuntu \
  --release 22.04 --codename jammy --output /data/security/ubuntu-2204.json
python -B -m opsfeast.package_security fetch --vendor redhat \
  --release 9.4 --advisory RHSA-2024:4312 --output /data/security/rhel-94-selected.json
```

Debian fetches the complete tracker JSON, selecting the requested codename.
Ubuntu fetches Canonical's complete `osv-all.tar.xz`, retaining applicable
`UBUNTU-CVE-*` records. USN/LSN notices do not substitute for CVEs with no available
fix. Red Hat fetches **only explicitly selected RHSA IDs**, up to 100; this is not
an exhaustive RHEL vulnerability database and does not cover all open/unpatched
issues. Import a separately acquired official OSV set to widen that record scope.
The report never treats absence from any provided dataset as not affected.

Alternatively import original vendor JSON, an OSV directory, or the Ubuntu
`.tar.xz` archive. The original acquisition timestamp is required; importing must
not reset old data to the current time:

```sh
python -B -m opsfeast.package_security import --vendor redhat --release 9.4 \
  --source /data/vendor/rhsa-json --source-url https://security.access.redhat.com/data/osv/ \
  --retrieved-at 2026-11-13T00:00:00Z --output /data/security/rhel-94-imported.json
```

Fetched inputs use fixed official HTTPS endpoints, no redirects or ambient proxy
configuration, a 60-second socket timeout and 128 MiB download bound per response.
Local source URLs/timestamps are **user-attested**, not verified fetch evidence.
Import does not contact the supplied URL. Symlink files are rejected. Archives
are not extracted; traversal/link members, oversized dictionaries, over 1 GiB
expanded content, over 250,000 members and records over 8 MiB are rejected.
Normalized snapshots and local import totals are bounded at 256 MiB. Debian's
whole tracker has the 128 MiB input limit rather than the OSV per-record limit.

`vendor-advisories` 0.1.0 stores vendor, exact requested scope, created time,
source URL/retrieval time/raw-byte SHA-256/acquisition kind, provided-record
coverage, normalized records/count and a canonical snapshot SHA-256. Records
retain advisory ID, aliases/upstream CVEs, severity/references/dates, affected
package ecosystem/native predicates and a native-record digest. Debian records
are adapted from source-package tracker entries, so their record digest is of
that normalized tracker entry. Original downloaded archives are **not archived**
by this service; keep originals separately if raw replay is required. Digests
provide integrity/reproducibility, not a signature or publisher attestation.

## Offline report and judgment evidence

```sh
python -B tools/opsfeast.py recipes run feast/report/package-security \
  --profile main --input /data/inventory-result.json \
  --input /data/security/debian-12.json --json

# Standalone module alternative, no Profile initialization or runner history:
python -B -m opsfeast.package_security assess \
  --inventory /data/inventory-result.json --advisory /data/security/debian-12.json \
  --output-dir /data/new-package-report
```

The report recipe writes `package-security.html`, `.md` and `.json` under its new
run artifact directory; normal report history/artifact interfaces apply. The
standalone CLI requires a **new** output directory and returns artifact receipts
on JSON stdout. Both accept direct inventory objects or general raw execution
results whose `data` is that inventory, plus direct vendor snapshots. They do not
accept the older basic software property or arbitrary retention envelopes.
Export/select the correct raw snapshot explicitly; do not reconnect to interpret
existing evidence. Multiple explicit inventories are assessed independently; the
service does not silently select a newest observation. Supply one compatible
vendor snapshot per inventory vendor; combine original records during import
rather than guessing precedence between overlapping snapshots.

Shared report inputs: `title`, `as_of` (timezone-aware ISO timestamp, default
current UTC), `max_inventory_age_hours` 24, `max_advisory_age_days` 7,
`max_findings` 100,000 (recipe maximum 1,000,000). Module CLI uses the corresponding
`--as-of`, `--max-inventory-age-hours`, `--max-advisory-age-days`, `--max-findings`.
Original timestamps are preserved in JSON; human-facing collection/assessment times use controller local seconds with an offset, and the report footer uses Asia/Taipei.
An explicit historical `as_of` permits reproducible historical analysis; it is
not a current-state assertion. Future source times, stale inventories/feeds,
ambiguous feeds, mismatched releases, missing identities and incomplete state
produce unknown findings. Report finding-limit omissions are counted and make
the assessment incomplete; they never disappear silently.

| Finding | Meaning |
| --- | --- |
| `affected` | Native installed/source version falls in a matching vendor affected range, or Debian explicitly lists an open issue |
| `fixed` | Version reaches a vendor fixed boundary; this does not prove binary provenance, patch installation integrity or a process/kernel restart |
| `not_affected` | Explicit vendor not-affected statement or outside its described intervals; scoped to that advisory |
| `unknown` | Missing, stale, unsupported, withdrawn, incomplete or ambiguous evidence, including no matching advisory |

Debian comparisons use **source** versions and dpkg ordering (including epochs,
revisions and `~`). Debian `resolved` with fixed version `0` is an explicit
not-affected case; `undetermined` remains unknown. Ubuntu OSV also compares source
versions, not a binary rebuild suffix. RHEL compares binary RPM EVR and exact
declared ecosystem; derivatives do not inherit Red Hat verdicts. RPM ordering
includes epoch, release, numeric segments, `~` and `^`. No semver/upstream-only
comparison is used. OSV ECOSYSTEM interval events/explicit affected versions are
supported; unsupported types, infinite-limit rules and malformed/unordered
predicates become unknown. There is no generic OVAL interpreter.

Each finding includes host/package/architecture, installed/source version, purl,
advisory/CVEs/summary, native severity/references, candidate judgment, uncertainty
reasons, comparison scheme/operands/results, stream and source/snapshot hashes.
HTML puts affected entries first and folds the other groups; details expose the
basis. Vendor fix boundaries are displayed, **not an automatically approved
upgrade plan**. No fix published means no fabricated target version.
`candidate_status` preserves a version-only result when stale/incomplete scope
forces the final status to unknown; it must not override that final status.

Report `attention` means at least one affected finding; `incomplete` means no
confirmed affected finding but unresolved coverage; `evaluated` means all emitted
package/advisory findings were evaluable in this scope. None means a safe host.
`assessment_complete` is false for any unknown or omitted finding. The recipe
returns `partial` for incomplete assessments, otherwise `success` (even when
vulnerabilities are present). Inspect finding counts, not execution status alone.
The module CLI returns exit 0 for completed generation/download/import, exit 1
for invalid input/I/O; stderr is a sanitized JSON failure receipt. Snapshot
mismatch, duplicate keys, nonfinite numbers and output conflicts fail explicitly.

## Reuse and extension

Checkout Python service 0.3.0 (not an independent public SDK):

```python
from opsfeast.package_security.inventory import collect
from opsfeast.package_security.advisories import fetch, import_local, load
from opsfeast.package_security.analysis import assess
from opsfeast.package_security.report import generate, render

# Inside an authorized Python recipe using its borrowed session:
result = collect(recipe)
# Offline; inputs have already been explicitly selected and validated:
finding_data = assess(inventory_snapshot, [advisory_snapshot])
```

`collect` returns the common status/reason/message/data result. `fetch` and
`import_local` return immutable normalized objects but only the CLI persists them;
`load` validates digest/shape. `assess` returns one report object; `generate`
accepts a list of inventory/advisory inputs and report variables, and `render`
writes artifacts to its caller-owned empty directory. These functions do not
initialize a Profile or infer targets. The report recipe is the preferred
reusable interface for existing raw results. Module code is a product dependency
of the two recipes; copying only their entrypoints does not make them standalone.

To add a vendor, implement an official-native adapter plus exact product matching,
native version rules and synthetic positive/negative/boundary tests. Unknown
scope must stay unknown. Add the new contract/platform evidence to this guide,
capability map and recipe skill before advertising support. Application/runtime
linkage, exploitability, signature verification, automatic
patching and compliance SBOM exports remain outside this phase.

Primary contracts: [Debian tracker](https://security-tracker.debian.org/tracker/),
[Ubuntu OSV](https://documentation.ubuntu.com/security/security-updates/osv/),
[Red Hat OSV](https://security.access.redhat.com/data/osv/),
[OSV schema](https://ossf.github.io/osv-schema/),
[Debian version ordering](https://www.debian.org/doc/debian-policy/ch-controlfields.html#version),
[RPM EVR ordering](https://rpm.org/docs/6.0.x/man/rpm-version.7).

## Targeted verification

```sh
python -B -m unittest discover -s tests -p test_package_inventory_platforms.py
python -B -m unittest discover -s tests -p test_package_security.py
python -B -m unittest discover -s tests -p test_package_security_pipeline.py
python -B -m unittest discover -s tests -p test_recipe_identity.py
python -B -m unittest discover -s tests -p test_recipe_inspection.py
python -B -m unittest discover -s tests -p test_recipe_library.py
```

These are focused checks for this development change, not the full project suite or native-host qualification.


Read [native vendor security 0.3.0](native-vendor-security.md) for FreeBSD, Proxmox VE
and ESXi acquisition, exact branch matching, API/import examples and coverage limits.
Report/run outputs are 0.3.0; inventory stays 0.2.0 and vendor snapshots stay 0.1.0.

*Last modified: 2026-11-13 23:25:46*
