# Linux firewall policy views

## Function and purpose

Provide reviewed, repeatable Linux policy/settings observations for human/agent
management. Recipe 0.1.0, descriptor 0.3.0, python-recipe 0.1.0; portable retention
linux-firewall-policy 0.1.0. Collection completeness and security/service health are separate.

## Declared scope and interpretation

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

## Implementation choice and prerequisites

Use the supplied Core Recipe session and shared
[Linux profile service](../../../../../opsfeast/linux_profile.py), which sends a
[fixed Python stdlib probe](../../../../../opsfeast/linux_policy_probe.py) by argv
and stdin using SSHScript 7.0.1. This reuses session/account ownership, total command
deadlines, raw saving, portable retention and consumer delivery rather than creating
new connection or storage machinery. Controller Python 3.11+; target Linux with
Python 3.8+ on PATH and these applicable existing tools/access: Available nft/iptables-save/ip6tables-save/firewall-cmd/ufw tools; kernel-query permissions where required.
Missing commands/flags/permissions/outputs remain gaps, not package installation
or automatic account retries. The product must provide policy service 0.1.0;
packing this recipe alone does not include an independent target agent.

The matching public SSHScript skill is [SOURCE.json](../../../../../skills/sshscript/SOURCE.json),
contract 7.0.1, source commit b8d7c8fe88b4096e8a58e6609ba805ee2bf41049. The body uses
exec_command(argv, input=..., check=False, command_timeout=...), not custom SSH.

## Inspect and execute

```sh
python -B tools/opsfeast.py inspect-recipe system/network/inventory/firewall-policy --json
python -B tools/opsfeast.py recipes run system/network/inventory/firewall-policy --profile NAME --host HOST --json
```

Inspection is local and data-only. Running requires the human's host/query scope.
Use the selected actor; any runner-configured elevation requires its existing
explicit grant. No target software, settings or schedules are installed/changed.
Native read queries may create normal OS/tool audit/cache records.

Variables: max_items 1–5000 (default 1000), command_timeout_seconds 1–120
(default 30, capped by Recipe timeout). SSH additionally accepts ssh_context
(default empty); see the [complete policy guide](../../../../../docs/linux-policy-profiling.md).

## Outputs, retention and Web

Each dataset contains source/scope, source timestamp, complete, typed projected
items, reason codes and attempted/unavailable counts. Query evidence preserves
fixed argv, times, exitcode and process termination state; streams are discarded.
Items label configured/effective/runtime/context explicitly. File scans have
bounded inputs and source-change detection. The payload also records selected
actor UID and separate target/controller intervals. Complete is only the declared
projection, not all host policy or freshness.

A valid payload with missing/denied/partial datasets returns partial and is retained.
Unsupported OS, missing Python, transport, invalid/truncated outer payloads remain
raw failures/unsupported results; the current runner does not turn those into new
retained attempts. Inspect recipe history too. Collection, raw, retention and
consumer outcomes remain separate. The descriptor embeds the strict schema;
collection.json binds the existing profiling read adapter. Web host 系統全貌 and
profiling show expose saved values, basis, scope, query evidence and gaps; opening
them never executes the recipe. Full data remains available via retention show.

## Verification and limits

Public tests: [test_linux_policy.py](../../../../../tests/test_linux_policy.py),
shared profiling HTTP tests and renderer tests. They cover fixed queries, schema
parity, source redaction, partial states, context validation, file/include bounds,
owned-process timeout/output cleanup and runner -> portable retention -> consumer
-> Web projection with synthetic transport. Native Linux tools/SSH/sudo policy
have not been verified in this delivery. A local Python subprocess test is not
managed-host evidence. See [sources and exact limits](../../../../../docs/linux-policy-profiling.md).

*Last modified: 2026-11-09 13:02:17*
