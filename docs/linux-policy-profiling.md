# Linux policy and configuration profiling 0.1.0

## Delivered capabilities

Five independent bundled recipes use the shared scoped Linux profile service and
portable retention. They never create a parallel connection/store or automatically
run as root. Web, CLI and agents read the same retained projections. Recipe paths:

| Recipe | Contract / version | Profiling capability |
| --- | --- | --- |
| [system/access/inventory/ssh-policy](../recipes/system/access/inventory/ssh-policy/README.md) | linux-ssh-policy / 0.1.0 | identity.authentication |
| [system/account/inventory/sudo-policy](../recipes/system/account/inventory/sudo-policy/README.md) | linux-sudo-policy / 0.1.0 | identity.privileges |
| [system/network/inventory/firewall-policy](../recipes/system/network/inventory/firewall-policy/README.md) | linux-firewall-policy / 0.1.0 | network.policy |
| [system/time/inventory/synchronization](../recipes/system/time/inventory/synchronization/README.md) | linux-time-sync / 0.1.0 | workloads.time |
| [system/logging/inventory/configuration](../recipes/system/logging/inventory/configuration/README.md) | linux-logging-config / 0.1.0 | observability.logs |

There are now 14 bundled recipes, 10 profiling providers and 104 projected
properties across 39 capabilities. Twenty-seven capabilities have partial
integrations and twelve remain unintegrated. Partial integration is not a complete
host policy/security claim. See [coverage review](profiling-coverage.md).

## Human/agent workflow and authorization

Describe the target, intended read/query scope and permitted execution account.
Inspect recipe metadata and existing saved evidence first. An agent can use
`profiling describe --json` / `profiling show --profile NAME --host HOST --json`
and raw recipe results without connecting. The recipes skill routes exact run
invocations. Setup, catalog inspection and opening Web do not authorize acquisition.

These recipes default to the supplied login actor. When already authorized,
operator-selected Core execution can use another account; the bodies do not add
root acquisition, credential retries or package installation. Permissions missing
from a read query remain recorded. sudo listing never runs a listed command or
collects passwords; normal tool audits/cache/provider lookups may occur.

Example requests: “Collect this host's declared firewall and time state under our
existing read grant; explain unavailable sources.” “Show SSH settings for operator
connecting from 192.0.2.5 to 192.0.2.2:22; do not infer successful login.”

## SSH Match context

```sh
python -B tools/opsfeast.py recipes run system/access/inventory/ssh-policy --profile NAME --host HOST --var 'ssh_context={"user":"operator","host":"client.example","addr":"192.0.2.5","laddr":"192.0.2.2","lport":22}' --json
```

Context is empty or has exactly user/host/addr/laddr/lport. Text rejects commas,
whitespace/control characters; addresses are unscoped IP literal strings (no numeric coercion or zone suffix), port an integer 1–65535.
Partial contexts fail before the probe. No context means global/default settings,
not a verdict for arbitrary Match blocks. Context-qualified output is a query of
the default disk configuration, not a running-daemon startup/loaded-generation
inspection, authentication attempt or complete PAM/login eligibility assessment.
Arbitrary -f/-o/command inputs are not exposed.

## Source-specific scope

### OpenSSH policy projection

Runs only `sshd -T` against the default configuration. Without context the
selected fields are global/default configuration, not a result for all Match
conditions. Optional ssh_context must contain all five fields user, host, addr,
laddr and integer lport; the probe passes one argv -C value, without shell
interpolation. Addresses must be unscoped IP literal strings and text fields reject commas/control
characters. Selected effective settings are still a disk/configuration query, not
proof of the running daemon's startup flags, loaded generation, PAM outcome or
actual successful login. Does not read authorized key contents, private keys or
arbitrary command directives. Only selected access/crypto/logging settings leave
the target, with the exact query context preserved.

### Selected-actor sudo policy projection

