# System inventory

## Function, purpose and Agent responsibility

The function is to collect the selected system, hardware, network, storage,
software/service and resource properties with verifiable source/time and explicit
coverage. The purpose is to give administrators and their agents trustworthy
knowledge of the target environment for operational decisions, not merely to
complete a fixed list of shell commands.

If this program cannot obtain an in-scope property, an agent should inspect the
saved cause, use suitable alternative methods within the authorized targets,
actors and effects, and verify the resulting evidence. Preserve unavailable,
unsupported, inapplicable and unknown distinctions; never fabricate values to
satisfy a completeness target. The declared selected properties bound the task;
the purpose does not authorize unrelated probing or modifications.

Record supplementary observations with their actual source/time and verification
limits; do not rewrite the failed run as success or claim unsaved findings are
retained inventory. Host experience belongs in reviewed private notes, while
portable validated methods belong in improved recipe code/tests/guidance. See
[execution experience](../../../../skills/opsfeast-recipes/references/execution-experience.md).


## Accumulated execution experience and lsblk support (0.4.3)

Use [the Agent workflow](../../../../skills/opsfeast-recipes/references/execution-experience.md)
to read Profile-specific host notes and saved results before execution, diagnose
new gaps, and propose reviewed evidence-linked lessons. Existing host notes store
host constraints; general methods become reviewed recipe code/tests. The runner
does not execute note content, call a model, automatically learn commands or cache
per-host strategy decisions.

Linux block-device collection first uses JSON `lsblk -b -J`. Only an explicit
unsupported-option error permits the bounded `LC_ALL=C lsblk -b -P` query with
the same six selected columns. Key/value rows preserve hex-escaped text and byte
sizes; absent optional filesystem/model/mountpoint values stay null. Empty,
malformed, duplicate/missing columns or invalid sizes fail parsing. Permission,
transport and unrelated failures do not trigger another query. Both attempts are
saved; successful samples cite the actual alternate probe. SSHScript execution,
accounts, dependencies, output limits and total deadlines remain unchanged.

`tests/test_inventory_legacy_lsblk.py` verifies synthetic parsing and capability
selection, permission/data failures and source evidence. The original old-Linux
`-J` rejection was observed in a saved result; the new pairs query has not yet
been executed on a managed host. Missing kernel interfaces such as PSI remain
explicit gaps; more time cannot create an unsupported feature. No package install
or host-setting change is part of this improvement.


## Linux iproute2 capabilities (0.4.2)

The existing SSHScript bounded-command collector first requests JSON from
`ip -j address show` and `ip -j route show table all`. When command failure
explicitly reports an unsupported JSON option, it reads `LC_ALL=C ip address show`
or `LC_ALL=C ip route show table all` within the same deadline/output limits.
No package installation, privilege escalation or host setting change is added.
Permission failures, timeouts, malformed JSON and other errors do not trigger
another command. Both the failed JSON probe and the text probe remain in saved
evidence; successful properties reference the text probe's own timestamp.

Address text is normalized into interface names, MACs, MTU/state, IPv4/IPv6
addresses and prefixes. Interfaces without addresses remain represented. Missing
attributes stay unavailable; malformed text does not become an empty successful
address list. Text routes retain `entry` rows rather than guessing structured
route fields. Reference IP publication reuses the normalized interface rows and
excludes loopback. Existing failed results are unchanged and require a newly
authorized collection to obtain fresh addresses.

Verification: `tests/test_inventory_legacy_ip.py` covers synthetic old-iproute2
errors, dual-stack/addressless interfaces, source evidence, reference IPs,
permission failures and malformed text. A human-authorized run on 2026-11-06 verified both text queries on a CentOS 7
host whose iproute2 rejects `-j`; addresses were retained and reference IP
publication succeeded. Other unsupported tools still produce explicit partial
coverage; this is not a claim of complete inventory support on every old Linux.


Recipe 0.4.0 uses descriptor 0.3.0, inventory-jobs runner 0.1.0 and raw job schema 0.3.0. It collects source-timestamped, sparse property observations through one program with independently selectable jobs.

Start with the [collection table](collection-plan.md) for all 11 job IDs, contents and default intervals, and the [inventory guide](../../../../docs/inventory-jobs.md) for utility queries, manual saved comparisons, scheduling, YANG mappings, provenance and verification.

## Implementation choice

