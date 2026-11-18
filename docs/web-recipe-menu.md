# Recipe menu and execution 0.1.0

The Web **execution plate** (`/recipe-plate?profile=NAME`) is an operational menu over
existing reviewed recipes. It explains the dishes before asking the administrator
to choose targets and confirm execution. This delivers the previously planned Web
workflow; it does not imply the entire profiling blueprint is already collected.
Read [bundle coverage](profiling-coverage.md), [execution](recipe-execution.md),
[results/accounts](recipe-results-and-accounts.md) and [Web authentication](web-administrator.md).

## Recipes review and execution plate

`/recipes` is the simple Recipe and meal index. The table shows name, type,
static state, source and purpose. Names open dedicated pages; there are no per-row
edit/delete/add-to-plate controls. Search/filter and refresh stay on the index,
along with **Create meal** and global category management. All recipes share the same descriptor and detail page.
States are **可執行 / 不可執行** (runnable / not runnable): these
represent static recipe checks or current meal expansion, not the Profile's
`enabled` flags, connectivity, privileges or permission to start work. Meal
readiness requires nonempty reachable contents and runnable leaf recipes; missing,
cyclic, entrypoint-free or empty contents remain not runnable. Refresh rereads sources
without clearing filters; discovery failures are distinct from empty results.

`/recipes?recipe=REFERENCE` owns recipe review/defaults/categories and **Add to
execution plate**. Recipe previews continue updating at the same stable URL and
have no add/run action. See [definition authoring](recipe-definition-authoring.md).

`/recipes?meal=ID` owns meal contents, incoming user-meal references, modification,
confirmed deletion and **Add to execution plate**. `/recipes?meal=new` opens its
creation page. Bundle meals are read-only; a user meal can reference them. User
meal edits retain their ID and validate the entire reference graph, available
recipe members and field scopes before a revision-checked atomic write. Saved
parents retain their child IDs and expand the current child definition. Empty
existing meals can be saved but cannot execute; creation requires members.
Cycles, unknown targets/fields and stale revisions fail without changing the file.

Adding a meal uses `/recipe-plate?meal=ID`, preserves direct recipes, hosts and
other selected meals, and consumes the query after mounting. It never executes.
The plate's **Save as user meal** shortcut also opens the dedicated creation page,
using one-time, tab-local, Profile-scoped member/scope prefill without hosts.

`/recipe-plate` owns target selection, recipe/meal composition, parameters,
execution review, start/stop, saved execution rivers and report/artifact viewers.
Its sidebar label is **執行餐盤**. A runnable recipe's **Add to execution plate**
link uses `/recipe-plate?add=EXACT_REFERENCE`: it merges that reference into the
current Profile's restored tab-local selection, preserving hosts, meals and scopes.
It never executes. The add query is consumed after mounting, so reset followed
by reload keeps the plate empty. Invalid/non-runnable add references are ignored.
Only the later reviewed and human-authorized start may run commands.

| Intent | Current URL |
| --- | --- |
| Recipe and meal index, including incomplete definitions | `/recipes` |
| Meal review/management | `/recipes?meal=ID` |
| Create meal | `/recipes?meal=new` |
| Exact recipe review | `/recipes?recipe=REFERENCE` |
| Compose this execution | `/recipe-plate` |
| Add one runnable recipe | `/recipe-plate?add=REFERENCE` |
| Saved execution river | `/recipe-plate?run=UUID` |
| Saved execution list | `/recipe-plate?history=1` |
| Report/artifact | `/recipe-plate?report=RESULT_ID&artifact=DECLARED_PATH` |
| Combined activity | `/logs` |

These operational URLs use the saved default Profile; an optional matching
`profile=NAME` preserves exact local links. Cross-Profile daily-work protection
remains unchanged. Settings source catalogs retain their existing ownership rules.
Activity timestamps open the saved plate river; summary titles open exact Recipe
reviews in a new tab. River/report return links name the execution plate or activity.
Sidebar and overview expose Recipes and the execution plate separately. Login
allowlists preserve each supported destination and reject external/duplicate or
inappropriate parameters.

**Development-stage URL change:** old `/recipes?run=...`, `?history=1` and
`?report=...` bookmarks must change their path to `/recipe-plate`, retaining query
values. There is no compatibility redirect; `/recipes` now owns discovery/review.
Exact `?recipe=...` definition/review URLs are unchanged. Saved run/results, recipe
references and the tab-local plate storage key are unchanged; no data migration,
rerun or automatic promotion of drafts occurs.

Public tests cover catalog filtering/escaping, empty/error states, draft action
exclusion, add/restore/reset behavior, default-Profile scope, both login allowlists
and activity/report/river links. Browser verification uses a separate synthetic
installation; it covers draft review, adding a runnable recipe and category edits
without starting a recipe or connecting a host.

## Current category-first selection preview (2026-11-10)

The main `/recipe-plate` page is currently a layout/selection preview, following the
owner's requested order. It presents these sections, with scope/execution review available from the plate:

1. Initially closed, independently expandable domain panels: hardware/environment, storage/filesystems, OS/software,
   network, workloads, identity, observability and analysis. Each expanded panel starts
   with a **Scopes** heading at the same level as **Bundle recipes** and **User recipes**, followed by capability summaries (inventory/configuration/state/metrics/events,
   partial/not-integrated labels) and directly visible scope descriptions, then
   **Bundle recipes** above **User recipes**, each with selectable rows. Empty
   User sections are omitted. Reports
   and uncategorized recipes get additional panels when present. Empty domains and
   empty Bundle lists remain explicit rather than hiding missing capability.
2. Suggested combinations, which add a meal reference to the plate without flattening it.
3. Host selection: individual configured hosts, resolved groups and All. The login
   account is not displayed. Profile selection, when needed, belongs in this area.
4. A plate with two columns: selected hosts and selected recipes/meals, with counts.

Recipes spanning several capability domains appear in each relevant category;
all checkboxes for the same exact reference stay synchronized, and the plate
lists the recipe once. User/external recipe paths infer a category from their
existing domain/subdomain taxonomy when no provider capability map exists;
unknown paths stay uncategorized. Classification is discovery guidance, not a
claim of native applicability or a newly integrated profiling provider.