Runs only `sudo -n -ll` for the selected execution actor. It does not ask for
passwords, validate credentials, switch accounts, use -U to enumerate other users,
or execute any listed command. It projects long-list RunAsUsers/RunAsGroups, a
small option allowlist and command executable names/negation. Arbitrary arguments,
Defaults values, unsupported tags and syntax are omitted and explicitly flagged.
Even a successful query remains partial (`sudo_defaults_not_projected`). Do not
interpret an omitted argument constraint as unrestricted permission. A failed
noninteractive list can mean authentication is required, not that the actor has
no sudo rights. Policy plugins may consult external identity/policy providers;
normal audit and authentication-cache effects are possible.

### Linux firewall policy views

Queries available `nft -j -n -a list ruleset`, iptables-save, ip6tables-save,
firewall-cmd runtime/permanent list-all-zones and ufw status verbose separately.
No add/flush/reload/restore/enable command is used. Native nft JSON retains rule,
chain, table, address/port and NAT structures; comments/log prefixes/userdata are
omitted with a partial flag. Legacy save tables retain token arrays and require
balanced COMMIT boundaries; comments, log prefixes and string-match values are
omitted explicitly. Frontend text is a source-native view, not normalized rule
semantics; permanent firewalld output is configured, other queries runtime.
Backends may represent overlapping rules. Empty successful enumeration is not a
proof that traffic is allowed, and local rules do not prove external reachability
or coverage of other network namespaces. Missing tools do not prove absent kernel
facilities; no unsupported-tool fallback silently changes the source.

### Linux time synchronization configuration and state

Queries selected timedatectl properties/show-timesync, chronyc -n tracking and
sources, ntpq -n -c rv and ntpq -pn. The numeric clients avoid requested reverse
DNS and address only their normal local daemon/socket, not configured upstream
servers directly. It reads selected source/clock options from standard chrony,
ntp and timesyncd configuration, with bounded static includes. Authentication-key
arguments and arbitrary secret options are omitted. Native units/selection codes
are preserved, not converted to a universal health score. A successful report
with NTPSynchronized=no remains a complete query reporting an unsynchronized
state. Target timestamps may themselves be wrong: controller acquisition times
are independent. No set-time, set-ntp, makestep, burst or server configuration
command is issued.

### Linux logging configuration metadata

Reads selected standard journald settings/drop-ins, rsyslog legacy routes and
single-line action metadata, nginx access_log/error_log destinations, mysqld/server
log options and logrotate paths/rotation options. It runs only journalctl
--disk-usage --no-pager for journal metadata. It does not tail/read event messages,
run nginx -T/-t, execute logrotate, run rotation scripts or restart services.
MySQL client/server password fields, arbitrary syslog actions/templates, URL
userinfo, shell scripts and non-allowlisted values are excluded. Includes and
symlinks stay within the declared config roots. Unsupported inline/multiline
syntax, missing includes, changes during reads and limits remain explicit gaps.
Individual file directives are configured evidence: vendor/drop-in precedence,
nginx inheritance, alternate installation roots, syslog-ng/auditd and complete
pipeline health are not resolved. Relative/variable log paths remain declarations,
not verified existing files.


## Shared acquisition interface and contracts

Controller Python 3.11+, SSHScript 7.0.1, target Linux/Python 3.8+ and existing
applicable read tools are required. `opsfeast.linux_profile.collect(recipe, kind)`
now also accepts ssh-policy, sudo-policy, firewall-policy, time-sync and
logging-config. Reuse a supplied Core Recipe (session, timeout and vars);
`linux_profile_schema.schema(kind)` supplies the corresponding portable data
contract embedded in each descriptor. This is a bundled checkout/package service,
not an arbitrary external probe/plugin loader or a compatibility shim.

max_items bounds each dataset (default 1000, 1–5000). Per-recipe command timeout
(default 30 seconds here, 1–120) is capped by Recipe timeout; the target probe uses
80% of it for all work. Each native subprocess receives at most three seconds
within that shared deadline, so a hung optional daemon does not consume the entire
recipe by default. Native outputs cap at 256 KiB, files at 64 KiB, discovered files
at 64 per file dataset, serialized payload at 128 KiB. Includes remain bounded and
within explicit roots; no environment/variable expansion or config scripts execute.

