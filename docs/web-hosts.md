# Host configuration service 0.1.0

`/hosts` now reads the explicitly selected registered profile's real host inventory.
The page supports creation, basic connection/metadata/group changes, and confirmed
host-definition deletion. The CLI and HTTP adapters use `opsfeast.host_settings`;
there is no separate Web configuration store. These operations do not connect,
run proxy commands, test credentials, collect inventory, execute recipes or stop
running work. Host ID filtering is case-insensitive; group matching uses exact
catalog IDs. Group input completes declared and implicit group IDs and permits
new implicit groups, preserving ordered membership. The enclosing group of a
bulk host remains its first membership under the canonical loader rules.

## Selection and supported writes

Every service call requires an explicit registered `profile`. UI URLs retain
`profile` when navigating to a host, its settings or the creation form. The
profile selector starts from the current default only when entering the list
without a profile. Missing/invalid profiles do not fall back to another root.
Host IDs are immutable in this editor (1–200 Unicode code points, no edge
whitespace/control characters); renaming is not provided.

New hosts go into top-level `hosts` in the entry `hosts.yaml`. Existing hosts are
updated/deleted in their actual defining source, including included documents and
`groups.NAME.hosts`. The source is displayed before deletion. Supported changes:

| Field | Behavior |
| --- | --- |
| `group` | Canonical string/list membership; input order preserved, duplicates removed |
| `enabled` | Explicit Boolean; new Web hosts start disabled until checked |
| `label`, `description` | Plain text metadata (up to 4,000 code points), no NUL |
| `connection` | Local, direct SSH or SSH-config alias on creation; patches supported fields on update |

Connection fields accepted by the service are `hostname`, `port`, `user`,
`identity_file`, `allow_agent`, `look_for_keys`, `ssh_config_alias`, `local` and
`via: {host: ID}`. Existing connection modes cannot be converted to/from local
through update. Optional `user`, `identity_file` and `via` can be explicitly removed
with JSON null on update; absence preserves their old value. Canonical connection
validation remains authoritative, including alias conflicts, port range, jump
references and cycles. Empty username uses the existing runtime's documented
fallback; it is not evidence of a remote identity.

The Web form exposes common connection fields. Raw proxy commands/environments,
inline jumps, passwords and arbitrary variables are not returned or accepted by
this service. Existing values remain in the original document. Existing users are
shown as names/sudo configuration only; account/secret and recipe-parameter editing
remain unimplemented. The actual host tabs never substitute synthetic run logs
or inventories. Saved reference IPs come from `profile.hosts.reference_ips`, retain
observation time and unknown/empty states, and never select a connection endpoint.
Full inventory rendering and live Console/history integration remain separate work.

## Revision, validation, comments and backup

`inspect(installation, profile=NAME)` uses Core/Validator and a sanitized, allowlisted
projection. Its revision hashes the resolved profile root plus every loaded YAML
source's relative path and bytes. Every mutation requires that revision. Cooperating
profile/host writers serialize through locks; other editors can still race, so all
source bytes are checked again immediately before commit. This is not filesystem
isolation from programs running under the same OS account.

The writer uses pinned `ruamel.yaml==0.19.1` in round-trip mode for comments, quoted
scalars and mapping order, with YAML 1.1 interpretation aligned to the existing
loader. Whitespace/directives can be normalized; byte-identical formatting is not
promised. Candidate canonical data must equal the intended narrow edit, then the
entire profile passes the existing `Validator.check()` before replacement. No
candidate recipe/provider code is imported or executed. A private in-memory
`Validator.read_document` override validates the staged source; it does not relax
include boundaries or schema rules. Files containing YAML anchors/aliases currently
fail with `yaml_alias_edit_unsupported` rather than risking changes to shared nodes.
Unknown fields, malformed configuration and semantic drift fail closed.