Group and All are selection shortcuts over **enabled** configured hosts. Individual
selection can include a disabled host explicitly; that state remains visible.
Checkboxes reflect the resulting exact host set, including partial (indeterminate)
group/All state. Overlapping groups deduplicate Host IDs. Unchecking a group
removes its enabled members from the selection; other group checkboxes recompute
from that resulting set. Names/counts never imply current reachability.

Selecting recipes/sets/hosts updates a tab-local sessionStorage draft, scoped to the
Profile root digest. It makes no connection, starts no worker, writes no server
settings/observations and grants no execution scope. Reloading or returning from a
recipe page restores known available selections; different Profiles use separate
drafts. **Reset · 清空餐盤** clears the current plate’s hosts, direct recipes, meals and
field scopes, synchronizes all selection checkboxes and replaces only this Profile’s
tab-local draft with an empty selection. Reloading keeps it empty. Saved meals,
recipe defaults and other Profiles’ drafts are preserved; no server request or
execution is triggered. The draft ends with the browser session and is not a saved user meal. Search, the category
filter, global blueprint panel, source dump, global parameter/timeout panels, report index and run-history sections remain
separate. The plate now offers field selection and explicit execution review. Existing data and execution/report APIs are retained.
Saved `/recipe-plate?profile=NAME&run=UUID` and report/artifact URLs still open their
separate result views; reading a result never retries it. The prior parameter and
confirmation templates remain available for a later reviewed layout iteration,
and are now reached through the plate review.


## Recipe pages, defaults, categories and user meals

On the execution plate, click a recipe **title** to open `/recipes?profile=NAME&recipe=EXACT_REFERENCE`
in a new tab (`target=_blank`, `rel=noopener`); meal-member links behave the same.
The original menu and plate remain in place;
the separate labelled checkbox selects it without opening the page. A Profile is
required for data/defaults. The page separates declared collection fields/contracts
from actual retained historical records. Inventory exposes its property catalog;
other recipes expose their retention/output declarations. Dotted field IDs form
a tree: `system.hostname` and `system.kernel_name` sit inside the initially closed
`system` disclosure. Deeper levels and schema array-item paths remain nested.
Single fields remain directly visible; descriptions/types/units accompany their
items. The complete raw contract stays available as a separate disclosure.

Declared input options whose **exact name matches a field ID** appear inside that
field item, including an object node when applicable. Unmatched recipe-wide inputs
appear under **Technical details and composition → Common options and save**.
Use **Save default options** there to save changes from both locations through
the same typed Profile-default service. When editable options appear with a
field, the field panel links to the save section.
This placement does not invent per-property inputs, change collection selections,
or create thresholds from arbitrary field names. Inventory currently declares
recipe-wide attention/budget/timeout inputs, so these remain common options. Saved records preserve
Host ID, namespace, source time, recipe reference, dataset completeness/gaps and
original data. Host filtering and pagination (5 records initially, at most 20 per
request) do not collect again. Previews truncate at 32,768 characters; expand or
download the full record (16 MiB response limit). A missing namespace/read failure
is unavailable, not an empty successful history. Recent raw attempts and their
retention/content receipts remain separate; an older retained success must not
hide a newer failed attempt. Existing report artifacts open the shared viewer.

**Default options** edits only declared, nonsensitive variables in the selected
Profile's existing `hosts.yaml default.recipes.EXACT_REFERENCE.vars` layer. Enable
an override, enter a typed value (JSON for non-string inputs), then save; clearing
the override restores the recipe/source value. Descriptor types/ranges are checked.
Precedence stays recipe -> source -> Profile defaults -> groups -> host -> invocation;
the page is not a per-host effective-value editor. It never changes Bundle source,
enabled flags, execution policy or credentials. Sensitive values are masked and
not editable here; new nested secret fields are rejected. Comment-preserving YAML
editing requires `requirements-host-settings.txt` (ruamel.yaml); missing dependencies
produce an explicit editor error and are never installed automatically. YAML aliases
are refused. Source
and code revisions are checked before save; stale saves return 409 without discarding
form text. Original entry bytes go to private `.recipe-default-backups/UUID.yaml`.

**Other / uncategorized** means no identified/selected category, not all user or
external recipes. Their recipe pages can assign multiple builtin or user categories,
clear all to place in Other, or restore automatic classification. Bundle recipe
assignments and builtin category names stay fixed. **Manage custom categories**
on the menu creates a category or edits its title/description while preserving its
ID and memberships. Creation/renaming belongs only on the Recipes page. Recipe pages contain assignment
controls plus a link to the menu manager, without a category-creation form.

Suggested and user meals expand/collapse to show recipes and nested meals. **Join this meal** adds the meal itself to the plate and preserves existing recipes, meals and host selections. The plate displays each selected meal with expandable contents and a remove-from-plate button. It does not replace selections or copy a meal's recipes into direct selections. Empty user meals remain labelled and cannot be added alone for execution. Missing recipe/meal references remain visible; preview fails instead of silently executing only the available subset. Rendering is bounded to 200 meal nodes per tree; the execution review shows the fully resolved distinct recipes.

**Save plate as user meal** creates a definition with a name, description, direct recipes, nested meal IDs and direct recipe field scopes. It saves no hosts, groups, variables, credentials, identities, jobs, schedules or execution authority. Host choices belong to this run's tab-local draft only. The dedicated creation/edit page allows reviewing members and their fields. Saved user meals support **Modify** and confirmed **Delete** on their own page; modification preserves the existing ID. Names are display labels, never reference identities.

Meals reference current definitions, not snapshots: Bundle updates change the effective contents of outer meals. User IDs are UUIDs; product-owned IDs have a `bundle:` prefix. Validate the complete graph on reads and writes and before preview; reject cycles and unknown IDs. Deleting a user meal atomically removes its incoming references from every user meal. Confirmation lists directly affected parents; transitive outer meals naturally see the resulting contents. Empty parents are retained, never cascade-deleted. Historical execution records and recipe/retention data are unchanged. Stale revisions fail with 409, including when another tab changes parents before deletion.

Execution preview resolves nested references on the server and executes each exact recipe reference once per selected host (reports once locally). Explicit property scopes, job scopes and recipe default scopes resolve to property sets whose union is collected. A default scope contributes its actual default fields, not every optional field. Different references remain distinct even if they collect related data. Conflicting variables/report inputs for the same reference are rejected rather than arbitrarily selected. Empty resolved selections and unavailable recipes fail. The 32-distinct-recipe limit applies after expansion; there is no separate host or invocation count cap. Review displays the effective fields and target/permission plan before confirmation. Meal definitions are fingerprinted; changed definitions require a new review before starting. Once started, the confirmed expanded work remains fixed.

