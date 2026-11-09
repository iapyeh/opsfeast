# Host configuration service 0.2.0

`/hosts` now reads the explicitly selected registered profile's real host inventory.
The page supports creation, basic connection/metadata/group changes, and confirmed
host-definition deletion. The CLI and HTTP adapters use `opsfeast.host_settings`;
there is no separate Web configuration store. These operations do not connect,
run proxy commands, test credentials, collect inventory, execute recipes or stop
running work. Search matches Host ID, display name, login account, group IDs, saved IPv4/IPv6
addresses and notes case-insensitively; group selection uses exact catalog IDs. Group input completes declared and implicit group IDs and permits
new implicit groups, preserving ordered membership. The enclosing group of a
bulk host remains its first membership under the canonical loader rules.

## Host workspace presentation

The list provides Profile-wide counts of configured hosts, enabled definitions
and hosts with known saved reference IPs. These counts do not change with list
filters. Enablement is configuration, not connectivity or health; known IPs are
historical evidence, not a live availability check.

Combine the search field, exact group selection and enabled/disabled filter.
The single status message reports matching versus total hosts. **清除篩選** resets
all three filters and returns keyboard focus to search. A Profile with no hosts,
no matching search results and a failed configuration read remain distinct states.
Search runs locally over the inspected snapshot; refresh the page to read updates.

Host rows show display names, login accounts, notes, group labels, complete saved
addresses and explicit configuration badges. On narrow screens the same semantic
table becomes labelled records; long IDs and addresses wrap instead of disappearing.
Opening a host retains its Profile and offers **總覽**, **設定**, **主機筆記**,
**Console 紀錄** and **Recipes**. The overview separates saved IP/source/time
from the latest inventory outcome. Valid source times display in Asia/Taipei with
seconds; missing times stay unknown and unparseable source strings stay visible.
Partial or failed results remain explicit and link to the existing result view.
No search, filter, summary or navigation action collects data or executes commands.

See [Web design and review](web-design.md) for the implementation, design source
and repeatable review procedure. Host service schemas, mutation authorization,
revision checks and storage are unchanged by this presentation update.

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
| `users` | Narrow account-name patches: explicit sudo Boolean to add/update, null to remove |

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
this service. Existing values remain in the original document. Declared accounts
support creation, sudo-policy updates and removal as described below. Password,
account rename and recipe-parameter editing remain outside this interface. The actual host tabs never substitute synthetic run logs
or inventories. Saved reference IPs come from `profile.hosts.reference_ips`, retain
observation time and unknown/empty states, and never select a connection endpoint.
Full inventory rendering remains unimplemented. The Console tab reads saved
history through the existing record service without reconnecting or replaying work.

## Account declarations (0.2.0)

On a host's **設定** page, **已宣告帳號** provides **新增帳號宣告**, **編輯**
and **移除宣告**. Enter a new account name and choose its sudo policy; new Web
account forms default sudo off. Editing an existing declaration keeps its name
read-only and updates its sudo Boolean. Removal opens a dialog showing the account
and host before submission. Focus returns to the account section after success;
validation/conflict errors retain the draft and do not change the displayed list.
The connection account is displayed separately. Removing a declaration does not
change `connection.user` or remove the OS account from the managed host.

The shared `inspect` snapshot and success receipts now use `schema_version: 0.2.0`.
`hosts[].users` contains only explicitly declared host `users` entries; an inferred
connection identity is no longer inserted into this list. `login_user` remains
separate. Clients expecting exact version 0.1.0 must read the updated schema;
no stored host data migration is required. Old snapshots are not rewritten.

`changes.users` is a nonempty mapping of account name to exactly `{"sudo": BOOLEAN}`
for add/update, or JSON null to remove an existing declaration. Names use the same
bounded nonempty, no-edge-whitespace/control-character text check as host IDs.
No implicit rename exists. New declarations receive only the supplied sudo policy;
existing ones merge just that field, retaining passwords, sudo-password, vars and
icons without reading or returning them. Other account fields, empty account
patches, non-Boolean sudo and removing nonexistent declarations fail with
`invalid_host_accounts` or `host_account_not_found` (422). Whole-profile validation,
source selection, revision checks and private pre-change backups apply as before.
An invalid multi-account patch has no persistent partial write.

Examples use the existing authorized Profile and a freshly inspected revision:

```python
from opsfeast.host_settings import inspect, mutate
snapshot = inspect(installation, profile="lab")
receipt = mutate(installation, profile="lab", action="update", host_id="web-01",
    expected_revision=snapshot["revision"],
    changes={"users": {"auditor": {"sudo": False}}})
# Removal is a separate explicit user-authorized operation with a fresh revision:
# changes={"users": {"auditor": None}}
```

```sh
python -B -m opsfeast.host_settings --profile lab update web-01 --expected-revision REV <<'JSON'
{"users":{"auditor":{"sudo":false}}}
JSON
```

The same `changes` object is accepted by administrator/agent-owner-authorized
`PATCH /api/v1/hosts`. This is local configuration editing, not account provisioning,
permission verification, credential recovery or authorization to run a recipe.
Removing an entry removes all of its private fields from the active configuration;
the original source remains in the private pre-change backup. Do not share backups.

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

All host endpoints require an authenticated administrator session or the launching
agent owner capability and enforce same-origin access. Site-edit/interactive-agent/operator tokens and the local
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
`tests/test_web_preview.py`, `tests/test_host_manager.mjs` and
`tests/test_host_accounts.mjs`. They use isolated
synthetic local profiles and preserve source/backup evidence. No real host has to
be added/deleted, connected or initialized to validate this feature.

## Saved Console history

Open a host's **Console 紀錄** tab to browse saved human-directed and agent-led
worker sessions for that exact Profile/host. It shows titles, creation/latest
record times, block counts and recorded failure/unfinished states, with links to
a separate read-only `/console/{session_id}/history` page in a new tab. Refresh and older-page loading are read-only and never
connect or replay commands. Unfinished blocks do not prove a live connection.
See [Console history discovery](console-records.md#discover-saved-console-history-by-host)
for matching, administrator access, pagination and producer conventions.

Example: ask your agent, “Show the saved Console records for web-01 in lab without
connecting.” In the Web UI, select that Profile and host, open Console 紀錄, then
choose a saved title or 檢視紀錄. Empty history and read errors are distinct; retry
a failed read with 重新整理. Keep a direct river URL if the host definition is
later removed. Viewing history does not verify the host's present health.

## Host notes

The host detail now includes a **主機筆記** tab with real shared profile-local notes, search, add/edit and confirmed delete. See [host notes 0.1.0](host-notes.md) for UUID/source/timestamp, CLI/API, concurrency and merge semantics. These notes are independent of configuration backups and preserved Vault README files.

*Last modified: 2026-11-08 23:07:31*
