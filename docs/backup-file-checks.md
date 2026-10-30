# Daily backup file checks 0.1.0

The shipped `opsfeast.backup_check` module supports a profile-local recipe at `recipes/backup/files/check/daily-backups/`, referenced as `:backup/files/check/daily-backups`. It checks files on the connection target, so host settings belong to the backup destination host. Source database names are backup-group subjects, not extra SSH targets. This module does not add a seventh bundled recipe or silently install user bindings.

The workflow checks today's expected files, lists recognized backups older than configurable `retention_days` (default 90), and lists unexpected entries. It reads directory metadata only: no deletion, content reads, checksum, SQL validation, arrival-time verification or restore test. A zero-length regular file counts as present, matching the presence-only rule. SSHScript supplies the runner connection and argv-based command execution; the target scanner is Python with JSON input, bounded metadata enumeration and no shell interpolation. No su/sudo/root is requested.

## Create a complete portable recipe

Use `opsfeast.backup_check.portable_files(identity)` to obtain a complete user-recipe source tree. It includes the scanner, domain validator, entrypoint, schema, README, applicable license and optional backup-check consumer implementation. The resulting entrypoint does not import the platform's backup domain module. It declares mode: portable retention with an embedded schema, so execution/retention/import does not require registering backup-files-check in the receiver's product registry. Generic connections, data contracts and notification/todo services remain platform APIs.

```python
from pathlib import Path
from opsfeast.backup_check import portable_files

identity = {"author": {"name": "Example operator", "contacts": ["ops@example.invalid"]},
            "license": "MIT"}
files = portable_files(identity)
destination = Path("/path/to/profile/recipes/backup/files/check/daily-backups")
# Review and authorize this new directory before writing; preserve an existing recipe.
destination.mkdir(parents=True, exist_ok=False)
for relative, content in files.items():
    target = destination / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
```

Use the installation's real author defaults, not the reserved Bundle identity. Controller Python 3.11+, OpsFeast API/data services 0.1.0 and SSHScript 7.0.1 are declared prerequisites. The target needs POSIX Python 3.8+. Linux, FreeBSD and macOS are declared scanner implementations; native FreeBSD scanning remains unverified. Package the explicit reviewed files using recipes pack (bundle 0.2.0), then use [recipe installation plans and conflict handling](portability.md#recipe-packages-and-path-conflicts). Receiver settings are bound separately. The old descriptor(identity)/thin-wrapper helper remains a direct module-use option, but such a wrapper alone does not carry its domain implementation.

The optional packaged consumers/backup-check directory is portable source. To use it on a receiver without the bundled policy, review/copy it into that profile's consumers/backup-check and explicitly register `source: local:consumers/backup-check`. Installation does not copy it into the active consumer directory or enable it. Use either that reviewed local consumer or the bundled consumer, with one owner for each condition; do not activate competing implementations.

## Configure the backup destination

Merge exact-reference settings into the destination host's existing `hosts.yaml` entry, preserving connection/accounts/groups. Normal default/group/host inheritance applies, and host settings win. Example fragment:

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
          patterns: ['archive-{date}.tgz', 'db/dump-{date}.sql']
          ready_after: '01:00'
          grace_minutes: 5
        - name: database-b
          directory: /srv/example-backups/database-b
          patterns: ['{date}.sql', '{date}.data.tar.gz']
          ready_after: '02:00'