### Profile-local menu preferences 0.2.0

`recipe-menu.json` is a versioned Profile-local document, separate from recipe code, retention and installation-level execution history:

```json
{
  "schema_version": "0.2.0",
  "categories": [{"id": "user-UUID", "title": "Owner checks", "description": "Scope"}],
  "assignments": {":system/network/check/local": ["network", "user-UUID"]},
  "sets": [{"id": "UUID", "title": "Daily checks", "description": "Scope", "recipes": [":system/network/check/local"], "meals": ["bundle:inventory-overview"], "selections": {}}]
}
```

Every meal requires exactly `id`, `title`, `description`, `recipes`, `meals`, `selections`. `selections` maps direct exact recipe references to either `{"properties":["FIELD"]}` or `{"jobs":["JOB"]}`. Omission of a recipe key uses that recipe's defaults. Creation requires at least one direct recipe or meal reference; update/deletion may leave an empty existing definition, which cannot execute. All member IDs are unique within each list. Builtin category IDs: hardware, storage, software, network, workloads, identity, observability, analysis, reports, custom (Other). Reference keys must be exact: bare Bundle path, `:path` for Profile recipes, or `source:path` for registered external sources. Limits: 64 custom categories, 1,000 assignments, 100 user meals, 100 direct recipes and 100 meal references per meal, 1 MiB document. An empty assignment is explicit Other; deleting an assignment restores inference. Symlinks, malformed documents, unknown versions and duplicate IDs are refused, never silently overwritten. Writes are locked, revision checked and atomic; prior bytes remain privately in `.recipe-menu-backups/UUID.json` without automatic expiry.

**Incompatible change:** preferences 0.1.0 (flat recipes plus hosts) and old tab drafts are not loaded or automatically migrated. Existing files are preserved. If an old `recipe-menu.json` exists, preserve it separately and deliberately recreate categories/assignments/meals under 0.2.0; remove host membership from recreated meals. Do not delete private files automatically. There is no migration/import command. CLI execution and historical observations retain their existing contracts.

### Authenticated service and agent workflow

All routes require administrator or owner-controller capability and same-origin
checks; a presentation-only edit token cannot read/write these Profile resources.
Use the selected installation's existing owner controller `request` operation;
do not scrape UI data or invent a separate settings store.

- GET `/api/v1/recipe-detail?profile=NAME&reference=REF&offset=0&limit=5&host=ID`:
  declarations, defaults revision, preferences revision, saved data and recent attempts.
- GET `/api/v1/recipe-detail/record?profile=NAME&reference=REF&record_id=ID&download=true`:
  exact-reference-checked saved JSON; omit download for inline JSON.
- POST `/api/v1/recipe-detail/defaults` with exact keys `profile`, `reference`,
  `expected_revision`, `changes` (typed variables object), `remove` (variable names).
- POST `/api/v1/recipe-menu/preferences` with exact keys `profile`, `expected_revision`,
  `action`, `changes`. Actions: category.create/update (title, description; update
  includes id), recipe.categories (reference, categories list or null to reset),
  set.create (title, description, recipes, meals, selections),
  set.update (the same fields plus id; Bundle IDs are rejected), set.delete (id only). Successful writes return the new preferences/revision.

For an authorized local meal edit, reuse the shared facade instead of editing
`recipe-menu.json` by hand:

```python
from pathlib import Path
from opsfeast import Instance, menu_preferences

product = Path.cwd()
selected = Instance.open(product).profile("main")
state = menu_preferences.inspect(selected)
meal = next(m for m in state["sets"] if m["id"] == "USER_MEAL_UUID")
changes = {**meal, "title": "Updated monitoring meal"}
saved = menu_preferences.mutate(product, profile=selected.name,
    expected_revision=state["revision"], action="set.update", changes=changes)
```

Use the operator-selected Profile and exact existing ID. Supply the complete
replacement definition; omitted members are removed, and omitted fields fail.
The API neither switches the default Profile nor connects to hosts. A stale save
requires reading and reconciling the latest definition, not an automatic retry.

Checkout facades are `opsfeast.recipe_detail.inspect/record`,
`opsfeast.recipe_defaults.inspect/update`, and `opsfeast.menu_preferences.inspect/mutate/expand`. `expand(profile, recipes, meals)`
returns `(deduplicated_choices, definition_digest)` without writes or connections.
Each direct choice has reference, vars, inputs and optional inventory_selection.
POST `/api/v1/recipe-runs/preview` accepts profile, hosts, recipes, timeout and
optional meals (meal-ID list); an empty recipes list is valid with nonempty meals.
They are checkout-level services, not a separately versioned Core API promise.
Read first, explain exact Profile/reference/host scope and consequences, reuse human
authorization, then write with the returned revision. On conflict reread and ask
for any material choice; never overwrite a newer edit automatically. These calls
neither connect nor grant authority to execute a later recipe. Non-retained custom
outputs need their own declared retention/report contract to appear as saved data.

## Select inventory jobs and individual sensors

The plate provides a field-scope editor for each inventory recipe: keep its defaults or explicitly select catalog properties, including sensors. Saved user meals preserve these scopes. The API additionally supports job-group selectors. The supported selector contracts are:

- **Default general jobs:** the ten currently default-enabled jobs, excluding
  hardware-sensors. This preserves existing recipe defaults.
- **Choose job groups:** explicitly choose one or more of the eleven catalog jobs.
  General jobs start checked; **Clear jobs** allows a sensors-only selection.
  Hardware sensors remain unchecked until explicitly selected. Choosing this group
  selects both temperatures and fans, subject to target support and permissions.
- **Choose individual fields/sensors:** open a group and select the exact property
  IDs, including sensors.fans alone or sensors.temperatures alone. At least one
  field is required; job and property modes cannot be combined. Table instance
  filtering (for example a single fan device) is not implemented.

The interface reads the actual reviewed inventory catalog: 11 jobs / 72 fields.
It displays IDs, descriptions and units; no new inventory data/schema is invented.
Changing mode or checked values invalidates the previous preview. Confirmation
shows the effective groups and all selected fields. Selection is bound into the
preview fingerprint and worker revalidation. A changed selector/catalog cannot
reuse a previous confirmation.

