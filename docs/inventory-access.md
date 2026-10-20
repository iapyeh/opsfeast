# Inventory access checks and partitioned results

system/inventory/overview 0.3.2 owns its [structured retention declaration, schema and normalizer](../recipes/system/inventory/overview/README.md#recipe-owned-retention-contract). This architecture change preserves the access, actor, data-state and identity rules below; it adds data-definition snapshots and registered schema/normalizer digests without new host probes.


Inventory-system recipe 0.3.0 adds an access gate and inventory-values contract 0.1.0. Read this guide before execution: selecting inventory includes bounded account selection with possible su/sudo by default. These are real connections and authentication attempts, even in dryrun. Login-shell startup, configured proxies and authentication/audit records can have side effects. No installation, target configuration changes, environment-variable capture, process arguments or arbitrary file crawling is performed.

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

These examples use synthetic values. Keep credentials in the private Feast. `sudo` and `sudo-password` are optional fields of `users.<account>`; they are not connection fields or recipe variables. SSH aliases select the actual runtime login account. Local connections use the actual local account. Inventory/dryrun considers that account and at most the first other sudo-enabled users account, using the selection rules below. The explicit check-access command additionally tests other declared users through independent su and enabled sudo, as described below.

| Account setting | Meaning |
| --- | --- |
| `sudo: true` or `sudo` omitted | Attempt and verify sudo to root unless already UID 0 |
| `sudo: false` | Disable this account's sudo; exclude it from inventory second-candidate selection |
| `sudo-password` omitted | Use the selected legacy explicit sudo credential, if present; otherwise account `password` |
| `sudo-password: "false"` | Use account `password` directly, bypassing legacy sudo overrides |
| `sudo-password: ""` | Submit an empty password; no fallback |
| `sudo-password: null` or a YAML key with no value | Normalize to an empty password; no fallback |
| Any other sudo-password string | Submit exactly that password; no fallback |
| No selected password | Attempt configured passwordless sudo without interactive input; fail if a password is required |

The `sudo` field accepts only Boolean values: `false` disables sudo; `true` or omission enables it. Strings (including `"false"` and `"true"`), numbers (including 0/1), null, lists and mappings are invalid. Values are validated by parsed type without string/number coercion. For `sudo-password`, the exact quoted lower-case string `"false"` remains the account-password fallback control value. `sudo-password` accepts only string or null; its other strings are literal passwords. Literal password `false` is therefore reserved in this field. Authentication failure never retries a different password source.

Legacy account `vars.sudo.password`, then host `vars.sudo.password` for the actual connection account, remain supported when the canonical sudo-password field is absent. Their presence uses the same null/empty/`"false"` rule: null/empty select an empty password; `"false"` selects account password. Host credentials are never borrowed for another sudo actor. The existing su credential rules remain unchanged. No stored configuration is rewritten. UI credential masking includes sudo-password.

To disable sudo for an account (inventory may still use an eligible second account):

```yaml
users:
  operator:
    sudo: false
```

Providing a login password does not prove sudo capability. The default policy means **attempt and verify**, not assume permission. Executing this version's check/collection includes those documented sudo attempts; set sudo to Boolean `false` to disable that account's sudo. Inventory may still select a second eligible account as described below. Effective UID 0 is root, regardless of the account name.

## Inventory account selection

Inventory and public [Recipe.root()](core-api.md#automatic-root-console) use the shared
strict checkout helper `root_access.root_actor` with selection policy
`two-candidate-v1`. The inventory_actor adapter alone chooses safe login fallback;
the public root() API raises RootUnavailableError instead. No per-recipe
admin account or extra configuration field is required. YAML `users` insertion order
is preserved by the configuration loader, including hosts defined in included files
or groups. Reordering accounts can therefore change inventory's second candidate.

1. Verify the actual login shell. An effective UID 0 collects immediately without su
   or sudo, including the verified ESXi root-shell model described in
   [host diagnostics](host-diagnostics.md#ssh-login-and-esxi-root-shell-identity).
2. Candidate one is the authenticated login account. Candidate two is the **first
   other** account in `users` whose `sudo` is true or omitted. Boolean false excludes
   that account from second-candidate selection. Do not search for a third candidate.
3. Normally try login-account sudo first (unless its `sudo` is false), then su to
   candidate two, verify that account, and sudo to root if its effective UID is not 0.
   **Exception:** if candidate two is named `root`, try `su root` before login-account
   sudo. A root account with `sudo: false` is not eligible as candidate two.
4. Missing su credentials skip the second route without probing passwordless su.
   A rejected entry or deadline may advance only after verifying restoration to the
   exact parent actor. Unknown/mismatched entered identities, failed context exits,
   unverified recovery, transport loss or cleanup failures stop that host.
5. If both routes are unavailable, collect as the verified original login shell.
   `access.mode` is `fallback_user`, `degraded` is true and the overall execution exit
   is nonzero even if all core data was collected. If login sudo is disabled and no
   second candidate exists, ordinary collection is intentional (`mode: user`, no
   degradation). An already-root shell always remains `mode: root`.

For example, this order selects `maintainer` as the second candidate; a later root
account is not attempted:

```yaml
hosts:
  example:
    connection:
      hostname: host.example.invalid
      user: operator
    users:
      operator:
        password: synthetic-login-password
        sudo: false
      maintainer:
        password: synthetic-su-password
        sudo: true
        sudo-password: synthetic-sudo-password
      root:
        password: synthetic-unused-password
```

Move the eligible root record ahead of maintainer to select root instead; inventory
then tries `su root` first. These are synthetic configuration examples, not permission
to connect. The login account need not appear in users. SSH aliases use the resolved
successful final-hop account; local execution uses the actual shell account.

Su credentials use the target's `vars.su.password`, then its account password. Sudo
credentials use that actor's canonical/legacy rules above. Host-level legacy sudo
credentials belong only to the login account and are never borrowed for candidate
two. Each entry has one selected credential and no alternate-password retry. A missing
sudo password still permits a configured passwordless policy.

The runner and its dryrun use this selection; explicit `check-access`, `test-su`,
`test-sudo` and `test-host` retain their diagnostic scopes and do not automatically
replace a failed account test with another account. Generic Python recipes retain caller-selected privilege scope; their supplied Recipe
can opt into the same policy with root(). Existing Recipe.su/sudo remain explicit.

Raw `access` adds `selection_policy`, ordered `candidate_users`, `selected_user`, and
ordered `attempts` (user/status/reason_code/steps). Steps retain operation, target,
credential-source name/presence, identity verification, entry failure category and
restoration evidence, never password values or third-party exception text.
`actual_identity` identifies the final collection actor; `login_identity` and
`shell_identity` preserve login/shell distinctions. The normalized retained/exchange data.collection_scope continues to store only mode
and effective_uid. New local raw/envelope collection_evidence 0.1.0 separately records
the actual actor and query sources; see [local evidence](retention.md#local-collection-evidence).

Preflight success means a safe collection actor is available, possibly fallback_user;
it does not promise root. During actual collection successful routes are re-entered
and identities verified again. Failed/skipped preflight routes are copied with
`reused_from_preflight: true` and not retried in that invocation. If a previously
successful route later rejects entry, the remaining untried candidate may be attempted,
then safe fallback applies. Collection-body failures never trigger a retry as another
account. Both preflight and collection verify each nested parent after context exit;
a working original SSH channel does not prove recovery of an inner su console. Raw errors preserve IdentityProbeError.reason_code and the summary names the
identity failure, rather than only reporting a generic collection error.

## Check access without collection

```sh
python -B tools/opsfeast.py check-access --all --root /srv/feasts/main
python -B tools/opsfeast.py check-access --host web-01 db-01 --threads 2
python -B tools/opsfeast.py check-access --group production
```

Choose `--host`/`--group` **or** `--all`; exclusions require --all. Additional examples:

```sh
python -B tools/opsfeast.py check-access --all --exclude legacy
python -B tools/opsfeast.py check-access --all --json --quiet
python -B tools/opsfeast.py check-access --all --json --quiet
```

Prefer check-access for hosts.yaml access validation and dryrun for a selected inventory invocation. Both share access contract 0.1.0. Check-access validates configuration/connections without inspecting recipe selections. Dryrun additionally statically validates the selected recipe and invocation inputs and uses inventory's bounded two-candidate selection. No recipe collection, platform discovery/cache writes, identity inventory, raw inventory or retained records are created. Check-access defaults to a tabulate table with status, host, test, user and reason columns; inventory dryrun uses terminal tables and retains JSON with --json or non-TTY output. For the complete check-access report, use --json and redirect stdout to a private file if persistence is wanted. Config checks alone do not connect. Check-access tests declared accounts only; skipped accounts remain unverified. Neither workflow proves command-specific sudo policy, recipe platform support or hardware visibility.

Check-access prints flushed progress to stderr before checking each host and after it finishes, even when stdout is redirected. Parallel progress follows actual completion order; the final stdout summary preserves selection order. Progress names the host/account; the table user column names the login for connection, the target account for su, and the actor for sudo. The sudo target remains root. Before identity verification, the configured connection user is shown; `unresolved` means the account is not yet known (for example, local or SSH-config-based login). If connection/identity verification fails, the configured name is only a requested account, not verified identity. The final summary has one row per connection/su/sudo test; a failure is prefixed with ❌. Totals count hosts: any failed account makes its host failed; otherwise any skipped account makes its host skipped. A host passes only when all its account checks pass.

Example final stdout with synthetic targets:

```text
╭──────────┬───────────┬────────────┬──────────┬─────────────────╮
│ status   │ host      │ test       │ user     │ reason          │
├──────────┼───────────┼────────────┼──────────┼─────────────────┤
│ PASS     │ 🐧 web-01 │ connection │ operator │                 │
│ PASS     │ 🐧 web-01 │ sudo       │ operator │                 │
│ PASS     │ 🐧 web-01 │ su         │ appuser  │                 │
│ PASS     │ 🐧 web-01 │ sudo       │ appuser  │                 │
│ ❌ FAIL  │ 🐧 web-01 │ su         │ auditor  │ su_entry_failed │
│ SKIP     │ 🐧 web-01 │ sudo       │ auditor  │ su_failed       │
╰──────────┴───────────┴────────────┴──────────┴─────────────────╯
Hosts: 0 passed, 1 failed, 0 skipped, 0 excluded
```

Check-access independently tests each `users` entry other than the verified login name, in configuration order. It uses the existing diagnostic su credential precedence (target vars.su.password, then target password, preserving empty values); it never borrows another actor's host/login credentials or retries a rejected password. After verified su, it tests sudo to root as that user unless the account has `sudo: false`. Sudo uses the canonical actor-scoped credential rules above, including passwordless policy when no password is selected. A sudo-disabled account passes when su, identity restoration and cleanup pass; disabling sudo is not a failed or skipped account check. Missing su credentials instead yield SKIP/missing_su_password and no sudo attempt. No passwordless su probe is added. This scope includes additional authentication attempts; invoking this version of check-access selects all these declared-account checks.

Each additional actor uses fresh Sessions through the existing `privilege_test` implementation, including a login identity probe and a fresh independent su/sudo group. It verifies the su target, elevated identity, return to the original login and cleanup. Failed su prevents sudo; other independent accounts and hosts continue. Login sudo failure still permits other account checks when login identity/restoration/cleanup are verified. Failed login, unknown restoration or login cleanup failure leaves other accounts skipped with login_unavailable/login_cleanup_unverified. No shared failed console is reused. Progress shows each account before its check and its outcome, then a host completion count; a failed extra account does not relabel the successful login row as failed.

The rounded-outline table is rendered by tabulate 0.10.0. `requirements-init.txt`, package metadata and pyproject.toml declare `tabulate[widechars]==0.10.0`; the extra installs wcwidth for Chinese/Japanese/Korean names and the ❌ marker. Host labels in the table, exclusion rows and stderr progress prefix the configured icon (default 🍎), loaded through Validator from the selected Feast. Icons are display-only: JSON host IDs and report structure are unchanged, and YAML is not rewritten. Checkout callers may pass a validated host-ID-to-icon mapping to format_summary/progress_printer; omitted mappings use the standard default. Column values remain text, preserving leading-zero IDs; control characters remain escaped. Wide or long names expand the table rather than being truncated. Progress remains line-oriented on stderr, the Hosts: footer counts hosts, and --json retains its existing structured output. Missing tabulate/wcwidth rejects text-mode checks before connection; use the selected interpreter's environment check and an authorized requirements installation. A package installed in another interpreter does not satisfy this one. No installation or environment upgrade is performed by the CLI. Both init/full environment checks report these base display dependencies. See the [upstream Unicode support](https://github.com/astanin/python-tabulate#wide-fullwidth-cjk-symbols).

A verified root login (effective UID 0) never runs sudo, even when its account has `sudo: true` or sudo is omitted. It needs no sudo executable for the login check. JSON records `access.sudo.status: not_needed`; the table shows `SKIP / already_root`, which does not fail the host. Other declared accounts still receive their independent su/enabled-sudo checks. Root is determined by actual identity, not merely the configured username.

Each PASS applies only to that test: connection proves transport/login establishment; a failed identity probe is a separate failed identity row and prevents host success. Su verifies the target identity, and sudo verifies root identity. Failed su produces SKIP/su_failed for enabled sudo; missing su credentials produce SKIP/missing_su_password for su. Disabled sudo produces SKIP/sudo_disabled and an already-root login produces SKIP/already_root; these intentional policy skips do not fail an otherwise verified host. Restoration and cleanup failures appear as separate restoration/cleanup rows, preserving earlier successful test rows. Successful internal reconnects are not repeated as connection rows; a failed reconnect or its identity check is shown explicitly, followed by skipped dependent tests. Hosts: totals and the exit code retain the aggregate host outcome; a test PASS alone does not prove the whole host passed. Minimal legacy display inputs without connection evidence use an access row instead of inventing test-specific success. FAIL includes the short reason code; use --json for connection, identity, sudo and cleanup evidence. SKIP is not verified access. Under --all/group selection, disabled targets appear as EXCLUDED with host_disabled; explicit --host selection produces SKIP instead. CLI exclusions show cli_excluded. Exclusions are counted separately and do not fail otherwise successful selected checks. An entirely filtered selection remains an error before connection.

```sh
python -B tools/opsfeast.py check-access --all --quiet
python -B tools/opsfeast.py check-access --all --json --quiet > access.json
```

Migration: scripts that parsed the previous default JSON must add --json; --quiet suppresses only stderr progress, not the final stdout report. The login access contract remains 0.1.0 with an additive per-host configured_user field (null when absent); the verified initial shell remains access.connection_identity, while access.login_identity identifies the authenticated account. Check-access adds accounts in display order: user (nullable until login is known), role (login/su), status and reason_code. Additional attempted accounts retain full diagnostic evidence in checks and sudo policy as enabled/disabled. The login row references existing top-level access evidence; the host status aggregates all rows. Inventory collection adds access.attempts for its two-candidate selection, rather than the diagnostic accounts list; TTY presentation follows the [console policy](cli.md#terminal-tables-and-json). The optional check_many(..., progress=callback, include_users=True) checkout helper enables the CLI account scope and calls callback(stage, report) at start/account_start/account_finish/finish in worker threads; callers must serialize shared output and avoid raising from callbacks. include_users defaults to False; inventory=True selects the inventory policy for runner callers; no callback means no progress output. This helper is not a versioned public Core API.

The test follows configured jump hosts, verifies actual login UID/name, enters the same root shell used for collection when enabled, verifies UID 0, exits and verifies original identity, then checks Session cleanup. It checks root-shell access, not sudo permissions limited to individual commands. SSHScript's authenticated console requires Bash and id. Supplied passwords may not be consumed when policy/cache permits entry; success cannot prove a password's correctness independently of that policy/cache. Every selected test runs even after another fails. Exit 0 means all selected targets passed; failed or explicitly skipped targets return 1. `--root` and `--profile` are mutually exclusive. `--timeout` is positive/finite, default 30 seconds per stage, not an entire invocation deadline. `--threads` is positive, defaults to 1 for check-access. Disabled/excluded hosts are not contacted.

## Collection and independent diagnostics

Inventory acquires its verified collection actor once per host through the bounded two-candidate policy above. Hosts execute independently; one failed host does not prevent another selected host from collecting. Safe fallback to the verified login account is explicit in access/actor evidence; uncertain identity or restoration stops that host. There is no all-host preflight gate, --dryrun/--force switch or credential retry.

Use opsfeast.py check-access for separately authorized account diagnostics. It can test more declared users than collection's bounded policy, so its result is diagnostic evidence rather than a cached route to reuse automatically. inventory dispatch --dry-run only previews due work without connections. Failed job acquisition saves explicit gaps when saving is requested; query without --save remains non-persistent.

## Separate results and execution evidence

Current inventory uses [job observations](inventory-jobs.md). The remainder of this section and the inventory-values/CSV catalog describe historical snapshot data, retained for saved-data interpretation. They are not an alternative execution mode.

Raw result 0.2.0 and retained/exchange 0.1.0 keep their seven-field compatibility interface. The new independently versioned extension has:

- `inventory_contract_version: "0.1.0"` and `inventory`: six fixed sections with typed values only. Missing results are JSON null, regardless of the reason. Zero and empty lists remain meaningful values. Nothing substitutes an error message for a value.
- Optional local envelope/raw collection_evidence 0.1.0 (recipe 0.3.2+): actual collection username/UID/mode and bounded query metadata, excluding outputs and credentials. Core/retention queries expose it; the legacy normalized exchange remains unchanged. Historical missing evidence remains missing.
- Raw-only `collection_process`: scope, times, limits and per-query source commands, states/reasons. Existing observations/sources/execution_errors remain the compatibility execution evidence; consumers wanting pure results read inventory.
- Raw-only `access` and `access_check`: actual account/effective UID, expected sudo policy, credential-source names, verified restoration and degraded mode. Never passwords.
- Retained/exchanged `collection_scope`: only mode and effective_uid, necessary to interpret visibility. Process diagnostics, command sources, stdout/stderr and credential sources are excluded from the retained extension.

Old records without the extension remain valid. Older strict consumers must update before accepting new extension-bearing records. SQLite stores the extension in the existing JSON payload; its seven-column compatibility view is unchanged. Query `json_extract(payload, '$.inventory.hardware.memory_total_bytes')` for a new scalar. Export/combination preserve the new extension and independent histories; a repeat with another account is a new observation, never an overwrite or an automatic merge of nonempty fields. Identity quality/warnings and original observation times remain mandatory context.

## Query completion and missing extended values

The extended collector normalizes PTY CRLF before parsing its producer completion marker, after checking the raw byte limit. SSHScript console results can contain CRLF even when direct execution uses LF. Missing markers, nonzero producer exit, parsing, truncation, time limits and unsupported probes remain distinct states/reasons. Root privilege does not install tools, guarantee parser compatibility, remove query bounds or implement missing probes. Code 127 is command_not_found; code 126 is command_not_executable, not proof of a permission-policy denial. Raw-only exception type is retained without exception text.

Base status still summarizes the seven observation fields; inspect collection_process or the optional collection_evidence for extended coverage. All extended fields can be null even when base status is success. Vault now reports those query outcomes separately instead of equating a missing value with an absent resource.

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

The bundled feast/report/execution-summary displays partitioned values and collection scope alongside compatibility evidence. It does not reconnect or refresh inventory. Custom report recipes can query inventory by section and must preserve null, scope, identity warnings and source times.

## Verification and migration

Synthetic tests cover credential presence/control values, default/passwordless/disabled/root modes, job acquisition, fallback, no retry, restoration and Session cleanup failures, collection-time sudo rejection, all platform parsers, budgets/truncation, retention/exchange and empty-cell CSV. Native SSH, sudo policy, FreeBSD/Linux/ESXi extended collection remain unverified; historical macOS evidence predates this extension. Documentation/command sources include the bundled SSHScript 5.0.0 public contract, [Linux proc documentation](https://www.kernel.org/doc/html/latest/filesystems/proc.html), [FreeBSD pkg query](https://man.freebsd.org/cgi/man.cgi?query=pkg-query&sektion=8), and platform manuals. A successful synthetic test is not real-host applicability evidence.

Migration: account `sudo: "false"` is no longer accepted; change it explicitly to `sudo: false`. `sudo: true` is also accepted. This change does not alter `sudo-password: "false"` or legacy credential fallback markers. No private configuration is rewritten automatically. For intentional ordinary-account collection, disable login sudo and leave no eligible second candidate. Existing users order now selects the second candidate; review that order and authorization before execution. Empty/null explicit sudo credentials now select empty passwords; use the exact string "false" to request account-password fallback. The current descriptor removes identity_sudo; account sudo policy controls collection privilege. New export extensions require updated strict validators. No private hosts.yaml, registrations, records or environments are automatically migrated.

Delivery verification on 2026-10-14: Python 3.11.15, 3.13.13 and 3.14.4 each passed 415 public synthetic/UI tests. The 3.11/3.13 suites reused the shared pure-Python dependency tree; this does not validate their native SSHScript dependency stack (the native cffi backend was unavailable for those interpreters). The selected 3.14 environment passed dependency/import-distribution checks and a credential-free local Session command with strict cleanup. AST/schema structure, synthetic retained/exchange examples, skill frontmatter, complete guide YAML and 39 added local documentation links passed. No native sudo or real SSH/host inventory was run.

Check-access display verification on 2026-10-15: Python 3.11.15, 3.13.13 and 3.14.4 each passed all 460 public synthetic/UI tests, including wheel/sdist boundary checks. The older interpreters reused the selected environment's pure-Python dependencies; native dependency readiness was checked only on 3.14. Concise/JSON/quiet output, progress-before-check ordering, parallel completion, failures/skips, unresolved accounts, exclusions and terminal controls are covered. AST, skill frontmatter, document dates and local link targets passed. No real host, SSH or sudo check was run for this display change.

Configured-account check verification on 2026-10-15: Python 3.11.15, 3.13.13 and 3.14.4 each passed 469 public tests, including nine new synthetic account tests and packaging/UI checks. The account tests also passed with explicit guards against native Session fallback. Older interpreters reused pure-Python dependencies; dependency readiness and credential-free local Session/strict cleanup were checked on 3.14. This does not establish real SSH or native su/sudo compatibility.

Boolean sudo policy verification on 2026-10-15: Python 3.11.15, 3.13.13 and 3.14.4 each passed 470 public synthetic/UI/package tests. Coverage includes false/true/omission, rejection of quoted strings/null/numbers/collections in configuration and runtime policy selection, rejection before connection, independent su/sudo routing, Core policy and retained-data fixtures. Credential string fallback rules remain covered. AST, changed-document links/dates and skill frontmatter passed; the 3.14 dependency check passed. Older interpreter suites reused pure-Python dependencies. No real SSH or native su/sudo validation is established by these tests.

Tabulate display verification on 2026-10-15: Python 3.11.15, 3.13.13 and 3.14.4 each passed 473 public tests with tabulate 0.10.0 and wcwidth 0.9.2 loaded from a temporary dependency target. Tests cover Unicode display widths, leading-zero identifiers, escaped controls, excluded/empty tables, JSON separation, dependency failure before connections and package metadata. Wheel build, no-dependency pip installation into a temporary target, isolated package import and installed Unicode rendering passed. Dependency checks with that target, AST, skill frontmatter and changed-document checks passed. Existing environments were not modified; the older interpreters reused the selected environment's remaining dependencies. No real host or privilege checks were performed for this table change.

Per-test table verification on 2026-10-15: Python 3.11.15, 3.13.13 and 3.14.4 each passed 478 public tests using temporary tabulate/wcwidth dependencies. Added projection tests distinguish connection/su/sudo results, failed-su dependent skips, policy skips, restoration/cleanup failures and suppressed successful reconnect duplicates; rendering issues no additional probes. Installed-wheel isolated Unicode per-test rendering, AST, documentation links/dates and skill frontmatter passed. JSON and operational probes are unchanged; no native SSH/su/sudo validation was performed.

Access host-icon verification on 2026-10-15: Python 3.11.15, 3.13.13 and 3.14.4 each passed 479 public tests with temporary display dependencies. Default/custom icons, per-test host cells, stderr start/completion, disabled/CLI-excluded labels, Unicode widths and unchanged JSON IDs/YAML are covered. Static documentation/skill checks passed. No native host or privilege tests were added or run.

ESXi login compatibility: when id is absent and uname reports VMkernel, the shared identity adapter can use the existing system Python to verify effective UID/name. Access JSON adds identity_probe/configured_identity_probe backend evidence and identity_error.reason_code on identity-stage failure; connection_identity remains unchanged. A successful SSH connection followed by failed identity is displayed as PASS connection plus FAIL identity; it remains a failed host and does not authorize trusting configured root. See [the canonical adapter contract](host-diagnostics.md#esxi-login-identity-without-id). UID 0 still skips sudo. Existing SSHScript authenticated-console prerequisites apply to other users; no native ESXi su/sudo or inventory execution is established.

## ESXi identity diagnostics and configured-account mismatches

The shared identity adapter accepts missing-id exit 127, or the narrowly recognized
exit 2 / empty stdout / shell missing-id stderr form, only after confirming VMkernel.
Access reports record identity_probe.id_exitcode. ESXi configured_identity_probe adds
normalized actual/expected account and effective UID fields plus matched. The observed
shell actor remains in access.actual_identity when a configured-account mismatch fails;
connection_identity and privilege access are not marked verified. A root effective UID with a different authenticated-account UID can be accepted by the verified ESXi root-shell model described below. Other mismatches remain identity_mismatch. A failed relationship check stops sudo and collection. See [diagnostic rules and native
evidence](host-diagnostics.md#diagnose-esxi-identity-failures). Retained inventory contracts
are unchanged; these fields explain raw access diagnostics.

## ESXi authenticated login with a root shell

For verified ESXi, an authenticated ordinary account may have a UID 0 execution shell.
The shared connection check accepts this as esxi_root_shell when final-hop login,
stable root UID and VMkernel evidence satisfy the [identity model](host-diagnostics.md#ssh-login-and-esxi-root-shell-identity).
Access login_identity identifies the SSH account; shell_identity and the legacy
connection_identity describe the initial shell. Policies/passwords and exclusion of
the login from extra-user tests use login_identity. Root execution sets mode root
and sudo not_needed, including when that login disables sudo; no elevation occurs.
The table names the login and explains its effective root shell rather than reporting
an identity error. Numeric matched may be false with status success and accepted_by
esxi_root_shell. Failed probes and other platform/privilege-target mismatches still
stop access. Collector provenance keeps the effective actor; retained schemas are
unchanged. This does not verify every command, a vSphere role or native ESXi su/sudo.

Two-candidate inventory verification (2026-10-17): Python 3.11.15, 3.13.13 and
3.14.4 each passed all 588 public tests, including 22 added selection/runner/error
regressions and the existing headless UI/package checks. Older interpreters reused
the shared environment's Python dependency tree; native dependency readiness and a
credential-free local Session with strict cleanup were checked only on 3.14. Wheel
and sdist boundaries, temporary no-dependency installation, installed policy import
and runner help, Python 3.11 grammar, skill frontmatter, document dates/local links,
two complete synthetic guide YAML examples and diff whitespace checks passed.
No private host connection, native su/sudo, ESXi inventory or release was performed
during these checks. Public SSHScript 5.0.0 knowledge came from the bundled Agent Guide,
API guide authenticated-console/failure sections, versioning guide and SOURCE.json;
no SSHScript library source or upstream snapshot was modified.

Recipe.root delivery verification (2026-10-17): Python 3.11.15, 3.13.13 and
3.14.4 each passed all 604 public tests, including 16 new root-console/Core/runner
cases and the complete preceding inventory/ESXi changes. Older interpreters reused
the shared maintenance environment's Python dependencies without modifying it;
native dependency readiness was checked only on 3.14. Wheel/sdist boundaries,
temporary no-dependency installation, installed Recipe.root/RootUnavailableError and
shared-policy imports, installed runner help, a credential-free local Session,
ordinary-user callable console/managed job and strict cleanup passed. Python 3.11
grammar, Core/recipe Python example syntax, changed skill frontmatter, document dates,
564 local links and diff whitespace checks passed. Operational native su/sudo and
ESXi inventory remain unverified; no private host connection or package/tag release
was performed. Existing data schemas and dependency settings need no update because
the API addition reuses existing contracts and SSHScript 5.0.0. Human/agent docs,
capability routing and public reproducible tests are included in this delivery.

_Last modified: 2026-10-20 11:24:28_
