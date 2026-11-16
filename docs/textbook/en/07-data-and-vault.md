# 7. Read data and use the operational Vault

[Book home](README.md) · Previous: [Inventory](06-inventory.md) · Next: [Consumers and services](08-consumers-and-services.md)

Use the operational Vault for plain reading and navigation. Use retention interfaces for structured analysis. Use saved raw results when you need original execution evidence. These interfaces answer different questions and preserve different detail.

## Navigate the operational Vault

Open the selected profile's actual `vault/` directory in Obsidian or another Markdown reader. This is separate from the textbook directory you are reading now.

| Entry | Read it for |
| --- | --- |
| `HOSTS.md` | Host navigation and Observations entrypoints |
| `Observations/SUMMARY.md` | Recorded execution batches and outcomes |
| `hosts/<primary-group>/<host>/SUMMARY.md` | One host's content and notes |
| `records/SUMMARY.md` under a host | Current datasets and operation history |
| `records/current-*.md` under a host | Readable latest state with original source times |
| Yearly `reports/` under a host | Complete historical observations and provenance |
| `Services/SUMMARY.md` | Notification/todo presentation |
| `Transfers/SUMMARY.md` | Imported evidence navigation |

Actual path segments are encoded by the publisher. Use returned links and generated indexes rather than synthesizing filenames. A host is routed under its first resolved group; other groups link to that location. Host history identity does not change when presentation moves groups.

Current inventory pages omit unreadable null/empty fields while retaining coverage warnings. Zero, false and an observed empty collection remain distinct. Some long lists have previews and historical source links. Historical reports retain complete stored observations and a final Collection metadata section. An omitted current field is not evidence of healthy absence.

Optional DGMO diagrams enrich tables. The data remains readable without that plugin, and no MCP server is required to generate the diagram text. Contents links use Obsidian heading conventions; other readers can differ. This book uses ordinary relative Markdown links for chapter navigation.

## Protect your notes

Generated pages are owned through manifests and can be replaced even if someone edits them manually. Removing a generated notice does not remove ownership. Keep human context in preserved host `README.md` files, separate unmanaged notes or supported service note fields.

A full rebuild can relocate owned content after a group change. Unmanaged notes remain at their original location, so relocate or relink them deliberately. Publication is atomic per file, not a transaction for the whole Vault.

## Query authoritative retained data

These commands read saved data without connecting or refreshing it:

```sh
python -B tools/opsfeast.py retention list --profile main --json
python -B tools/opsfeast.py retention show RECORD_ID --profile main --json
```

Select a real record ID returned by list. Read dataset definitions, units, original source times, origin, actual actor and quality/coverage evidence before combining results. For reusable Python composition use Core `profile.retention.query/show`; for report recipes use `context.retention.query/show`. Do not parse Markdown tables as a database or read SQLite directly to recreate existing public interfaces.

Imported retention has origin-qualified identities and stays independent of native host data. A matching display name is not a merge instruction. Retained data can be sensitive even when it has no explicit credential field; inspect content before selecting an export for sharing.

## Repair the stage that failed

If retention exists and only Markdown needs refreshing, an authorized local rebuild is:

```sh
python -B tools/opsfeast.py vault inspect --profile main --json
python -B tools/opsfeast.py vault rebuild --profile main --json
```

Inspect reads ownership/status; rebuild rewrites owned content from saved data without recollecting or altering retention/run evidence. It cannot recreate output that was never captured. It does not acknowledge consumer event receipts or execute arbitrary custom consumers. Service presentation has its own dispatch path and transfer views have `transfer rebuild`.

If raw evidence exists but retention failed, first validate selected raw offline:

```sh
python -B tools/opsfeast.py retention ingest /absolute/path/to/selected-raw.json --profile main --dry-run --json
```

Dry-run validates without writes or dispatch. Actual ingest writes retained data and may dispatch enabled consumer programs afterward, including configured service effects. Review that downstream scope before dropping `--dry-run`. Replay never reconnects or executes candidate recipe code and preserves historical classification; it does not refresh the measurement or authorize current incidents from old evidence.

Use `retention rebuild` for retention projections, not to recollect data. Protected write/unknown operation evidence cannot be made disposable by changing a current recipe descriptor. Destructive removal and storage reclamation belong to the reviewed [portability and archive workflow](10-portability.md).

Agent prompt:

> Read the saved records for this host and explain freshness, units, coverage and identity warnings. If only owned Vault pages are stale, rebuild those locally within my existing scope. Do not reconnect, rewrite history or overwrite human notes.

**Checkpoint:** Find one readable current page and the historical record supplying it. Identify which values are measured zero, observed empty or unknown, and keep your own note outside generated ownership.

Canonical guidance: [result-data skill](../../../skills/opsfeast-result-data/SKILL.md), [retention](../../retention.md), [result data](../../result-data.md), [Vault](../../host-vault.md), and [replay](../../retention-replay.md).

*Last modified: 2026-10-26 12:55:26*
