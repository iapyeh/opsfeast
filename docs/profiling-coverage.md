# Bundled profiling coverage review

## Current review (2026-11-10)

This section supersedes the earlier delivery order below. The original baseline
and batch records remain historical evidence. This review inspects current product
catalogs, recipe descriptors, collector bodies/schemas and consumer/report readers;
it does not connect to managed hosts, run collectors or infer a host's actual state.

### Verified scope and counting

- Bundle: **25 entries = 24 recipes plus one Overview meal**. Twenty recipes produce
  profiling datasets: eleven inventory children, seven Linux account/process/policy
  collectors, disks/RAID and configured MySQL replication. Two point diagnostics
  and two offline reports are useful but do not add broad profiling acquisition.
- Catalog: **10 provider bindings, 104 projected properties, 39 capabilities**;
  **27 partial, 12 not integrated, none declared complete**. These are catalog
  counts, not a percentage of the original blueprint achieved or of hosts covered.
  Arrays such as processes/packages contain many fields and instances; a projected
  property count is not a count of independently verified measurements.
- The eleven child recipes retain the existing **72 inventory properties**;
  Overview defaults to ten general children / 70 properties, with two sensor
  properties opt-in. Splitting execution and fixing consumers did not add fields.
- New routine execution supplies one host-owned connection, permission phases,
  independent child retention and shared-source provenance. The seven Linux
  Python-recipe collectors and specialized producers retain their independent
  execution; putting them in a Web plate does not automatically share their
  connection or move their privilege handling into the routine executor.
- Web field selection, saved meals, review/execution, profiling and report readers
  are implemented. Vault and reports now read children without reassigning history.
  See [routines](recipe-routines.md) and [consumer dependencies](inventory-consumers.md).

### Coverage against the original blueprint

“Partial” below means useful acquired data exists, with explicit limits. It does
not establish complete enumeration, policy effectiveness or a continuous history.

| Domain | Partial / total capabilities | Actual current acquisition | Main remaining gaps |
| --- | --- | --- | --- |
| Hardware and environment | 4 / 7 | Vendor/model/serial/UUID, architecture/virtualization, CPU model/logical CPU count, total RAM, Linux thermal-zone temperatures and hwmon fans. Protected Linux identity fields use root routines. | Socket/core/NUMA topology and microcode; board/DIMM manufacturing identity and ECC; PCIe/USB/Thunderbolt/controllers and attachment relations; BIOS/UEFI/BMC/Secure Boot; GPU/disk-specific sensors, PWM, power/throttling/ECC health. Some vendor raw details can exist without a generic structured projection. |
| Storage and filesystems | 6 / 6 | Block/mount rows, space/inode/swap, cumulative Linux disk counters; specialized disk/controller/physical/virtual/MD/health evidence, with model/serial/WWN where the provider supplies it. | Physical-to-OS-to-volume relationships; LVM/LUKS/multipath/ZFS/Btrfs topology; NFS/SMB/iSCSI and cloud attachment metadata; actual versus configured mount policy/options; SMART/NVMe health and error counters; quota/thin-pool/snapshot accounting; rates/latency and saturation context. Six partial entries do not mean complete storage coverage. |
| OS, software and libraries | 2 / 4 | Host/kernel/distribution identity, timezone abbreviation, platform package/receipt/VIB lists. | Kernel boot parameters/config/modules, tool/runtime versions and executable paths, per-user/virtual/container language environments and modules; installed versus loaded libraries and relationships; package provenance/security-update status. Package lists alone are not a complete SBOM. |
| Networking and exposure | 6 / 7 | Interface/MAC/MTU/state, IPv4/IPv6 with prefixes, DNS server entries, route rows, TCP/UDP listener rows, separate firewall backend views, cumulative traffic/error counters. | Listener PID/executable ownership; active connections and observed direction/lifecycle; per-namespace topology, drivers/link speed/bond/VLAN/bridge relationships; complete resolver/search/hosts and policy routing; effective cross-backend exposure/NAT analysis; traffic rates. Current Linux listener query does not request PID ownership. |
| Services, applications and processes | 5 / 6 | Service-manager rows, clock/NTP/chrony/timesyncd/configured time-source views, explicitly configured MySQL replica identity/channels; procfs snapshots with PID/PPID/start ticks/boot ID, UIDs/GIDs, state/threads/RSS/VSZ/CPU ticks and executable/deleted state; uptime/load, sampled overall CPU, available RAM and memory PSI. | Startup enabled/masked/dependency detail; cron/user cron/timers; automatic application/DB instance discovery, versions/configuration/health beyond configured replication; process FD/limits/I/O/cgroup/security context and lifecycle; CPU mode breakdown/CPU and I/O PSI, sampled disk/network/process rates. |
| Accounts, authentication and privilege | 3 / 4 | Local passwd/group data and shell hints; selected sshd settings with optional complete Match query context; current-actor noninteractive sudo projection. | NSS/directory accounts, lock/expiry/PAM and effective login eligibility; SSH key fingerprints; other actors/full sudo constraints/capabilities/su; login success/failure, active sessions, privilege-use events and source/time baselines. A configured shell is not proof of login eligibility. |
| Logging and monitoring | 1 / 2 | Selected journald/rsyslog/nginx/MySQL/logrotate configuration, destinations and journal size metadata. | Actual event ingestion, incremental checkpoints, forwarding/retention/pipeline health, complete inheritance/alternate roots, auditd/syslog-ng, SNMP and other monitoring agents/trap destinations. Never collect passwords/private keys/community strings as ordinary profiling fields. |
| Baselines and anomaly analysis | 0 / 3 | Retained history/latest attempts and limited deterministic Attention thresholds, including as-of cross-child hardware baselines. | General configuration drift, counter reset-aware trends/rates, workload/time-window baselines, authentication/connection behavior correlation and event-driven alerts. Existing threshold hints do not close these three capability gaps. |

