# SSHScript Ops to OpsFeast

The product and repository are now OpsFeast (`iapyeh/opsfeast`). The local checkout does not need to move. Private management directories, profile names, targets, credentials, human notes, observations and execution history retain their existing locations and contents.

## Centralized skill sources (2026-10-13)

The complete bundled SSHScript snapshot moved from `.agents/skills/sshscript/` to `skills/sshscript/`, alongside all OpsFeast skills. Its contents, documentation contract and provenance are unchanged. Environment and bundle-check tools use the new location. Update explicit links and local integrations that used the former path; do not create a second source copy there. Existing agent installation copies are not automatically moved or updated. For duplicate names, version/instruction differences or loader conflicts, preserve local files and agree on the user's integration plan as described in [agent guidance](agent-guidance.md#skill-storage-and-conflict-resolution). Feast-specific user skills use `<management-root>/skills/`; this convention adds no automatic installer or discovery mechanism.

## Parameterized Python recipes (2026-10-13)

run_recipe.py now accepts --var NAME=VALUE and a JSON --vars-file for inventory and general Python-session recipes. Invocation inputs overlay existing defaults/source/host values without rewriting configuration. Existing inventory descriptor/result 0.2.0, legacy collectors without effective vars, host/group selection and retention stay supported. Other IDs require descriptor 0.3.0, runner python-session 0.1.0 and execute(session, *, context, timeout); existing standalone main.py --host programs are not automatically adapted. Move only their operation into execute and declare inputs/results after reviewing the complete implementation. See [execution/migration](recipe-execution.md) and [authoring](recipe-authoring.md). Generic results save raw JSON with skipped inventory retention.

## Name mapping

| Former name | New default | Compatibility |
| --- | --- | --- |
| SSHScript Ops / sshscript-ops | OpsFeast / opsfeast | Update clone URLs and repository references. |
| tools/ops.py / Python import ops | tools/opsfeast.py / import opsfeast | Old CLI/import names are removed; update callers to the new names. |
| skills/sshscript-ops-hosts | skills/opsfeast-hosts | Update skill paths/names and install complete candidates through the agent platform's procedure when authorized. |
| skills/sshscript-ops-recipes | skills/opsfeast-recipes | Update skill paths/names; linked guides remain part of the complete skill. |
| .my-ops.yaml | .opsfeast.yaml | Read and update the existing legacy registry if it is the only one. New checkouts use the new filename. |
| my-ops.yaml, schema 1, kind sshscript-ops | feast.yaml, schema 1, kind opsfeast | Validate each filename against its corresponding kind. Existing definitions are preserved. |
| my-ops/main or my-ops/NAME | feasts/main or feasts/NAME | New profiles use feasts/. Named init reuses an already registered profile's root. Existing directories are not moved. |

The SSHScript library, public skill snapshot, source provenance, recipe IDs and recipe/result versions keep their original identity. There is no new pip-installed OpsFeast package or bare opsfeast executable in this rename; use the Python script entrypoint.

The earlier tools/my_ops.py and tools/ops.py entrypoints are removed. Configuration/data compatibility remains supported; CLI and Python callers must use opsfeast.py / opsfeast.

## Use an existing checkout without data migration

After updating the checkout, use the same interpreter:

```sh
python -B tools/opsfeast.py profiles
python -B tools/opsfeast.py check --profile main
```

Choose an existing profile name from profiles; old schema-1 locators expose the name default, not main. Both commands are read-only and do not connect. Update old commands to tools/opsfeast.py and Python imports to opsfeast; no ops.py wrapper is provided.

Only one registry may exist at a time: .opsfeast.yaml or .my-ops.yaml. Both together fail with a conflict instead of silently preferring one. The same rule applies to feast.yaml and my-ops.yaml within a Feast. Symlinks, wrong entry types and unsupported definitions remain errors; dangling symlinks count as present.

Registry schema 1 is still interpreted as a default profile. Registration or use writes schema 2 to the same active registry filename; read-only commands do not convert it. This preserves prior behavior and does not rename the registry.

## Optional explicit naming migration

Migration is unnecessary for continued use. Perform it only after reviewing the affected paths and authorizing that specific migration. Stop concurrent writers and keep a private backup outside public publication inputs.

1. Check the current profile registry and definitions with profiles/check. If both naming generations exist, review both first and consolidate registrations manually; do not discard an unreviewed file.
2. To rename the registry, confirm .opsfeast.yaml is absent, then rename .my-ops.yaml to .opsfeast.yaml without changing its contents. Schema 1 or 2 remains supported. Keep all profile names, selected default and root values.
3. For each definition being migrated, confirm feast.yaml is absent. In the backed-up my-ops.yaml, change only kind from sshscript-ops to opsfeast, retaining schema_version: 1 and comments, then rename it to feast.yaml. Keep the environment offline during this two-step edit. A filename/kind mismatch fails validation.
4. Leave existing management directories in place. Moving them is a separate operation requiring review of registry roots and any absolute paths or integrations.
5. Run profiles and check for every affected profile. Confirm configuration, notes and historical files were preserved before resuming work. These checks do not establish connectivity or execution success.

The tools do not provide a migration command or automatically rewrite private data. A newer definition schema should be introduced only for an actual contract change, not for a brand rename.

## Profile command names

