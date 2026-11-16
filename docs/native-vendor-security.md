# Native vendor security (0.3.0)

Use **OS 套件弱點分析套餐** (`bundle:package-security`), which runs
`system/software/check/package-security` for each selected host. The same workflow
now collects inventory, selects official vendor data, reuses a fresh Profile-local
snapshot and saves linked HTML/Markdown/JSON reports for FreeBSD, Proxmox VE and
ESXi. Collection remains read-only; downloads occur on the controller. No packages,
repositories, privileges, credentials or host connections are changed by assessment.

Read [the meal workflow](package-security-meal.md) for authorization, concurrency,
limits, cache and receipts; [the platform collector](os-package-platforms.md) for
required facts; and [the shared service](os-package-security.md) for APIs, native
Debian/RPM analysis and source/signature limitations.

## Prerequisites and contracts

Use the checkout's normal Python 3.11+ environment; no new dependency is added.
Collection uses the existing authorized Recipe session and SSHScript 7.0.1.
Inventory and the collector stay 0.2.0. The report service and package-security run
outputs are 0.3.0; immutable `vendor-advisories` stays 0.1.0 with optional
`coverage_gaps` (up to 32 reason strings, 256 characters each). Recipe/report runner
contracts stay 0.1.0. Inventory 0.1.0 remains unsupported; never relabel or rewrite
old snapshots. Existing data, caches, notes, recipes, menu selections, accounts,
ports and Profiles are not initialized or replaced by this feature.

Reuse these checkout interfaces before writing a scraper or vulnerability engine:

```python
from opsfeast.package_security.advisories import fetch, import_local, load
from opsfeast.package_security.analysis import assess
from opsfeast.package_security.pipeline import execute

# Local/controller operations only; supply reviewed scope and new output storage.
feed = fetch("freebsd", {"os_id": "freebsd", "version_id": "14.3", "codename": ""})
assessment = assess(inventory_snapshot, [load(feed)])
# Inside the human-authorized host recipe, use its supplied Recipe/Profile:
# result = execute(recipe)
```

`fetch` returns an object; the CLI persists it with exclusive creation. `import_local`
accepts an official original XML/bzip2, ASCII advisory, HTML file or a directory of
original files. Preserve its original acquisition time and official source URL.
Imported bytes are user-attested; importing never visits that URL. Mixed-format
FreeBSD directories should be split into separate imports when their source URLs
or compressed/uncompressed content types differ. Report input requires one
combined compatible snapshot per vendor/scope; use automatic acquisition to combine
ports/base sources. There is no implicit local-file/latest selection in the meal.

## Automatic sources and matching

| Platform | Official acquisition | Matching scope |
| --- | --- | --- |
| FreeBSD | `https://vuxml.freebsd.org/freebsd/vuln.xml.bz2`; base SAs referenced by FreeBSD ranges for the exact observed release | Native pkg name/glob and OR-of-AND version predicates; separate installed kernel, running kernel and userland corrected RELEASE patch versions |
| Proxmox VE | All discovered pages of the fixed VE security-advisory thread on `forum.proxmox.com`, staff author `ProxmoxSecurityAdvisory` only | PSA package/glob, explicit fixed Debian version and product/package branch |
| ESXi | Broadcom's paginated VC advisory search API; original VMSA HTML for ESX/ESXi-titled entries | ESX/ESXi Response Matrix product/CVE/runtime scope, exact installed update branch and fixed build |

Sources keep exact URL, retrieval time and raw-byte SHA-256. Broadcom's read-only
search uses POST with fixed JSON `pageNumber`, `pageSize: 100`, empty `searchVal`,
`segment: VC` and null `sortInfo`; its request body is retained in source evidence.
All pages are read, up to 100; only ESX/ESXi-titled entries are selected. This is
not a promise to cover every VMSA, embedded third-party component, VMware Tools,
VCF appliance or vCenter issue. API schema/auth/access failures remain explicit.