The twelve currently unintegrated catalog capabilities are hardware expansion,
firmware and health; language environments and libraries; active connections;
workload schedules; authentication activity; monitoring agents; and all three
analysis capabilities. Partial capabilities also contain substantive gaps, so
prioritization must not look only at these twelve labels.

### Recommended next batch: connections, authentication activity, schedules

Choose these first because they close three entirely missing portions of the
original blueprint and supply evidence needed for intrusion/abnormal-behavior
review. Linux is the initial delivery target; broader platforms need independent
source/permission/parser verification. This is a proposed sequence, not execution
authorization or a declaration that these collectors already exist.

1. **Connection snapshot and process attribution.** Observe TCP/UDP sockets,
   local/remote IPv4/IPv6 endpoints, state, namespace and available PID/executable
   association; enrich listener ownership at the same time. Use existing process
   identity keys and bounded acquisition. Unattributed sockets remain unknown.
   Snapshot endpoint/listener matching is not proof of inbound/outbound initiation;
   label inferred/unknown direction explicitly. Later connect/accept event sources
   are required to claim observed direction or complete short-lived connections.
2. **Authentication/login/session activity.** Start with existing journal/login
   evidence, bounded time ranges and reviewed projections: success/failure, account,
   source endpoint, method/service and session metadata where available. Add
   privilege-use events only where the source supports them. Do not export full
   messages, credentials or arbitrary command arguments by default. Build the
   minimal incremental envelope/checkpoint handling needed by this collector,
   including source identity, event ID/cursor, source/controller times, gaps and
   completeness. Cursor advancement must follow durable data acceptance; test
   interruption/replay, duplicates, rotation/vacuum/reboot and denied/missing sources.
   A finite read is useful before background operation exists; it is not continuous
   surveillance and cannot reconstruct events never recorded or already lost.
