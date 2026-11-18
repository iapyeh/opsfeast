# Saved-data Web workspace 0.1.0

The `/recipes` entrance is now a simple combined Recipe/meal table. Open names for all per-item actions; create meals through `?meal=new` and manage them through `?meal=ID`. Static labels **可執行 / 不可執行** are distinct from enabled flags. See [meal management and state semantics](web-recipe-menu.md#recipes-review-and-execution-plate).


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
- `/recipes`: the [Recipe discovery/review list](web-recipe-menu.md#recipes-review-and-execution-plate), including incomplete definitions. Search/filter by source, status and category; open
  `?recipe=ENCODED_REFERENCE` for the exact review page. Execution actions require a validated entrypoint.
- `/recipe-plate`: target/recipe/meal selection, parameters and confirmed execution.
  `?add=REFERENCE` adds once to the restored plate; `?run=UUID`, `?history=1` and
  `?report=RESULT_ID` open saved execution/report views. Viewing or adding never
  executes. Old execution/report bookmarks under `/recipes` must use this path.
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
visible with `status: partial`. Daily data pages use only the persisted default Profile, with
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
generic service transfer/archive/import/delete, automatic upgrade and arbitrary Web app hosting
are outside this read-only adapter. Existing Core/CLI capabilities retain their
own scope; use their canonical workflows rather than inventing browser writes.

`tests/test_workspace_web.py` exercises authorization, exact Profile selection,
catalog reads, service objects, saved-history projections, pagination, failures,
document path/symlink rejection and read-only behavior with synthetic data.
`tests/test_workspace.mjs` covers escaping, source rendering, unavailable versus
empty state, Profile-aware links and removal of production mock imports. Native
SSH and remote privilege behavior are not established by these tests.


For incomplete-property causes, Web/CLI inspection and reference-IP recovery, see [result diagnostics](result-diagnostics.md) and [reference addresses](host-reference-ips.md).

## Host system profiling

The host's **系統全貌** tab reads saved inventory values, property-level failed or
uncollected attempts, original sample times and source record IDs. Eight domains
also expose partial and missing integrations. It performs no collection. See
[profiling HTTP/read contract](profiling.md) for authentication, Profile selection,
preview/pagination limits and unsupported contracts. The running Python server
needs the updated routes; browser refresh alone cannot load new backend code.


## Specialized sources in system profiling

The same host 系統全貌 tab now includes saved disk/RAID, configured MySQL replica,
local Linux account/group and visible process snapshots. Instance labels and
source-specific completeness are shown; recipe health is retained as data, not
converted to collection success. The profiling viewer does not run collectors; explicit menu execution is separate.
See [coverage and provider limits](profiling.md).


## Policy/configuration evidence labels

Policy rows now label configured, context-qualified effective, runtime and operator
context evidence. Expand 收集範圍與查詢證據 for the source scope and safe query
argv/timestamps/exit/termination state. Full tool streams and config dumps are not
rendered. Complete means acquired projection, not secure policy or synchronized
time; omitted details/missing providers remain visible. See [policy guide](linux-policy-profiling.md).

## Recipe menu and human-confirmed execution

The [recipe menu 0.1.0](web-recipe-menu.md) now delivers the planned
Web selection workflow: recipe purpose/limits, suggested combinations, the shared
39-capability blueprint, exact targets and inputs, review/confirmation, serial
runner progress/stop and saved receipts. This is separate from read-only saved-data
and profiling views. Opening a viewer or history never collects or retries work.
The original profiling blueprint remains the Bundle target, not a claim that all
current capabilities are complete.

## Current recipe layout preview

The [category-first Recipes page](web-recipe-menu.md#current-category-first-selection-preview-2026-11-10)
is now a selection-only layout review: domain/capability scope, Bundle/User dishes,
sets, configured host/group/All choices and a two-column plate. Extra controls and
indexes are hidden on this main page; saved result URLs/APIs are preserved. The
menu's group membership projection is read-only and exposes no login account.

## Recipe activity names

Activity entries prefer the same human-facing titles used in the Recipes picker.
Web-selected meals appear alongside their executed recipe titles; the original
`recipe_reference` remains secondary text and is still searchable. New confirmed
Web runs snapshot per-task `title` and `meal_titles`, so subsequent recipe/meal
renames or deletion do not relabel those runs. Existing runs resolve currently
available recipe/meal metadata without rewriting saved evidence; unavailable
recipes fall back to the exact reference. Console titles/history links are unchanged.

`GET /api/v1/workspace/logs` returns `title`, `recipe_title`, `meal_titles` and
`recipe_reference` on recipe entries. `opsfeast.recipe_activity.history_labels`
uses the existing Profile and RecipeRuns read interfaces; `meal_labels` follows
nested membership without executing recipes or exposing private variables.
These are checkout-level presentation helpers, not a new retained-data schema.

Activity summaries separate host completion, collection/advisory/report stages and
retention/downstream receipts. Web plate entries expose `web_run_id` from their
saved observation-to-execution association. Observations with the same Web
execution ID appear in one activity row, with the host results and linked worker
rivers inside its disclosure. Its timestamp links directly to
`/recipe-plate?profile=NAME&run=UUID`, with the shared progress and host task
results. Summary titles open the exact Recipe page in a new tab (`target=_blank`,
`rel=noopener`) using `recipe_reference`,
not to the run. The list has Time, Source and Summary columns; it has no separate
Status column. Console/CLI status remains inside its existing detail disclosure.
The activity row shows host completion totals in its closed host-result
disclosure; incomplete-stage summaries and raw JSON are omitted there.
The execution page reads the selected-entry API only when an incomplete host task
is expanded, with `item_id=OBSERVATION_ID&host_id=HOST`. Both result links and
summary targets are restricted to that saved host, including before the six-file
read limit. Its stage/receipt summary appears inside that task, beside diagnosis;
no all-host summary is inserted above task cards during loading.
Missing summary reads show an error without hiding the river or task results.
CLI-only observations have no Web run association and retain their diagnosis
entrypoints. Console links are unchanged. The list uses saved run metadata; selecting an entry
reads at most six incomplete-host result files and shows at most 20 incomplete hosts
with explicit omission counts. Missing raw evidence stays unknown. For CLI-only entries, JSON remains in
the closed advanced disclosure. Reuse `recipe_activity.activity_summary` and the
existing workspace logs API; reads never reconnect, retry or rewrite observations.
Web date/time rendering uses the shared `formatDateTime`/`formatTime` helpers with
Asia/Taipei, seconds and the 00–23 hour cycle, including execution and Console views.

## Activity pagination and deferred results

The Web list requests 25 entries per page with Previous/Next links, retaining
search and Profile scope. It replaces the page rather than accumulating rows.
The existing API accepts `offset` and `limit` (1–250; default 100). Initial lists
read observation metadata, Web labels and Console references without scanning raw
operation results. Recipe entries have `results_loaded: false` and empty
`result_links`; this is deferred evidence, not proof that no results exist.
Expanding the closed result-count disclosure reads the exact `item_id` and
shows its result count/links. A failed read stays visible and can be retried by
closing and reopening. Selected recipe reads skip unrelated Console enumeration.
An optional `host_id` requires logs plus `item_id` (otherwise 422) and scopes
the selected recipe’s targets, links and bounded raw summary to that host.
Metadata catalogs are still read dynamically; no persistent cache or weekly
archive is introduced, and pagination is not a stable historical snapshot.

Single-host task cards use a focused explanation rather than the batch summary:
no one-host totals, repeated headings or raw receipt JSON. The explanation
deduplicates stage/gap reasons, names advisory-cache waiting and download timeouts,
and separates incomplete assessment from saved data. Asynchronous detail reads
patch only the card body, preserving the clicked summary and page position.
Original evidence and report artifacts are not rewritten. The unfinished-task
jump list is removed. Card labels give one outcome; the body omits duplicate
overall status and successful receipts while preserving processing problems. Host
links open separately. Package counts describe acquired installed-package input
records, not findings or evidence that all packages were assessed.

*Last modified: 2026-11-18 14:14:40*
