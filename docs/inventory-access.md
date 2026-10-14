# Inventory access checks and partitioned results

Inventory-system recipe 0.3.0 adds an access gate and inventory-values contract 0.1.0. Read this guide before execution: selecting inventory now includes connection-account sudo testing by default. These are real connections and authentication attempts, even in dryrun. Login-shell startup, configured proxies and authentication/audit records can have side effects. No installation, target configuration changes, alternate-account su, environment-variable capture, process arguments or arbitrary file crawling is performed.

## Configure the actual connection account

```yaml
hosts:
  example:
    connection:
      hostname: host.example.invalid
      user: operator
    users:
      operator:
        password: synthetic-login-password
        sudo-password: synthetic-sudo-password
```

These examples use synthetic values. Keep credentials in the private Feast. `sudo` and `sudo-password` are optional fields of `users.<account>`; they are not connection fields or recipe variables. SSH aliases select the actual runtime login account. Local connections use the actual local account. Only that account is considered; other declared users are not tested automatically by inventory or check-access.

| Account setting | Meaning |
| --- | --- |
| `sudo` omitted | Attempt and verify sudo to root unless already UID 0 |
| `sudo: "false"` | Disable sudo testing/elevation; ordinary-account collection is intentional and valid |
| `sudo-password` omitted | Use the selected legacy explicit sudo credential, if present; otherwise account `password` |
| `sudo-password: "false"` | Use account `password` directly, bypassing legacy sudo overrides |
| `sudo-password: ""` | Submit an empty password; no fallback |
| `sudo-password: null` or a YAML key with no value | Normalize to an empty password; no fallback |
| Any other sudo-password string | Submit exactly that password; no fallback |
| No selected password | Attempt configured passwordless sudo without interactive input; fail if a password is required |

Only the exact quoted lower-case string `"false"` is a control value. For `sudo`, omit the field to enable; all other explicit values are invalid. Boolean `false`, Boolean `true`, `No`, `0`, `"0"`, `"False"` and `"true"` are not normalized. `sudo-password` accepts only string or null; its other strings are literal passwords. Literal password `false` is therefore reserved in this field. Authentication failure never retries a different password source.

Legacy account `vars.sudo.password`, then host `vars.sudo.password` for the actual connection account, remain supported when the canonical sudo-password field is absent. Their presence uses the same null/empty/`"false"` rule: null/empty select an empty password; `"false"` selects account password. Host credentials are never borrowed for another sudo actor. The existing su credential rules remain unchanged. No stored configuration is rewritten. UI credential masking includes sudo-password.

To deliberately collect as an ordinary account:

```yaml
users:
  operator:
    sudo: "false"
```

Providing a login password does not prove sudo capability. The default policy means **attempt and verify**, not assume permission. Executing this version's check/collection includes those documented sudo attempts; set sudo to `"false"` to opt out. Effective UID 0 is root, regardless of the account name.

## Check access without collection

```sh
python -B tools/opsfeast.py check-access --all --root /srv/feasts/main
python -B tools/opsfeast.py check-access --host web-01 db-01 --threads 2
python -B tools/opsfeast.py check-access --group production
```

Choose `--host`/`--group` **or** `--all`; exclusions require --all. Additional examples:

```sh
python -B tools/opsfeast.py check-access --all --exclude legacy
python -B tools/run_recipe.py inventory/system --all --dryrun
python -B tools/opsfeast.py recipes run inventory/system --all --dryrun
```

Prefer check-access for hosts.yaml access validation and dryrun for a selected inventory invocation. Both share access contract 0.1.0. Check-access validates configuration/connections without inspecting recipe selections. Dryrun additionally statically validates the selected recipe and invocation inputs. No recipe collection, platform discovery/cache writes, identity inventory, raw inventory or retained records are created. JSON stdout is the test report; redirect it to a private file if persistence is wanted. Config checks alone do not connect, and access checks do not prove every declared user, command-specific sudo policy, recipe platform support or hardware visibility.

The test follows configured jump hosts, verifies actual login UID/name, enters the same root shell used for collection when enabled, verifies UID 0, exits and verifies original identity, then checks Session cleanup. It checks root-shell access, not sudo permissions limited to individual commands. SSHScript's authenticated console requires Bash and id. Supplied passwords may not be consumed when policy/cache permits entry; success cannot prove a password's correctness independently of that policy/cache. Every selected test runs even after another fails. Exit 0 means all selected targets passed; failed or explicitly skipped targets return 1. `--root` and `--profile` are mutually exclusive. `--timeout` is positive/finite, default 30 seconds per stage, not an entire invocation deadline. `--threads` is positive, defaults to 1 for check-access; dryrun uses the runner concurrency default. Disabled/excluded hosts are not contacted.

## Gate and force behavior