3. **Scheduled/startup workload inventory.** Enumerate system/user cron, cron
   directories and systemd timers, their service association, declared schedule,
   enabled/masked/active state and available last/next execution metadata. Treat
   schedule strings and command lines as potentially sensitive: retain reviewed
   executable/association summaries rather than arbitrary arguments or environments.
   This is inventory of target schedules, not installation of an OpsFeast scheduler.

Implement snapshot and incremental evidence as distinct modes. Reuse routine
ownership, immutable field selection and retention-to-consumer flow for compatible
new work; do not build a general daemon/eBPF platform before the first bounded
collectors can deliver useful records. There is no current generic event scheduling
or continuous capture guarantee. Persistent polling needs a separately implemented
and authorized lifecycle with overlap, restart, cancellation and retry semantics.
Do not silently repurpose the inventory-specific scheduler as that service.

### Subsequent implementation order

| Order | Batch | Concrete deliverables and dependencies |
| --- | --- | --- |
| 0, alongside the next batch | Verify existing Linux sources | Representative distro/tool/privilege checks for current inventory and policy collectors, within a separate human grant. Preserve actual identities, denied/partial states and cleanup evidence. Most new profiling collectors have synthetic-only verification; old Linux MySQL and ESXi RAID evidence is narrowly scoped, not general native validation. |
| 1–3 | The next batch above | Connection/PID snapshot, bounded incremental authentication/session observations, cron/timer/startup inventory. Supply field selection, required permissions, exact child ownership, Web/history and tests in each step. |
| 4 | Quantitative resource/process telemetry | CPU user/system/iowait/steal breakdown; CPU/memory/I/O PSI where supported; disk IOPS/throughput/latency, network rates, process CPU/I/O/FD/limits and cgroup/unit attribution. Keep counters in producers and implement reusable rate projections with comparable intervals, boot/process/device identity, reset/wrap, clock and denominator checks. Missing prerequisites yield unknown, not zero. |
| 5 | Component identity and storage graph | CPU/RAM/board/firmware/PCIe/USB manufacturing inventory plus supported disk identities/health; explicit device -> partition -> RAID/DM/LVM/LUKS/pool -> filesystem/mount and network-storage edges. Derive links only from actual source evidence; do not guess physical mapping or use MAC/serial as a new Host ID. |
| 6 | Software environments and workload discovery | Kernel/modules/tools; language runtimes and isolated environments/packages; installed/loaded libraries; service/app/DB instance/version/configuration inventory. Use bounded discovery and safe metadata readers, not arbitrary module imports or unrestricted filesystem crawling. Separate unauthenticated discovery from credentialed application queries. |
| 7 | Remaining policy/log/agent depth | Effective login/PAM/key fingerprints and broader privilege context; DNS/network policy detail; complete supported log source/rotation/forwarding roots, audit/SNMP/agent metadata. These deepen partial capabilities rather than merely increasing the catalog count. |

Add explanatory consumers progressively rather than waiting for every source:
configuration diffs when stable fields exist; reset-aware trends after quantitative
telemetry; login/source/time and connection/process rules once their actual events
exist. Keep configured expectations, threshold findings and statistical baselines
separate. Reserve complex seasonal/correlation models for adequate history, and
never label deleted executables, missing TTYs or unusual times malicious by themselves.

### Acceptance criteria for every batch

- Reviewed, bounded read sources; platform/tool/namespace scope; conditional
  login/root routines; no implicit installation, credential retries or remote changes.
- Versioned producer schema, units/object keys, source times/windows and independent
  collection/raw/retention/consumer outcomes. New fields must not rewrite frozen
  schemas, source records, definition digests or historical ownership.
- Successful empty enumeration, incomplete sampling, unavailable, unsupported,
  denied and failed states stay distinguishable. Snapshot absence is not an event.
- Web dish explanations, fields/options, source/permission preview, retained results
  and interpretable consumer views ship with each capability, not afterward.
- Public success/failure/limit/privacy/identity/restart tests and separately scoped
  native verification. This review itself adds no executable collector or schedule.