FreeBSD does not infer a complete base advisory history from a recent RSS feed.
It selects official SAs referenced by VuXML's exact-release FreeBSD ranges; absent
mapping is a coverage gap. Missing current-release SAs, EOL releases, future issues
or vulnerabilities absent from the supplied sources remain unknown. pkg version
ordering handles PORTEPOCH, PORTREVISION, prerelease/stage/component rules and
native comparisons, not semver or Debian ordering. VuXML range predicates `lt`,
`le`, `eq`, `gt`, `ge` are supported; alternatives are OR, predicates within a range
are AND. Unknown operators or malformed versions never yield a clean finding.

Base targets are report-only identities (`package_kind: platform`), not fabricated
pkg records. The base adapter requires exact `X.Y-RELEASE[-pN]` and a single same-
release Corrected boundary. A RELEASE without a p suffix is compared as the native
initial release; the collector's absent numeric patch field remains null. STABLE,
CURRENT, RC, ambiguous boundaries and unknown module scope stay unknown. Known
kernel modules compare both installed and running kernels; recognized userland
modules compare userland. Other modules retain all three targets as unknown for
review. A newer installed kernel does not mask an older running kernel. No finding
proves that a process restart is complete, a service is exploitable or an upgrade
is approved.

Proxmox selects the PVE major from native pve-manager facts while keeping Debian
OS identity. Explicit `Proxmox VE N.x` fix qualifiers must match. Unqualified fixes
are ordered only within the same package major; other branches need review. PSAs
with unparsed fix prose become platform unknown findings; explicit unfixed packages
retain their advisory identity and reason. The adapter covers the official VE
thread, not PBS/PMG/PDM or a complete Debian-base feed. Debian-only inputs cannot
substitute for Proxmox vendor evidence. No advisory match remains unknown.

ESXi uses the native Version and Build facts and explicit fixed labels such as
`ESXi80U3d-24585383`. Build ordering is allowed only within the exact update branch
(`8.0.3` here), including equality at the fixed boundary; a higher build from another
branch is not proof of repair. Alternative matrix update branches are combined
within the same product/CVE/runtime scope. Matrix row/column spans are handled;
vCenter and Workstation/Fusion rows are excluded. A non-Any runtime, missing CVE
scope/build, unrecognized labels or an absent exact branch remains unknown.
OEM component/VIB records retain unknown status when no matching component rule
exists; a fixed platform finding does not attest all VIBs or signatures.

## Invocation and reviewed source overrides

The ordinary host-selected invocation is unchanged:

```sh
python -B tools/opsfeast.py recipes run system/software/check/package-security \
  --profile main --host node --json
```

Setup/source inspection alone does not authorize it. Follow existing human target,
account, controller HTTPS and local storage authorization. No host runs were used
to develop these adapters.

For an explicitly selected official bulletin instead of discovery, set the meal's
`vendor_advisory_urls` array (up to 1,000 URLs). Empty means automatic discovery.
Only fixed vendor hosts and known public source paths are accepted. The selected
URL list is part of the Profile cache key; it does not expand to arbitrary URLs,
redirects, proxies, credentials, scripts or additional vendor sources. For example:

```sh
python -B tools/opsfeast.py recipes run system/software/check/package-security \
  --profile main --host esxi-node \
  --var 'vendor_advisory_urls=["https://support.broadcom.com/web/ecx/support-content-notification/-/external/content/SecurityAdvisories/0/25390"]' --json

# Explicit controller-only download, no host connection:
python -B -m opsfeast.package_security fetch --vendor esxi --release 8.0.3 \
  --advisory https://support.broadcom.com/web/ecx/support-content-notification/-/external/content/SecurityAdvisories/0/25390 \
  --output /data/security/esxi-selected.json
python -B -m opsfeast.package_security fetch --vendor freebsd --release 14.3 \
  --output /data/security/freebsd-143.json
python -B -m opsfeast.package_security fetch --vendor proxmox --release 9 \
  --output /data/security/pve-9.json

# Explicit original-HTML import when an official endpoint is unavailable:
python -B -m opsfeast.package_security import --vendor esxi --release 8.0.3 \
  --source /data/original/vmsa.html \
  --source-url https://support.broadcom.com/web/ecx/support-content-notification/-/external/content/SecurityAdvisories/0/25390 \
  --retrieved-at 2026-11-13T00:00:00Z --output /data/security/esxi-imported.json
```

