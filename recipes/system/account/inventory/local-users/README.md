# Linux local users and groups

## Function, purpose and scope

Collect scoped Linux facts for administrators and agents without requiring a
custom per-host parser. Recipe version 0.1.0, python-recipe 0.1.0 and descriptor
0.3.0; portable retention contract follows the recipe ID at version 0.1.0.

Reads only /etc/passwd and /etc/group. Emits names, UID/GID, home, shell,
a shell hint and explicit group members. Password fields (including legacy hashes)
and GECOS are discarded on the target before output. It never reads shadow,
gshadow, SSH keys, PAM/sudo configuration or directory services. Primary groups
are represented by users.gid; explicit group members are not complete membership.
A configured shell is not evidence that SSH/login succeeds; nologin/false are
shell hints, not a comprehensive classification of human versus service accounts.

## Implementation choice

The supplied Core Recipe session executes one fixed Python stdlib probe using
SSHScript 7.0.1 argv plus stdin and a total command deadline. No SSH connections,
password retries, privilege loops or target script files are created by the body.
Target Python 3.8+ and controller Python 3.11+ are required. The shared
[Linux profile service](../../../../../opsfeast/linux_profile.py) and
[probe](../../../../../opsfeast/linux_profile_probe.py) are bundled product modules;
a packaged copy requires a product release providing service 0.1.0. They are not
a standalone installed plugin or automatic loader. The public SSHScript contract
is the bundled [7.0.1 source snapshot](../../../../../skills/sshscript/SOURCE.json),
commit b8d7c8fe88b4096e8a58e6609ba805ee2bf41049; see its Agent/API guides.

## Inspect, authorize and execute

```sh
python -B tools/opsfeast.py inspect-recipe system/account/inventory/local-users --json
python -B tools/opsfeast.py recipes run system/account/inventory/local-users --profile NAME --host HOST --json
```

Inspection is static. Execution connects and needs the user's host/read scope.
The recipe defaults to the supplied login actor and performs no elevation. An
explicitly configured runner execution account is separate authority; inspect raw
execution_identity and the payload's target effective_uid. No target dependency
is installed. Unsupported platforms return unsupported; unavailable python3 or
transport/invalid-output failures are raw failures, not empty successful data.

Variables:

- max_items: 1–5000, default 1000, per dataset / attempted processes.
- command_timeout_seconds: 1–120, default 20, capped by the recipe timeout.

The probe reserves time inside the deadline and caps each account file at 1 MiB,
process stat/status files at 32 KiB and serialized output at 128 KiB. Item/time,
source-change, permission, parsing and output-limit gaps mark affected datasets
incomplete. These bounds limit controller response/storage; they are not real-time
scheduling guarantees. Large populations may need a larger reviewed selection or
future incremental sources. Defaults neither enable schedules nor run other recipes.

## Retention, interpretation and Web

Each dataset has source/scope, target observed_at, items, complete, reasons and
attempted/unavailable counts. The payload includes target sampling start/end and
an independent controller acquisition interval. Target clock correctness is not
assumed. Complete means enumeration of the declared visible scope, not a global
host completeness or health claim. Optional process fields can remain null even
when enumeration succeeds. Valid metadata plus dataset failures is a partial
collection; wholly invalid/missing responses are failed and not retained by the
current general runner. Inspect raw-result history for those failures.

The recipe returns final data; its descriptor embeds the strict portable schema.
The platform owns raw persistence, retention validation and consumer dispatch,
with independent receipts. Generic consumers may use the dataset immediately.
Web **Hosts -> host -> 系統全貌** and profiling show read the same saved evidence
through the shared [profiling service](../../../../../docs/profiling.md), which
bounds previews and exposes source record IDs. Opening the viewer never collects.
Use retention show RECORD_ID for all fields/instances. No historical data is migrated.

## Verification and limits

Public tests in tests/test_linux_profile.py cover synthetic files/procfs, redaction,
permission/malformed/race/limit behavior, descriptor/schema agreement, runner raw
and retention delivery, and shared profiling values. Python probe functions run
locally against fixture directories; no native Linux or managed SSH execution is
claimed. Query semantics follow [Linux procfs](https://www.kernel.org/doc/html/latest/filesystems/proc.html)
and the [Linux passwd format](https://man7.org/linux/man-pages/man5/passwd.5.html).
See the [bundle coverage review](../../../../../docs/profiling-coverage.md) for
remaining discovery/policy/event gaps and staged delivery.


Reproduce the shared collector and retention tests without host access:

```sh
python -B -m unittest discover -s tests -p 'test_linux_profile.py'
python -B -m unittest discover -s tests -p 'test_profiling_sources.py'
python -B -m unittest discover -s tests -p 'test_profiling_web.py'
```

The full local delivery regression passed 1,340 Python and 74 JavaScript tests.
Native Linux/SSH and target Python 3.8 execution remain unverified.

## Staged execution

Version 0.1.1 declares one Python `collect` stage under
[staged Recipe execution 0.1.0](../../../../../docs/staged-recipe-execution.md).
Normal CLI runs record one execution and river across the selected hosts.
Web plates retain their own shared execution, including grouped routine workers.
Recipe scope, permissions, result/retention schemas and native verification limits
are unchanged. Earlier saved results are preserved; no migration or replay occurs.

*Last modified: 2026-11-18 15:56:07*
