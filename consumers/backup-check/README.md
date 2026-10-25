# Backup-check consumer 0.1.0

This bundled **opt-in** batch consumer subscribes to `retention.observation.created` for `backup-files-check` 0.1.0. It reads the latest retained backup observation per host/exact recipe reference and reconciles platform-owned conditions through `context.services`. No source host connection, scan, deletion or todo execution occurs.

Enable with `consumers.backup-check: {source: builtin:backup-check, enabled: true}` in the selected profile's `feast.yaml`, preserving its other registrations. Discovery never enables it; use `consumers list/show/inspect --profile NAME --json` and inspect the service configuration before activation. Controller Python 3.11+ and normal OpsFeast dependencies suffice. No consumer-specific provider credentials are required.

| Rule / stable owner `backup-check` | Effect | Recovery evidence |
| --- | --- | --- |
| daily-missing | Error notification | Known healthy daily presence; pending/unknown does not clear |
| expired-files | Warning todo | Complete scan with no expired files |
| unexpected-entries | Warning todo | Complete scan with no unexpected entries |
| scan-failed | Error notification | Complete scan |

Sources distinguish host, exact recipe reference, group name and rule. Evidence carries retained record ID, directory, check date and threshold. Incomplete counts are lower bounds. Ownership conflicts and service failures remain explicit; retained observations remain available even if policy or presentation fails. Retried live events retain their effects eligibility, while historical ingest/replay through the consumer facade cannot create new notification/todo objects.

Service dispatch is attempted after consumer processing and reports independent projection/delivery receipts. Delivery requires separately authorized routes; no SMTP channel is supplied here. For activation, API, status interpretation, retry and tests, read [backup checks](../../docs/backup-file-checks.md), [consumer contract](../../docs/retention-consumers.md) and [services](../../docs/services.md). Public tests exercise the complete synthetic runner chain and recovery; a real authorized SSH run verified collection, retention, Vault and todos. SMTP delivery remains unverified.

*Last modified: 2026-10-25 14:06:31*
