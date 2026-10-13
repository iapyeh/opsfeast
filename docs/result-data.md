# Result retention, identity and exchange

OpsFeast separates four data needs. Stage 1 is raw execution evidence; stage 2 is retained business observations; stage 3 is a selected exchange of those observations; stage 4 is the recipient's query, chart or reporting store. Stage 4 is not implemented and does not require SQLite. No central service, transmission or company asset registry is required for stages 1–3.

The inventory runner now performs stage 1 → 2 after every completed report. Humans and agents invoke stage 2 → 3 explicitly. Exporting creates data; it does not send it to anyone. See the [CLI reference](cli.md#retained-observations-and-exchange) and [result-data skill](../skills/opsfeast-result-data/SKILL.md).

## Contracts and storage

| Stage | Implemented contract | Storage |
| --- | --- | --- |
| Raw report | inventory-system result 0.2.0, with optional identity evidence 0.1.0 and retention receipt | `observations/inventory-system-<uuid>.json` |
| Retained observation | [0.1.0 schema](../schemas/retained-observation.schema.json) | `records/observations.sqlite3` within each Feast |
| Exchange | [0.1.0 schema](../schemas/observation-exchange.schema.json) | Explicit JSON stdout/file selected by the user |
| Analysis | Recipient-selected | DuckDB, SQLite or another consumer; no bundled importer |

SQLite is the first local stage-2 implementation, using Python's standard library. It is not an exchange-format requirement. Database `user_version=2` identifies this physical layout; contract versions identify data independently. Python 3.11+, PyYAML and SQLite JSON functions are required. Existing environment checks remain applicable; the tests exercise JSON SQL views with the chosen interpreter.

`metadata` stores a persistent `source_id` UUID. `observations` contains indexed identity, recipe, time and state columns plus the canonical retained JSON payload. `inventory_system` exposes the seven inventory values and their statuses as SQL columns. There is no automatic latest-state view: partial data, identity conflicts and old observations must not disappear behind a guessed latest record. This database is operational data, not a Git artifact or a replacement for human records.

Transactions serialize local writers with a 30-second database-lock timeout. Schema initialization and insertion happen in one transaction. Export is read-only and never initializes a missing database. Symlink directories, database files and SQLite sidecars are rejected. Concurrent access across network/shared filesystems or editing the live database through cloud synchronization is not supported. Keep the live database local; exchange exported JSON. Backup or move the complete Feast using an appropriate SQLite backup procedure while coordinating writers. A copied database retains the same source identity: it is a continuation, not a new independent Feast. Do not copy it to seed independent A/B installations.

## Stage 1 → 2: automatic retention and recovery

The runner closes its Session, finalizes the report, atomically saves raw JSON, then invokes the trusted inventory-system adapter. It saves a receipt back into the raw report and includes it in stdout. The receipt is excluded from observation-ID calculation so replay is idempotent. Atomic raw writes prevent readers from seeing a partially serialized final file; a process crash can still occur between stages.

Only operational `local`/`ssh` reports with status `success` or `partial` are retained. Mock/non-operational, failed, skipped and unsupported reports are excluded. Disabled hosts/sources still produce no raw inventory file. A partial report retains all seven fields, including null/missing states; it is never promoted to complete inventory. Identity fallback does not by itself fail otherwise successful collection. A failure to establish privilege-context cleanup fails execution and excludes that report from retained observations.

Retained records omit commands, stdout/stderr, connection details, credentials, paths, error text, input values and raw report receipts. They retain recipe version, raw schema version, evidence kind, source/target identity, observation state and timestamp. Device identifiers are intentionally shareable business data, but may be sensitive; review the export before delivering it.

`observation_id` is `<source UUID>:<SHA-256 of canonical raw report excluding retention>`. Reprocessing identical raw content within its originating Feast does not duplicate it. Modifying raw content creates a new observation; this is not an authenticated audit ledger. If a raw file carries a successful source receipt, another source cannot re-ingest it as its own: use structured exchange instead. Old raw files without a receipt are attributed to the explicitly chosen local source, so do not use raw ingestion for sharing.

A failure to persist the receipt also preserves the initial raw file and returns a receipt_save_failed summary; replay deduplicates any already committed observation. Retention failure preserves raw evidence, adds `retention.status=failed`, prints a sanitized warning and makes the runner return 1 even if collection status is success. Replay does not reconnect or re-run a recipe:

```sh
python -B tools/observation_store.py ingest /path/to/raw-result.json --profile main
```

Repeat paths to recover selected files. The entire eligible batch is validated before any mutation, then inserted transactionally. Unknown contracts, malformed fields, conflicting IDs or database versions fail explicitly. Excluded results report skip reasons. No automatic directory scan or retention/deletion policy is implemented.

## Host identity: an OS installation, not an address

A host means an OS installation instance. Reinstalling/changing the OS defines a different host, even on the same equipment; normal upgrades, IP and hostname changes do not. Change a user-assigned identity_key after reinstall/replacement. Automatic evidence may not detect a reinstall when identifiers are preserved, and source-scoped fallback cannot establish continuity; those are identification limitations, not exceptions to this definition. Hardware serial/UUID identifies equipment or a VM, not an OS installation. Do not construct identity from IP, hostname, OS version or a hash of every available field.

The current best-effort implementation is deliberately explicit about evidence limits:

| Platform | Non-root probes first | OS installation identity |
| --- | --- | --- |
| Linux | `/etc/machine-id`; DMI system serial and product UUID | Application-specific HMAC-SHA-256 of valid machine-id, quality `machine-derived` |
| FreeBSD | `kenv -q smbios.system.serial` and `smbios.system.uuid` | No verified native installation identifier; fallback |
| macOS | XML plist from `ioreg -a -r -d 1 -c IOPlatformExpertDevice` | Hardware serial/UUID only; fallback |
| ESXi | `esxcli hardware platform get` | Hardware serial/enclosure serial/UUID only; fallback |

Linux machine-id is a candidate, not proof of uniqueness: copied images can duplicate it and a reinstall can preserve it, including firmware-derived initialization. We do not modify the target or generate installation markers. The original Linux machine-id is not retained in identity output; the application-specific digest is shared so independent collectors can compare it. Hashing is not authentication or a guarantee of anonymity.

Missing/invalid/placeholders remain explicit evidence states. Hardware firmware data may be inaccurate. VMware guests may expose a duplicated BIOS UUID or the physical host's serial via `SMBIOS.reflectHost`; never merge them solely on that basis. ESXi is an independent implementation, not a Linux collector. Shell commands have synthetic verification only; vSphere API collection is not implemented. ESXi `system_version` retains the full `vmware -v` line, so numeric version-match conditions require a future normalized contract.

When no supported OS identifier is found, use `fallback:<source UUID>:<SHA-256 of local host_id>`, quality `fallback`. Local host_id remains unchanged in the record. Different Feasts' same-name hosts remain distinct. Reusing a local host_id after replacement cannot be detected reliably under fallback; do not interpret that history as proven continuity. Successful hardware evidence alone never upgrades fallback to an OS identity.

Every fallback emits a runner warning, raw identity warnings and retained `identity_warning`. To resolve it, inspect the probe states: supply authorized sudo capability when permission is the cause, correct the local platform prerequisites, or keep the host unresolved when no native installation identifier is supported. FreeBSD/macOS/ESXi currently remain fallback even when serial collection succeeds. Do not promise sudo will resolve those installation-identity gaps. No automatic historical reassignment is performed when a later report obtains stronger evidence; reviewed alias/identity mapping remains a future operation.

### Sudo selection and authorization

All fixed probes first run under the connection account. If probes fail and an explicit sudo password is configured in the actual account's `vars.sudo.password` or host `vars.sudo.password`, that supplied capability enables one root sudo context. A login password alone does not opt in. Existing credential precedence applies: account sudo password → connection-account host sudo password → account password. Credentials and third-party error text are never retained in identity reports.

Recipe input `identity_sudo: false` explicitly disables elevation; `identity_sudo: true` enables the existing login-account sudo/passwordless policy. It authorizes only the documented read-only identity probes and requires the user's actual execution scope. Example host recipe configuration:

```yaml
recipes:
  - recipe: inventory/system
    vars:
      identity_sudo: true
```

The runner does not enumerate other sudo actors or su to another configured account. It verifies root identity and return to the original account. Missing capability, rejected entry or failed probes can degrade to fallback after verified restoration; unknown or failed cleanup is execution failure. These console/root identity checks require standard `id` support; failure remains explicit. Sudo is not attempted merely because a document suggests it.

## Stage 2 → 3: selection, validation and combination

```sh
# A and B execute this against their own selected Feast.
python -B tools/observation_store.py export --profile main \
  --recipe inventory-system --host web-01 db-01 \
  --since 2026-10-01T00:00:00+08:00 \
  --until 2026-10-14T00:00:00+08:00 > inventory-share.json

# Validate before authorized delivery.
python -B tools/observation_store.py validate inventory-share.json

# C combines received stage-3 files, without accessing A/B credentials or raw files.
python -B tools/observation_store.py combine a-inventory.json b-inventory.json > company-inventory.json
python -B tools/observation_store.py validate company-inventory.json
```

`--host` uses exact local host IDs and `--recipe` uses the recipe ID (`inventory-system`, not its directory selector `inventory/system`). No filters exports all retained records. Time bounds are inclusive and select the report completion time; field observation times remain separately available. Input timestamps require timezone and are normalized to UTC with six fractional digits. Empty selections are valid empty exchanges; they do not prove an empty company inventory. Output sorts by completion time, then observation ID. Export timestamps describe packaging, not collection.

Exchange carries contract/version metadata and retained records only. Strict validation rejects unknown keys/contracts, invalid states/timestamps, duplicate IDs and invalid identity keys. Combination validates all inputs, removes identical repeated observations and rejects same-ID/different-content conflicts. It retains distinct observations, even for matching host keys. No observation is overwritten, and no latest-state or conflict-resolution policy is guessed. Hardware conflicts for a matching machine-derived key must be reviewed before grouping records as one host. Equal-time differing observations remain separate.

For stage 4, a recipient can ingest the validated records into DuckDB, SQLite or another tool following the published schema. Use host keys as identity candidates with their quality/warnings; preserve source IDs, observation IDs, statuses and times. Do not merge fallback hosts across sources, treat null as zero, or infer host removal from absence. Authentication of publishers, automatic transport, receiver database import, charting and company-wide asset reconciliation are not implemented.

## Recipe extension contract and verification

The bundled descriptor advertises retained/exchange contract 0.1.0 and `inventory-system-v1`. The runner's trusted adapter currently supports only inventory-system raw schema 0.2.0. Legacy descriptors without these additive declarations use that same known adapter. Other recipe IDs/contracts fail rather than silently dumping arbitrary raw JSON into shared data. New adapters require reviewed code, a versioned retained schema, extraction/partial/failure/identity rules, synthetic fixtures and updates to the recipe skill and this capability guide. There is no dynamically executed adapter path. [Execution/report result queries](recipe-experience.md#results-and-artifacts) provide a separate raw-run index and offline report artifacts; they do not change inventory identity, extraction or exchange rules. [General Python-session execution](recipe-execution.md) saves raw JSON and explicitly skips retention; it does not route other recipe IDs into this inventory adapter.

Automated tests cover non-root/sudo/fallback paths, credential omission, platform parsers, ESXi dispatch, retention replay/concurrency/rollback, filtered exports, two-source combination, conflicts, malformed exchanges and stage-2 recovery. Real SSH, sudo policies, ESXi and hardware identity uniqueness remain unverified. Source documentation: [systemd machine-id contract](https://github.com/systemd/systemd/blob/main/man/machine-id.xml), [Linux DMI](https://github.com/torvalds/linux/blob/master/drivers/firmware/dmi-id.c), [FreeBSD SMBIOS](https://github.com/freebsd/freebsd-src/blob/main/stand/libsa/smbios.c), [Apple serial lookup](https://support.apple.com/en-us/102767), [ESXi platform information](https://knowledge.broadcom.com/external/article/384493/hardware-information-in-esxi-host-summar.html) and [VMware serial reflection](https://knowledge.broadcom.com/external/article/313985/virtual-machines-are-having-the-same-ser.html). These live sources are reference evidence, not pinned or real-host verification.

## Explicit identity and display metadata

A host-level identity_key provides a cross-Feast identity assertion. Priority is configured identity_key → native OS candidate → source-scoped host_id fallback. Its retained method is configured-identity-key-v1, quality user-assigned, and host_key is user: followed by SHA-256 of the exact UTF-8 key. The original identity_key is included in retained/exchange records to make the assertion inspectable; it must not contain secrets. Native/hardware probes still collect supporting evidence but do not override the user's assertion. Coordinate namespaces across installations and rotate the key after reinstall/replacement. No historical observations are reassigned.

Host label and description are human-authored display text. label is preferable to caption for a reusable host label; it is not a lookup key. Raw host_metadata records the supplied strings; retained/exchange records contain optional label/description fields. Empty/missing label falls back to local host_id in the SQL view. Values are observation-time snapshots; A/B differences remain separate and do not affect identity. Treat text as data and escape it when rendering HTML or other report formats.

The draft retained/exchange 0.1.0 contract now permits these optional fields and the explicit identity method. Old records without them remain valid; consumers with the older strict validator must update before accepting user-assigned records. Database physical version is now 2. A write transaction upgrades a version-1 view while preserving its source UUID and all observation payloads; read-only export accepts versions 1/2 and does not migrate. Human notes outside these captured metadata fields are untouched.

MAC addresses may be useful network-interface evidence but are not automatically used as fallback keys. They identify an interface, can remain unchanged across OS reinstall, and may be cloned, changed or randomized. Multiple interfaces also require an explicit selection rule. MAC collection is not implemented by this change. A manually assigned MAC-based identity_key remains a user assertion and needs an installation-specific component/rotation policy. Reference: [Apple private Wi-Fi addresses](https://support.apple.com/en-ie/102509), [NetworkManager address configuration](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/settings-802-11-wireless.html).

_Last modified: 2026-10-13_
