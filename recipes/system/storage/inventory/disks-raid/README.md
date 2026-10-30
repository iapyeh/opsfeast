# Physical disk inventory and separate RAID checks

`system/storage/inventory/disks-raid` 0.4.0 counts every reported physical disk, including spare, unconfigured, JBOD and standalone disks, independently of virtual disks or RAID membership. Human configuration uses purposes and counts, never a controller FQDD or RAID name. All data and boot disks remain visible with state, use, capacity and reported health; RAID names, levels, capacities and health are a separate view.

## Human-readable configuration

This synthetic host expects four non-boot physical disks, a mirrored boot pair and two RAID volumes/arrays:

```yaml
hosts:
  synthetic-host:
    recipes:
      system/storage/inventory/disks-raid:
        enabled: true
        vars:
          expected_disks:
            data: 4
          boot_policy: mirrored-ssd-pair
          expected_raids: 2
```

No probe is needed to guess configuration keys. `data` means all non-boot physical disks in the supported inventory, including spare/unused/standalone drives across multiple controllers. It does not mean members of one data RAID. If four active drives plus one spare are expected, configure data: 5. SSD media alone does not make a disk a boot disk.

Inputs:

| Variable | Definition |
| --- | --- |
| expected_disks | Optional object containing only data: a nonnegative integer. No hardware IDs or boot count are accepted. Missing data expectation is NOT CONFIGURED; a baseline is never learned from observed occupancy. |
| boot_policy | auto (default), or mirrored-ssd-pair. The explicit policy expects two boot drives even if the whole controller disappears. auto applies two drives per identified BOSS-S1 controller. |
| expected_raids | Optional nonnegative integer, checked independently against hardware VDs plus Linux MD arrays. Zero is valid for intentionally non-RAID storage. |
| raid_cli | auto, or a reviewed absolute local executable path using letters/digits/slash/dot/underscore/hyphen. RACADM executables must be named racadm or idracadm7. |
| require_root | Boolean, default true. Root login runs directly; Linux non-root uses the shared Core root-console policy. |
| command_timeout_seconds | 1–120 seconds, default 20, capped by the runner timeout per command. |

The boot policy is an explicit mirrored-pair policy, not a claim that every server or SSD controller has two drives. BOSS-family source model identification establishes boot role; BOSS-S1 supports the automatic pair policy. Other controllers remain data/unknown as supported source evidence permits. An explicit mirrored-ssd-pair policy records operator intent and detects an absent boot controller without storing its FQDD. It also independently requires a reported RAID-1 volume on each identified boot controller; missing or unrecognized levels leave mirroring unverified, while another reported RAID level fails the policy. Boot disks are never hidden or excluded.

Use default/group/host recipe mappings and the [shared merge rules](../../../../../docs/recipe-sources.md). Each host can have its own data count. Configuration enables future explicit runs, not a schedule or immediate execution.

## Inspect and execute

```sh
.venv/bin/python -B tools/opsfeast.py inspect-recipe system/storage/inventory/disks-raid --json
.venv/bin/python -B tools/opsfeast.py recipes run system/storage/inventory/disks-raid --profile NAME --host HOST --json
.venv/bin/python -B tools/opsfeast.py recipes run system/storage/inventory/disks-raid --profile NAME --host HOST --var 'expected_disks={"data":4}' --var boot_policy=mirrored-ssd-pair --var expected_raids=2 --json
```

Static inspection never connects. Execution requires the approved host/root/query scope and existing configured accounts/jumps. The [entrypoint](main.py) reuses SSHScript 7.0.1, Core verified execution identity and cleanup; it does not recreate connection/credential logic. ESXi root execution uses existing Core identity prerequisites, including systems without id/command shell utilities. Linux non-root requires a compatible Bash root console; no new target software is installed.

## Implementation choice