The former add ROOT command is replaced by attach ROOT, retaining --profile NAME for registration naming. There is no add alias. Detach NAME unregisters an exact name without deleting its management directory; main cannot be detached. Removing the selected default first validates a registered usable main and switches to it atomically, or fails without changing the registry. Profiles now shows basic location status, retaining missing registrations. Registry/definition filename and schema compatibility remain unchanged; see [profiles](profiles.md).

## Host group field

Host membership uses `group: NAME` for one group or `group: [NAME, ...]` for multiple groups. Rename the former `groups` key to `group`, retaining its values and comments; groups is not an alias, and configurations with either the old key alone or both names fail with a migration hint. Omitted group or group: [] means no membership. Run check after updating the defining YAML files, including includes; see [host groups](hosts-yaml.md#host-groups). No connection or recipe execution is required to validate the migration.

## Named recipe sources and input context

Bare inventory/system keeps its checkout meaning; :inventory/system selects profile recipes/, and source:inventory/system selects an explicitly registered recipe_sources root in entry hosts.yaml. Existing recipes/... YAML and ./ instance paths remain supported. Source registrations do not widen include/output paths or authorize execution. Enabled source/host flags and --all --exclude add explicit skips/omissions without rewriting settings. See [sources and controls](recipe-sources.md).

Host recipes lists now accept strings or mappings with vars. Vars-bearing inventory implementations must accept the context keyword and declare inputs.variables; legacy four-argument collectors remain valid without effective vars. The bundled recipe is 0.2.1, with descriptor/result schema 0.2.0 unchanged. Linux implementation is 0.1.2 and FreeBSD/macOS are 0.1.1. Required/type/bound checks and first-level overlay precedence are documented in the [input contract](recipe-sources.md#variables-and-implementation-context); no arbitrary-recipe runner or installer is added.

## Inventory runner arguments

The inventory runner now requires explicit recipe and target selection. Replace positional host/root arguments and --hosts with `run_recipe.py inventory/system --host HOST ... --root ROOT`. Use --group for group names, or exclusive --all for every configured host. A positional recipe must come first; --recipe DIRECTORY may appear at any option position. Omitting the recipe no longer uses host YAML selectors. See the [runner reference](cli.md#toolsrun_recipepy-inventory-execution) for the complete interface, examples and result behavior. Existing YAML recipe selections, profiles and private data are preserved.

## Git and local integrations

New clones use https://github.com/iapyeh/opsfeast.git. Existing clones can update origin explicitly:

```sh
git remote set-url origin https://github.com/iapyeh/opsfeast.git
git remote -v
```

Review scripts, bookmarks, installed agent skills and local project settings that refer to the old repository or skill paths. Do not modify the bundled skills/sshscript/ knowledge snapshot as part of the OpsFeast rename. Local checkout paths can stay unchanged; moving a checkout requires separately updating those local integrations.

## Inventory result pipeline 0.2.2

Updating to inventory-system recipe 0.2.2 adds ESXi dispatch, read-only identity probes and automatic stage-2 retention. Raw schema/descriptor remain 0.2.0; identity and retained/exchange contracts are 0.1.0. Existing management directories receive records/observations.sqlite3 only when eligible data is first retained. Existing raw reports are not scanned automatically; backfill selected originating-source files with observation_store.py ingest. Preserve raw evidence and human records.

Explicit sudo credentials for the connection account can enable failed identity probes; a login password alone does not. Set recipe variable identity_sudo false to disable, or true for authorized passwordless sudo. Existing collection-only authorizations must be reviewed before enabling privilege changes. Root probes are fixed and read-only. No target identifier file is created. See [identity scope and limitations](result-data.md#sudo-selection-and-authorization).

Single/batch runner summaries now include retention and identity_quality; a retention failure returns 1 even if collection status is success. Raw files include a receipt. Consumers must check collection and retention independently. Copies of the retained database preserve source UUID and must not seed independent installations. Structured JSON export/combine, not raw re-ingestion or database file merging, is the sharing path.

Host identity_key, label and description are now supported. An explicit identity_key takes precedence and is shared across Feasts as user-assigned identity; change it after OS reinstall/replacement and coordinate its namespace. label/description are captured human text, never identity keys, and are preserved through retention/exchange. See [the canonical host configuration](../docs/hosts-yaml.md#explicit-host-identity-and-human-readable-metadata) and [identity/metadata rules](../docs/result-data.md#explicit-identity-and-display-metadata). MAC is not an automatic key.

## Inventory 0.3.0 access and result extension

Inventory now tests selected login/root access before the whole batch, attempts sudo by default and collects under the verified root actor. For intentional ordinary-account use, set users.<account>.sudo to the exact quoted string "false". Canonical sudo-password selects by presence; null/empty are empty passwords and "false" selects account password. Legacy explicit sudo vars follow the same presence migration; no alternate-credential retry. Test-host now permits enabled passwordless sudo when no password is selected; check-access/--dryrun are narrower readiness tests without su/platform collection. Review existing authorization before executing the changed defaults.

Six-section inventory-values 0.1.0 is an additive raw/retained/exchange extension; old seven-field results remain readable and unchanged. Update strict validators before reading new extension fields. New report-summary 0.1.1 displays values/scope. Recipe changes invalidate pinned jobs; review and save new definitions without automatic scheduling. No private settings, historical records or environments are rewritten. See [the complete access, CSV and migration guide](inventory-access.md).

_Last modified: 2026-10-14_
