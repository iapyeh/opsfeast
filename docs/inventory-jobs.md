# Inventory jobs, immediate queries and periodic collection

System inventory recipe 0.4.0 provides one collection program with independently selectable jobs. Read the [collection table](../recipes/system/inventory/overview/collection-plan.md) for job IDs, contents and starting intervals. The new job observation contract is `inventory-job-observations` 0.1.0; raw job results use schema 0.3.0. Historical whole-snapshot inventory/exchange files remain separate read/replay contracts; new collection has no snapshot execution path. No old-data migration or automatic deletion is performed, and no legacy payload is converted to job samples.

## Discover before running

```sh
python -B tools/opsfeast.py inventory describe --json
python -B tools/opsfeast.py inventory describe --job storage-capacity --json
python -B tools/opsfeast.py recipes show system/inventory/overview --checkout-only --json
```

`describe` needs no profile and performs no connection or writes. It lists human-readable property IDs, job IDs/titles, units, types, entity keys, module namespaces/revisions and exact YANG schema-node paths. `recipes show` exposes the recipe's `collection` declaration, catalog and independent job retention contract. Availability is declared support, not proof that a target probe will succeed.

## Query without keeping a record

```sh
python -B tools/opsfeast.py inventory query --profile main --host node \
  --property storage.filesystems.used_percent --json
python -B tools/opsfeast.py inventory query --profile main --host node \
  --property system.kernel_name --property system.kernel_version --json
```

Select one host and one or more `--property` values or `--job` values; do not combine property and job selectors. Table properties return the measured instances, for example every visible filesystem keyed by source and mountpoint. Instance filtering is not implemented. Query only executes the required probes and their prerequisites, such as platform/actor verification. A shared probe can supply several selected properties. Unsupported fields are explicit gaps.

Without `--save`, results go only to stdout/the terminal. There are no raw result, retention, Vault, host-fact cache or scheduler-state writes by this utility. The response still contains actual sample/source times, actor scope, statuses, errors and property definitions. This does not suppress the target OS's SSH/sudo audit mechanisms. Connections and the existing bounded root-selection/user-fallback policy are real operations and require the user's target/privilege authorization. No packages or agents are installed on targets.

Use `--root PATH` instead of `--profile NAME` when selecting an explicit management directory. Existing connection/jump/trust settings are loaded at runtime through Core configuration. Neither utility mode changes them. `--timeout` bounds connection stages/actor checks and default command duration, and `--budget` bounds the collection commands rather than the whole connection lifecycle. Existing declared source/host recipe variables and `--var`/`--vars-file` remain available; variable values are not included in provenance. `command_timeout_seconds` and `collection_budget_seconds` set collection command budgets.

## Save an immediate refresh for comparison

```sh
python -B tools/opsfeast.py inventory query --profile main --host node \
  --property storage.filesystems.used_percent --save \
  --note "After clearing obsolete application logs" --json
python -B tools/opsfeast.py inventory run --profile main --host node \
  --job storage-capacity --json
python -B tools/opsfeast.py recipes run system/inventory/overview \
  --profile main --host node --json
```

`query --save` and `run` use the same raw → registered normalizer → retention → configured-consumer flow as scheduled jobs. `run` defaults to all recipe-enabled job definitions (schedule overrides control automatic dispatch only); explicitly selecting an opt-in job is an intentional immediate request. The general `recipes run` command also selects this job flow for this recipe. All immediate and scheduled inventory execution uses this job collector. The standalone runner and whole-snapshot execution path are removed; use check-access for separate privilege diagnostics.

Saving requires an initialized retention namespace before connection. Each refresh creates independent raw and retained observation IDs, including repeated equal values. Raw JSON is written under `observations/`; authoritative SQLite remains under `retention/`. Failed probes produce null/unavailable values and reasons, never copied old successes. Acquisition failures are recorded without invented values. An optional note is human-supplied context, not proof that cleanup commands actually ran. A note is accepted by `query` only with `--save`.

