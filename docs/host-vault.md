# Bundled host vault content application

Automatic publication is performed by the [bundled Vault consumer](../consumers/vault/README.md), registered as `builtin:vault` through the [consumer contract](retention-consumers.md). Its subscriptions are discoverable with `consumers list --recipe system/inventory/overview`. Failures are tracked per event/consumer and retried with `consumers dispatch vault`; explicit `vault rebuild` regenerates current content independently of delivery acknowledgements.

Vault is the bundled application over [recipe retention](retention.md). The platform manages its structure, identity/path rules and output ownership. The bundled content author renders retained observations and operation evidence. User AI agents may create other content authors or use retention for web pages, graphs and reports without using vault.

## Identity and configuration

Open `<profile-root>/vault/` in a Markdown reader or Obsidian. No plugin, model or connection is needed. Logical namespace/host identity and all authoritative SQLite data belong to [retention](retention.md#storage-and-execution-phases). Vault contains content and human notes only. `feast.yaml` accepts `vault: {auto_refresh: false}` to disable automatic publication; default is true.

## Enable or migrate

`opsfeast.py init NAME --namespace production --json` initializes data storage and the bundled vault without connecting or collecting. Namespace defaults to the saved namespace or first profile name. Reinitialization preserves it. There is no `vault migrate` command: the earlier SQLite-in-vault layout is incompatible and not moved automatically. Preserve the old profile and initialize a separate one, then use [retention replay](retention-replay.md) for selected raw results. Never delete old data or notes to enable initialization.

```sh
python -B tools/opsfeast.py vault rebuild --profile main --json
python -B tools/opsfeast.py vault groups --profile main --json
python -B tools/opsfeast.py vault inspect --profile main --json
```

All commands also accept `--root PROFILE_ROOT` instead of `--profile`. Rebuild refreshes local content and group links; groups only refreshes membership links. Inspect is read-only. Output is JSON, exit 0 success, 1 failure, 2 parsing error. `retention rebuild` rebuilds SQLite projections independently; `vault rebuild` never writes SQLite or executes recipes.

## Directory and ownership

```text
vault/
  README.md                        # preserved human landing page
  HOSTS.md                         # platform index
  .content-structure.json
  .content-bundled-retention.json
  .content-groups.json
  hosts/<encoded-primary-group>/<encoded-host-id>/
    README.md                      # preserved human host notes
    records/README.md
    records/current-<consumer-title-slug>.md
    <UTC-year>/reports/<YYYYMMDDHHMMSS>-<title-slug>.md
    <UTC-year>/operations/<UTC-timestamp>-<title-slug>--<record-hash12>.md
  overview/README.md
  groups/README.md
  groups/<encoded-group-id>/README.md
  groups/<encoded-group-id>/<encoded-host-id>.md
```

The consumer chooses a presentation title independently of the recipe path. Inventory pages use System inventory; other pages use a human label derived from their recipe ID. Latest filenames look like current-system-inventory.md: a current prefix and the consumer-selected readable title, without UUIDs or reference hashes. Observation report filenames use a compact UTC timestamp to whole seconds plus the label, for example 20261019084328-system-inventory.md. They have no fractional seconds, timestamp punctuation, UUID or hash suffix. Independent current datasets resolving to the same title fail publication explicitly rather than overwrite one another; consumers must choose distinct titles. Operation-journal filenames retain precise timestamps and record discriminators because an intent and result share an observation time. Any equal-second/equal-title observation path collision fails explicitly without overwriting a report or removing retained records; publication failure is separate from successful retention. Names are normalized, path-safe and bounded. Source-qualified references and full record IDs remain in historical report metadata. These are content-author naming rules, not recipe naming or retention identity.

Primary group means the first ordered group membership in the current resolved host configuration (a scalar is one group). A host has one content tree, such as hosts/production/node/; secondary groups link to it. No current membership, including an archived/unconfigured host, uses hosts/_ungrouped/HOST/. A real group named _ungrouped is encoded as %5Fungrouped so it cannot merge with that bucket. Group and host identity still use reversible safe path components. This routing affects Vault content only; authoritative retention/hosts/HOST/ remains independent of groups.

A full rebuild publishes current-group history/latest pages, updates HOSTS/overview/group links and removes stale owned pages. It creates missing human README entrypoints but never relocates, rewrites or deletes unmanaged notes, including old host README files. After this layout change or a later primary-group change, move or link your human notes from their preserved old directory deliberately. Empty or note-containing previous directories can remain. groups alone refreshes membership links; use full rebuild after changing primary groups so target pages are also regenerated.

Rebuild replaces old manifest-owned encoded-reference/digest pages with the new names and updates generated indexes. Unmanaged notes remain untouched; a collision with an unmanaged target fails. Existing hand-written links to old generated paths need manual updates. No aliases, old-path migration utility or user-data rewrite is supplied.

Separate manifests track platform structure, bundled content and groups. Each maps relative Markdown paths to SHA-256 digests of the latest generated bytes. Manifest ownership authorizes replacement: regeneration overwrites owned outputs even after manual edits or editor formatting, without confirmation or a required backup. The generated notice states this policy; removing the notice does not remove ownership. Digests record generated content and do not block replacement. Stale outputs belonging to that owner are removed even if edited. Unmanaged files and other authors' outputs still cause an explicit collision, including unmanaged files carrying a generated notice. Human landing pages and notes outside the manifests remain intact. Publication can leave different generations across files; interrupted writes may require inspection before retrying.

Checkout authors can use `host_vault.publish(root, owner, entries)` while holding `host_vault.locked(root)`. `owner` is a stable lowercase letter followed by lowercase letters/digits/hyphens/underscores. `entries` maps safe relative `.md` paths to Markdown bodies. The platform adds a generated notice and local-second modification footer. Assets can remain validated report artifacts linked from Markdown; arbitrary binary vault publication is not part of this interface. Ownership manifests are coordination metadata, not a security sandbox against arbitrary Python/filesystem writes.

## Record and SQLite contracts

Vault stores no databases. Use the [retention query and schemas](retention.md#discover-and-read-data); never derive data access from generated page paths. The retained envelopes remain authoritative and preserve precise source timestamps and quality warnings.

## Recipe retention and Markdown

Recipe creators own the data declaration and extraction. Content authors own Markdown and other presentation. `retention.markdown_template` is removed. `consumers/vault/main.py` is the event entrypoint. The shared renderer `vault_content.build(root, runtime)` is the bundled content author: it selects public retention records and returns Markdown bodies, a host index and host IDs; it performs no writes or connections. `host_vault` publishes those bodies under the bundled author's manifest. User AI agents can query multiple recipe references independently and use [offline content reports](retention.md#content-authors-and-offline-reports).

The host list includes configured and archived hosts. Latest-state pages select the newest whole observation per stable recipe ID within its origin namespace and recipe source, with record ID breaking equal-time ties. Partial remains partial; no old-value backfill occurs. The host index reports latest observation status or no observations, not online status or health. Every historical observation report preserves record ID, origin, source time/status, environment identity evidence and typed values. Observation pages use readable sections and tables rather than dumping inventory JSON. The header shows only the host. Successful observations have no Status: success banner. Historical reports have a single final Collection metadata section that combines the report title, recipe/source, observation time, collection account, query/coverage states and provenance. Partial/identity warnings remain visible, and nonsuccess observation state is retained in metadata. Identity warnings and partial-observation limits remain visible. Inventory pages cover System, Hardware, Storage, Network, Software and Services; collections such as interfaces, packages and filesystems have column headings derived from their retained keys. Capacity/time fields show human units with exact base values. Null means Not available; zero and false remain values, while an empty collection says No entries reported and does not prove absence beyond collection scope. Observation states/times and supplied collection coverage remain available. General host-values pages show values, states, units and meanings without an empty inventory block.

Opaque identifiers, original origin fields, mapping/retention provenance and identity evidence appear in the final Collection metadata section as labeled fields under an HTML details element. Readers supporting disclosure show this section collapsed; other Markdown readers may show it expanded. This is a navigation aid, not secrecy or an access boundary. Content is escaped before entering headings, lists or tables. Operation-journal pages retain their existing JSON presentation in this change.

The final Collection metadata section reads the actual recorded collection actor from optional local collection_evidence 0.1.0, separate from the login account. Collection queries show recorded commands, per-query state, reason and exit code/time, including the base fields and extended probes. Missing data can mean command_not_found, command_not_executable, command_failed, producer_marker_missing, parse_failed, output_limit, item_limit or total_budget_exhausted; not_supported means the platform has no implemented query. The base seven-field observation state does not promise that every extended query succeeded. No password, raw output, stderr or privilege-attempt credential source is retained here. The identity adapter may supplement hardware fields; its separate raw evidence is not presented as the extended probe's output.

Historical records lacking the optional evidence show Not recorded for account name and explain that commands/reasons were not retained. Their retained collection_scope may still report effective UID/mode, but UID 0 does not establish a username. A Vault rebuild cannot reconstruct missing inventory or missing evidence and does not inspect raw results. New authorized collection with recipe 0.3.2 records it; do not manufacture historical metadata or rerun hosts merely to change page names.

Both yearly reports and latest-state records share data rendering and begin with a Contents index linking to native Obsidian headings. Current records contain data and a Latest report link to ../<UTC-year>/reports/<timestamp>-<title>.md, with no Collection metadata section; follow that link for collection account, partial/identity warnings, queries and provenance. The link always targets the selected latest whole observation, including across year boundaries. Historical reports retain the final metadata section. Neither view includes the redundant Field observations table. System values use the seven primary observations from the same retained record when present; no earlier observation supplies missing values. A section with no collected values says No data was collected for this section; a missing collection within a populated section says No data was collected. An observed empty list remains No entries reported. Original field states/times remain available through structured retention reads. Existing pages adopt the new layout on the next enabled consumer refresh or an explicit authorized vault rebuild; no recipe rerun, new collection or retention rewrite is required. The generator replaces its owned Markdown even after manual edits, as described above. CLI example: python -B tools/opsfeast.py vault rebuild --profile main --json. Human notes remain outside generator ownership. Query original structured values with retention show RECORD_ID --profile main --json instead of parsing Markdown. Groups are relative Markdown links, never symlinks. Host-index and overview group cells accept scalar or list membership: group: backup and group: [backup] both display backup; multiple groups are comma-separated. Rendering does not rewrite hosts.yaml. The host-index and overview tables always have six columns, including matching header/delimiter/data rows.

Generated pages distinguish observation/generation times and display controller-local seconds. Original precision remains in retention JSON/SQLite. Host/group IDs use reversible UTF-8 percent encoding and Markdown URLs encode filesystem components as URL targets. One profile has one namespace. Do not place credentials in retained fields or notes merely because content is stored locally.

## Long-lived operation journal

Write/unknown operation evidence belongs to retention. Vault renders intent/outcome links and preserves unresolved/unknown verification states. A successful operation result is not proof of a verified change. Content failure does not erase the journal. See [data/audit interfaces](retention.md#operation-journals-and-module-boundaries).

## Checkout module interfaces

Use `host_vault.rebuild(root)`, `refresh_groups(root)`, `publish(root, owner, entries)` and the vault CLI for content work. Use `profile.retention`, `retention_store.query/show`, `retention rebuild/ingest` and explicit journaling for data work. Storage functions are no longer exposed from `host_vault`.

## Consistency and verification limits

Synthetic tests cover independent storage/content, offline reads/reports, source-qualified selection, partial data, publication conflicts, replacement of edited generated files, stale-output cleanup, replay and protected operation evidence. Vault publication is local; it provides no hosting, transport, automatic private-data migration, Obsidian UI automation, whole-vault atomic snapshot or cryptographic evidence guarantee.

Current selection groups each host by origin namespace, recipe-source qualifier (the prefix before a colon, or the unqualified source) and stable recipe ID, then selects the whole record with the greatest (observed_at, record_id). Recipe-directory moves within that source therefore keep one current page without aliases or rewriting historical references. Partial results remain partial. Distinct sources, origin namespaces or recipe IDs remain independent; a shared output title still fails publication explicitly rather than silently replacing another dataset. All historical reports remain available.

Vault Contents links use Obsidian-native heading fragments: `[System](#System)` and `[Collection metadata](#Collection%20metadata)`. Heading case is preserved and spaces/non-ASCII text are URL-encoded; arbitrary HTML anchor IDs are not used. Repeated headings are given unique readable titles (for example Services details) so each link reaches one section. In Obsidian Reading view, click a Contents link; in Live Preview, use the normal follow-link gesture (Cmd-click on macOS or Ctrl-click on Windows/Linux). Other Markdown readers can use different heading-fragment conventions; this is not a universal reader-compatibility guarantee. Rebuild regenerates current and historical observation pages plus the records index from retention, without recollection. See [Obsidian internal links](https://obsidian.md/help/links).

_Last modified: 2026-10-19 20:06:02_
