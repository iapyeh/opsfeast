# Recipe catalog

[System inventory Overview](system/inventory/overview/README.md) is a meal of eleven independently executable inventory recipes, ten enabled by default. Children declare inventory-routine-observations 0.1.0; the meal stores child receipts rather than duplicate data. See [routines and meals](../docs/recipe-routines.md).


This catalog lists recipes currently supplied by OpsFeast. To ask your AI agent to create a recipe, share content or acquire someone else's work, start with the [user guide](../docs/recipes.md).

The bundled [system/account/check/identity](system/account/check/identity/README.md) demonstrates python-recipe 0.1.0 with the Core Recipe scoped session. It observes the login account without su/sudo; local and synthetic evidence do not prove remote applicability.

The bundled [feast/report/retention-summary](feast/report/retention-summary/README.md) reads declared retention through the offline report reader and produces Markdown/HTML, including cross-recipe selections. Operation recipe creators own their retention declarations; content is a downstream application.

For current inventory, use the [collection table](system/inventory/overview/collection-plan.md) and [job/utility/scheduling guide](../docs/inventory-jobs.md). Each child owns its retention declaration; frozen historical formats remain readable. `recipes run` uses job collection, while `inventory query` can avoid storage or save an explicit comparison.

## Classification

Use [domain/subdomains/action/name](../docs/recipe-taxonomy.md) for new recipes. Paths can have more than two levels. Bundle recipes live here; user-authored recipes normally live under the selected profile's recipes/ and use :references. Shared user repositories use registered source references. Classification-only moves retain IDs and historical evidence; see the guide's relocation table and required configuration/job/consumer updates.

For an evidence-based coverage/gap review, see [profiling coverage](../docs/profiling-coverage.md).

## Available recipes

