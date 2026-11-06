# Saved-data Web workspace 0.1.0

The local website displays existing data rather than synthetic management records.
Open the launcher's returned URL, sign in and choose a Profile on a data page.
Changing the page's selection does not change the installation's default Profile.
The owner identity, administrator login, host editor and Console remain separate
interfaces with their existing authorization rules.

## Human workflows

- `/workspace`: configured host count, active notifications and open/in-progress/
  blocked todos from the selected Profile. Counts are configuration and saved
  service evidence, not online status. The newest five of each service are shown;
  use **查看全部** to read the service list.
- `/recipes`: the shared static catalog, with Profile/external recipes before
  bundled recipes. Search, source status, versions, metadata and inspection errors
  are available. `?recipe=ENCODED_REFERENCE` selects one exact recipe. Inspection
  does not import recipe entrypoints, verify target applicability or grant execution.
- `/retention` and `/recipes/data`: saved retention index with original observation
  times, host, recipe, kind and status. These are summaries; use Core/CLI for full
  retained data and explicit export. No automatic recollection or rebuild occurs.
- `/work`: saved notifications and todos, including source, state, human fields
  and timestamps. Search or filter by type. Editing remains through the existing
  [Services interfaces](services.md); no issue-tracking service is implied.
- `/logs`: saved Recipe observation runs and Console sessions for hosts currently
  configured in the selected Profile. Shared sessions appear once. Console links
  open read-only `/console/{sid}/history`; they never reconnect or replay commands.
  `?entry=ID` selects a saved entry. This is not a general system log or chat archive.
- `/skills`: actual bundled Markdown sources and references under `skills/`.
  This does not enumerate agent-loaded copies or private Profile skills, or prove
  that an agent used a skill. `/learn` lists local textbook sources; `/docs` lists
  local guides. Search by source path and open `?doc=ENCODED_PATH` to read the
  original text. Source is displayed as inert text, including Markdown and HTML.
- `/settings`: installed versions, explicit official-source checks and a confirmed
  [Agent update handoff](web-updates.md), with Site/Profiles/Bundle Recipe hierarchy.
  Updates are performed by the Agent after the human sends the instruction.
- `/operations` and `/apps`: real Console/host/history and Vault documentation
  entrypoints. Browser-only command playback and speculative mutation controls
  have been removed. No arbitrary Web application host is provided.

Empty sources show an empty state. Read failures show an error, never a fabricated
zero count. Overview service failures are independent; available sources remain
visible with `status: partial`. Data pages have explicit Profile selection,
server-side search and **載入更多** pagination. Times are displayed in Asia/Taipei
with seconds; reading a page does not change source observation times.

## HTTP adapters

Reuse the shared domain interfaces directly for recipes and local agent programs:
`recipe_catalog.catalog(profile.root)`, `profile.services.notifications.list()` /
`todos.list()`, `profile.retention.query()` and `profile.retention.runs()`. These
are the checkout-level interfaces documented in the [capability map](agent-capabilities.md),
[recipe catalog](recipe-experience.md), [Services](services.md) and
[Retention](retention.md). The Web adapter adds presentation summaries and pagination,
not another authoritative store or a new recipe execution service.

Authenticated HTTP clients may use these GET-only adapters:

| Route | Output |
| --- | --- |
| `/api/v1/workspace/summary?profile=NAME` | `host_count`; independent `components.notifications/todos` with status and first five objects |
| `/api/v1/workspace/recipes?profile=NAME` | Projected static recipe catalog and source status; no private source directories or runtime bindings |
| `/api/v1/workspace/work?profile=NAME` | Saved notification and todo objects |
| `/api/v1/workspace/retention?profile=NAME` | Retained record metadata, not full payloads |
| `/api/v1/workspace/logs?profile=NAME` | Saved run metadata and deduplicated Console history references |
| `/api/v1/updates` | Installed version/commit/support evidence; [check API](web-updates.md) |
| `/api/v1/library?kind=docs\|learn\|skills` | Public local Markdown index with `items[].path/title` |
| `/api/v1/library/content?path=docs/cli.md` | Public allowlisted Markdown `{path,content}` as JSON |

Workspace routes require an administrator session or the independent launching-agent
capability. The site-edit capability alone is insufficient. Library routes serve
public product guides only: `README.md`, `docs/**/*.md` and `skills/**/*.md`.
Symlinks, traversal, private profile files, repository metadata and arbitrary paths
are rejected. A source document over 2 MiB is rejected with 413. Existing security
headers and `Cache-Control: no-store` apply.

List adapters return `schema_version: 0.1.0`, `profile`, `read_at`, `status`, `items`,
`total` and nullable `next_offset`. `offset` defaults to 0, `limit` to 100 (1–250).
`q` performs a case-insensitive metadata search before pagination (at most 1000
characters). Work supports `kind=notification|todo`. Recipes/logs support exact
`item_id` selection. `scope=bundle` on the Recipe list uses the checkout catalog without opening a
Profile; `scope=user` excludes Bundle recipes from the selected Profile catalog.
`profile` omission otherwise uses the current default; unregistered
names fail rather than selecting another Profile. Catalog status and errors are
preserved even when a filter yields no entries. Results are live reads rather than
a frozen cursor snapshot; concurrent changes can change offset boundaries.

Unauthenticated reads return 401. Unknown sections/documents return 404. Invalid
arguments or Profile configuration return 422; storage failures return 503. Overview
component failures and missing recipe history in the log view yield a partial
response, with available evidence preserved. Raw exception strings and private
filesystem paths are not used as storage-error messages.

## Compatibility and verification

Synthetic roadmap modules, host drafts and browser-only playback were removed from
the served assets. Old synthetic recipe/log IDs no longer resolve. No saved user
data is deleted or migrated. Recipe execution, service lifecycle mutations,
transfer/archive/import/delete, automatic upgrade and arbitrary Web app hosting
are outside this read-only adapter. Existing Core/CLI capabilities retain their
own scope; use their canonical workflows rather than inventing browser writes.

`tests/test_workspace_web.py` exercises authorization, exact Profile selection,
catalog reads, service objects, saved-history projections, pagination, failures,
document path/symlink rejection and read-only behavior with synthetic data.
`tests/test_workspace.mjs` covers escaping, source rendering, unavailable versus
empty state, Profile-aware links and removal of production mock imports. Native
SSH and remote privilege behavior are not established by these tests.


For incomplete-property causes, Web/CLI inspection and reference-IP recovery, see [result diagnostics](result-diagnostics.md) and [reference addresses](host-reference-ips.md).

*Last modified: 2026-11-05 23:07:10*