## Historical review and delivery records

## Reviewed baseline and evidence

Baseline: checkout main at 0784263 plus the uncommitted profiling foundation.
This is static source/descriptor/retention review, not execution against hosts.
The bundle contained seven descriptors at review start; profile/external recipes
are deliberately excluded. Current snapshot probes and historical verification
must not be mistaken for complete platform support.

| Bundled recipe | Actual profiling contribution | Main gap / disposition |
| --- | --- | --- |
| system/inventory/overview 0.4.3 | 72 source-timed properties across eleven jobs: visible machine/OS identity, package lists, mounts/space, interfaces/routes/DNS/listeners/services, Linux resource counters and sensors. | Already integrated; partial component, software, policy and workload coverage. Keep its frozen property/retention definitions. |
| system/storage/inventory/disks-raid 0.4.0 | Controller/physical-drive/virtual-drive/MD/OS-device evidence, roles, spare/standalone counts, separate array health and policy findings. | Acquisition already exists; integrate retained data. No full LVM/ZFS/LUKS/SAN mapping, generic SMART or universally stable physical-to-OS relation. |
| database/mysql/check/replication 0.1.0 | Configured replica instances, server identity/version, authenticated DB identity, channels/lag/filter/health/cleanup evidence. | Acquisition already exists; integrate retained data. Not automatic database discovery, all-engine coverage or source-side consistency verification. |
| system/account/check/identity 0.1.0 | Effective account of one supplied execution session. | Useful actor evidence, not OS account/group enumeration, sudo policy or login eligibility. Do not call it account profiling. |
| system/network/check/port 0.1.0 | One explicitly selected TCP endpoint tested from one host. | Useful point-in-time reachability evidence; not listener discovery, firewall inventory, network topology or connection activity. |
| feast/report/execution-summary 0.1.2 | Presents saved execution results offline. | Consumer/report support; performs no acquisition. |
| feast/report/retention-summary 0.1.0 | Combines retained datasets offline. | Consumer/report support; performs no acquisition. |

## Capability-level baseline matrix

The labels below describe the baseline, before the next acquisition batch. Partial
means some declared fields exist, not that the entire capability is complete.