| Reference | Stable ID / version | Purpose | Runtime/platform | Verification evidence | Invocation |
| --- | --- | --- | --- | --- | --- |
| [database/mysql/check/replication](database/mysql/check/replication/README.md) | mysql-replication / 0.1.1 | MySQL/MariaDB replica state across instances/channels, safe query evidence, retention and Vault | Core Recipe, SSHScript 7.0.1, target Python/client | Synthetic/local protocol fixtures and Linux SSH MySQL 8.0.46; MariaDB/TLS native unverified | opsfeast.py recipes run database/mysql/check/replication --host HOST --profile NAME --json |
| [system/storage/inventory/disks-raid](system/storage/inventory/disks-raid/README.md) | disks-raid / 0.4.1 | All physical disks including spare/standalone, human-purpose count policy, tray state/capacity and separate RAID health/count | Core Recipe, local RACADM preferred; PERC/LSU alternatives; Linux/Proxmox and ESXi | Synthetic plus native ESXi RACADM PERC/BOSS health/capacity/SSH/retention/Vault; Proxmox and PERC CLI unverified | opsfeast.py recipes run system/storage/inventory/disks-raid --host HOST --json |
| [system/inventory/overview](system/inventory/overview/README.md) | inventory-overview / 0.1.1 | Shared-connection meal of ten default inventory recipes; sensors opt-in | SSHScript 7.0.1; Linux, FreeBSD, macOS, ESXi | Synthetic; historical local macOS evidence does not verify new native access/retention behavior | opsfeast.py recipes run system/inventory/overview --host HOST |
| [system/network/check/port](system/network/check/port/README.md) | check-port / 0.1.1 | One bounded TCP connection from the selected host | SSHScript Session plus target Python socket; Linux, FreeBSD, macOS | Synthetic; no native target/SSH verification | opsfeast.py recipes run system/network/check/port --host HOST --var port=8888 |
| [system/account/inventory/local-users](system/account/inventory/local-users/README.md) | linux-local-accounts / 0.1.1 | Local Linux user/group files without hashes or login-eligibility claims | Core Recipe, target Linux/Python 3.8+ | Synthetic filesystem, runner/retention/HTTP tests; native Linux/SSH unverified | opsfeast.py recipes run system/account/inventory/local-users --profile NAME --host HOST --json |
| [system/process/inventory/snapshot](system/process/inventory/snapshot/README.md) | linux-process-snapshot / 0.1.1 | Visible procfs identity/resource snapshot without argv/environment | Core Recipe, target Linux/Python 3.8+ | Synthetic procfs/race/limits, runner/retention/HTTP tests; native Linux/SSH unverified | opsfeast.py recipes run system/process/inventory/snapshot --profile NAME --host HOST --json |
| [system/access/inventory/ssh-policy](system/access/inventory/ssh-policy/README.md) | linux-ssh-policy / 0.1.1 | OpenSSH policy projection; scoped projections and explicit gaps | Core Recipe, Linux/Python 3.8+, existing native read tools | Synthetic parser/runner/retention/HTTP tests; native tools/SSH unverified | opsfeast.py recipes run system/access/inventory/ssh-policy --profile NAME --host HOST --json |
| [system/account/inventory/sudo-policy](system/account/inventory/sudo-policy/README.md) | linux-sudo-policy / 0.1.1 | Selected-actor sudo policy projection; scoped projections and explicit gaps | Core Recipe, Linux/Python 3.8+, existing native read tools | Synthetic parser/runner/retention/HTTP tests; native tools/SSH unverified | opsfeast.py recipes run system/account/inventory/sudo-policy --profile NAME --host HOST --json |
| [system/network/inventory/firewall-policy](system/network/inventory/firewall-policy/README.md) | linux-firewall-policy / 0.1.1 | Linux firewall policy views; scoped projections and explicit gaps | Core Recipe, Linux/Python 3.8+, existing native read tools | Synthetic parser/runner/retention/HTTP tests; native tools/SSH unverified | opsfeast.py recipes run system/network/inventory/firewall-policy --profile NAME --host HOST --json |
| [system/time/inventory/synchronization](system/time/inventory/synchronization/README.md) | linux-time-sync / 0.1.1 | Linux time synchronization configuration and state; scoped projections and explicit gaps | Core Recipe, Linux/Python 3.8+, existing native read tools | Synthetic parser/runner/retention/HTTP tests; native tools/SSH unverified | opsfeast.py recipes run system/time/inventory/synchronization --profile NAME --host HOST --json |
| [system/logging/inventory/configuration](system/logging/inventory/configuration/README.md) | linux-logging-config / 0.1.1 | Linux logging configuration metadata; scoped projections and explicit gaps | Core Recipe, Linux/Python 3.8+, existing native read tools | Synthetic parser/runner/retention/HTTP tests; native tools/SSH unverified | opsfeast.py recipes run system/logging/inventory/configuration --profile NAME --host HOST --json |
| [system/account/check/identity](system/account/check/identity/README.md) | check-identity / 0.1.1 | Observe the supplied session's effective account without escalation | Core Recipe and SSHScript; Linux, FreeBSD, macOS | Synthetic and earlier local Core evidence; remote applicability unverified | opsfeast.py recipes run system/account/check/identity --host HOST |
| [feast/report/execution-summary](feast/report/execution-summary/README.md) | report-summary / 0.1.4 | Render selected saved execution results as HTML and JSON | Offline controller Python; python-report 0.1.0 | Synthetic and isolated local report generation | opsfeast.py recipes run feast/report/execution-summary --input RESULT.json |
| [feast/report/retention-summary](feast/report/retention-summary/README.md) | report-retention / 0.1.1 | Combine retained observations as Markdown and HTML | Offline controller Python; python-report 0.1.0 | Synthetic and installed-wheel retention/report tests | opsfeast.py recipes run feast/report/retention-summary --profile NAME --json |
| [system/inventory/hardware](system/inventory/hardware/README.md) | inventory-hardware / 0.1.1 | Independent hardware-baseline observations; partial source/permission coverage remains explicit. | Core routines; shared collector and guarded login/root phases | Synthetic transports; native applicability unverified | opsfeast.py recipes run system/inventory/hardware --host HOST --profile NAME --json |
| [system/inventory/hardware-sensors](system/inventory/hardware-sensors/README.md) | inventory-hardware-sensors / 0.1.1 | Independent hardware-sensors observations; partial source/permission coverage remains explicit. | Core routines; shared collector and guarded login/root phases | Synthetic transports; native applicability unverified | opsfeast.py recipes run system/inventory/hardware-sensors --host HOST --profile NAME --json |
| [system/inventory/network-configuration](system/inventory/network-configuration/README.md) | inventory-network-configuration / 0.1.1 | Independent network-configuration observations; partial source/permission coverage remains explicit. | Core routines; shared collector and guarded login/root phases | Synthetic transports; native applicability unverified | opsfeast.py recipes run system/inventory/network-configuration --host HOST --profile NAME --json |
| [system/inventory/network-state](system/inventory/network-state/README.md) | inventory-network-state / 0.1.1 | Independent network-state observations; partial source/permission coverage remains explicit. | Core routines; shared collector and guarded login/root phases | Synthetic transports; native applicability unverified | opsfeast.py recipes run system/inventory/network-state --host HOST --profile NAME --json |
| [system/inventory/resource-metrics](system/inventory/resource-metrics/README.md) | inventory-resource-metrics / 0.1.1 | Independent resource-metrics observations; partial source/permission coverage remains explicit. | Core routines; shared collector and guarded login/root phases | Synthetic transports; native applicability unverified | opsfeast.py recipes run system/inventory/resource-metrics --host HOST --profile NAME --json |
| [system/inventory/services](system/inventory/services/README.md) | inventory-services / 0.1.1 | Independent service-state observations; partial source/permission coverage remains explicit. | Core routines; shared collector and guarded login/root phases | Synthetic transports; native applicability unverified | opsfeast.py recipes run system/inventory/services --host HOST --profile NAME --json |
| [system/inventory/software](system/inventory/software/README.md) | inventory-software / 0.1.1 | Independent software-inventory observations; partial source/permission coverage remains explicit. | Core routines; shared collector and guarded login/root phases | Synthetic transports; native applicability unverified | opsfeast.py recipes run system/inventory/software --host HOST --profile NAME --json |
| [system/inventory/storage-capacity](system/inventory/storage-capacity/README.md) | inventory-storage-capacity / 0.1.1 | Independent storage-capacity observations; partial source/permission coverage remains explicit. | Core routines; shared collector and guarded login/root phases | Synthetic transports; native applicability unverified | opsfeast.py recipes run system/inventory/storage-capacity --host HOST --profile NAME --json |
| [system/inventory/storage-layout](system/inventory/storage-layout/README.md) | inventory-storage-layout / 0.1.1 | Independent storage-layout observations; partial source/permission coverage remains explicit. | Core routines; shared collector and guarded login/root phases | Synthetic transports; native applicability unverified | opsfeast.py recipes run system/inventory/storage-layout --host HOST --profile NAME --json |
| [system/inventory/system](system/inventory/system/README.md) | inventory-platform-system / 0.1.1 | Independent system-configuration observations; partial source/permission coverage remains explicit. | Core routines; shared collector and guarded login/root phases | Synthetic transports; native applicability unverified | opsfeast.py recipes run system/inventory/system --host HOST --profile NAME --json |
| [system/inventory/system-runtime](system/inventory/system-runtime/README.md) | inventory-system-runtime / 0.1.1 | Independent system-runtime observations; partial source/permission coverage remains explicit. | Core routines; shared collector and guarded login/root phases | Synthetic transports; native applicability unverified | opsfeast.py recipes run system/inventory/system-runtime --host HOST --profile NAME --json |