Before inventory, validate all selected inventory recipes/inputs, then complete all access tests. Any required access failure rejects the entire batch before inventory starts. No result/retention file is fabricated for rejected targets. The test report includes connection/identity evidence, sudo state and credential-source names, restoration/cleanup states and times, without credential values or third-party exception text.

`--force` permits unavailable connections to be skipped, and a failed sudo test to use the verified original account. It does not bypass malformed settings, unknown targets, path/manifest/runtime checks or uncertain identity/cleanup. A failed preflight sudo is not retried during collection. A successful test is time-local evidence: collection revalidates identity and re-enters root; a later sudo rejection stops that host unless force allows verified fallback. A later transport loss is skipped under force after successful cleanup, otherwise failed. A later collection or cleanup failure remains failed. Previously completed results are preserved; this is not an atomic batch transaction.

Dryrun and force are mutually exclusive and apply only to enabled inventory-system recipes. Generic operation/report execution retains its existing privilege scope; force/dryrun are not saved-job fields. Saved inventory jobs still run through the default gate and current account settings; changed recipe content invalidates pinned jobs. Batch JSON includes access_checks and counts for root/user/fallback_user/skipped/failed. Raw inventories record access and the preflight report when available. A forced fallback retains collection results but returns nonzero; force authorizes continuation, not a success claim. Missing optional inventory fields alone do not fail a completed core inventory.

## Separate results and execution evidence

Raw result 0.2.0 and retained/exchange 0.1.0 keep their seven-field compatibility interface. The new independently versioned extension has:

- `inventory_contract_version: "0.1.0"` and `inventory`: six fixed sections with typed values only. Missing results are JSON null, regardless of the reason. Zero and empty lists remain meaningful values. Nothing substitutes an error message for a value.
- Raw-only `collection_process`: scope, times, limits and per-query source commands, states/reasons. Existing observations/sources/execution_errors remain the compatibility execution evidence; consumers wanting pure results read inventory.
- Raw-only `access` and `access_check`: actual account/effective UID, expected sudo policy, credential-source names, verified restoration and degraded mode. Never passwords.
- Retained/exchanged `collection_scope`: only mode and effective_uid, necessary to interpret visibility. Process diagnostics, command sources, stdout/stderr and credential sources are excluded from the retained extension.

Old records without the extension remain valid. Older strict consumers must update before accepting new extension-bearing records. SQLite stores the extension in the existing JSON payload; its seven-column compatibility view is unchanged. Query `json_extract(payload, '$.inventory.hardware.memory_total_bytes')` for a new scalar. Export/combination preserve the new extension and independent histories; a repeat with another account is a new observation, never an overwrite or an automatic merge of nonempty fields. Identity quality/warnings and original observation times remain mandatory context.

## Inventory-values 0.1.0 field catalog

All sections/fields exist on every supported platform. Unsupported, denied, failed, timed-out, truncated or unparseable results are null; the process report distinguishes reasons. This is a bounded extensible union of implemented probes, not every readable byte on a POSIX machine.

| Section | Fields and units |
| --- | --- |
| system | hostname, platform, system_name, system_version, kernel_name, kernel_release, architecture (strings); uptime_seconds (nonnegative number); timezone (date abbreviation, not an IANA zone); virtualization (tool-reported string) |
| hardware | cpu_model, vendor, model, serial, uuid (strings); logical_cpus (nonnegative integer); memory_total_bytes (nonnegative integer) |
| storage | filesystems and block_devices (lists of rows) |
| network | interfaces, routes, dns_servers, listening_endpoints (lists of rows) |
| software | packages (list of rows) |
| services | services (list of rows) |

The machine-readable schema is [inventory-values](../schemas/inventory-values.schema.json). Units are encoded in field/column names. Filesystems use df -Pk, with capacities converted from KiB to bytes; rows include source, total_bytes, used_bytes, available_bytes, used_percent and mountpoint. Paths with spaces in source names may fail parsing rather than produce guessed columns. Linux devices use lsblk JSON, bytes, with name/type/size/fstype/mountpoint/model. Linux interfaces flatten ip JSON addresses with name/mac/mtu/state/address/prefix_length; BSD/macOS interfaces contain name/kind/address. Linux routes preserve documented selected scalar keys; BSD/macOS routes preserve platform entry lines. DNS rows have address. Linux listening endpoints have protocol/state/recv_queue/send_queue/local/peer and do not include process ownership/arguments.

Linux packages use dpkg-query or RPM name/version rows; unsupported package managers remain null. FreeBSD packages use pkg query -a name/version. macOS packages are Installer receipt IDs with version null and kind installer-receipt; this is not a complete application inventory. Linux services contain name/load/active/sub/description; FreeBSD service -e yields enabled script names, not health; macOS launchctl list yields the current launchd domain's pid/exit_status/name, not a universal service-health check. ESXi tables preserve platform entry lines for interfaces, VIBs and chkconfig services; they are not normalized Linux tables. Richer normalization and unsupported probes need a future contract revision.