Only selected properties and their shared prerequisites run. The common runner
forwards the scope to the existing inventory job collector; its raw result,
retention normalization, actor selection and consumer receipts remain unchanged.
A shared query can serve several properties; choosing one field is not a claim
that no prerequisite command is needed. Manual Web execution never enables,
changes or advances a schedule. Unsupported sensors or missing tools/permissions
remain explicit gaps. No target software is installed automatically.

## View and download report artifacts

Saved run views offer **Open report artifacts**. The report index remains available
through the API independently of Web execution history, including CLI-generated
reports; its main-page section is hidden for this layout preview. The API is Profile
scoped and paginated (50 by default, maximum 100), preserving original status/times.
Invalid result files produce a partial index rather than a complete-looking empty list.

The viewer URL is `/recipe-plate?profile=NAME&report=RESULT_ID&artifact=DECLARED_PATH`;
artifact is optional and defaults to the first declaration. Login preserves this
exact destination. Select any declared artifact, inspect its size/digest, and:

- HTML has a static preview in an opaque-origin iframe sandbox. The server strips
  scripts, meta refresh, frames, forms, external image URLs, navigation attributes
  and event handlers. Safe structural markup/tables, inline styles and selected
  static SVG elements remain. CSP disables scripts, connections and external
  resources. The preview may differ from the original interactive report; it is
  not an arbitrary HTML application host. The original source is separately readable.
- UTF-8 text/Markdown/JSON/XML/SVG is shown as inert text, not executable markup.
  Common raster images (PNG/JPEG/GIF/WebP) have an image preview. Other formats,
  including PDF, offer download for the user's chosen reader.
- **Download original** returns the exact verified bytes as an attachment, not
  executable HTML in the workspace origin. It does not publish or transfer a file
  to any external destination.

Every read/download uses the existing declared-artifact resolver and SHA-256/size
check, refuses missing/changed/undeclared files, traversal and symlinks, and
rechecks the exact served bytes. Individual artifacts are bounded to 16 MiB;
oversize, non-UTF-8 text or unreadable artifacts report an explicit failure.
Listing metadata is not proof that the artifact still passes verification.
Viewing/downloading never reruns recipes, recollects, updates retention, dispatches
consumers or creates new observations. The original report/result contracts and
artifact files are not rewritten. User/private data stays within its Profile.

## Authorization, privacy and worker lifecycle

The authenticated installation administrator or memory-only owner capability can
prepare/start/stop; site-edit tokens cannot execute. All mutations require the
same-origin gate and bounded JSON. Human confirmation authorizes precisely the
previewed selection; discovery, saved-data reads and a recipe's prose do not.
Agents still need the user's actual operation grant before submitting a start.

Explicit hosts retain the CLI rule: host/source/recipe enabled gates can be
bypassed for those selected targets, not for disabled jump hosts. The confirmation
shows that rule. Generic recipes use the configured login/su/sudo execution
policy; inventory retains its bounded actor/root-selection policy. Preview identity
is configured, unverified identity; actual evidence comes from execution results.
Configured consumers may write content or send messages after retention. Review
those private effects before approving; read-only target queries do not imply
that all downstream operations are side-effect-free.

One Web service process owns one confirmed selection at a time, with bounded parallel host lanes (8 by default). There is no fixed host/invocation count cap; previews retain the 64 KiB request-body limit and 32-distinct-recipe limit. Previews expire after ten minutes; at
most 32 pending previews are held in memory. A repeated confirmed start with the
same preview returns the original run, without retrying it. Recipe Python,
descriptor, loaded host documents, effective inputs, selected identity, feast.yaml,
inventory.yaml and selected report input hashes are checked after preview and
immediately before each worker runs. Inventory selection/catalog hashes are included. Changes require a fresh review. This is
change detection, not a sandbox, code signature or filesystem transaction; keep
trusted code and configuration stable during execution.

The POSIX controller starts its own Python worker with fixed argv and JSON stdin.
The worker invokes the same `recipe_cli.execute` / recipe runner / report executor
as the CLI. Typed overrides stay in memory/stdin; no plaintext input file, secret
argv or alternative connection implementation is introduced. The Web service's
existing execution environment and dependencies must already work; nothing is
installed. The implementation requires Python 3.11+, existing Web requirements,
and matching SSHScript 7.0.1 for operation recipes. Native Linux recipe/tool scope
and verification remain in each recipe's guide.

Each worker has a ten-minute wall deadline. The selection's timeout (1–120 seconds,
default 30) remains the existing per-command/connection-stage budget, not a whole
recipe deadline. Progress retains the last 64 KiB per task, with truncation marked.
The wheel/sdist include the Web HTML, CSS, SVG and JavaScript modules; the Web
adapter resolves them through bundled resources in both checkout and installed use.
Final runner JSON capture is bounded to 4 MiB; invalid/oversize output is a failure,
even if raw/retention evidence was already saved. Receipts exceeding 64 KiB are
reduced to IDs/status with an explicit preview-truncated marker. Further tasks
continue after ordinary failures; there is no automatic retry, resume or schedule.
Closing the browser does not stop a run. Graceful Web shutdown requests stopping
owned workers; an unexpected restart shows old running records as interrupted and
never signals a saved PID or replays work. Use one owning Web process per installation;
these controls do not coordinate independent controllers across servers.

Saved records live in installation-data `recipe-runs/UUID.json`, separate from
profile observations, retention and content. New directories/files request modes
0700/0600. Records contain the confirmed profile/target/recipe/version, requested
identity, hashes, input names, bounded progress, receipts and stop evidence. Input
values are not independently stored here, but recipe output, artifact titles and
stderr may contain values; there is no universal secret-redaction guarantee.
Only reviewed code should print diagnostics. Records are not automatically deleted.
Profile scoping binds the registration name, resolved management root and retention
namespace. Reusing a Profile name for another root does not expose the old records
or continue a preview; detaching/reattaching does not migrate them. Lifecycle integration
and explicit archival/deletion of execution records remain later work.

## Interfaces for agents and product contributors

`opsfeast.recipe_menu.menu(profile=None)` is static/read-only and returns schema
0.1.0, actual items, four suggested sets, safe source status and the shared
profiling blueprint. `opsfeast.recipe_runs.RecipeRuns(product, data_root)` supplies
preview/start/show/list/stop/close in the running Web process. These are checkout
services, not an installed plugin API or a second scheduler. Do not instantiate a
new service to take over active workers; use the owning authenticated HTTP API.