This checkout ships 25 entries (24 recipes and one meal). Catalog discovery also includes enabled profile and registered external sources; publisher trust, dependencies and host applicability remain separate evidence. No live exchange or automatic third-party installer is implemented. Update this catalog with actual coverage and verification when adding recipes.

## Custom and third-party content

Users may create recipes in their own working directories or repositories without forking Ops. Custom recipes within a management directory can be selected through explicit `./recipes/...` paths. opsfeast.py recipes run supports the python-routines and recipe-meal 0.1.0 contracts and [general Python-session execution](../docs/recipe-execution.md) (descriptor 0.3.0, contract 0.1.0). Reviewed compatible custom recipes use its connection/input/result lifecycle. The [recipe experience](../docs/recipe-experience.md) provides offline python-report 0.1.0, catalog/result/artifact views, explicit-file bundle candidates and saved reruns. An automatic third-party installer and arbitrary operational backend loader are not implemented.

- [Create a custom recipe](../docs/recipe-authoring.md)
- [Share one or multiple recipes](../docs/recipe-sharing.md)
- [Acquire, review, verify and authorize installation](../docs/recipe-acquisition.md)
- [Recipes skill for AI agents](../skills/opsfeast-recipes/SKILL.md)

## Recipe documentation requirements

Recipe authors should follow the shared [vision and design principles](../docs/vision.md) and [authoring guide](../docs/recipe-authoring.md). Design for human intent, repeatable execution with less model work, community reuse, clear authorization and outcomes supported by evidence.

