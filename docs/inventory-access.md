# Inventory access checks and partitioned results

Inventory-system recipe 0.3.0 adds an access gate and inventory-values contract 0.1.0. Read this guide before execution: selecting inventory now includes connection-account sudo testing by default. These are real connections and authentication attempts, even in dryrun. Login-shell startup, configured proxies and authentication/audit records can have side effects. No installation, target configuration changes, environment-variable capture, process arguments or arbitrary file crawling is performed.

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

These examples use synthetic values. Keep credentials in the private Feast. `sudo` and `sudo-password` are optional fields of `users.<account>`; they are not connection fields or recipe variables. SSH aliases select the actual runtime login account. Local connections use the actual local account. Inventory/dryrun considers only that account. The explicit check-access command additionally tests other declared users through independent su and enabled sudo, as described below.

| Account setting | Meaning |
| --- | --- |
| `sudo: true` or `sudo` omitted | Attempt and verify sudo to root unless already UID 0 |
| `sudo: false` | Disable sudo testing/elevation; ordinary-account collection is intentional and valid |
| `sudo-password` omitted | Use the selected legacy explicit sudo credential, if present; otherwise account `password` |
| `sudo-password: "false"` | Use account `password` directly, bypassing legacy sudo overrides |
| `sudo-password: ""` | Submit an empty password; no fallback |
| `sudo-password: null` or a YAML key with no value | Normalize to an empty password; no fallback |
| Any other sudo-password string | Submit exactly that password; no fallback |
| No selected password | Attempt configured passwordless sudo without interactive input; fail if a password is required |

The `sudo` field accepts only Boolean values: `false` disables sudo; `true` or omission enables it. Strings (including `"false"` and `"true"`), numbers (including 0/1), null, lists and mappings are invalid. Values are validated by parsed type without string/number coercion. For `sudo-password`, the exact quoted lower-case string `"false"` remains the account-password fallback control value. `sudo-password` accepts only string or null; its other strings are literal passwords. Literal password `false` is therefore reserved in this field. Authentication failure never retries a different password source.

Legacy account `vars.sudo.password`, then host `vars.sudo.password` for the actual connection account, remain supported when the canonical sudo-password field is absent. Their presence uses the same null/empty/`"false"` rule: null/empty select an empty password; `"false"` selects account password. Host credentials are never borrowed for another sudo actor. The existing su credential rules remain unchanged. No stored configuration is rewritten. UI credential masking includes sudo-password.

To deliberately collect as an ordinary account:

```yaml
users:
  operator:
    sudo: false
```

Providing a login password does not prove sudo capability. The default policy means **attempt and verify**, not assume permission. Executing this version's check/collection includes those documented sudo attempts; set sudo to Boolean `false` to opt out. Effective UID 0 is root, regardless of the account name.

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

Prefer check-access for hosts.yaml access validation and dryrun for a selected inventory invocation. Both share access contract 0.1.0. Check-access validates configuration/connections without inspecting recipe selections. Dryrun additionally statically validates the selected recipe and invocation inputs. No recipe collection, platform discovery/cache writes, identity inventory, raw inventory or retained records are created. Check-access defaults to a tabulate table with status, host, test, user and reason columns; inventory dryrun retains its JSON output. For the complete check-access report, use --json and redirect stdout to a private file if persistence is wanted. Config checks alone do not connect. Check-access tests declared accounts only; skipped accounts remain unverified. Neither workflow proves command-specific sudo policy, recipe platform support or hardware visibility.

Check-access prints flushed progress to stderr before checking each host and after it finishes, even when stdout is redirected. Parallel progress follows actual completion order; the final stdout summary preserves selection order. Progress names the host/account; the table user column names the login for connection, the target account for su, and the actor for sudo. The sudo target remains root. Before identity verification, the configured connection user is shown; `unresolved` means the account is not yet known (for example, local or SSH-config-based login). If connection/identity verification fails, the configured name is only a requested account, not verified identity. The final summary has one row per connection/su/sudo test; a failure is prefixed with ❌. Totals count hosts: any failed account makes its host failed; otherwise any skipped account makes its host skipped. A host passes only when all its account checks pass.

Example final stdout with synthetic targets:

