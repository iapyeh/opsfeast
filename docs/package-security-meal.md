# OS package security meal (0.3.0)

In **Recipes → Meals**, add **OS 套件弱點分析套餐**, select the hosts in the default
Profile, review and confirm execution. Each host then runs three dependent stages:

1. Collect a full native OS package snapshot through its supplied Recipe session.
2. Acquire the matching vendor advisory snapshot on the controller, or reuse an
   intact, fresh snapshot for the same Profile/vendor/release/advisory selection.
3. Generate saved HTML, Markdown and JSON vulnerability reports from those exact
   inputs. Expand the host task and choose **開啟產生的報告** when it completes.

No manually copied input paths or separate report selection are needed. The menu
meal has stable ID `bundle:package-security` and contains one orchestration
operation, `system/software/check/package-security`. The operation sequences the
three dependent stages; this is not three unrelated plate entries and does not
extend the `recipe-meal` shared-routine engine. Running it directly is equivalent:

```sh
python -B tools/opsfeast.py recipes run system/software/check/package-security \
  --profile main --host node --json
```

The menu stores definitions, not hosts or execution authorization. Selecting this
meal and confirming its reviewed effects authorizes host reads, controller vendor
HTTPS and local snapshot/retention/report writes. It does not authorize package
installation, metadata refresh on targets, privilege changes or remediation.
The review explicitly discloses controller downloads. Existing configured
consumers may run after retention, with their own receipts and scope.

## Sources and platform limits

| Detected distribution | Automatic source |
| --- | --- |
| Debian | Complete Debian Security Tracker JSON, scoped to the observed release/codename |
| Ubuntu | Canonical's complete CVE OSV archive, scoped to the observed release |
| RHEL | Selected official RHSA OSV records; IDs supplied by settings or discovered from existing DNF security metadata |
| FreeBSD | Official compressed VuXML and release-specific base SAs referenced by its FreeBSD ranges |
| Proxmox VE | Every discovered page of the official staff-authored VE PSA thread; native Debian version ordering within confirmed branches |
| ESXi | Paginated official Broadcom VC advisory search API and ESX/ESXi-titled VMSA Response Matrices; same update branch/build only |
| Other distributions | No vendor adapter; preserve available collection and generate an incomplete/unknown report |

This workflow reuses the [phase-one package service](os-package-security.md), its
native Debian/RPM version comparison, completeness checks and exact OS matching.
Do not substitute upstream versions, another distribution's advisory set or a
same-named host from another Profile. Linux/FreeBSD collection requires target Python
3.8+ and native dpkg-query/rpm/pkg; ESXi uses native XML esxcli without target Python.
See [platform identity and patch versions](os-package-platforms.md). Controller execution requires SSHScript 7.0.1,
normal OpsFeast dependencies and public vendor HTTPS access. No tools are installed.

For RHEL, a bounded, fixed target probe runs
`dnf --cacheonly --noplugins updateinfo list --all --security` to discover RHSA IDs
for versions of installed packages. It does not refresh metadata, enable plugins,
change repositories or connect from the target to obtain advisories. DNF's cache
may be absent, expired or filtered by enabled repositories/modules. Its freshness
is not established, so automatically discovered scope is explicitly incomplete.
At most 100 newest discovered RHSA IDs are fetched; excess selection is recorded
as a gap, not an exhaustive database claim. No matching advisory remains unknown.
Missing DNF/cache or an empty list produces an unknown report rather than guesses.

An operator may configure `redhat_advisory_ids` (up to 100 exact `RHSA-YYYY:NUMBER`
strings) to select reviewed records without the DNF query. Exact RHEL product
streams and Ubuntu Pro ecosystems still require `declared_ecosystems`; the
workflow never infers subscription/module/EUS scope from the OS major version.
Configure these once through exact-reference Profile/group/host recipe vars.
Host selection alone then uses that existing configuration. Absent scope remains
unknown, even when the version-only candidate is affected or fixed. Selected RHSA
records do not cover every open/unpatched Red Hat vulnerability.