Manual refreshes do not advance scheduler timestamps or postpone a scheduled run. They only replace the measured properties in the read-only latest view. Raw save, retention and content updates have separate receipts; inspect all three. Raw retention failures can be investigated/replayed through the existing retention workflow without recollecting. New-format failed job observations can also be replayed; replay never executes the collector or a candidate normalizer.

## Configure a schedule explicitly

Scheduling is opt-in per host in `<profile-root>/inventory.yaml`, separate from `hosts.yaml`. Missing inventory.yaml means no enabled hosts. The default precedence is recipe job definitions → shared `defaults` → host `jobs`. Settings never enable a host by implication.

```sh
# Set a shared job default; does not enable hosts.
python -B tools/opsfeast.py inventory configure --profile main --defaults \
  --job storage-capacity --interval 30m --json
# Override one host/job; the scheduled host remains disabled until enabled explicitly.
python -B tools/opsfeast.py inventory configure --profile main --host node \
  --job storage-capacity --interval 5m --json
python -B tools/opsfeast.py inventory configure --profile main --host node --enable --json
python -B tools/opsfeast.py inventory configure --profile main --host node \
  --job hardware-sensors --disable --json
python -B tools/opsfeast.py inventory configure --profile main --host node --disable --json
```

Intervals accept finite numeric seconds or integer durations with `s`, `m`, `h`, `d`, `w`; the minimum is 60 seconds. A day is 24 elapsed hours. IDs are stable selectors; titles are display text. Unknown IDs, invalid intervals and non-Boolean enabled values fail rather than being ignored. A host's optional `recipe` reference can select an explicitly registered source clone with the same registered property definitions. Different definitions need their own reviewed contract registration, not a changed executable path in the descriptor.

Example configuration (a public synthetic host; enabling it is a real authorization decision):

```yaml
schema_version: 0.1.0
defaults:
  storage-capacity: {interval: 30m}
hosts:
  node:
    enabled: true
    recipe: system/inventory/overview
    jobs:
      storage-capacity: {interval: 5m}
      hardware-sensors: {enabled: false}
```

`configure` writes equivalent JSON, which is valid YAML, atomically. It does not connect or install cron. `--job --enable` enables only that job, not the host. Existing `hosts.yaml` host/source disabled controls still apply. Preserve private configuration; do not copy synthetic host IDs as actual targets.

## Dispatcher and cron

```sh
python -B tools/opsfeast.py inventory status --profile main --json
python -B tools/opsfeast.py inventory dispatch --profile main --dry-run --json
python -B tools/opsfeast.py inventory dispatch --profile main --json
python -B tools/opsfeast.py inventory cron show --profile main --json
python -B tools/opsfeast.py inventory cron install --profile main --json
python -B tools/opsfeast.py inventory cron remove --profile main --json
```

`status` and `dispatch --dry-run` read only. Dry-run reports due work without connection, locks or writes; it is distinct from check-access, which makes real diagnostic connections. Ordinary dispatch runs only explicitly enabled hosts and due enabled jobs, once, with up to four concurrent hosts by default (`--threads 1` is sequential; valid range 1–64). It acquires a nonblocking profile lock; an overlapping tick reports skipped. It determines due jobs before runtime/SSH/privilege acquisition. No due work means no host connection or observation.

The first enabled job without attempt state is due. Each selected job's attempt time is persisted before connection. Success, partial results and failures all advance to the next normal interval. There are **no automatic acquisition retries, backoff, notifications or AI calls**. Retention-consumer delivery keeps its existing independent receipt/retry semantics. A stopped/crashed run leaves its started attempt as evidence and waits for the normal interval; missed intervals are not replayed as a backlog. Setup/persistence exceptions have individual local JSON records under `inventory-errors/`. Ordinary probe/connection failures are in raw job results and retained outcomes. State lives in `.inventory-state.json`; its key separates profile storage, host, source-qualified recipe reference and property-definition digest. Clock rollback delays due work until the elapsed interval is met; no synthetic catch-up observations are generated.