| Method and path | Inputs / output |
| --- | --- |
| GET /api/v1/recipe-menu | Optional explicit profile; catalog/blueprint, configured host IDs/labels/enabled states and resolved groups (id/title/host_ids); no login account names. No profile lists Bundle only. |
| POST /api/v1/recipe-runs/preview | Required profile, hosts (distinct IDs), recipes, timeout; optional meals (distinct meal IDs); returns preview_id, pairs, overrides, expiry, scope/visibility limits. Each recipe has reference, vars (typed object), inputs (result-ID array), and optional inventory_selection (see below). |
| POST /api/v1/recipe-runs | Required preview_id and confirmed:true, optional threads (positive integer); returns the saved run. No editable command/argv or arbitrary program endpoint. |
| GET /api/v1/recipe-runs?profile=NAME | At most 100 newest summaries with total count; no automatic history deletion. |
| GET /api/v1/recipe-runs/UUID?profile=NAME | Profile-scoped task states, progress, receipts, local-termination and remote-cleanup evidence. |
| POST /api/v1/recipe-runs/UUID/stop | Exactly profile; returns acknowledgment. Poll the saved run for the final state. |
| GET /api/v1/reports?profile=NAME&offset=0&limit=50 | Profile-scoped saved report index, original times/status and partial-index evidence. |
| GET /api/v1/reports/result?profile=NAME&result_id=ID | Report metadata and declared artifacts only; no raw server path. |
| GET /api/v1/reports/artifact?profile=NAME&result_id=ID&name=PATH&mode=text | Verified UTF-8 content JSON. mode=preview is static HTML or raster image; mode=download is an original-byte attachment. |

Requests are bounded to 64 KiB for previews and 8 KiB for other mutations. Errors:
401 unauthenticated; 403 cross-origin; 413 too large; 415 wrong content type; 422
invalid selection/configuration; 409 expired/changed preview or another active
selection. Errors never return raw configuration or credential exceptions. Worker
failure, malformed JSON, missing tool/runtime and scope limitations remain failed,
partial, unsupported or skipped evidence rather than fabricated success.

Example preview body (synthetic names, actual execution requires authorization):

```json
{"profile":"main","hosts":["node"],"recipes":[{"reference":"system/access/inventory/ssh-policy","vars":{},"inputs":[]}],"timeout":30}
```

After the human has reviewed the exact returned plan, start with
`{"preview_id":"RETURNED_VALUE","confirmed":true}`. Retain the returned run ID;
poll show, then inspect raw/retention/content separately. An owner agent uses its
existing [memory-only controller](agent-owner.md); do not create or save a new token.
CLI remains `python -B tools/opsfeast.py recipes run REFERENCE --profile NAME
--host HOST --json`. There is no new CLI subcommand. Checkout contributors may
use `recipe_cli.execute(root, spec, json_output=True, variables={...})` for typed
in-memory invocation inputs instead of vars_file; combining the two is rejected.
Input resolution and required/type/range checks remain the existing common path.
For inventory, pass optional `inventory_selection={"jobs":["hardware-sensors"]}` or
`{"properties":["sensors.fans"]}`. Omit/null means defaults. Empty, duplicate,
unknown, mixed job/property selections and selectors on non-inventory recipes
fail before connection. `opsfeast.recipe_runs.prepare_pair` resolves this scope data-only;
the worker and `recipe_cli.execute(..., inventory_selection=...)` forward it to
the same `recipe_runner.run/execute_hosts` and inventory collector. This adds no
new CLI flags and does not replace inventory run/query.

Checkout `opsfeast.report_view.list_reports/show_report/read_artifact` provides
read-only artifact projection; read_artifact returns verified metadata/bytes and
static_html builds the restricted preview. Recipe report helpers support optional
max_bytes on show_artifact/validate_artifacts for bounded readers. Extensions must
keep declared-path/hash checks, opaque sandbox, inert text, bounded reads and
separate execution authorization. No arbitrary artifact directory or external
renderer is mounted.

## Verification

Public tests: `tests/test_recipe_runs.py`, `tests/test_recipe_run_view.mjs`, `tests/test_recipe_menu.mjs`,
`tests/test_web_inventory_reports.py`, `tests/test_report_viewer.mjs` and affected
workspace/login tests. They exercise real static discovery, no-write preflight,
changed/expired/confirmed selections, strict targets/types/report input resolution,
real offline worker/artifact generation, idempotency, owned-process stop with
remaining work skipped, recovery without replay, authentication/origin/body gates,
escaping and distinct partial/unknown outcomes. Shared-progress tests cover interleaved host receive order, line timestamps, shared-worker attribution, persisted events, bounded truncation and missing historical events. All host transports are synthetic
or absent; no managed host or native Linux tool applicability is inferred.

## Delivery evidence (2026-11-09)

- Complete local regression: 1,366 Python tests and 82 JavaScript tests passed.
  An initial existing interactive Console stop/cleanup test failed; all 15 tests
  in that group passed on isolated rerun, followed by the passing complete suite.
- The 13 new Python cases include real offline worker/artifacts and synthetic
  operation -> common runner -> portable retention -> shared profiling reads.
  Stop/deadline/output-limit tests use owned local fixture processes, never SSH.
- Chrome desktop verified login return-to-menu, the 14-dish menu and review,
  explicit confirmation, actual offline report completion and saved-run reload.
  Receipt details collapse and long paths wrap; the tested desktop had matching
  content/viewport widths. No mobile/assistive-technology certification is claimed.
- Wheel/sdist builds and an extracted-wheel run passed, including shipped Web
  modules, 14 recipes, confirmed report execution and generated artifacts.
- The temporary synthetic QA server was closed. The former controller handle was
  unavailable and port 8741 had no listener; the original checkout/interpreter,
  installation-data binding, saved port and agent-control launch options were
  reused to restore the user Web. Authenticated menu API, recipe page and new
  assets returned HTTP 200. No host commands were replayed.
- No real host connection, credential/policy change, dependency installation,
  scheduled acquisition, commit, push or release was performed.

## Inventory scope and artifact delivery checks (2026-11-09)

- Complete local Python suite: 1,373 passed; JavaScript suite: 88 passed. Final
  focused tests also passed after making the equivalent inventory CLI preview
  include its exact --job/--property selectors.
