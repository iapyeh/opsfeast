# SSHScript Ops to OpsFeast

The product and repository are now OpsFeast (`iapyeh/opsfeast`). The local checkout does not need to move. Private management directories, profile names, targets, credentials, human notes, observations and execution history retain their existing locations and contents.

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

## Git and local integrations

New clones use https://github.com/iapyeh/opsfeast.git. Existing clones can update origin explicitly:

```sh
git remote set-url origin https://github.com/iapyeh/opsfeast.git
git remote -v
```

Review scripts, bookmarks, installed agent skills and local project settings that refer to the old repository or skill paths. Do not modify the bundled .agents/skills/sshscript/ knowledge snapshot as part of the OpsFeast rename. Local checkout paths can stay unchanged; moving a checkout requires separately updating those local integrations.

_Last modified: 2026-10-12_
