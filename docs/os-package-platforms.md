# OS package native platform support (0.2.0)

Use `system/software/inventory/os-packages` for native package snapshots. Reuse
`opsfeast.package_security.inventory.collect(recipe)` inside authorized checkout
Python recipes; it borrows the provided Recipe session. The human chooses the
Profile, hosts and account policy. No command installs tools, refreshes repositories,
changes packages or acquires additional privileges. See [the service guide](os-package-security.md)
for CLI inputs, module APIs, scope, source provenance and report interpretation.

## Platform selection and availability

The collector first runs fixed `uname -s`. Linux/FreeBSD then use the bounded
Python 3.8+ standard-library probe through stdin. VMkernel selects native ESXCLI
and controller-side XML parsing, without invoking Python on ESXi. Unknown kernels,
failed detection and unavailable tools remain explicit failures; no automatic
installation, interpreter fallback, credential retry or reconnect occurs.

| Platform | Fixed read commands | Identity and package evidence |
| --- | --- | --- |
| Linux | `dpkg-query -W` or `rpm -qa`, with fixed field formats | Existing full native package versions, architecture, source identity and installation state |
| FreeBSD | `pkg query -a`, `freebsd-version -k`, `freebsd-version -r`, `freebsd-version -u` | Ports/package identity plus independent installed kernel, running kernel and userland versions |
| Proxmox VE | dpkg inventory, then `pveversion --verbose` when a native `pve-manager` row exists | Debian OS identity plus a separate Proxmox product identity, installed manager version, running kernel/manager and component versions |
| ESXi 7+ | `uname -m`; `esxcli --formatter=xml system version get`, `software profile get`, `software vib list`, `software component list` | Version/build/update, image profile and separately typed VIB/component records |

ESXi requires SSH/exec access with permission to read all these namespaces. The
component namespace is available on ESXi 7+; older/missing/denied namespaces retain
available VIBs but cannot produce a complete package snapshot. The host's command
availability and output decide coverage; declared support is not native-host
qualification. A component can contain VIBs: retain both kinds without claiming
they are independent installations or summing them into a software-product count.

## Fields and interpretation

Inventory 0.2.0 adds `platform_details` with `kind`, `status`, `facts`, `sources`,
`gaps` and `package_database_status`. Each source retains fixed argv, success/failure,
output SHA-256 and failure type; acquisition pages additionally retain time and
transport evidence. Platform facts and source evidence participate in the canonical
snapshot fingerprint and final reread. Missing identity metadata keeps available
packages, with `packages_complete: true` only when database enumeration and its
consistency checks succeeded; overall `complete` additionally requires complete
platform identity. Missing package databases never become successful empty lists.

FreeBSD facts `installed_kernel`, `running_kernel` and `userland` each contain
native `version` and `patch_level`. Only an explicit trailing `-pN` becomes a numeric
patch level; absence stays null, never an invented zero. Keep all three values:
an installed kernel can differ from the running kernel after an update. These
values do not prove that a reboot is required or that a specific advisory is fixed.
Base-system facts are separate from pkg rows; the base system is not fabricated
as a ports package. Missing pkg does not discard successfully read base facts.

Proxmox retains `os.id: debian` and adds `platform_details.kind: proxmox-ve`.
Facts contain `product`, `manager_package_version`, `manager_installation_state`,
`running_kernel`, `running_manager` and native `components`. An available upgrade
version is separate from the installed version; residual/incomplete component
states stay unavailable. Command presence alone is not sufficient identification.
If pveversion is missing, the native dpkg manager identity and rows remain, with an
explicit identity gap. Custom Proxmox packages are compared to official Proxmox PSAs by confirmed branch;
they do not inherit an unqualified Debian safe/fixed conclusion.

ESXi stores native `system_version` fields and `image_profile` records in facts.
Package rows distinguish `package_kind: vib` and `component`; duplicate detection
includes kind, name, native version and architecture. Report findings and displayed
package identities also distinguish these kinds. `native_fields` preserves
vendor, acceptance level, installation date and other returned XML fields. Those
fields are reported metadata, not independently verified signatures. Missing
package architecture is `unknown` with `architecture_source: not_reported`; host
architecture is not substituted. ESXi purl stays null rather than inventing a
package URL scheme. Components may include managed-DPU entries as reported by the
native namespace; retain native fields and do not silently relabel their scope.

ESXi reads the fixed queries twice and compares fingerprints; it does not page
through a target interpreter. Each native output is bounded at 64 MiB; XML rejects
DTDs/entities, excessive nesting, over 200,000 nodes and oversized scalar fields.
Controller package bytes and total collection time are also bounded. Linux/FreeBSD
retain the documented byte-bounded paging. Limits, parse failures, truncation,
permission failures and changes during collection produce explicit incomplete
results. Rereads detect observed changes; they are not an atomic database lock.

## Reports, upgrades and extension

The collector and inventory remain 0.2.0. The package-security run and report
service/output are now 0.3.0; vendor snapshots remain 0.1.0 and Python runner
contracts remain 0.1.0. Older inventory 0.1.0 is rejected by the current assessor;
recollect selected hosts only when authorized. No migration or deletion occurs.

[Native vendor security 0.3.0](native-vendor-security.md) adds official FreeBSD
VuXML/base SAs, Proxmox VE PSAs and ESXi VMSA comparison to the same meal. Read
that guide for supported predicates, platform targets, branch confirmation,
source selection, missing data and verification limits. Extending collection
still requires fixed read-only probes and consistency tests; extending assessment
separately requires official sources and exact native matching rules.

## Verification and primary references

Targeted public tests: `test_package_inventory_platforms.py`,
`test_package_security.py` and `test_package_security_pipeline.py`. They exercise
synthetic native output, borrowed-session transport, XML rejection, metadata
failures, consistency, schema validation and report/retention integration. They do
not establish live SSH, ESXi release/OEM XML compatibility, FreeBSD installation
variants or native Proxmox version coverage. No managed hosts were run for this change.

Native command references: [FreeBSD freebsd-version](https://man.freebsd.org/cgi/man.cgi?query=freebsd-version&sektion=1),
[Broadcom ESXCLI software](https://developer.broadcom.com/xapis/esxcli-command-reference/latest/namespace/esxcli_software.html),
[Broadcom ESXCLI system](https://developer.broadcom.com/xapis/esxcli-command-reference/latest/namespace/esxcli_system.html),
and [Proxmox pveversion developer format discussion](https://lists.proxmox.com/pipermail/pve-devel/2024-April/063253.html).
The Proxmox discussion is a format reference, not proof of deployment on every release.

*Last modified: 2026-11-13 23:25:46*