- Synthetic worker -> common inventory runner -> retention -> profiling tests
  verified fans-only scope, rejected invalid/mixed/changed selectors, and preserved
  default sensor opt-in and schedule settings. No original inventory schemas changed.
- Report/API tests covered original-byte hashes, no-write viewing, missing/changed/
  undeclared/oversize/symlink/path failures, authentication/origin/Profile boundaries,
  inert text, sanitized HTML, sandbox/CSP and attachment headers.
- Chrome used a separate temporary installation and fixture transport: selected
  sensors.fans, confirmed one group/one field, completed and retained collection,
  generated a retention report, read Markdown, rendered static HTML and downloaded
  the original. The 6,819-byte download matched the declared artifact SHA-256.
  An initial QA helper import-path error remained a visible failed run; correcting
  the fixture and explicitly rerunning succeeded, without changing product imports.
- Wheel/sdist and extracted-wheel checks verified inventory selection, report worker,
  artifact readers and shipped viewer resources. Native target tools, real SSH and
  mobile/assistive-technology behavior were not established by these tests.
- Temporary QA service and the hash-verified synthetic download were cleaned up.
  All three current Profiles reported no active Web recipe runs; the owned controller
  closed with workers={} and restarted on its original 8741 endpoint/data/options.
  Authenticated menu/catalog and report index plus page/viewer assets returned 200.
- No real host connection, policy/credential change, schedule, dependency install,
  commit/push or release was performed.

## Category layout verification (2026-11-10)

- Full local regression: 1,373 Python and 93 JavaScript tests passed. Group API
  tests check safe resolved membership/no login names; UI tests check domain/source
  ordering, classification, exact-reference deduplication, overlap, disabled hosts,
  indeterminate states, plate columns and no mutation during selection.
- Chrome desktop used an isolated synthetic installation with a Profile recipe,
  three enabled hosts/two groups and one disabled host. Bundle/User columns,
  synchronized cross-domain choices, suggested sets, Group/All and the plate were
  verified. All selected three enabled hosts, while the plate retained four unique
  recipes. Content width matched the 1,470-pixel tested viewport. No recipe ran.
- A copied QA recipe initially failed the reserved Bundle-author check; its
  fixture metadata was corrected to synthetic user attribution. The invalid row
  was not treated as runnable and the partial catalog remained visible.
- No real host connection, account/settings mutation, new schedule, install,
  commit/push or publication was part of this layout work.

The extracted-wheel smoke passed. Temporary layout QA was closed; the existing
Web reported no active recipe runs and closed with workers={}. Its original
checkout/interpreter/data/8741/agent-control options were restored. Authenticated
menu and main-page/layout assets returned HTTP 200.


## Earlier recipe library verification (2026-11-10)

This records the earlier flat-meal iteration; current nested-meal verification is below.

- Full local regression passed: 1,381 Python and 100 JavaScript tests. The first
  restricted run had ten loopback-bind permission errors; the complete suite passed
  when local fixture listeners were allowed. Focused library tests passed again
  after the final dependency-error handling adjustment.
- Public tests cover no-write reads, exact-reference ownership, typed defaults,
  existing comment/private-field preservation, group/host precedence, stale revisions,
  malformed/symlink metadata, category assignment/reset, meal create/update/delete,
  retained-record reads, authentication/origin checks and escaped UI contents.
- Chrome with disposable synthetic Profiles verified dedicated pages, original
  retained JSON expansion, default edits, custom category creation/assignment/rename,
  plate save, meal modify/apply/delete and preserved selection across navigation.
  The tested desktop had no horizontal overflow; mobile/assistive testing is not claimed.
- An initial HTTP fixture selected the checkout registry accidentally. Its exact
  synthetic category and default edit were identified and reverted (original YAML
  bytes restored). Fixtures now explicitly separate temporary product/registry and
  installation-data directories and assert synthetic Host IDs before mutations.
- Wheel/sdist and extracted-wheel checks passed for recipe pages, metadata services,
  real default edits, meals, existing report worker/artifact readers and shipped assets.
- Temporary QA listeners were closed. The existing user Web had no active recipe
  runs and closed with workers={}; it was restored on its original endpoint/options.
  Live private-detail inspection was not performed after automatic review rejected
  that check; public-resource and unauthenticated access checks are used instead.
- No managed-host command, dependency installation, schedule, commit, push or release
  was performed for these library features. Views use saved evidence, not current
  managed-host verification.


## Field tree and menu refinement verification (2026-11-10)

- Full local regression: 1,381 Python and 104 JavaScript tests passed. UI tests cover
  inline scope text, Bundle-before-User ordering, absent empty User sections,
  independent new-tab links, initially closed field branches, nested/array paths,
  escaped field descriptions, one editor per input and no recipe-page category form.
- Chrome used isolated disposable product/registry and installation-data directories.
  It verified one-column source lists, visible scope notes, opening Overview in a
  separate tab while the original plate stayed selected, expanding system fields
  while hardware remained closed, and saving port-local plus common timeout options
  in one action. There was no horizontal overflow in the tested desktop viewport.
- Wheel/sdist and extracted-wheel checks passed, including shipped modules and the
  unchanged default/meal/report services. The temporary QA listener was closed;
  the existing 8741 Web remained running without restart. No managed host connection,
  real Profile edit, dependency install, schedule, commit or push was performed.
- That UI-only stage preceded the now implemented [routine/meal contract](recipe-routines.md). The following section describes current execution.


## Executable plate and inventory meals

The plate now offers **Review and execute**, restoring an explicit confirmation path. Select a recipe field scope from its plate row; saving a user meal preserves nonsecret selectors in `sets[].selections` (reference -> jobs/properties selector). Missing selectors fail review rather than widening scope. Suggested Overview now adds a meal reference resolving to ten independent recipes; sensors remain separate opt-in. Compatible routine recipes share one owned worker/connection per host and run login before root. Other tools remain independent. Review shows groups, conditional permissions, fields and fingerprints. Saved run views link each child result and show independent retention/consumer outcomes. The metadata version remains 0.1.0 with optional selections; reads do not rewrite old documents. The preferences API validates selectors against the current exact recipe catalog. See [routines](recipe-routines.md) for limits and unchanged human authorization.

## Use the split inventory from the Web

1. Open **Recipes** in the intended Profile. Choose independent inventory dishes,
   or expand **系統全貌盤點套餐** and add the meal reference. Sensors are separate.