| Capability | Existing acquisition / integration | Remaining work |
| --- | --- | --- |
| `hardware.identity` | Inventory / integrated | Visible machine manufacturer/model/serial/UUID and virtualization; not full component manufacturing inventory. |
| `hardware.cpu` | Inventory / integrated | CPU model/logical CPU count/architecture; sockets, microcode and topology need deeper probes. |
| `hardware.memory` | Inventory / integrated | Total visible RAM only; DIMM identity, slots and ECC are not integrated. |
| `hardware.expansion` | No integrated provider | PCIe/USB/controllers/enclosures and connection topology are not integrated. |
| `hardware.firmware` | No integrated provider | BIOS/UEFI/BMC/device firmware and Secure Boot are not integrated. |
| `hardware.sensors` | Inventory / integrated | Available Linux thermal-zone and hwmon values only; explicit opt-in and source scope apply. |
| `hardware.health` | No integrated provider | ECC, power, throttling and hardware error events are not integrated. |
| `storage.devices` | Inventory / integrated | Observed block-device columns only; complete serial/controller/path inventory is not implied. |
| `storage.filesystems` | Inventory / integrated | Observed filesystem sources and mounts, not configured mount policy or full filesystem attributes. |
| `storage.topology` | Specialized disk/RAID data exists / integration missing | RAID/LVM/encryption/pools/multipath/NFS/SMB relationships need specialized provider integration. |
| `storage.capacity` | Inventory / integrated | Filesystem space/inodes and swap; no quota/thin-pool/snapshot accounting or growth prediction. |
| `storage.io` | Inventory / integrated | Linux cumulative disk counters only; no automatic rates, saturation diagnosis or latency baseline. |
| `storage.health` | Specialized disk/RAID data exists / integration missing | Specialized disk/RAID recipes exist; their retained data is not integrated into this read model yet. |
| `software.os` | Inventory / integrated | Visible platform/kernel/distribution identity and timezone abbreviation, not full kernel/configuration inventory. |
| `software.packages` | Inventory / integrated | Platform package/receipt/VIB snapshot; not universal application coverage or a full SBOM. |
| `software.environments` | No integrated provider | Per-runtime/per-user/isolated environments and module discovery are not integrated. |
| `software.libraries` | No integrated provider | Installed versus actively loaded libraries and dependency relationships are not integrated. |
| `network.interfaces` | Inventory / integrated | Observed interfaces/MAC/MTU/state/IPv4/IPv6; not full physical or namespace topology. |
| `network.resolution` | Inventory / integrated | Resolver-file nameservers only, not all effective DNS/search/hosts policy. |
| `network.routing` | Inventory / integrated | Platform route rows only; complete policy routing is not guaranteed. |
| `network.listeners` | Inventory / integrated | Platform-visible TCP/UDP endpoints; no external reachability claim. |
| `network.policy` | No integrated provider | Firewall/NAT rules and effective policy relationships are not integrated. |
| `network.connections` | No integrated provider | Inbound/outbound connections, lifecycles and destinations are not integrated. |
| `network.traffic` | Inventory / integrated | Cumulative traffic/error/discard counters; no automatic rates or event history. |
| `workloads.services` | Inventory / integrated | Platform-visible service rows only; application health and dependency discovery are not implied. |
| `workloads.time` | No integrated provider | NTP sources/synchronization/offset/RTC policy are not integrated. |
| `workloads.applications` | Configured MySQL replica data exists / integration missing | Specialized database recipes exist; instance discovery/health integration is not provided by this adapter. |
| `workloads.schedules` | No integrated provider | Cron/timer inventories and execution histories are not integrated. |
| `workloads.processes` | No integrated provider | Process trees/lifecycles/resources/executable provenance are not integrated. |
| `workloads.resources` | Inventory / integrated | CPU/load/available RAM/Linux PSI and uptime; not complete resource accounting or workload attribution. |
| `identity.accounts` | Execution-actor check only / enumeration missing | Host account configuration is separate from observed OS account/group discovery; discovery is not integrated. |
| `identity.authentication` | No integrated provider | Account/PAM/SSH/key policy and effective login eligibility are not integrated. |
| `identity.privileges` | No integrated provider | Effective sudo/su/group/capability policy is not integrated; execution actors are not a privilege inventory. |
| `identity.activity` | No integrated provider | Login success/failure, sessions and privilege-use events are not integrated. |
| `observability.logs` | No integrated provider | Log sources/routes/formats/retention/access and pipeline health are not integrated. |
| `observability.agents` | No integrated provider | SNMP/other agent capabilities and event destinations are not integrated; secrets are not ordinary profile data. |
| `analysis.configuration` | No integrated provider | Cross-domain expected configuration and change analysis are not integrated. |
| `analysis.performance` | No integrated provider | Sampling history is available separately; seasonal baselines and anomaly models are not integrated. |
| `analysis.behavior` | No integrated provider | Cross-source process/connection/login baselines and correlation are not integrated. |

## Delivery order

1. Integrate existing disks/RAID and configured MySQL replica retention without
   rerunning their probes or rewriting historical schemas. Keep health separate
   from collection completeness and preserve source/instance/definition boundaries.
2. Add two independent Linux recipes: local account/group files, and a visible
   procfs process snapshot. Reuse shared bounded SSHScript acquisition and portable
   retention, then use the same profiling Web/CLI read projection. No password/hash,
   command-line or environment capture; no claim of effective login/sudo policy or
   complete process lifecycle history.
3. Add effective SSH/sudo/firewall/time/logging configuration through dedicated
   reviewed parsers; distinguish configured, effective and contextual policy.