`cron install` adds/replaces one marked minute entry in the **current user's crontab**, using absolute interpreter/script/profile-root paths. It preserves other entries and does not use the system-wide root crontab. It does not enable any host, change the active profile or install a model-driven heartbeat. The entry is pinned to the selected root rather than the future default profile. It runs ordinary reviewed code, not this chat. Standard output is redirected to `/dev/null`; command/setup stderr appends to profile-root inventory-cron-errors.log. Structured attempt/error/observation evidence is also local. `cron show` and read-back verify configuration only; a later scheduler lock-file timestamp or saved attempt is evidence of an actual tick. The computer must be running and the OS must permit cron to access the checkout and management directory. No wake-from-sleep or sub-minute scheduling is provided.

## YANG mapping and data interpretation

Use published modules before extensions. Standard mappings are to specific schema nodes, not arbitrary human-readable names or reused MIB OIDs. The [static property catalog](../recipes/system/inventory/overview/collection.json) records the chosen module namespace/revision/path/type/units and describes deliberate extensions. The [public module snapshots](../recipes/system/inventory/overview/yang/SOURCE.json) preserve RFC provenance and hashes; OpenConfig snapshots also pin their upstream commit and license. The local [extension module](../recipes/system/inventory/overview/opsfeast-inventory.yang) declares the additional nodes.

Samples are **projected property observations referencing YANG schema nodes**, not complete RFC 7951 datastore documents or a NETCONF/gNMI implementation. Partial collection is explicit. Full datastore constraints, cross-node `must`/`when`, configuration enforcement and complete module conformance are not claimed. The runtime validates the registered property/observation contract, including selected primitive constraints such as address-family prefix bounds and interface-state enums. Values use the projection's typed JSON primitives; uint64 consumers must preserve integer precision rather than relying on JavaScript Number. Offline model QA resolves every referenced node against the pinned module sources; JSON Schema validates the data envelope. This distinction permits sparse collection without pretending missing mandatory siblings exist.

For example, `system.kernel_name` uses ietf-system's platform/os-name (utsname semantics); distribution `system.system_name` is separate. Generic link MTU is not silently mapped to IP-layer MTU, resolver-file entries are not claimed to be complete configured DNS policy, and unnormalized platform route rows are not claimed to be complete ietf-routing RIB entries. Public models can have transport/NOS-specific scopes; use an extension when the actual measurement differs and document why. Whole-host DMI evidence does not by itself establish an ietf-hardware physical-component hierarchy.

## Source times, histories and latest views

Each group retains its own ID/title, status, coverage and samples. Each probe has a unique ID, command, start/end/sample times, outcome and bounded reason/type/exit-code evidence; stdout/stderr and credentials are excluded from retained probe metadata. Samples refer to those probes and to declared property IDs, with entity keys where applicable. Each observation includes its measured property definitions, public-node/key-path mappings and implementation digest. Standard module definitions are also bound through the schema/catalog digest; source/version and actual actor scope are retained independently of job intervals. Host identity remains namespace/host-ID scoped unless administratively bound; warnings explain that physical replacement and namespace changes are not independently verified. Do not use a source key as a globally persistent hardware identity.

UTC timestamps retain available fractional precision. Source sample times, CPU measurement windows, collection lifecycle times, ingestion and content-generation times are distinct. Utility and scheduled collections do not read cached inventory values as new samples. Equal values collected again remain separate historical samples; this implementation does not automatically compact, downsample or delete them.

```sh
python -B tools/opsfeast.py inventory latest --profile main --host node --json
python -B tools/opsfeast.py retention list --profile main \
  --recipe system/inventory/overview --json
```

`latest` is a read-only latest-attempt view per property; records and original times remain unchanged. Updating one property does not clear other properties in that job. A newer failure replaces that property's current attempt with a gap, not a carried-forward success. Complete empty enumeration differs from a failed/truncated enumeration; do not infer disappearance from incomplete coverage. Different namespaces, recipe sources and definition digests remain separate. Renamed/recreated devices require identity review, not array-position matching.

