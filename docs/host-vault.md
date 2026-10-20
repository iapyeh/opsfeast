# Bundled host vault content application

Vault is the bundled content application over [recipe retention](retention.md). Structured retention remains authoritative; generated Markdown and human notes live in `vault/`. The platform owns paths and publication, while the bundled author chooses readable views. Other reviewed content applications can consume the same data without Vault.

## Identity and configuration

Open `<profile-root>/vault/` in Obsidian or another Markdown reader. Reading tables requires no model, connection or plugin. The optional DGMO plugin renders `dgmo` fences; a DGMO MCP server is not required to generate these text definitions. Tables remain available when diagrams are unsupported. `feast.yaml` accepts `vault: {auto_refresh: false}` to disable automatic publication; it does not disable retention or change recipe selection.

Host identity is namespace plus host ID. Primary group affects content routing, not identity or the independent annual SQLite archives. See [retention storage](retention.md#storage-and-execution-phases).

## Enable or migrate

```sh
python -B tools/opsfeast.py init main --namespace production --json
python -B tools/opsfeast.py vault rebuild --profile main --json
python -B tools/opsfeast.py vault groups --profile main --json
python -B tools/opsfeast.py vault inspect --profile main --json
```

All commands also accept `--root PATH` instead of `--profile`. Init preserves an existing namespace/configuration. Rebuild refreshes generated pages and group links without collecting or writing retention/run data; groups refreshes membership links only; inspect is read-only. Exit codes are 0 success, 1 failure, 2 argument error. The old SQLite-in-vault layout is incompatible and is never moved/deleted automatically: preserve the old profile and use a separate initialized profile plus reviewed [raw replay](retention-replay.md). Rebuild cannot reconstruct missing old collection values/evidence.

Automatic publication uses the [Vault consumer](../consumers/vault/README.md), default registration `builtin:vault`. Observation creation/deletion, operation creation and `retention.run.updated` events trigger current-state rebuilds. Use `consumers inspect` and `consumers dispatch vault` for failed deliveries. Explicit `vault rebuild` does not create or acknowledge events.

## Directory and ownership

```text
vault/
  README.md                         # preserved human landing page
  HOSTS.md                          # generated host and Observations navigation
  .content-structure.json
  .content-bundled-retention.json
  .content-groups.json
  Observations/
    SUMMARY.md                      # explicit execution-batch index
    YYYYMMDDHHMMSS.md                # UTC batch start, collisions use -2, -3...
  hosts/<encoded-primary-group>/<encoded-host-id>/
    README.md                       # preserved human notes/entrypoint
    records/SUMMARY.md               # generated host record index
    records/current-<title>.md       # readable current state
    <UTC-year>/reports/<YYYYMMDDHHMMSS>-<title>.md
    <UTC-year>/operations/<precise-UTC-time>-<title>--<record-hash12>.md
  overview/README.md
  groups/README.md
  groups/<encoded-group-id>/README.md
  groups/<encoded-group-id>/<encoded-host-id>.md
```

The consumer title is independent of recipe path; inventory uses System inventory. Historical observation report names contain a whole-second UTC time and title, with no UUID, fractional seconds or hash suffix. Same-second/title collisions get `-2`, `-3`, etc.; a shared mapping drives generated report paths and source links. Operation journals retain precise time and intent/result discriminators. Independent current datasets that resolve to the same title still fail publication rather than overwrite one another. Names are safe and bounded; full IDs/references remain in report metadata.

Primary group is the first resolved membership; secondary groups link to that one host tree. Ungrouped/archived hosts use `_ungrouped`; a real group with that name is encoded distinctly. Full rebuild routes all generated history/current pages and indexes to the current primary group and removes stale owned pages. Human README files and unmanaged notes stay at their original paths; relocate/link them deliberately. `groups` alone does not relocate host content.

`records/SUMMARY.md` replaces the generated records/README index. It is a navigation page for current records and operation history, not an additional observation or human notebook. Missing host README stubs point to SUMMARY. Existing human README pages are preserved and may need their own link updates. Generated old names are removed only when manifest-owned; manual links are not migrated or aliased.

Manifests track separate structure, bundled-content and group owners. Ownership authorizes replacing generated output even after editor/manual changes and removing stale owned paths. Removing the notice does not remove ownership. Unmanaged paths and other owners' files remain protected; collisions fail explicitly. Publication is atomic per file, not for the whole Vault; inspect an interrupted generation before retrying. Never store human notes inside owned pages.

Checkout authors may call `host_vault.publish(root, owner, entries)` while holding `host_vault.locked(root)`. owner is a stable lowercase identifier and entries maps safe relative `.md` paths to bodies. The publisher adds the generated notice and local-second modification footer. Arbitrary binary publication is outside this interface; link validated report artifacts instead. This is a checkout service, not a stable Core API.

## Recipe retention and Markdown

Recipe authors own data definitions/extraction; content authors own presentation. There is no `retention.markdown_template`. `vault_content.build(root, runtime)` reads retained records and explicit runs, returning bodies/index/host IDs without writes or connections. `host_vault` publishes them; consumers/vault/main.py supplies event dispatch. Never scrape Markdown as the data interface: use `profile.retention.query/show` and `runs/run`.

### Current records: readability

Current inventory pages start with the configured host icon/name and Observed time. Empty Attention is omitted; flagged Attention appears before Contents. Content is grouped by subject: System, Hardware, CPU and memory, Network, Storage, Software and Services. There is no static/dynamic split. Network configuration and measured network state stay together, as do other topic-related values.

Current views omit null/empty-string fields and sections with no readable data. Zero, false and explicitly observed empty collections remain distinct; the latter says No entries reported. Missing/failed/latest coverage is still signaled and linked to the full report; an omitted value is not a successful absence check. Package and service collections are shown completely, sorted by name. Other long collections can use a 12-row preview and source-report link. Table units are incorporated into values instead of a redundant Unit column; duplicate Sample time columns are removed while section/sample provenance remains in reports/structured data. Matching byte/MB filesystem projections are deduplicated only when entity, source/time and converted value agree. Filesystem layout and capacity remain distinct tables.

Single cumulative I/O counters do not establish rates and are omitted from current views; measured-window CPU utilization remains. The renderer does not invent throughput or link topology. Data/coverage and identity warnings remain visible. A single top source-report link is used when all displayed sections share it; mixed-age sections link their own source reports when different. Current pages omit the full Collection metadata disclosure, which belongs in reports.

The DGMO definitions add reported filesystem-usage bars and host/interface/address overviews. Example text generated from observed values:

```dgmo
bar Filesystem usage (%)
orientation-horizontal
y-label Used (%)
"/ (/dev/example)" 82
```

Only valid reported percentages in 0–100 are plotted; absent percentages are not calculated or treated as zero. Interface graphs show grouping/addresses, not physical links or inferred operational health. Labels are escaped/sanitized against fence/line/diagram injection. Diagram support is optional and introduces no collection or network dependency.

### Reports: complete evidence

Yearly reports prioritize completeness over compact display. Job reports retain every sample's property, entity, value, unit, state, sample time and source; full observations and collection metadata remain available, including null/unavailable values. Null, false, zero and empty collections are not interchangeable. Original precision is retained in structured data even when Markdown uses human units or local-second time display. Current-view omission/preview/deduplication does not remove stored or full-report data.

Historical reports have one final Collection metadata section with source/reference/version, record/origin/retention provenance, actor/identity scope and recorded coverage/queries. Detailed provenance can use HTML disclosure; readers without it may show expanded content. Commands/states/reasons come only from recorded collection evidence or job probes. Legacy reports lacking evidence explicitly say Not recorded; rebuilding does not read raw results, guess the collector or recollect data. A successful base observation does not establish full extended coverage. Identity quality, partial/unknown states and failure reasons remain interpretation context.

### Latest selection and source times

Current datasets are grouped per host by origin namespace, recipe-source qualifier and stable recipe ID, then the newest whole record is selected with record ID breaking equal-time ties. Recipe moves within that source do not rewrite historical references or create aliases. Independent sources/origins remain separate; title collisions are errors.

For inventory-job-observations, current pages combine the latest attempt per property/entity, with original group/sample source times. Failed latest attempts stay gaps; they never fall back to older successes. Attention can compare different-age baseline/metric observations and identifies their times. Other contracts retain their own whole-observation semantics. The host index reports observation state/time, not online status or live health.

Contents links use native Obsidian heading fragments with preserved case and URL-encoded spaces/non-ASCII text. Repeated headings get distinct readable names. In Reading view follow the link normally; Live Preview uses the reader's follow-link gesture. Heading conventions in other readers can differ.

## Observation batches and Attention

[Execution runs](observation-runs.md) produce `Observations/SUMMARY.md` and timestamp-named batch pages. They list selected hosts, available major collection jobs, outcomes, retention state and source reports. Attention contains flagged hosts only. This directory is distinct from profile-root `observations/` raw JSON. Old nearby records are not fabricated into historical runs.

Current inventory Attention uses the current resolved `recipes.REFERENCE.vars.attention` policy; a local rebuild applies changed thresholds without recollection. Batch pages display the saved policy/findings for that execution and do not reevaluate history using current settings/new samples. Disabling recipe execution preserves retained data/current pages; disabling `attention.enabled` suppresses current threshold evaluation independently. See [threshold definitions and limits](inventory-jobs.md#attention-thresholds).

## Long-lived operation journal

Write/unknown operation evidence belongs to retention. Vault renders intent/outcome links, preserving unresolved and unknown verification states; successful command results do not prove a verified change. Content failure never erases the journal. See [operation interfaces](retention.md#operation-journals-and-module-boundaries).

## Checkout module interfaces

Use `host_vault.rebuild/refresh_groups/publish` and Vault CLI for content. Use Core `profile.retention.query/show/runs/run`, checkout `retention_store.query/show`, `observation_runs.list_runs/show`, and the retention CLI for data. Read [run producer interfaces](observation-runs.md#checkout-interfaces-and-verification) before composing a batch writer. Do not edit annual SQLite tables or instantiate a second configuration/normalization pipeline.

## Consistency and verification limits

Public synthetic tests cover current-view omission versus full reports, sorting, units, filesystem deduplication, I/O suppression, diagram-label safety, thresholds, batch snapshots, links, collisions, publication ownership, retention/replay and independent failure receipts. The local verification rendered 44 generated DGMO diagrams with @diagrammo/dgmo 0.85.0 without diagnostics; this is renderer evidence, not a universal editor/plugin compatibility guarantee. No new native SSH/privilege-policy evidence, hosting, transmission, whole-vault transaction or cryptographic authenticity claim is added.

_Last modified: 2026-10-20 23:08:29_