The [entrypoint](main.py) uses SSHScript 7.0.1 through the supplied Core Recipe session for argv commands, explicit POSIX discovery and bounded output/command deadlines. Core owns verified actors, Linux root acquisition and cleanup; [synthetic tests](../../../../../tests/test_disks_raid.py) exercise those boundaries. Vendor CLIs provide controller-specific facts that OS disk lists cannot supply. The fixed [MD helper](md_probe.py) uses target Python and sysfs without installing mdadm. Public SSHScript API knowledge is the bundled 7.0.1 contract, sourced from [release commit a1c76d0](https://github.com/iapyeh/sshscript/tree/b8d7c8fe88b4096e8a58e6609ba805ee2bf41049); native verification limits are below.

## Collection is physical-first

Dell local RACADM is preferred: fixed `storage get controllers -o`, `storage get pdisks -o` and `storage get vdisks -o` queries. Every physical record comes from pdisks, not by traversing a RAID volume's members. Controller IDs remain source/diagnostic references and RAID display names. They are not settings keys or physical-count boundaries.

A failed or empty RAID query does not discard known physical drives, their capacities, count or source health. Missing controller metadata can prevent data/boot classification without erasing a complete physical inventory. Role-specific expected counts then remain UNVERIFIED. Separate RAID findings remain visible instead of redefining how many physical disks exist.

Auto discovery prefers racadm/idracadm7, then storcli64/storcli/perccli64/perccli. It tests executable files on PATH and under /opt/dell/racadm/bin, /opt/dell/srvadmin/bin, /opt/MegaRAID/{storcli,perccli} and /opt/lsi/{perccli,storcli}. It uses POSIX file tests instead of command -v. A selected provider failure is not silently rescued by a different provider.

PERC JSON queries remain `/call show all J` and `/call/eall/sall show all J`; physical rows include listed spares/unconfigured/JBOD drives. Linux uses explicit-column lsblk JSON and a fixed [python3 MD sysfs reader](md_probe.py). ESXi OS devices use CSV storage core device list. With no supported CLI, LSU can expose RAID-member locations, but cannot verify an all-installed-disk count because spare/unconfigured/standalone devices may be omitted. Such a source stays incomplete for the physical baseline.

RACADM duplicate/malformed records, embedded errors, nonzero exits, timeout and truncation stay failures/gaps. The exact standalone STOR0104 “No virtual disks are displayed” result is a recognized current empty VD view, including a nonzero CLI exit; its original command evidence remains unchanged. It does not prove storage metadata is absent everywhere or that an expected RAID should disappear. expected_raids and boot-mirror checks still detect an unexpected empty view. Additional errors mixed with that result are not accepted as empty success.

## Physical state, use and health

RACADM physical state is distinct from RAID membership. Use is spare when Hotspare/HotSpareStatus indicates it, unconfigured for Ready, standalone for Non-RAID/JBOD, and online when only the online state is known. Online does not assert a specific RAID membership. Every such disk counts once by its physical source identity.

With Status=Ok and RollupStatus=Ok, Online, Ready, Non-RAID/JBOD and recognized hot-spare states support reported physical health. A healthy ready spare is not required to be Online. FailurePredicted=YES overrides a good state. Offline/failed/missing/degraded/rebuilding states and bad status remain unhealthy; unfamiliar/missing evidence remains unknown. Virtual disks require their own good status/rollup and Online state; a Ready physical disk cannot establish RAID health.

Physical purpose groups are data, boot and (when needed) unknown. Data/boot membership is inferred from supported hardware/OS evidence, not from whether the disk belongs to a RAID. Unknown roles are retained, not dropped. Identified BOSS boot drives and an explicit expected boot pair remain checked even if data disks are healthy.

Counts use MATCH, MISMATCH, UNVERIFIED or NOT CONFIGURED. Mismatched or unverified configured counts are critical. Count checks and source health are independent: a complete inventory can report healthy disks while role classification is unavailable, and an unhealthy RAID does not remove its physical disks. Overall health is HEALTHY/UNHEALTHY/UNKNOWN; a verified empty RAID view with no expected arrays is NOT CONFIGURED for RAID health. Linux MD health and controller problems contribute separately.

Critical findings or unknown required health yield a non-success result. Cleanup, execution, retention and content failures remain independent. HEALTHY means reported state passed this check, not a SMART self-test, data-integrity test or universal redundancy guarantee. No repair, RAID configuration, rescan, patrol read, SMART test, software installation, remote-iDRAC login, notification or transmission runs.

## Data contract and display

Recipe/output/portable disks-raid **0.4.0** replaces per-controller count settings. Configure expected_disks, boot_policy and optional expected_raids; remove expected_group_disks, expected_physical_disks and include_boot_devices. There are no aliases or automatic compatibility layers. Existing observations and their saved schemas/policies remain unchanged; recollect for the new independent interpretation.

The [embedded schema](recipe.yaml) defines policy, disk_groups, summary and findings. disk_groups.id/role are data, boot or unknown; expected count/source, physical IDs and observed controller references describe physical inventory only. They have no RAID health or virtual-member list. Physical rows retain role, usage, tray/address, capacity, original fields and interpreted health. Virtual rows independently retain their FQDD/controller name, source name, RAID level, capacity and health. A RAID counter covers hardware VDs and Linux MD arrays, not physical disks or controllers.

The root physical total is the complete reported inventory when available, while count_status rolls up purpose-specific constraints. A known total does not establish which drives belong to data/boot roles. For LSU the observed value is only a lower bound from supported member locations and total stays unknown. Capacities remain exact source strings, including GB; no silent byte conversion occurs.

The Vault leads with physical and RAID counts/health separately, then purpose-group tray/use/state/capacity tables and an independent RAID table. Multiple physical controllers do not require extra count settings; diagnostic subtables disambiguate trays. Expanded source fields use narrow two-column tables. Historical views keep the historical scope/assessment rather than applying today's policy or relabeling an excluded-boot observation as complete.

Raw output, eligible success/partial retention and content publication have separate receipts. Read via Core retention or the CLI, preserving source times, identities, unknown/failure states and provenance. Captured probe streams are bounded to 262144 UTF-8 bytes each; null/empty/truncated remain distinct and privileged PTYs can merge streams. Private serials, host bindings and output stay in the management environment.

## Verification and limits

Run `python -B -m unittest discover -s tests -p test_disks_raid.py`. Public synthetic tests cover friendly settings without FQDD keys, changed hardware IDs, multiple controllers sharing one data baseline, spare/Ready/Non-RAID inclusion and health, physical inventory preserved across RAID/controller-metadata failure, explicit no-RAID storage, independently mismatched physical/RAID counts, boot-pair/controller/mirror failure, malformed/error/truncated output, scopes/identity/root cleanup, MD health, portable retention/replay and narrow/historical Vault rendering.

Native ESXi 7.0.0 with local RACADM 11.0.0 verifies complete physical and RAID reads, data/boot purpose counts, health/capacity, configured data baseline, mirrored-boot policy, independent RAID baseline, jump/SSH, retention and Vault. Native spare/unconfigured/JBOD, Proxmox/Linux RACADM, PERC/StorCLI and su/sudo remain unverified. Their cases are synthetic, not native hardware evidence. ZFS, LVM RAID and additional vendor protocols remain unsupported.

Sources: [Dell RACADM storage interface](https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v5.x-series/idrac9_5.xx_racadm_pub/storage?guid=guid-23586e74-58bd-46af-b1e6-0855a6e43e0c&lang=en-us), [Dell Ready physical-disk example](https://www.dell.com/support/manuals/en-ai/idrac8-with-lc-v2.05.05.05/racadm_idrac_pub-v1/storage?guid=guid-9e3676cb-b71d-420b-8c48-c80add258e03&lang=en-us), [Dell hot-spare status values](https://www.dell.com/support/manuals/en-ed/dell-active-system-manager-v8.2.1/asm%20rest_%20api/hotsparestatus?guid=guid-59a29686-97e0-4d52-9fa0-ba01b6e30022&lang=en-us), [Dell STOR0104 description](https://www.dell.com/support/kbdoc/en-ca/000220599/avamar-gen-5a-storage-controller-failure-eventid-52806).

*Last modified: 2026-10-30 12:17:33*