The [job collector](jobs.py) uses SSHScript 7.0.1 sessions for bounded local/SSH commands and the shared verified collection-account policy. It reuses [platform parsers](details.py) and recipe-local helpers; no target agent/package is installed. The [internal runner](../../../../tools/recipe_runner.py) and [inventory service](../../../../tools/inventory_jobs.py) own session/actor acquisition, strict cleanup, raw saving and retention-consumer delivery. Public SSHScript skill provenance is in [SOURCE.json](../../../../skills/sshscript/SOURCE.json). Synthetic tests are separate from native evidence.

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

New job records preserve probe IDs, commands, outcomes, errors, times, property definitions and implementation digests with bounded original stdout/stderr for new probes. The original command, streams, states and source times are available in default-collapsed code blocks on current Vault records. Empty, unavailable and truncated streams remain distinct; no redaction is applied by this display. See [capture and retention semantics](../../../../docs/inventory-jobs.md) and [presentation](../../../../docs/host-vault.md#original-command-output). Vault renders independent histories and a mixed-age latest-attempt view per property. A manual note is context, not independent proof that remediation commands ran. Use structured retention APIs for trends.

## Retained data and identity

Identity is scoped to namespace and configured host ID unless administratively assigned; physical replacement is not independently detected. Preserve identity/actor warnings, source references and original times. Missing optional probes remain gaps; consult per-property coverage instead of assuming complete platform support.

tools/run_recipe.py, --recipe, --dryrun/--force and the former snapshot execution route are removed. Use opsfeast.py recipes run or inventory query/run. Existing pinned job fingerprints change and require explicit review/recreation; no user files are rewritten.

## Execution policy, Attention and batch evidence

Configure this recipe with its exact reference system/inventory/overview (bundle: is equivalent), not its descriptor ID inventory-system. default/group/host recipes mappings accept enabled/vars; enabled defaults false, and new init enables inventory in default. Bulk/group/scheduled collection requires enabled host/source/recipe, plus schedule opt-in/due checks. Explicit inventory/recipe --host overrides the three enabled gates for that target; it does not permit disabled jump hosts or invalid vars/paths. See [configuration examples and precedence](../../../../docs/recipe-sources.md).

The optional attention object input defines enabled and thresholds for filesystem_used_percent, cpu_utilization_percent, memory_available_percent and load_5m_per_cpu. The inventory owner validates numeric ranges and direction before connecting; current views evaluate current settings while [completed run snapshots](../../../../docs/observation-runs.md) preserve actual policy/findings/source and baseline evidence. Read [defaults, example YAML and limits](../../../../docs/inventory-jobs.md#attention-thresholds); no findings does not establish full coverage/health. Changing recipe.enabled does not delete old data or hide pages.

Saved manual execution joins one explicit batch; dispatch owns one batch for due work. Unsaved queries, dry runs, raw replay and content rebuild do not create batches or infer old membership. Read inventory runs list/show or Core retention.runs()/run(run_id) without connecting. Raw reports include observation_run_id and the validated nonsecret attention_policy outside the recipe-normalized payload, so existing registered normalizer/schema digests remain unchanged. Vault's [records/reports/batch views](../../../../docs/host-vault.md) are separate optional content over these contracts.

## Reference IP publication (0.4.1)

A successful interface probe emits raw `reference_ips` with deduplicated IPv4/IPv6
addresses, original probe time and source ID. The shared saved-inventory service
publishes the profile-local reference only after raw and retention storage succeed.
The additive raw projection does not change inventory-job-observations 0.1.0,
normalizer/schema digests or property/YANG definitions. `query` without `--save`
never updates local references. Failed/unsupported address parsing and unrelated
selections preserve earlier values; a successful empty enumeration replaces them
with empty lists. Other probe failures do not invalidate successful addresses.

Users/agents read `opsfeast.py hosts list --profile NAME --json` or Core
`profile.hosts.reference_ips(HOST_ID)` without parsing this recipe's results.
Addresses are reference-only and never affect SSH. See the
[complete update, storage, provenance and platform contract](../../../../docs/host-reference-ips.md).
Current ESXi opaque rows and old Linux without `ip -j` cannot supply the projection;
this change does not add tool fallbacks. Public synthetic tests are in
`tests/test_host_reference.py`; no new native host evidence is claimed.


For incomplete-property causes, Web/CLI inspection and reference-IP recovery, see [result diagnostics](../../../../docs/result-diagnostics.md) and [reference addresses](../../../../docs/host-reference-ips.md).

*Last modified: 2026-11-06 14:07:41*