4. Add component/runtime/application discovery and deeper storage relationships.
5. Add incremental event sources for connections/authentication/process lifecycle,
   followed by baseline and correlation consumers. Short-lived events require
   actual event sources; snapshots alone do not close those gaps.

Every batch needs declared scope, actor/time evidence, independent failure states,
privacy/output limits, retained contract, shared viewer and reproducible tests.
Optional jobs and target software installation remain separate authorization.


## First batch delivered

The bundle now has nine descriptors. Profiling has five providers / 84 properties
across the same 39 capabilities: 22 partially integrated, 17 not integrated.
The baseline matrix above is retained as the before-change review.

- Existing disks-raid and mysql-replication retention is now integrated with
  data-only adapters, preserving per-source coverage and per-instance query times.
- New system/account/inventory/local-users and system/process/inventory/snapshot
  recipes close the local-file account and visible process-snapshot portions.
- No existing inventory property/schema digest was changed; the two new recipes
  carry separate strict portable definitions. No historical observations migrated.
- Effective login/sudo/firewall/log policy, deeper component/runtime discovery,
  event capture and baseline analysis remain the next substantive gaps. The shared
  catalog's capability scope notes describe these limits explicitly.


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


## Policy/settings batch delivered

Five new independent recipes add SSH/sudo/firewall/time/logging observations using
the existing shared acquisition, portable retention, consumer and Web read flow.
The bundle now has 14 recipes and profiling has 10 providers / 104 properties;
27 capabilities are partially integrated and 12 have no integration. The baseline
matrix remains the before-change record. See [policy scope and verification](linux-policy-profiling.md).

- identity.authentication: sshd -T selected settings, with optional complete Match
  context; no live-daemon generation or full PAM/login eligibility claim.
- identity.privileges: current-actor noninteractive sudo long list; sensitive
  Defaults/command arguments and unsupported details are omitted/flagged.
- network.policy: native nft/legacy saves and runtime/permanent frontend views,
  not cross-backend reconciliation or a proof of external reachability.
- workloads.time: configured sources, clock state, chrony tracking/source and NTP
  peer reports; source/query completeness is separate from synchronization health.
- observability.logs: selected configuration/rotation/log-destination projections
  and journal disk metadata; no event contents or effective config merge inference.

Residual work remains within these partial capabilities: other actors and su/PAM,
SSH startup overrides/key inventory, full frontend policy semantics, alternate
configuration roots, auditd/syslog-ng, complete log-pipeline health and native
platform verification. Deeper hardware/runtime discovery, incremental events and
baseline/correlation consumers are still later work.


## Policy batch delivery checks (2026-11-09)

- Complete local Python 3.14.4 suite: 1,353 passed. JavaScript suite: 75 passed.
- Extracted-wheel smoke: ten provider catalogs, fourteen bundled recipes, shared
  service imports and all five portable policy definitions passed. The target
  probe parses under Python 3.8 grammar; no target Python 3.8 runtime claim follows.
- Synthetic tests exercise configured/context-qualified/runtime basis, native
  ruleset/query formats, credential/script/comment omissions, error categories,
  source/include/output/time bounds, process cleanup and recipe -> retention ->
  consumer -> HTTP projection. Existing inventory/RAID/MySQL retention definitions
  and historical records were not rewritten.
- Chrome desktop used a separate temporary synthetic installation to verify the
  saved SSH values, configured basis, explicit no-Match scope and safe command
  evidence. The temporary QA service was closed afterward. Mobile was not retested.
- The task-owned Web controller closed with zero workers, then resumed with the
  original checkout/interpreter/8741 port/installation data. Homepage, viewer asset
  and authenticated ten-provider catalog returned HTTP 200. No host commands replayed.
- Native Linux OpenSSH/sudo/firewall/chrony/logging tools, managed SSH and actual
  policy applicability remain unverified. No managed hosts, real policies,
  credentials, installed dependencies or schedules were changed by this delivery.

*Last modified: 2026-11-10 17:20:59*