```text
╭──────────┬────────┬────────────┬──────────┬─────────────────╮
│ status   │ host   │ test       │ user     │ reason          │
├──────────┼────────┼────────────┼──────────┼─────────────────┤
│ PASS     │ web-01 │ connection │ operator │                 │
│ PASS     │ web-01 │ sudo       │ operator │                 │
│ PASS     │ web-01 │ su         │ appuser  │                 │
│ PASS     │ web-01 │ sudo       │ appuser  │                 │
│ ❌ FAIL  │ web-01 │ su         │ auditor  │ su_entry_failed │
│ SKIP     │ web-01 │ sudo       │ auditor  │ su_failed       │
╰──────────┴────────┴────────────┴──────────┴─────────────────╯
Hosts: 0 passed, 1 failed, 0 skipped, 0 excluded
```

Check-access independently tests each `users` entry other than the verified login name, in configuration order. It uses the existing diagnostic su credential precedence (target vars.su.password, then target password, preserving empty values); it never borrows another actor's host/login credentials or retries a rejected password. After verified su, it tests sudo to root as that user unless the account has `sudo: false`. Sudo uses the canonical actor-scoped credential rules above, including passwordless policy when no password is selected. A sudo-disabled account passes when su, identity restoration and cleanup pass; disabling sudo is not a failed or skipped account check. Missing su credentials instead yield SKIP/missing_su_password and no sudo attempt. No passwordless su probe is added. This scope includes additional authentication attempts; invoking this version of check-access selects all these declared-account checks.

Each additional actor uses fresh Sessions through the existing `privilege_test` implementation, including a login identity probe and a fresh independent su/sudo group. It verifies the su target, elevated identity, return to the original login and cleanup. Failed su prevents sudo; other independent accounts and hosts continue. Login sudo failure still permits other account checks when login identity/restoration/cleanup are verified. Failed login, unknown restoration or login cleanup failure leaves other accounts skipped with login_unavailable/login_cleanup_unverified. No shared failed console is reused. Progress shows each account before its check and its outcome, then a host completion count; a failed extra account does not relabel the successful login row as failed.

The rounded-outline table is rendered by tabulate 0.10.0. `requirements-init.txt`, package metadata and pyproject.toml declare `tabulate[widechars]==0.10.0`; the extra installs wcwidth for Chinese/Japanese/Korean names and the ❌ marker. Column values remain text, preserving leading-zero IDs; control characters remain escaped. Wide or long names expand the table rather than being truncated. Progress remains line-oriented on stderr, the Hosts: footer counts hosts, and --json retains its existing structured output. Missing tabulate/wcwidth rejects text-mode checks before connection; use the selected interpreter's environment check and an authorized requirements installation. A package installed in another interpreter does not satisfy this one. No installation or environment upgrade is performed by the CLI. Both init/full environment checks report these base display dependencies. See the [upstream Unicode support](https://github.com/astanin/python-tabulate#wide-fullwidth-cjk-symbols).

Each PASS applies only to that test: connection includes login identity verification, su verifies the target identity, and sudo verifies root identity. Failed su produces SKIP/su_failed for enabled sudo; missing su credentials produce SKIP/missing_su_password for su. Disabled sudo produces SKIP/sudo_disabled and an already-root login produces SKIP/already_root; these intentional policy skips do not fail an otherwise verified host. Restoration and cleanup failures appear as separate restoration/cleanup rows, preserving earlier successful test rows. Successful internal reconnects are not repeated as connection rows; a failed reconnect or its identity check is shown explicitly, followed by skipped dependent tests. Hosts: totals and the exit code retain the aggregate host outcome; a test PASS alone does not prove the whole host passed. Minimal legacy display inputs without connection evidence use an access row instead of inventing test-specific success. FAIL includes the short reason code; use --json for connection, identity, sudo and cleanup evidence. SKIP is not verified access. Under --all/group selection, disabled targets appear as EXCLUDED with host_disabled; explicit --host selection produces SKIP instead. CLI exclusions show cli_excluded. Exclusions are counted separately and do not fail otherwise successful selected checks. An entirely filtered selection remains an error before connection.

```sh
python -B tools/opsfeast.py check-access --all --quiet
python -B tools/opsfeast.py check-access --all --json --quiet > access.json
```