Official references: [Debian tracker](https://security-tracker.debian.org/tracker/),
[Canonical OSV](https://documentation.ubuntu.com/security/security-updates/osv/),
[Red Hat OSV](https://security.access.redhat.com/data/osv/),
[DNF cache and updateinfo semantics](https://dnf.readthedocs.io/en/latest/command_ref.html).

## Inputs, budgets and caching

| Variable | Default | Bounds/effect |
| --- | --- | --- |
| `collection_budget_seconds` | 180 | 1–240 seconds, total collection budget |
| `command_timeout_seconds` | 30 | 1–120 seconds; also bounded by runner timeout |
| `page_size` | 200 | 1–500; complete enumeration, not a total package limit |
| `declared_ecosystems` | `[]` | Exact operator-confirmed RHEL/Ubuntu Pro scopes; original collector limits apply |
| `advisory_cache_hours` | 24 | 0–168; 0 forces a new fetch |
| `advisory_budget_seconds` | 180 | 1–240; bounded lock wait/acquisition checks and socket/read timeouts |
| `redhat_advisory_ids` | `[]` | Up to 100 exact IDs; empty means try DNF cached discovery on RHEL |

These variables belong to the orchestration reference, not the standalone
collector/report references. Defaults mean a normal Debian/Ubuntu host needs no
extra execution parameters. Host concurrency remains the existing temporary run
parameter; it is not a meal definition field. The Web's existing 600-second worker
deadline remains in force, including native command, feed processing and report
work. Raising individual budgets cannot bypass that deadline. Source byte/archive
limits remain those in the phase-one guide. Stop never retries or patches a host;
confirmed local worker termination and unknown remote cleanup remain separate.

Profile-local `security/advisories/` stores immutable `SHA.snapshot.json` objects,
small mutable scope indexes and private lock files. Cooperating workers serialize
per vendor/release/advisory selection; equal scopes share a fresh snapshot even
when multiple hosts execute. Cache freshness uses the original source retrieval
times, never filesystem mtime. Network failures do not silently reuse expired
snapshots. Corrupt/foreign-scope/tampered cache data is rejected and reported;
there is no automatic cache repair or network retry. A fresh matching cache avoids
the network; downloads use only the reviewed official HTTPS endpoints, bypass
ambient proxies and reject redirects. Unrelated Profiles never share indexes.

## Saved results and failure interpretation

`security/package-runs/RUN_ID/inventory.json` contains the exact input inventory.
The normal report runner writes `reports/ID/result.json` and its declared artifacts;
its input receipts record the inventory/cache filenames and byte hashes. The
operation's ordinary raw result and portable `os-package-security-run` 0.3.0
retention preserve:

- `package_snapshot`: full inventory, original source times, fingerprint, counts,
  incomplete states and gaps;
- `stages`: collection, advisory and report status/reason, scoped input references,
  vendor hashes/counts and any DNF discovery receipt;
- `gaps`: acquisition/processing limitations;
- `report`: saved result ID, generation status and finding counts.

The raw operation also supplies a bounded `summary` for CLI output and `reports`
links for the Web. JSON CLI output sets `data_is_summary: true` and puts that small
summary in `data`; full package rows remain in the saved raw/retained result.
This prevents large inventories from overflowing worker receipt transport. Report
links are Profile-relative, validated saved report IDs; artifact preview/download
uses existing authorization, hash checks, sandboxing and preview size limits.

A complete workflow returns `success`, including when affected findings exist.
Read finding counts and evidence: execution success is not a safe-host verdict.
Incomplete collection, unsupported vendor, missing stream, stale cache metadata,
limited RHSA selection or download failure returns `partial` with a generated
report where possible. Missing advisories produce unknown entries and acquisition
gaps in that report. Original collection completeness is not falsified merely
because advisory acquisition failed. If report generation itself fails, return
`failed`, keep the inventory/stage receipts and provide no fabricated artifact
link. Retention and configured consumer delivery have independent receipts.

The standalone `feast/report/package-security` now has optional
`allow_missing_advisories` (default false) and `acquisition_gaps` (`[]`) inputs for
this explicit failure-report workflow. Without that flag it still requires an
advisory input. `analysis.assess(inventory, [])` preserves unknowns; it never turns
an absent feed into not-affected. Acquisition gaps make assessment incomplete,
while retaining evaluable per-advisory findings and candidate evidence.

## Agent reuse and verification

Reuse `opsfeast.package_security.pipeline.execute(recipe)` inside reviewed
Python-recipe orchestration using its supplied Profile/session. It reuses
`inventory.collect`, immutable advisory normalization and `recipe_reports.run_report`;
do not generate temporary host shell scripts or a separate renderer. Cache helpers
are internal, not a public cache-editing API. Direct offline report generation
continues to require no host or vendor network operations.

Public focused tests exercise complete runs with mocked host/vendor I/O, original
snapshot retention, shared cache/forced refresh/scope separation, failures and
unknowns, cache tampering, RHEL fixed command/declared streams, bounded CLI receipts,
report references and Web review/results. The shared runner test also checks real
local report/SQLite/Vault delivery with synthetic data. No actual managed host,
DNF cache, full live vendor archive or live recipe execution was used to qualify
native platform support. Platform declarations remain implemented, not natively
verified. No full project test suite was run for this development change.


## Native vendor selection and source overrides

Version 0.3.0 selects FreeBSD release, Proxmox VE major (separate from Debian OS
release), or exact ESXi version automatically from inventory 0.2.0 facts. See
[native vendor security](native-vendor-security.md) before interpreting those findings.
The optional `vendor_advisory_urls` array selects up to 1,000 reviewed, allowlisted
official URLs instead of discovery; it is part of the cache selection key. With
`[]`, official discovery is automatic. It does not select arbitrary websites,
credentials or local files. For example, supply an exact Broadcom VMSA HTML URL
when a public API is unavailable, or use the explicit import/offline-report flow.
Acquisition/parse gaps remain in stage receipts and the report. The existing
`advisory_budget_seconds`, cache freshness and no-retry rules still apply.

*Last modified: 2026-11-13 23:25:46*
