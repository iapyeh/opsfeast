# Vault retention consumer

`builtin:vault` (ID vault) implements [consumer contract 0.1.0](../../docs/retention-consumers.md) with default activation. It subscribes to observation creation/deletion, operation creation and retention.run.updated across sources. Its entrypoint delegates to host_vault.rebuild; explicit vault rebuild uses that same renderer without creating/acknowledging events.

Requirements are Python 3.11+, OpsFeast initialization dependencies, a namespace-enabled profile, valid hosts.yaml, retention read access and writable owned Vault output. No connection, SSHScript execution or model is needed. Plain Markdown tables work without a plugin; optional DGMO rendering requires a compatible reader/plugin, not an MCP server or new collection. The renderer consumes registered inventory-job-observations 0.1.0, historical inventory-observations 0.1.0, host-values 0.2.0, operation evidence and explicit observation-run 0.1.0.

## Views and ownership

[Vault layout and ownership](../../docs/host-vault.md#directory-and-ownership) defines the primary-group host tree, generated host/SUMMARY.md entrypoint, preserved human README.md notes, records/SUMMARY.md, current-title pages, yearly reports/operations and Observations timestamp pages. Read [current/report separation](../../docs/host-vault.md#recipe-retention-and-markdown) before extending presentation: current pages omit unreadable fields, show complete name-sorted packages/services and optional diagrams; full reports preserve detailed values/states/units/source times and collection metadata. Partial/identity warnings, zero/false and observed empty collections remain meaningful. Current title collisions still fail; equal-second historical report/batch names use ordinal suffixes rather than UUID/hash filenames.

Current inventory records also show [original command output](../../docs/host-vault.md#original-command-output) in default-closed escaped code blocks. Use retained data.probes/source_probes with their actual source record/time, never read raw files to reconstruct old output. Empty/unavailable/truncated streams remain distinct; shared probes are deduplicated per source record.

Current inventory Attention uses current exact-reference recipe vars; rebuilding can apply threshold changes without collection. [Batch pages](../../docs/observation-runs.md#attention-evidence-and-vault-pages) use saved host membership, outcomes, policy/findings and source links. The index displays original Targets selectors and command success/failure from the execution receipt; absent old metadata is Not recorded. Per-run metadata/duration precedes Contents; Hosts tables link the host name to its source report and show Status/Collection jobs. Failed storage/publication is a warning rather than a Retention column. Empty Attention is omitted. Never infer old batches by time proximity, read raw results to fill missing collection evidence or reevaluate historical warnings using newer settings/data. A deleted record leaves an unavailable reference without a dangling report link.

vault_content.build/render_observation supplies presentation and host_vault publishes owned Markdown with separate manifests. Regeneration replaces edited owned files and removes stale owned outputs; unmanaged notes and other owners remain protected. Human README notes are not moved on primary-group changes. Rebuild is atomic per file, not across the whole Vault; repeated events rebuild current persisted state idempotently.

## Configure and recover

Disable delivery in feast.yaml with `consumers: {vault: {source: builtin:vault, enabled: false}}` or `vault: {auto_refresh: false}`. Other consumers remain independent; retention and completed run snapshots are preserved.

```sh
python -B tools/opsfeast.py vault rebuild --profile main --json
python -B tools/opsfeast.py consumers inspect vault --profile main --json
python -B tools/opsfeast.py consumers dispatch vault --profile main --json
```

Rendering/ownership failures preserve committed retention/run data and produce a separate retryable receipt. Enabling after a disabled period processes matching journal backlog. Explicit rebuild regenerates current output independently of event acknowledgements. Old records without run membership remain ungrouped; no automatic migration or recollection occurs.

For another content application, declare a separate reviewed consumer, source and output owner, then explicitly enable it. Use context.retention.query/show for records and runs()/run(run_id) for execution batches; a run event's record_id is a run UUID. Do not add application-specific branches to runner or storage. Synthetic tests verify dispatch/rollback, read-only inputs, policy snapshots, ownership, collisions, links and current-view rendering. Native SSH/privilege-policy behavior, external hosting and universal editor compatibility are not established by these tests.

_Last modified: 2026-10-21 11:19:57_