2. Select individual hosts, a group or All. In the plate, open **採集欄位** for each
   inventory recipe. Keep its defaults or choose exact properties, such as
   `system.hostname` or `sensors.fans`; an empty explicit selection is rejected.
3. Optionally save the plate as a user meal. Adding that meal preserves nested
   references and field selections, without changing selected hosts or executing.
4. Choose **檢閱並執行餐盤**. Review exact scope, enabled overrides, host connection
   groups, conditional login/root requirements and configured consumer effects.
   Confirm explicitly to start. Shared routines use one worker/connection per host;
   other recipe tools remain independent.
5. Read each task's collection, retention and consumer receipts. Follow its history
   or system-profile link, or open the recipe's separate page for actual retained
   data. Reading saved results does not reconnect. A prior successful result does
   not establish that a later attempt succeeded.

The initial routine contract and compatibility limits are in [routines and meals](recipe-routines.md).
The 2026-11-10 isolated browser test verified this full path with synthetic transports,
including saved scopes and independent retained fan/hostname results. Public frontend
checks passed 109 tests and the complete Python suite passed 1,395. Native host access
and assistive-technology verification are separate; this was not real-host QA.



## Nested meal verification (2026-11-10)

Public Python/JavaScript tests cover closed domain disclosures and Scopes headings, additive meal references, nested rendering, stable-ID creation/update, host-free storage, cycle/unknown-ID rejection, Bundle-definition changes, direct/indirect deletion effects, retained empty meals, stale revisions, field/job/default union, recipe deduplication, conflicting inputs, HTTP preview and changed-definition refusal before worker start. The installed wheel test also creates and expands a nested meal without checkout imports. These are synthetic/local checks; browser automation was unavailable in this session, so rendered desktop/mobile/assistive behavior and real SSH collection are not claimed. The existing Web listener was preserved.


## Concise execution review preview

The confirmation page groups each exact recipe into one row across its selected hosts. It shows friendly recipe labels, collection field counts, operation type and the existing command timeout. The common host list appears once above the table, rather than repeated in each recipe row. Targets and field scopes remain read-only here: return to the plate to change them. The threads control is a one-time execution option sent only with Start; changing it does not require another preview. Account details, original invocation, overrides, exact field IDs and routine/connection plans remain inside a closed technical disclosure. Permission and configured downstream-effect notes remain visible. The checkbox and start request still authorize only the server-reviewed preview. The concise layout retains the confirmation boundary; focused front-end rendering and confirmation tests cover this iteration. Browser visual verification is not claimed.


Batch previews retain the exact All/Group selection minus individual exclusions. There is no fixed host/invocation count cap; execution concurrency uses the threads setting described below.



## Execution throttle and defaults 0.1.0

**Settings → Execution** (`/settings/execution`) edits the installation-wide Web recipe default. It is 8 threads when no settings file exists. Each execution review offers a temporary threads value. Editing threads does not change the plate, invalidate confirmation or request another preview. Start validates the supplied value and records it for that run only. It is absent from plate/meal definitions and preview requests/plans. Once a run has started its threads value is fixed; changing the installation default does not alter running work. No settings file is written by an invocation override or a read.

Threads is a positive integer. It limits concurrently active host lanes, not the number of selected hosts. Same-host recipes remain sequential; compatible routine recipes still share one worker/connection with login/root phases. Local reports form one separate sequential lane and share the same concurrency budget. The controller creates at most `min(threads, number_of_lanes)` pool threads, queues remaining lanes, and starts the next lane when a slot becomes free. There is no fixed host-count limit. The HTTP request-size limit, 32-recipe limit, per-command timeout, per-worker wall deadline and bounded output remain; this is not a measured unlimited-capacity claim. Existing CLI `recipes run --threads` behavior is unchanged by this Web default.

Ordinary recipe failure does not prevent independent hosts or following recipes from running. Stop prevents queued hosts/recipes from starting and requests termination of every active owned worker process; original remote-cleanup uncertainty remains. Unexpected controller/profile-binding failure stops active lanes and marks unfinished tasks explicitly. Collection, retention and consumer receipts remain separate. Saving defaults never connects or executes.

The persisted contract is [`recipe-execution-settings.schema.json`](../schemas/recipe-execution-settings.schema.json). Installation data contains `recipe-execution-settings.json` with exactly `{"schema_version":"0.1.0","threads":8}`. It is outside replaceable product code and separate from profiles, hosts.yaml, credentials and menu meals. Absence uses 8 without writing; malformed/unknown-version/symlink files fail explicitly. Saving is locked, atomic and revision-checked; stale updates return 409. Settings have no automatic legacy conversion.

Shared checkout facade: `opsfeast.execution_settings.inspect(data_root)` returns schema_version, threads and a content revision; `save(data_root, threads=N, expected_revision=REV)` saves and returns the new state. Authenticated administrator/owner routes are GET/PUT `/api/v1/recipe-execution/settings`; PUT accepts exactly threads and expected_revision, with existing same-origin protection. Read with GET, explain scope, reuse the human grant, and save using the returned revision. No extra approval is required for previously authorized changes. Presentation-only edit tokens cannot use these routes.

```sh
python -B -m opsfeast.execution_settings show --installation /path/to/opsfeast
python -B -m opsfeast.execution_settings set --installation /path/to/opsfeast --threads 8 --expected-revision REV
```

POST `/api/v1/recipe-runs/preview` accepts the plate selection without threads. POST `/api/v1/recipe-runs` accepts preview_id, confirmed:true and optional threads. Omission uses the installation default at Start; supplied threads overrides it for this run only. The saved execution record exposes the actual threads, while plate drafts, meals and preview plans do not contain it. Invalid zero/negative/fractional/Boolean/null HTTP thread values fail before starting work. Repeated Start for an already-started preview returns its original run without changing threads. Scope/fingerprint validation and explicit execution confirmation remain intact. Synthetic tests verify runtime/default isolation, concurrency, stop, authentication and revision conflicts; no managed-host connections or fleet capacity claims are established.


The review page immediately renders a provisional summary from the current plate/catalog while server validation runs in the background. Pending scopes are labelled unverified, technical details wait for the real plan, and confirmation/start remain disabled. Users can edit threads or return to the plate without waiting. Typed runtime thread values survive the incoming plan without requesting another preview; late responses cannot overwrite a returned/replaced page. This improves initial UI responsiveness without claiming that server validation itself has become faster.


