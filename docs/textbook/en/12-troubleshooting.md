# 12. Troubleshooting by evidence

[Book home](README.md) · Previous: [Backup case](11-backup-case.md) · Next: [Desk reference](reference.md)

Start with the original profile and saved execution identifiers. Locate the first failing stage before rerunning operations. A data or content failure often has a local recovery path; repeated collection can obscure the original problem and create unnecessary operations.

## Find the stage

| Symptom | Inspect first | Appropriate response |
| --- | --- | --- |
| Wrong/missing environment | `profiles`, selected `--profile`, actual root and locator files | Correct selection or repair registration; preserve data |
| Configuration rejected | `check` errors and defining YAML file | Correct the specific field/reference; repeat local validation |
| SSH fails | Saved hop/auth/command evidence and actual target | Diagnose address, trust and selected authentication within scope |
| Login succeeds, execution identity fails | Requested account policy, actor/UID and restoration evidence | Review the permitted method; do not silently change account or transport |
| Recipe unsupported or preflight fails | Descriptor, exact source, target platform/dependencies and typed inputs | Choose supported implementation or fix a concrete prerequisite |
| Partial measurement | Per-query/probe state, reason, capture limits and actual scope | Preserve unknowns; collect again only if needed and authorized |
| Raw exists, retention failed | Saved raw, snapshot/schema and retention receipt | Dry-run selected replay; repair data path without reconnecting |
| Data exists, page missing/stale | Retained record, publication ownership and consumer receipt | Rebuild appropriate owned content or retry reviewed consumer |
| Notification exists, mail absent | Routes, delivery receipt, mute/resolution and adapter result | Diagnose delivery separately from condition and collection |
| Import/archive interrupted | Plan, verified package and durable receipt | Use documented recovery/resume, preserving recovery artifacts |

## Read saved evidence first

```sh
python -B tools/opsfeast.py observation latest --status failed partial --profile main --json
python -B tools/opsfeast.py observation result RESULT_ID --profile main --json
python -B tools/opsfeast.py observation result RESULT_ID --detail --profile main --json
python -B tools/opsfeast.py consumers inspect --profile main --json
python -B tools/opsfeast.py services deliveries --profile main --json
```

These reads do not retry or reconnect. An empty filtered latest-batch host list does not prove there were never failures; it describes that selected batch/filter. For older batches, use `observation` and the CLI's explicit selection. If a target failed before raw storage, read the batch evidence and acknowledge absent host detail.

Do not treat the command used to read history as a rerun: exit zero can mean a failed historical result was read successfully. Keep collection status, command execution outcome and retention/content/service outcomes distinct.

## Three local recovery examples

**Case A: complete retained backup data, failed Vault publication.** Verify the record and content error. An authorized `vault rebuild` republishes bundled owned views without rescanning. A consumer retry updates its delivery receipts but can also dispatch configured services. Select the recovery that matches the failure and authorized effects.

**Case B: valid raw result, incompatible saved retention definition.** Use `retention ingest ... --dry-run` and inspect the precise compatibility error. A reviewed `--recipe-dir` override is available for documented snapshot/digest cases; it cannot relabel old write/unknown operations as read. Actual ingest may invoke enabled downstream programs. Preserve original raw and do not edit evidence to force acceptance.

**Case C: archive interrupted after package verification.** Inspect `transfer receipts` and the matching archive package. `transfer resume ARCHIVE_RECEIPT_ID` checks remaining source fingerprints and resumes recorded cleanup. If the package is missing or changed, stop further cleanup and resolve recovery; never remove the only verified package.

## Diagnose without inventing evidence

| Observed evidence | Claim you can make | Claim that remains unproved |
| --- | --- | --- |
| Configuration check passed | Locally validated settings are accepted | SSH login works |
| Hostname/date test passed with cleanup | Those connection commands completed | Database access or sudo works |
| Sudo identity probe matched UID | The tested shell/identity path worked | Every privileged command is allowed |
| Backup regular file is present | Presence policy found a regular file | Dump integrity, timely arrival or restoreability |
| Retention stored | Structured evidence is durable in that storage path | Every consumer or external delivery completed |
| Page rebuilt now | Saved evidence was rendered now | Measurements were refreshed now |
| SMTP mock tests passed | Tested protocol paths behaved under mocks | A real recipient received this message |

Missing historical output stays “not recorded.” A timeout can leave remote termination unknown. Confirmed local cancellation, remote process termination, restoration and verified operational outcome are separate claims. A reassuring recipe assessment must not override these gaps.

## Ask for the smallest next action

> Diagnose RESULT_ID in profile main from saved evidence only. Identify the first failing stage, what succeeded, and what is unknown. Prepare the smallest concrete recovery with its effects and expected proof. Continue within my existing authorization; ask only if new target access, privileges, deletion, delivery or a material decision is required.

If external sending is in scope and a delivery is unknown, explain the possible duplicate before selecting `--retry-unknown`. If a todo is manually done but the adverse condition persists, inspect evidence and policy rather than deleting the object or inventing a clear observation. If the failure is a missing product interface, record that gap and prefer a reusable fix over a private parallel implementation.

**Checkpoint:** Take one historical failure and identify the earliest failing stage, the most specific saved reason, the missing evidence and a recovery that avoids unrelated operations.

Canonical guidance: [CLI diagnosis](../../cli.md#diagnose-a-saved-failure), [host diagnostics](../../host-diagnostics.md), [replay](../../retention-replay.md), [consumers](../../retention-consumers.md), [service delivery](../../service-adapters.md), and [transfer recovery](../../portability.md).

*Last modified: 2026-10-26 12:55:26*
