# System inventory

Recipe 0.4.0 uses descriptor 0.3.0, inventory-jobs runner 0.1.0 and raw job schema 0.3.0. It collects source-timestamped, sparse property observations through one program with independently selectable jobs.

Start with the [collection table](collection-plan.md) for all 11 job IDs, contents and default intervals, and the [inventory guide](../../../../docs/inventory-jobs.md) for utility queries, manual saved comparisons, scheduling, YANG mappings, provenance and verification.

## Implementation choice

The [job collector](jobs.py) uses SSHScript 5.0.0 sessions for bounded local/SSH commands and the shared verified collection-account policy. It reuses [platform parsers](details.py) and recipe-local helpers; no target agent/package is installed. The [internal runner](../../../../tools/recipe_runner.py) and [inventory service](../../../../tools/inventory_jobs.py) own session/actor acquisition, strict cleanup, raw saving and retention-consumer delivery. Public SSHScript skill provenance is in [SOURCE.json](../../../../skills/sshscript/SOURCE.json). Synthetic tests are separate from native evidence.

## Collection contract

The [descriptor](recipe.yaml) declares inventory-jobs 0.1.0 and [collection.json](collection.json). Every job has a human-readable ID/title and a default interval. Every property records types, units, entity keys and a fixed public YANG node or explained extension. Public IETF/OpenConfig modules are preferred; observations are node-referenced projections, not complete RFC 7951 datastores or NETCONF/gNMI support.

## Execute

```sh
python -B tools/opsfeast.py inventory run --profile main --host HOST --json
python -B tools/opsfeast.py inventory query --profile main --host HOST   --property storage.filesystems.used_percent --save --note "After log cleanup" --json
python -B tools/opsfeast.py recipes run system/inventory/overview --profile main --all --json
```

Default immediate runs select the ten recipe-enabled jobs; hardware-sensors is opt-in and can be explicitly selected. Query without --save writes no OpsFeast data. Manual execution ignores due times and does not enable/advance schedules. Real connections and possible su/sudo need target authorization. Read [access policy](../../../../docs/inventory-access.md#inventory-account-selection) before execution. Use check-access for separate diagnostics.

## Recipe variables

command_timeout_seconds and collection_budget_seconds accept positive finite numbers and bound collection command work, not the complete connection lifecycle. Precedence is recipe defaults → source → matching host → vars-file → --var. Values are private runtime bindings; provenance records names only. The obsolete identity_sudo variable is removed; account sudo policy controls privileges.

## Host initialization and selection

The job collector detects the current platform within the collection and does not write a host-fact cache. host-init/test-host remain independent diagnostic workflows. General host/group/all/exclude and registered-source selection are documented in [CLI execution](../../../../docs/cli.md#operational-recipe-execution). There is no selectable snapshot implementation or fallback to older collection code.

## Authoring and execution boundaries

Only reviewed current inventory-job descriptors with the registered property/schema definitions are executable. Custom definitions require reviewed product contract registration; arbitrary candidate normalizers are never loaded during replay. Python executes in process and is not sandboxed. Source/host disabled controls and path boundaries still apply.

## Results and verification

Each job/property preserves original sample times, source commands/outcomes, actor scope, coverage and gaps. Successful empty enumeration is distinct from failed acquisition; newer failure is not replaced with old success. See [delivery verification](../../../../docs/inventory-jobs.md#delivery-verification-2026-10-20) for tested environments and limitations.

## Recipe-owned retention contract

The current declaration is inventory-job-observations 0.1.0, registered with [job_retention.py](job_retention.py) and [job-retention.schema.json](job-retention.schema.json). Raw, retention and consumer receipts remain independent. Vault presents retained data and does not remap property semantics.

Historical inventory-observations 0.1.0 definitions in [retention.py](retention.py) and [retention.schema.json](retention.schema.json), example raw files and parser helpers remain available for saved-data inspection/replay. They do not expose a runnable snapshot collector. Existing histories are preserved without automatic conversion or migration. Read [retention replay](../../../../docs/retention-replay.md) before changing extraction definitions.

## Query evidence and human content

New job records preserve probe IDs, commands, outcomes, errors, times, property definitions and implementation digests without retained command output or credentials. Vault renders independent histories and a mixed-age latest-attempt view per property. A manual note is context, not independent proof that remediation commands ran. Use structured retention APIs for trends.

## Retained data and identity

Identity is scoped to namespace and configured host ID unless administratively assigned; physical replacement is not independently detected. Preserve identity/actor warnings, source references and original times. Missing optional probes remain gaps; consult per-property coverage instead of assuming complete platform support.

tools/run_recipe.py, --recipe, --dryrun/--force and the former snapshot execution route are removed. Use opsfeast.py recipes run or inventory query/run. Existing pinned job fingerprints change and require explicit review/recreation; no user files are rewritten.

_Last modified: 2026-10-20 11:22:14_