Each recipe should document its purpose, supported and tested platforms, selected tools and compatibility, dependencies, required permissions, inputs, outputs, side effects and verification method. Follow the [tool selection workflow](../docs/recipe-authoring.md#choose-execution-tools) and explain the implementation choice. SSHScript recipes should link actual capabilities to code and evidence; other tools and mixed recipes are welcome, with their own reviewed standalone usage where the current runner does not apply.

Collection recipes should retain observation sources and timestamps and distinguish success, permission denial, unsupported operations, timeouts and parsing failures.

The first result contract and synthetic example live with inventory-system. Inventory-system retains its shared observation schema; other compatible Python recipes return the versioned general result envelope and recipe-owned data.

Retained inventory and JSON exchange are implemented through [result-data tools and contracts](../docs/result-data.md), with the [agent skill](../skills/opsfeast-result-data/SKILL.md). Identity/sudo probes and ESXi have synthetic coverage only; prior macOS local tests cover the older collection path.


## Profile-local backup-file checks

For daily dated backup presence, configurable expiry lists and unexpected directory entries, reuse the shipped [backup-files-check module and profile recipe procedure](../docs/backup-file-checks.md). The agreed profile path is `recipes/backup/files/check/daily-backups/`, reference `:backup/files/check/daily-backups`. It is user-installed support rather than an additional bundled descriptor; the bundled recipes above are separate. Real host bindings stay private. The opt-in [backup-check consumer](../consumers/backup-check/README.md) creates service objects without deleting files.

## Web menu

The **Recipes** page explains these dishes with human-readable purposes,
limits, prerequisites and suggested combinations. It supports explicit
multi-host/multi-recipe review and execution through the existing runner, plus
offline reports. See [Web menu and execution](../docs/web-recipe-menu.md).
The [profiling blueprint](../docs/system-profiling.md#profiling-scope) is the Bundle
coverage target; current partial/unintegrated capabilities remain visibly distinct.

Inventory's Web parameters now select jobs or exact fields/sensors. Report tasks
link to saved artifact previews/downloads, also discoverable from the menu's report
index. These reuse existing acquisition/result contracts; see
[Web scope and artifacts](../docs/web-recipe-menu.md).

## Inventory child consumers and reports

Use [the inventory dependency map](../docs/inventory-consumers.md) for current
child references, exact report filters, subscription/read-filter updates and
unchanged historical ownership. Vault already subscribes to all observations;
backup-check has no inventory dependency. Retention-summary keeps exact filters;
execution-summary 0.1.3 preserves child/meal outcomes and routine/connection evidence.
Saved-result collection_user is unknown for mixed/unverified routine actors. Existing
Overview-only filters are not aliases for children; private configuration and
historical records are never rewritten automatically. These read/presentation
interfaces require no host access; explicit report, dispatch or rebuild writes
need the human's corresponding scope.

## OS package security

- [Complete OS package snapshot](system/software/inventory/os-packages/README.md): Linux/Proxmox dpkg/RPM, FreeBSD pkg/base/kernel and ESXi VIB/component identities, source times, pagination and explicit completeness; no application/container crawl.
- [Vendor vulnerability report](feast/report/package-security/README.md): explicit inventory/advisory inputs, offline HTML/Markdown/JSON and comparison evidence.

Read [vendor support and acquisition limits](../docs/os-package-security.md). Debian/Ubuntu and explicitly declared RHEL streams have native version analysis; selected RHSA fetch is not exhaustive. FreeBSD VuXML/base SAs, Proxmox VE PSAs and ESXi VMSA matrices have native comparison with explicit branch/coverage limits. Synthetic tests do not establish native SSH/platform execution.

## One-selection package security

The **OS 套件弱點分析套餐** menu meal uses [this orchestration recipe](system/software/check/package-security/README.md) for package collection → matching official advisory acquisition/cache → linked vulnerability artifacts. It requires only normal selected-host review for supported default sources. See [limits, RHEL configuration and partial reports](../docs/package-security-meal.md).

For collector 0.2.0 platform prerequisites, fixed native commands, `platform_details`,
`package_kind`, `packages_complete` and version limits, read [OS package platform support](../docs/os-package-platforms.md).
Reuse the collector for ESXi VIB/component metadata, FreeBSD base/kernel patch identity
and Proxmox VE product identification; missing commands remain explicit gaps. Older
0.1.0 inventory inputs must be recollected for the current report; do not rewrite
or delete old evidence. Inventory remains 0.2.0; report/run service 0.3.0 also provides native vendor advisory adapters.


For native vendor acquisition/assessment, read [vendor security 0.3.0](../docs/native-vendor-security.md).
Reuse `opsfeast.package_security.advisories.fetch/import_local/load` and
`analysis.assess`, or prefer the existing host-selected meal. FreeBSD uses
VuXML pkg ordering plus separate installed/running kernel and userland targets;
Proxmox uses staff PSAs and confirmed package/product branches; ESXi uses the
official paginated read-only search API and same-update build matrices.
`vendor_advisory_urls` is an optional official-source override in the meal;
missing/failed/unparsed/ambiguous/stale evidence stays unknown. Inspect stage,
retention and linked report receipts. No host execution or remediation follows
from source inspection, download or offline reporting.

All 28 bundled Recipes now declare [staged execution](../docs/staged-recipe-execution.md): host operations and meals use a Python stage, and offline reports use a controller-scoped Python stage. CLI, scheduled inventory and Web plate entrypoints retain their existing authorization and result contracts.

*Last modified: 2026-11-18 15:56:07*