Migration: scripts that parsed the previous default JSON must add --json; --quiet suppresses only stderr progress, not the final stdout report. The login access contract remains 0.1.0 with an additive per-host configured_user field (null when absent); verified login identity remains access.connection_identity. Check-access adds accounts in display order: user (nullable until login is known), role (login/su), status and reason_code. Additional attempted accounts retain full diagnostic evidence in checks and sudo policy as enabled/disabled. The login row references existing top-level access evidence; the host status aggregates all rows. No separate account list is added to inventory preflight/dryrun reports. Runner dryrun/gating output is unchanged. The optional check_many(..., progress=callback, include_users=True) checkout helper enables the CLI account scope and calls callback(stage, report) at start/account_start/account_finish/finish in worker threads; callers must serialize shared output and avoid raising from callbacks. include_users defaults to False for existing library/runner callers; no callback means no progress output. This helper is not a versioned public Core API.

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

Migration: account `sudo: "false"` is no longer accepted; change it explicitly to `sudo: false`. `sudo: true` is also accepted. This change does not alter `sudo-password: "false"` or legacy credential fallback markers. No private configuration is rewritten automatically. Ordinary accounts previously usable without sudo testing now need sudo: false when intentional. Empty/null explicit sudo credentials now select empty passwords; use the exact string "false" to request account-password fallback. Legacy identity_sudo remains accepted for descriptor compatibility but does not choose collection privilege or bypass the gate; account sudo policy controls the new workflow. New export extensions require updated strict validators. No private hosts.yaml, registrations, records or environments are automatically migrated.

Delivery verification on 2026-10-14: Python 3.11.15, 3.13.13 and 3.14.4 each passed 415 public synthetic/UI tests. The 3.11/3.13 suites reused the shared pure-Python dependency tree; this does not validate their native SSHScript dependency stack (the native cffi backend was unavailable for those interpreters). The selected 3.14 environment passed dependency/import-distribution checks and a credential-free local Session command with strict cleanup. AST/schema structure, synthetic retained/exchange examples, skill frontmatter, complete guide YAML and 39 added local documentation links passed. No native sudo or real SSH/host inventory was run.

Check-access display verification on 2026-10-15: Python 3.11.15, 3.13.13 and 3.14.4 each passed all 460 public synthetic/UI tests, including wheel/sdist boundary checks. The older interpreters reused the selected environment's pure-Python dependencies; native dependency readiness was checked only on 3.14. Concise/JSON/quiet output, progress-before-check ordering, parallel completion, failures/skips, unresolved accounts, exclusions and terminal controls are covered. AST, skill frontmatter, document dates and local link targets passed. No real host, SSH or sudo check was run for this display change.

Configured-account check verification on 2026-10-15: Python 3.11.15, 3.13.13 and 3.14.4 each passed 469 public tests, including nine new synthetic account tests and packaging/UI checks. The account tests also passed with explicit guards against native Session fallback. Older interpreters reused pure-Python dependencies; dependency readiness and credential-free local Session/strict cleanup were checked on 3.14. This does not establish real SSH or native su/sudo compatibility.

Boolean sudo policy verification on 2026-10-15: Python 3.11.15, 3.13.13 and 3.14.4 each passed 470 public synthetic/UI/package tests. Coverage includes false/true/omission, rejection of quoted strings/null/numbers/collections in configuration and runtime policy selection, rejection before connection, independent su/sudo routing, Core policy and retained-data fixtures. Credential string fallback rules remain covered. AST, changed-document links/dates and skill frontmatter passed; the 3.14 dependency check passed. Older interpreter suites reused pure-Python dependencies. No real SSH or native su/sudo validation is established by these tests.

Tabulate display verification on 2026-10-15: Python 3.11.15, 3.13.13 and 3.14.4 each passed 473 public tests with tabulate 0.10.0 and wcwidth 0.9.2 loaded from a temporary dependency target. Tests cover Unicode display widths, leading-zero identifiers, escaped controls, excluded/empty tables, JSON separation, dependency failure before connections and package metadata. Wheel build, no-dependency pip installation into a temporary target, isolated package import and installed Unicode rendering passed. Dependency checks with that target, AST, skill frontmatter and changed-document checks passed. Existing environments were not modified; the older interpreters reused the selected environment's remaining dependencies. No real host or privilege checks were performed for this table change.

Per-test table verification on 2026-10-15: Python 3.11.15, 3.13.13 and 3.14.4 each passed 478 public tests using temporary tabulate/wcwidth dependencies. Added projection tests distinguish connection/su/sudo results, failed-su dependent skips, policy skips, restoration/cleanup failures and suppressed successful reconnect duplicates; rendering issues no additional probes. Installed-wheel isolated Unicode per-test rendering, AST, documentation links/dates and skill frontmatter passed. JSON and operational probes are unchanged; no native SSH/su/sudo validation was performed.

_Last modified: 2026-10-15_