Then use the ordinary offline report with the exact inventory and advisory files.
Old acquisition times remain old; imports/downloads never patch targets or infer
current credentials. Output directories must already exist and snapshots are
immutable. Cache freshness defaults to 24h; 0 forces acquisition, with no stale-
cache substitution or network retries. A selected bulletin set is not an exhaustive
vulnerability database.

## Failure, resource and report evidence

Native discovery bounds are 1,000 documents, 100 Proxmox/Broadcom pages, eight
controller download workers, at most 30 seconds per native read and the existing
overall advisory budget. Native responses/HTML are bounded at 32 MiB, retained raw
inputs at 256 MiB, and bzip2 expansion at 128 MiB. XML node/depth and HTML structure
limits apply. Only the unused official VuXML historical-year declarations are
accepted as inert metadata: entities are never resolved, DTDs are never fetched,
and entity references/unsafe XML are rejected. Downloaded HTML/JS is never executed.

Some official records may be unparseable; successful originals remain usable and
coverage gaps are saved. Download/truncation/timeout/parse/index failures preserve
collection evidence and create a partial report where possible. Missing/stale/
ambiguous/partial evidence forces unknown final status while preserving the native
candidate, source hashes, rule, operands, fixed boundary and comparison result.
Report `attention` is not a safe-host assessment; inspect affected/unknown counts
and independent execution, retention and consumer receipts. The full platform facts
and typed platform/package identities remain in JSON and readable report evidence.

## Verification and extension

Public focused tests are `test_package_native_advisories.py`,
`test_package_inventory_platforms.py`, `test_package_security.py` and
`test_package_security_pipeline.py`, with static recipe/schema inspection and the
existing menu tests. They cover success, wrong/stale scope, native version
boundaries, missing fixes, malformed/unsafe XML, pagination, partial source failure,
source allowlists, imports and all three saved-report pipelines. They use synthetic
host/native transport and no managed hosts. Separately, official compressed VuXML,
a Proxmox thread page, a FreeBSD SA, a Broadcom search page and an original VMSA
matrix were parsed locally. This is not a full live-feed or native-host qualification.

To extend matching, add a source adapter and explicit native predicates in
`opsfeast.package_security.native_advisories`, preserve source/rule evidence, test
success/failure/boundaries and update this guide/capability/recipe skill together.
Do not add generic upstream version matching, automatic fix execution or silent
fallback to another distribution.

Primary references: [FreeBSD VuXML guidance](https://docs.freebsd.org/en/books/porters-handbook/security/),
[FreeBSD base SA format](https://www.freebsd.org/security/advisories/FreeBSD-SA-24:14.umtx.asc),
[FreeBSD pkg ordering source](https://github.com/freebsd/pkg/blob/master/libpkg/pkg_version.c),
[official Proxmox VE PSAs](https://forum.proxmox.com/threads/proxmox-virtual-environment-security-advisories.149331/),
[Broadcom official public frontend module](https://support.broadcom.com/o/js/resolved-module/internal-tools-portlet@1.0.0/lib/index.es),
and [VMSA Response Matrix example](https://support.broadcom.com/web/ecx/support-content-notification/-/external/content/SecurityAdvisories/0/25390).
The FreeBSD ordering port retains the original source's complete copyright/license
notice in `opsfeast/package_security/freebsd_versions.py`.

*Last modified: 2026-11-13 23:25:46*