The subprocess reader drains both pipes, kills only its owned process group on
time/output limits and records not_started/confirmed/unknown termination. A reaped
query process is not proof that all OS audit/cache side effects were undone. Hard
outer command interruption or kernel-blocked I/O can still leave termination
unknown; inspect the independent runner cleanup evidence. No log file contents,
private keys, password/hash fields or arbitrary command arguments are returned.
This is projection-based privacy, not a generic secret detector for every possible
third-party syntax; unsupported syntax is omitted/flagged rather than dumped.

Payload 0.1.0 fields: kind/platform, target started_at/observed_at, effective_uid,
datasets and a separate controller acquisition interval. Each dataset has source,
scope, observed_at, complete, items, reason_codes, counts and commands. Each item
has name, source, value and basis (configured/effective/runtime/context). Values
are source-native JSON/scalars/text; units, rule equivalence, inherited defaults
and effective merges are not invented. Query metadata includes requested argv/times/exitcode/
termination/reason only. Binaries are resolved on target PATH (or standard sshd
locations); their version/hash is not certified by this collector; stdout/stderr and source files are not persisted verbatim.

Strict portable schemas constrain dataset and row keys; reviewed parsers own
semantic interpretation. Missing tool, denied access, authentication requirement,
unsupported output/configuration, missing include, source change and truncation
stay explicit. Valid metadata with dataset gaps is partial; malformed/no-payload
acquisition is failed. Failed outer runs may be raw-only under the existing runner;
old retained success must not be presented as a new successful refresh.

## Retention, consumers and Web

Each recipe produces its final data under its own portable contract. Existing
inventory/RAID/database schemas and historical observations are untouched. Generic
consumers can read the declared data; the bundled consumer updates owned content
separately. Shared profiling uses retained-fields adapters and source/definition
boundaries; newer partial/unavailable datasets replace old values for that scope.

Web host 系統全貌 labels item basis and shows expandable source scope plus safe
query evidence. Raw exitcode 0 or complete enumeration does not mean secure policy,
synchronized time, healthy logging or fresh evidence. Source file directives are
not automatically merged. Samples and values remain bounded previews; use
retention show RECORD_ID --profile NAME --json for full retained evidence. Opening
Web/CLI views never connects, schedules or invokes any policy command.

## Reproducible verification

```sh
python -B -m unittest discover -s tests -p 'test_linux_policy.py'
python -B -m unittest discover -s tests -p 'test_profiling_web.py'
node --test tests/test_profiling.mjs
```

Fixtures exercise the five parser/query families, credentials/scripts/comment
omission, explicit contexts, configured/runtime separation, unsynchronized-but-
collected state, include loops/symlinks/limits, subprocess cleanup and full recipe
-> retention -> consumer -> HTTP data flow. No managed-host collection is performed
by these tests. Native OpenSSH/sudo/firewall/chrony/rsyslog versions and target
Python 3.8 remain separately unverified; parsing against Python 3.8 grammar is only
syntax evidence. Unsupported tools/flags are gaps, not silent installs/fallbacks.

## Primary interface references

- [OpenSSH sshd extended test/context](https://man.openbsd.org/sshd).
- [Sudo upstream manual source](https://github.com/sudo-project/sudo/blob/main/docs/sudo.mdoc.in) (list/noninteractive options; sudo.ws retrieval was unavailable during review).
- [nftables manual](https://www.netfilter.org/projects/nftables/manpage.html).
- [chronyc 4.6 manual](https://chrony-project.org/doc/4.6/chronyc.html).
- [timedatectl](https://www.freedesktop.org/software/systemd/man/latest/timedatectl.html).
- [journald configuration](https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html).
- [rsyslog configuration structure](https://docs.rsyslog.com/doc/configuration/basic_structure.html).
- [nginx access logging](https://nginx.org/en/docs/http/ngx_http_log_module.html).
- [MySQL server variables](https://dev.mysql.com/doc/refman/8.4/en/server-system-variables.html).

These explain source interfaces; they are not execution or native-platform evidence.


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

*Last modified: 2026-11-09 13:14:43*