```

`backups` is a required nonempty array. Names must be unique lowercase alphanumeric/underscore/hyphen identifiers up to 63 characters. Each group requires a bounded absolute non-root directory and unique safe relative patterns, each with exactly one `{date}` in its basename. `{date}` is a valid calendar date `YYYY-MM-DD`, never a wildcard. Required parent directories are allowed; misplaced files, invalid dates, unrelated directories, symlinks and special entries are unexpected. Symlink directories are not followed, including child-open races.

Timezone defaults to Asia/Taipei and must be an IANA zone. `retention_days` is an integer 0–365000. Age is the calendar difference between today's date in that zone and the filename date; expired means **strictly greater** than the threshold. Exactly 90 days old is retained with threshold 90. `mtime` is metadata only. Future dates are not expired. `max_entries` is 1–100000 per group, default 10000; directory traversal also has a depth cap of 64. `ready_after` defaults to 00:00 and grace_minutes to 0; both must keep the daily deadline within the filename date. No arbitrary regex or automatic naming discovery runs during routine checks.

Before the deadline, missing daily files are `pending`. After it, complete evidence of missing files is `missing`. All expected regular files present is `healthy`; incomplete enumeration preserves unknown presence when not observed. Limits, unreadable directories, invalid filenames, command failure/timeout/truncation or invalid JSON preserve incomplete/unknown evidence. Even known daily presence with an incomplete scan yields a partial execution result. Expired/unexpected entries are findings and do not by themselves make daily presence unhealthy.

## Retain, interpret and apply policy

Inspect before authorized execution:

```sh
python -B tools/opsfeast.py inspect-recipe :backup/files/check/daily-backups --profile main --json
python -B tools/opsfeast.py consumers list --recipe :backup/files/check/daily-backups --profile main --json
python -B tools/opsfeast.py recipes run :backup/files/check/daily-backups --profile main --host backup-example --json --timeout 30
```

The last command connects and collects; inspection alone does not authorize it. Explicit --host overrides the normal enabled gate as documented by the runner. A connection failure before a usable observation is retained does not automatically create a missing-backup notification. Assess raw execution and cleanup separately from retention/content receipts.

The complete portable recipe validates typed and semantic data in its reviewed local validator before returning final data. The platform saves/validates its embedded data-only definition; replay/import never execute the validator. Direct module-based recipes using the registered backup-files-check 0.1.0 contract retain their existing digest-bound normalizer behavior. Operational local/SSH success or partial results can retain; mock, failed or skipped outputs do not become authoritative backup observations. See [retention](retention.md) and [replay](retention-replay.md).

Retained data includes actor username/effective UID/mode, target Python version, check_date, resolved policy and backup-group observations. Each group preserves expected paths/presence and metadata, scan_status/reason_code, health, expired-file path/date/age/size/mtime, unexpected path/kind/reason and counts. Incomplete lists/counts are lower bounds, never proof that the directory has no other files. Saved thresholds and findings are authoritative for that observation; Vault does not recompute historical age using today's config.

Enable the reviewed bundled policy consumer explicitly in `feast.yaml`:

```yaml
consumers:
  backup-check:
    source: builtin:backup-check
    enabled: true
```

The [backup-check consumer](../consumers/backup-check/README.md) uses shared [services](services.md), independently from the Vault consumer. It reconciles the latest record per host/exact recipe reference and backup group: missing daily files → error notification; expired files → warning todo; unexpected entries → warning todo; incomplete scan → error notification. Pending/unknown presence never clears a daily-missing incident. Only complete scans can clear hygiene todos. Historical replay cannot produce new objects via the consumer service facade. Live verified recovery resolves conditions, and persistent findings reuse objects and a verified-clear then adverse recurrence creates a new episode according to platform lifecycle.

Vault shows current expected-file tables, short expired/unexpected previews and full historical lists, linking service objects to available historical evidence. Generated pages are projections. To acknowledge a notification, assign/schedule a todo or record a note, use revision-checked [service API/CLI](services.md), then dispatch projections. Neither this consumer nor a todo deletes files. Mail remains separately configured and authorized; no relay or recipients are installed by this recipe.

## Verification

Public tests in `tests/test_backup_check.py` cover local metadata scans, dates/expiry, zero-length presence, subdirectories/symlinks, limits/failures, input rejection before commands, semantic corruption, the runner/retention/policy/Vault chain and historical-effects suppression. `tests/test_services.py` covers shared lifecycle/adapters. The full suite passed on Python 3.11–3.14 on macOS. An authorized SSH run verified both configured backup groups, retention, Vault and hygiene todos without deleting files or sending mail. This evidence does not establish dump integrity, native FreeBSD support or actual SMTP delivery.


## Assessments and operator-selected account

The producer now returns backup-specific assessment labels, including `BACKUPS OK · CLEANUP NEEDED` for hygiene findings despite successful daily presence checks. Run the supplied Recipe under inherited login/su/sudo policy without changing scanner code. [Results and accounts](recipe-results-and-accounts.md) explains fixed status, severity, prerequisites and verification limits. Existing private recipe copies need reviewed replacement to acquire new producer code; product update alone does not rewrite them.

*Last modified: 2026-10-30 12:17:33*