The threads input displays 8 immediately rather than an empty inheritance placeholder. Saved execution defaults are fetched independently of the full preview and replace that initial value when available. A manually entered per-run value is never overwritten by a late defaults response; the authoritative preview still controls confirmation.

## Staged plate execution

Confirmed selections now use [staged execution](staged-recipe-execution.md#web-execution-plates-and-grouped-routine-workers).
The saved plate UUID is also its parent execution and Console UUID. The existing
recipe-runs GET response exposes `execution_id`, `river` and the final
`execution_status`. A parent spans all selected hosts, including grouped routine
workers; report-only plates use controller scope without a fake host. Individual
Recipe/report receipts may also retain child execution IDs. Existing task outcomes,
stop/cleanup evidence, retention and the continuous receive-order progress display
remain separate. The generated `feast/plate` record is not a catalog Recipe or a
CLI handoff target. A recording failure stays explicit; viewing never retries.
Web must be reloaded after reconciling active work to use the new coordinator.

## Execution page and return navigation

Activity log timestamps for Web plates link to this exact saved execution page;
summary titles open the exact Recipe page in a new tab instead. The activity list omits its
separate Status column. Execution-page navigation offers **Activity and logs**
(`/logs?profile=NAME`) and **Execution plate** (`/recipe-plate?profile=NAME`), rather
than sending the reader to the separate `history=1` list.
Its shared river and individual host tasks remain available. Expanded incomplete tasks
also load their bounded, host-filtered saved activity summaries (collection/advisory/report
stages and retention/content receipts) through the workspace selected-entry API.
Summaries appear inside the corresponding task; closed tasks issue no summary
or diagnosis requests. A failed summary read remains visible without hiding task outcomes; viewing the
page never reruns operations. The activity list keeps only host completion totals
and a closed host-result count disclosure for these Web plates.


The saved execution page `/recipe-plate?profile=NAME&run=UUID` now shows one shared progress area that scrolls with the page above independently expandable task cards. Cards start closed; their summaries retain live indicators and completion/partial/failure labels. Host names link to their exact host page in a new tab (`target=_blank`, `rel=noopener`); the three repeated host/log/retention footer links are removed. Report artifacts also open separately. The common progress area is a continuous receive-order log across all hosts, without host/task blocks. Every displayed line includes the controller receive time (Asia/Taipei), host and recipe references. Shared-worker output is appended once for all its child recipes. New saved run records expose `progress_events` (sequence, received_at, host_id, references, text), `progress_sequence` and `progress_truncated` through the existing recipe-runs GET API. Sequence is assigned under the shared receive lock; timestamps describe controller receipt, not remote execution time. Reads may split partial lines; each received fragment keeps its own position/time. The record retains the newest 128 Ki characters of output and at most 2,048 chunks, with explicit truncation. Existing task progress remains available separately. Old records without events explicitly report that receive-order progress was not saved; no chronology is reconstructed or historical data rewritten. Reload the Web service before new executions to load this recording change; refreshing the browser alone only loads the renderer. Polling preserves expanded cards and the river's scroll position when the reader has scrolled up.

The former unfinished-task jump list is removed. Each host card directly exposes
a single outcome label: **執行完成**, **有未完成項目**, or **結果處理有問題**
when execution succeeded but result processing did not. Expand a card for concrete
causes. The body omits the duplicate operation-result line and successful receipts;
failed, partial or unknown retention/content receipts remain explicit. Host links
open a new tab and do not toggle the card. Incomplete fields and reasons reuse saved `collection_gaps` or lazily GET `/api/v1/results/diagnosis?profile=NAME&result_id=ID&limit=50` when the task opens. These reads do not connect or collect. Missing/failed diagnosis stays explicit; absent evidence is not invented, and omitted groups remain labelled. Existing status and historical data are not rewritten.

On the execution plate, **Execution history** opens `/recipe-plate?profile=NAME&history=1`, backed by GET `/api/v1/recipe-runs?profile=NAME`. It lists up to the 100 newest saved selections, including running selections, with exact links back to their execution pages. The normal browser address can be bookmarked for older records. Closing the browser does not stop workers while Web remains running; reopening the history/page only reads and reattaches polling. Restarting Web instead preserves the existing interrupted/no-automatic-retry semantics. No execution is started by opening history, a task or a diagnosis.

Task details update only the selected card body when saved summaries/diagnosis
arrive; its summary DOM node stays in place, avoiding scroll jumps caused by
replacing the entire execution page. Single-host explanations omit batch totals,
duplicate host/status headings, successful-stage rows and duplicate reason/gap
codes. Known advisory timeout reasons use plain-language descriptions; failed
advisory acquisition plus a partial report explains that vulnerability assessment
is incomplete. The package count is explicitly the number of installed-package records acquired
from the native OS package database as assessment input. It is neither a
vulnerability count nor proof that every record was assessed. Report counts
represent findings, so they need not match input record counts. Only problematic
retention/content receipts remain visible; successful receipts stay in saved data. Unknown reasons are retained and escaped, not reclassified.
Raw task JSON is no longer rendered here; saved results and generated reports
remain unchanged and report links remain available. Meaningful missing-field
diagnosis and read errors stay visible, while empty generic diagnosis text is
suppressed when a specific saved explanation is available.

## OS package vulnerability meal

Add **OS 套件弱點分析套餐**, select default-Profile hosts and review/confirm. The [three-stage workflow](package-security-meal.md) collects native identities, acquires matching official advisories on the controller and generates linked HTML/Markdown/JSON reports. The review calls out outbound controller HTTPS. Expand a completed host task and choose **開啟產生的報告**. Missing feeds/scope remain partial/unknown; affected findings can occur in a successful run. The menu meal wraps one dependency-aware operation, not independent collection/report entries with manually copied inputs.

## Agent-required Recipe launch

An executable definition with `launch.mode: agent` shows a suggested prompt and a
copy button on its Recipe page, replacing the plate execution link. Copying never
starts or notifies anything. Paste it into an agent conversation to review scope,
arrange tools and start one authorized CLI invocation. These recipes are disabled
in the plate picker; Web preview also rejects direct or expanded-meal attempts.
Meals retain static readiness but suppress Web launch when a nested recipe needs
an agent. See [launch guidance 0.1.0](python-workflows.md#agent-conversation-as-the-launch-surface)
for fields, API readiness semantics, errors and authorization limits.

*Last modified: 2026-11-18 15:56:07*
