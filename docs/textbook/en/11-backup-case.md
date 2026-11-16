# 11. Complete case: daily backup checks

[Book home](README.md) · Previous: [Portability](10-portability.md) · Next: [Troubleshooting](12-troubleshooting.md)

This case follows a daily backup check from human intent to saved evidence and a hygiene todo. All hosts, paths and database names below are synthetic. The exercise does not require connecting to learn its interpretation. Execute only the steps within your actual authorized scope.

## Define the question

Two applications send dated database dump files to a backup host. We want to know whether today's required regular files are present after their deadlines, which recognized backups exceed a filename-date retention threshold, and whether unexpected entries need review.

The SSH target is the **backup destination**, `backup-example`. `database-a` and `database-b` are subjects within that host's backup configuration, not additional connection targets. The operation reads directory metadata. It does not read dump contents, validate SQL, check checksums, prove arrival time, restore a database or delete files. A zero-length regular file counts as present under this policy.

Suggested human request:

> In profile main, prepare a reusable presence check for database-a and database-b on backup-example. Use our saved filenames and local deadlines in Asia/Taipei. Keep files older than 90 calendar days as cleanup findings, and list unexpected entries separately. Save evidence and readable results. Enable only the reviewed local backup policy if needed; do not delete files, send mail or schedule execution. Reuse existing authorization and ask only for missing real paths or policy.

The agent first resolves actual paths and prerequisites, inspects existing recipe/consumer/configuration and identifies the reviewed operations. A mail route already configured elsewhere must be considered before any dispatch even when this case requests no mail.

## Prepare complete reusable code