Before replacing the one changed file, the writer saves original bytes as
`<profile-root>/.host-settings-backups/<backup-id>/original.yaml` (0600 under private
0700 directories), with a `receipt.json` describing the intended change, source and
before/after revisions. These backups contain credentials from the original file:
do not share, serve or package them as recipe artifacts. A backup can exist even
if the later write fails; its `backup_kind: pre-change` is not proof of successful
application. A successful returned receipt has `configuration_changed: true`.
Atomic replacement writes the updated source as 0600. Automatic backup cleanup,
restore/rollback commands and a general audit/log service are not provided.

Deletion requires `confirmation` exactly equal to the host ID, in addition to
profile/revision selection. The Web shows a modal explaining scope, then asks the
operator to type the ID; cancel or Escape sends no deletion. A host used as a jump
by another host is rejected. Deletion removes only the host definition: observations,
retention, records, human notes, recipe code and remote machines remain untouched.
It does not stop already running work. The original source is backed up first.

## Python and CLI

Install optional writer dependencies in the approved environment using
`requirements-host-settings.txt` (also included by `requirements-web.txt`). Reads
need only the existing Core dependencies. Imports are checkout-level:

```python
from opsfeast import host_settings
snapshot = host_settings.inspect('/srv/opsfeast', profile='lab')
receipt = host_settings.mutate('/srv/opsfeast', profile='lab', action='update',
    host_id='web-01', expected_revision=snapshot['revision'],
    changes={'group': ['production', 'linux']})
```

CLI output is always JSON; it does not accept passwords on argv or stdin. Run from
the checkout or supply `--installation /srv/opsfeast` before the action. Create and
update read one changes object from stdin (max 64 KiB); delete requires typed scope:

```sh
python -B -m opsfeast.host_settings --profile lab list
# Replace REV with the revision just inspected; all values here are synthetic.
python -B -m opsfeast.host_settings --profile lab create web-01 --expected-revision REV <<'JSON'
{"connection":{"hostname":"web.example.invalid","user":"operator"},"group":["production"],"enabled":false}
JSON
python -B -m opsfeast.host_settings --profile lab update web-01 --expected-revision REV <<'JSON'
{"group":["production","linux"]}
JSON
python -B -m opsfeast.host_settings --profile lab delete web-01 --expected-revision REV --confirm-host web-01
```

CLI authority is the local OS account; it neither logs into Web nor proves fresh
human approval. User agents must reuse the user's exact authorized host/profile
scope and obtain deletion confirmation before invoking delete. Never use this
service or a different profile to bypass authorization, credential failures or a
pending operation checkpoint. Configuration changes do not authorize connection.

## HTTP and errors

All host endpoints require an authenticated administrator session and enforce
same-origin access. Site-edit/interactive-agent/operator tokens and the local
site-edit cookie are not host-management credentials. No delegated host API token
has been introduced; local agents can use the shared CLI/Python service within
OS authority and user authorization.

| Request | Input / result |
| --- | --- |
| `GET /api/v1/hosts?profile=NAME` | Snapshot: `schema_version`, `profile`, `revision`, groups, sanitized hosts, `connectivity_verified: false` |
| `POST /api/v1/hosts` | `{profile, host_id, expected_revision, changes}`; create receipt |
| `PATCH /api/v1/hosts` | Same envelope; selected-field update receipt |
| `DELETE /api/v1/hosts` | `{profile, host_id, expected_revision, confirmation}`; delete receipt |

Bodies are bounded to 64 KiB. Unknown body keys are rejected. Authentication/origin
failures return 401/403, stale revision/duplicate/dependent jump conflicts 409,
unknown host 404, validation/unsupported edit or storage failures 422, and missing
optional writer dependencies 503. Errors are sanitized codes, not raw YAML,
passwords or exception snippets. Do not retry ambiguous writes automatically:
reload and reconcile the selected profile before proposing the next action.

Public tests: `tests/test_host_settings.py`, real host API tests in
`tests/test_web_preview.py`, and `tests/test_host_manager.mjs`. They use isolated
synthetic local profiles and preserve source/backup evidence. No real host has to
be added/deleted, connected or initialized to validate this feature.

*Last modified: 2026-11-01 23:38:13*