Vault renders independent histories and a mixed-age current view with original sample times and source observation IDs. Job-history filenames include a short record digest to preserve manual samples taken within the same second. A manual annotation is visible in its historical report. Trend consumers should use retention APIs, not Markdown scraping. Counters are counters, not rates: calculate deltas only across comparable entities/scopes and valid elapsed times, handling resets/wraps/restarts explicitly. CPU load average and CPU utilization remain different measurements. Gaps are never silently interpolated.

## Reuse, extension and verification

Checkout-level Python interfaces are `inventory_jobs.catalog()`, `collect_host(root, host, properties=[...], save=False)`, `dispatch(root, dry_run=True)` and `latest_groups(records)`. Use the existing Core `profile.retention.query/show` to obtain input records. These helpers are bundled product services, not a new installed stable SDK contract. The collector entrypoint is recipe-local `jobs.collect`; normalizer registration and storage remain shared services. Do not create per-host scripts with copied credentials or load candidate normalizers during replay.

Linux has the broadest probes. Inode/swap, utilization/pressure/counter and sensor additions are Linux-specific in this delivery; other platforms preserve unsupported gaps. FreeBSD/macOS/ESXi retain their documented existing source/normalization limits. Source commands remain bounded by output/item/time limits and require existing tools. No native Linux/FreeBSD/ESXi or remote SSH/su/sudo verification follows from synthetic tests.

Run public unit tests with the selected environment. For complete offline schema/node checks, use Python 3.11–3.13 with pyang 2.7.1 and jsonschema 4.25.1 in a separate QA environment, then `python -B tools/check_inventory_models.py`. After editing properties.py, explicitly regenerate the catalog/schema/extension module with `python -B tools/build_inventory_catalog.py`, then rerun checks. Do not install those validators on targets or modify a user's existing environment automatically. Model files retain their original notices and pinned sources; changing definitions, schema or executable content requires reviewed versioning, tests and documentation rather than silently bypassing saved digests.

## Delivery verification (2026-10-20)

- Current full public suite after entrypoint consolidation: 763 tests passed on CPython 3.11.15, 3.13.13 and 3.14.4. The inventory-specific file contains 29 tests; test_recipe_runner.py adds nine focused unified-entrypoint regressions. Obsolete snapshot-runner/dryrun/force integrations were removed, while independent parser, historical-data/replay, actor, selector, concurrency, report and Vault coverage remains. This supersedes the earlier 808-test count for the dual-runner implementation.
- Offline model QA: 72 property paths and their standard list-key paths resolved; 122 pinned public module snapshots passed digest checks, and the extension/module graph and JSON Schema passed validation. Validators ran in an isolated Python 3.13 QA directory; no target dependencies were installed.
- Native local evidence: macOS with SSHScript 5.0.0 passed a credential-free selective kernel/architecture query with unchanged profile files, followed by two independent saved observations and successful retention/Vault updates. Installed-wheel smoke checks also passed. This does not establish remote SSH, su/sudo or native Linux/FreeBSD/ESXi probe behavior.
- Wheel and sdist builds include all 123 YANG files, public source manifests and the OpenConfig license. Private profile settings, generated observations, local guidance and caches are excluded. Packaging is local verification, not a release or publication.
- Cron management has synthetic preservation/read-back tests. Installation remains an administrator-authorized local action; verify the selected profile has no enabled hosts for a dormant entry. On the development machine, entry installation/read-back and one initial tick were observed with no enabled hosts. A later launch recorded an OS PermissionError while Python accessed its environment in a protected directory; subsequent cron health has not been established. Resolve the OS access prerequisite before enabling hosts. Entry presence and an old lock timestamp do not guarantee future execution.

Reproduce the public suite with `python -B -m unittest discover -s tests -p 'test_*.py'`; run the inventory subset with `-p test_inventory_jobs.py`. Use the model checker described above for schema-node validation. Environment and target-specific evidence must be reassessed when porting this recipe.

_Last modified: 2026-10-20 14:36:51_