| Platform | Extra sources and current gaps |
| --- | --- |
| Linux | proc uptime/cpuinfo/meminfo, getconf, DMI files, lsblk, ip, ss, dpkg-query/RPM, systemctl, resolv.conf, systemd-detect-virt |
| FreeBSD | sysctl CPU/memory/boot time/disks, kenv SMBIOS, ifconfig, netstat, pkg, service -e, resolv.conf; virtualization/listeners not implemented |
| macOS | sysctl CPU/memory/model/boot time, ifconfig, netstat, pkgutil, launchctl, resolv.conf, existing ioreg identity; block devices/virtualization/listeners not implemented |
| ESXi | esxcli CPU/interfaces/VIBs, chkconfig and existing identity; unsupported fields remain null |

Missing tools do not trigger installation or speculative alternate probes. Logical CPU counts and memory describe the API's visible scope, which can differ from affinity/cgroup quotas; they are not guaranteed workload allocations. Container/jail/net namespaces can change hostname, devices, routes and services. macOS resolv.conf is a file snapshot, not complete scoped resolver policy. Root does not remove namespace restrictions or guarantee every probe works. Hardware identity is not an OS-installation identity.

Extended probes use a default 90-second shared budget (`--var collection_budget_seconds=90`), per-command timeout, 262144-byte stdout limit and 2000-row limit. Target-side head bounds captured stdout; command completion markers detect producer failure. Over-limit data stays null, not a plausible incomplete list. These bounds are for extended queries, not connection/discovery/core/identity/cleanup or the entire run. Channel closure still does not prove remote-process termination. Raw-only process evidence preserves budget exhaustion and truncation; root queries are read-only but may consume resources or wait on mounted filesystems.

## CSV and reports

```sh
python -B tools/observation_store.py export --profile main --format csv > inventory.csv
python -B tools/observation_store.py export --profile main --format json > inventory.json
```

CSV is a long-form inspection export, not the JSON exchange format. Columns include observation_id, host_id, observed_at, identity_quality, collection_mode, effective_uid, section, field, item, attribute and value. Missing values produce empty CSV cells, never the string NULL. Zero stays zero. An observed empty list is represented as [] to distinguish it from missing data. Each table item/attribute has its own row; old seven-field records are projected into an otherwise empty partitioned result. Spreadsheet formula-looking strings receive a leading apostrophe. CSV does not preserve all JSON types or full provenance; use JSON for validated exchange/re-ingestion. Standard JSON export does not transmit data. Exported addresses, serials, paths, packages and services can be sensitive; select/review before authorized sharing.

The bundled report/summary displays partitioned values and collection scope alongside compatibility evidence. It does not reconnect or refresh inventory. Custom report recipes can query inventory by section and must preserve null, scope, identity warnings and source times.

## Verification and migration

Synthetic tests cover credential presence/control values, default/passwordless/disabled/root modes, access gate, dryrun, forced skip/fallback, no retry, restoration and Session cleanup failures, collection-time sudo rejection, all platform parsers, budgets/truncation, retention/exchange and empty-cell CSV. Native SSH, sudo policy, FreeBSD/Linux/ESXi extended collection remain unverified; historical macOS evidence predates this extension. Documentation/command sources include the bundled SSHScript 5.0.0 public contract, [Linux proc documentation](https://www.kernel.org/doc/html/latest/filesystems/proc.html), [FreeBSD pkg query](https://man.freebsd.org/cgi/man.cgi?query=pkg-query&sektion=8), and platform manuals. A successful synthetic test is not real-host applicability evidence.

Migration: ordinary accounts previously usable without sudo testing now need sudo: "false" when intentional. Empty/null explicit sudo credentials now select empty passwords; use the exact string "false" to request account-password fallback. Legacy identity_sudo remains accepted for descriptor compatibility but does not choose collection privilege or bypass the gate; account sudo policy controls the new workflow. New export extensions require updated strict validators. No private hosts.yaml, registrations, records or environments are automatically migrated.

Delivery verification on 2026-10-14: Python 3.11.15, 3.13.13 and 3.14.4 each passed 415 public synthetic/UI tests. The 3.11/3.13 suites reused the shared pure-Python dependency tree; this does not validate their native SSHScript dependency stack (the native cffi backend was unavailable for those interpreters). The selected 3.14 environment passed dependency/import-distribution checks and a credential-free local Session command with strict cleanup. AST/schema structure, synthetic retained/exchange examples, skill frontmatter, complete guide YAML and 39 added local documentation links passed. No native sudo or real SSH/host inventory was run.

_Last modified: 2026-10-14_