OpsFeast ships `opsfeast.backup_check`, which provides `portable_files(identity)` to build a complete profile-local portable recipe. It includes scanner, validator, schema, entrypoint, documentation, license and optional consumer source. Use the [canonical creation procedure](../../backup-file-checks.md#create-a-complete-portable-recipe), actual author attribution and a new reviewed destination. Preserve an existing recipe; do not overwrite it silently.

Expected location and selector:

```text
<actual-profile-root>/recipes/backup/files/check/daily-backups/
:backup/files/check/daily-backups
```

Controller prerequisites are current OpsFeast APIs and supported SSHScript 7.0.0. The target needs POSIX Python 3.8+. Declared scanner platforms include Linux, FreeBSD and macOS; native FreeBSD scanning remains unverified. Private settings stay on the receiver. A portable entrypoint carries its domain code rather than depending on a thin platform-domain wrapper.

## Bind the real destination and policy

The following is a fragment to merge under the existing `hosts.backup-example` mapping, preserving its connection, accounts, groups and other recipes:

```yaml
recipes:
  ':backup/files/check/daily-backups':
    enabled: true
    vars:
      timezone: Asia/Taipei
      retention_days: 90
      max_entries: 10000
      target_python: python3
      backups:
        - name: database-a
          directory: /srv/example-backups/database-a
          patterns: ['dump-{date}.sql']
          ready_after: '01:00'
          grace_minutes: 5
        - name: database-b
          directory: /srv/example-backups/database-b
          patterns: ['{date}.sql', '{date}.data.tar.gz']
          ready_after: '02:00'
```

These paths are examples, not discovery hints or execution targets. Each pattern contains exactly one `{date}` in its basename, replaced with a valid `YYYY-MM-DD` calendar date. Safe relative parent directories are supported. Age comes from the filename date in the configured timezone, not filesystem mtime. Expired means strictly older than the threshold: age 90 is not expired with threshold 90; age 91 is.

Before the daily deadline plus grace, absent expected files are pending. Afterward, a complete scan can establish missing. Limits or unreadable directories can leave presence unknown, even when some files were found. Symlinks and misplaced/unrecognized entries are not accepted as expected regular files. No findings imply deletion permission.

Default execution uses the login account. If the actual paths require another account, review and configure supported exact-reference execution policy as described in [chapter 4](04-hosts-and-access.md) and [results/accounts](../../recipe-results-and-accounts.md). Do not add an ad hoc sudo loop or assume root is required.

## Inspect and execute once

After code/configuration preparation:

```sh
python -B tools/opsfeast.py check --profile main --json
python -B tools/opsfeast.py recipes show :backup/files/check/daily-backups --profile main --json
python -B tools/opsfeast.py consumers list --recipe :backup/files/check/daily-backups --profile main --json
```

These are local inspections. Review any existing downstream consumers/service routes and their effects. Once one target run and its persistence/downstream scope are authorized:

```sh
python -B tools/opsfeast.py recipes run :backup/files/check/daily-backups --profile main --host backup-example --timeout 30 --json
```

The command connects to the backup host and required hops, scans metadata, saves the result, and attempts retention and enabled downstream processing. Explicit `--host` bypasses host/source/recipe enabled gates for this target; it does not grant privileges or disable validation.

Keep the returned batch/result/record IDs and actual saved paths. Inspect execution identity and restoration, group scan completeness, expected-file presence, expired/unexpected lists, retention and content/service receipts. A connection failure without eligible retained data does not automatically become a missing-backup incident.

## Work through three synthetic outcomes

| Evidence | Interpretation | Next action |
| --- | --- | --- |
| All expected files present; complete scan; one 91-day file | `BACKUPS OK · CLEANUP NEEDED`; presence is healthy, hygiene needs review | Read retained expired list; consider a todo, with no deletion |
| Required file absent after deadline; complete scan | `BACKUPS MISSING`; partial execution with a daily-missing finding | Investigate the source/transport under separate scope; preserve evidence |
| Entry limit reached; some expected files unseen | `CHECK INCOMPLETE`; absence is unknown and counts may be lower bounds | Review limits/permissions and authorize a bounded recheck if appropriate |

Before the deadline, missing files can instead be `BACKUPS PENDING`. Success with a hygiene warning is intentional. A custom label never suppresses storage, identity, cleanup or publication failure. An apparently present dump still needs a different operation to prove content integrity or restoreability.

## Add the reviewed policy consumer

After review and within explicit local activation scope, merge into existing `feast.yaml`:

```yaml
consumers:
  backup-check:
    source: builtin:backup-check
    enabled: true
```

Use one policy implementation per condition owner. A packaged local copy is an alternative reviewed source, not another policy to run in parallel. Activation can expose pending backlog; actual dispatch executes code and may attempt configured service delivery. Inspect service configuration first, particularly when mail is outside scope.

The policy reconciles the latest eligible evidence per host/exact reference and group:

- Missing daily files produce an error notification.
- Expired files or unexpected entries produce warning todos.
- Incomplete scans produce an error notification and cannot falsely verify clearance.

Repeated findings reuse the episode. Verified clearance resolves it; recurrence can create a new episode. Historical replay cannot produce fresh live incidents. Todo creation does not delete files or schedule cleanup.

## Read the result and record human work

```sh
python -B tools/opsfeast.py observation latest --profile main --json
python -B tools/opsfeast.py observation result RESULT_ID --detail --profile main --json
python -B tools/opsfeast.py retention show RECORD_ID --profile main --json
python -B tools/opsfeast.py services list --kind todo --host backup-example --profile main --json
```

Read the current backup page through the host's generated records index and follow its historical source report. Current views show short previews; historical records preserve complete stored lists and policy. Do not recalculate old file ages against today's date when explaining that observation.

For a hygiene todo, read its current revision and use the [revision-checked update workflow](08-consumers-and-services.md) to assign or note a review. A cleanup proposal should separately identify exact candidate files, evidence freshness, exclusions, expected effects and recovery. Nothing in this presence check or its todo authorizes removal.

## Recover and hand off

If the scan succeeded but publication failed, inspect receipts and repair the relevant content stage without another scan. If retention failed and valid raw exists, validate replay before actual ingest; downstream effects still matter. If the scan itself was incomplete, rebuilding cannot supply missing directory evidence. A new bounded collection requires applicable execution scope.

The handoff should provide the actual reusable recipe location, exact reference, private configuration location, one rerun command, result/record links, observed account/time, independent receipts and outstanding gaps. For another Feast, package complete portable source and bind that receiver's private paths locally. Export evidence separately if requested; packaging is not transmission authorization.

**Checkpoint:** Explain why “all expected files present,” “scan complete,” “cleanup needed,” “todo done” and “database restore verified” are five different claims. Trace one finding from raw result through retention, policy and its service object.

Verification sources: [backup workflow and limits](../../backup-file-checks.md), [module](../../../opsfeast/backup_check.py), [public backup tests](../../../tests/test_backup_check.py), [consumer](../../../consumers/backup-check/README.md), [services](../../services.md), and [portability](../../portability.md). Product evidence includes an earlier authorized SSH backup check, but this textbook's examples were not executed on managed hosts. Actual SMTP delivery and native FreeBSD scanning remain unverified in the cited delivery evidence.

*Last modified: 2026-10-26 12:55:26*
