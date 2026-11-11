# OpsFeast local Web workspace

The local website provides administrator login, saved site presentation,
Profile/host configuration, confirmed recipe execution and saved-data views.
Read [saved-data workspace 0.1.0](../docs/web-workspace.md) for page behavior,
HTTP schemas, Profile scope, document access, failures and verification limits.
UI copy remains Traditional Chinese until English translation is requested.

The current design/verification target is desktop browsers; dedicated mobile and
tablet support is deferred. For the shared design system, all-page scope and review, read
[Web design and review](../docs/web-design.md) and [host presentation](../docs/web-hosts.md#host-workspace-presentation).

## Human-centered management workspace

`/workspace`, `/recipes`, `/work`, `/retention` and `/logs` read the selected
Profile's existing data. `/skills`, `/learn` and `/docs` expose actual local public
Markdown sources. `/settings` shows installed versions, explicit official-source checks and a
[confirmed Agent handoff](../docs/web-updates.md), with
[Site/Profile/Bundle Recipe hierarchy](../docs/web-settings.md).
Synthetic management records, draft editing modules and browser-only command
playback have been removed from served assets; no saved user data is deleted.
The website does not substitute sample results for unavailable or empty sources.

The [first-use guide](../docs/web-administrator.md#first-use-web-guide),
[site presentation](../docs/site-presentation.md), [host editor](../docs/web-hosts.md)
and Profile/account settings retain their existing contracts. Saved-data pages are
read-only; recipe execution now uses the separate confirmed menu. Core/CLI execution, service lifecycle and transfer workflows
remain available under their own authorization scope.

## Real interactive Console

For chat-owned interaction use the shipped [Console worker](../docs/console-agent.md)
and [owner controller](../docs/agent-owner.md). It creates a reader URL before SSH,
streams output and preserves saved records. The host's Console history and the
activity page open read-only readers without reconnecting or replaying work.

The separate `/interactive` exact-plan service is enabled only with explicit
`--interactive-profile` and `--interactive-host` flags; otherwise its API returns
503. See [interactive protocol](../docs/interactive-console.md) and the
[interactive skill](../skills/opsfeast-interactive/SKILL.md). No data-page visit
creates an execution target or expands host-operation authorization.

## Persistent data before startup

Use [installation storage 0.1.0](../docs/installation-storage.md) before startup.
Web now requires a marked external data root or a valid checkout binding. Existing
product-local site files are not a fallback. For the installation's first
separation, stop writers and run `python -B -m opsfeast.storage init --data-root
/absolute/absent/destination`; it copies/verifies known identity/site data and keeps
sources. For replacement checkouts, use `storage attach --data-root EXISTING_ROOT`
before starting, or pass `--data-root EXISTING_ROOT` to Web for one invocation.
Profile registries/data are not moved by this procedure. Never delete a checkout
containing profile data merely because Web presentation is now stored outside it.

## Run locally

Use the selected checkout Python. Install optional dependencies only within the
operator's authorized environment:

```sh
.venv/bin/python -B -m pip install -r requirements-web.txt
.venv/bin/python -B -u -m opsfeast.web --agent-control
```

Open the URL returned at startup. The launcher binds only to IPv4 loopback and
uses [this checkout’s saved port](../docs/web-server.md); first launch allocates
and saves one in `.opsfeast.yaml`. `--port N` persists an explicit choice. An
occupied port fails without automatic replacement or process termination.
The [agent owner controller](../docs/agent-owner.md) keeps its highest Web capability
only in memory and accepts JSON-lines API/password/worker controls. It creates no
token files. Preserve its private stdin; EOF or shutdown closes workers then stops
the server. Closing a browser tab does not stop it. Without --agent-control, the
foreground server supports an already configured human administrator. No automatic
restart recovery exists. Node.js and a frontend build are not needed.

## Available interfaces

| Path | Current behavior |
| --- | --- |
| `/` | First-use guide until an administrator exists; ordinary welcome afterward |
| `/setup`, `/api/v1/setup` | Three-step first-use guide and nonsecret progress status |
| `/login` | Administrator login; valid sessions redirect to the workspace/supported next destination; first-use guide before account setup |
| `/workspace` | Saved active notifications/todos and configured host count |
| `/operations` | Host/Console/history entrypoints; no command playback |
| `/hosts` | Real host configuration; [CRUD/group/backup contract](../docs/web-hosts.md) |
| `/recipes` | Purpose-based menu with explicit confirmed execution |
| `/recipes/data`, `/retention`, `/work`, `/logs` | Actual Profile-scoped read-only data views |
| `/skills`, `/apps` | Bundled Skill sources; Vault/application guidance |
| `/learn`, `/docs` | Local public Markdown index/search and inert source readers |
| `/settings` | Shared settings hub; site/profiles/hosts available, installed version panel; other categories remain planned |
| `/settings/hosts` | Link to real host settings in `/hosts` |
| `/settings/recipes?profile=NAME` | Read-only user/external Recipe catalog within the owning Profile |
| `/settings/bundle-recipes` | Independent read-only Bundle Recipe catalog |
| `/settings/execution` | Installation recipe concurrency default; 8 host lanes, with temporary per-run overrides |
| `/settings/parameters`, `/settings/retention` | Profile-scoped guidance; Web writers remain planned |
| `/api/v1/settings/catalog` | Static settings availability, shared with module/CLI |
| `/settings/site` | Site presentation plus private administrator setup/change; see the account guide |
| `/settings/profiles` | Administrator-only profile status, create, attach and default switch |
| `/api/v1/site`, `/api/v1/site/settings`, `/api/v1/site/images`, `/site-assets/{id}` | Versioned site settings/image interfaces; see the canonical presentation guide |
| `/api/v1/preview` | Preview mode, installation presentation source, single-administrator authentication, profile configuration enabled, operations disabled |
| `/assets/` | Only bundled public CSS, JavaScript and the SVG mark |

Unknown paths return 404; no repository/profile directory is served. Operational routes remain GET-only. Site/account/profile/host writes use protected HTTP endpoints described in
the canonical guides. API documentation routes are disabled to keep
`/docs` available for product documentation. Host-header restrictions and response
security headers reduce incidental exposure. A single-administrator session protects
profile/account APIs. An independent agent owner capability can perform all Web
operations, including administrator reset, under human instructions and consent.
This is one launching-agent identity per server, not multi-agent accounts or OS isolation. Do not expose this local service through a
proxy or external bind. Further domain authorization is required before executable host operations are connected.

## Language and authentication

The authoring language is Traditional Chinese (`zh-TW`). English translation is
deferred until explicitly requested after content review. Only `zh-TW` is
registered; no empty or machine-translated English catalog is shipped.

Rendered UI copy lives in `assets/locales/zh-TW.mjs` and the task-specific
locale modules, including `workspace-zh-TW.mjs`. `assets/i18n.mjs` owns locale resolution, whole-message
interpolation, optional browser preference storage and number/date formatters.
It is prototype-private, not a public extension SDK. Prefer semantic message keys;
do not add UI text directly to rendering code. Add approved locales by importing
their catalogs and registering their locale IDs. Missing keys/parameters fail
explicitly during development. Translated strings are escaped before HTML insertion.

Locale selection currently considers saved browser preference, then browser
languages, then the `zh-TW` default. Restricted storage does not block rendering.
No account preference exists yet. Document language and operational source text
remain independent of UI locale; commands, identifiers and evidence must not be
automatically translated. Date formatters accept an independent timezone, defaulting
to Asia/Taipei. This does not change any stored timestamps.

The welcome page `/` remains public. `/login` performs actual single-administrator
authentication after owner setup; there are no default credentials. See
[administrator and profile settings](../docs/web-administrator.md) for bootstrap,
password storage, session expiry/invalidation, current-password requirements and
private profile interfaces. Data-page visits do not execute commands.

For the setting categories, cross-interface rules, site/admin CLI and bundled
logo/avatar defaults, see [shared settings](../docs/web-settings.md). Null custom
image references use the bundled OpsFeast mark; uploaded images remain in persistent
data. Interface language is independent of account credentials and profile namespace.

## Sources and extension boundaries

### Owner-centered identity

Follow [make the user's workspace the protagonist](../docs/vision.md#make-the-users-workspace-the-protagonist).
The saved installation name/logo/slogan occupy primary positions; the avatar has
a companion card on the welcome page, while OpsFeast attribution is in the footer.
The [presentation guide](../docs/site-presentation.md) defines the shipped schema,
module/API, private storage and public-before-login image visibility. Multiple user profiles,
delegated agent credentials and theme controls remain separate future work.

- `web/index.html` and `web/assets/` are framework-free local source assets for
  layout review. They are served directly, with no CDN or external font requests.
- `opsfeast/web/` contains the optional FastAPI/Uvicorn adapter and launcher. It
  serves a fixed page allowlist and delegates presentation data to `opsfeast.site`;
  it does not duplicate Core or retention logic.
- The Python app factory is `opsfeast.web.app.create_app()`. Web assets are served
  from the checkout layout; do not infer an installed-wheel Web deployment contract.
- Svelte/SvelteKit integration, versioned presentation SDK, shared public UI
  libraries, extension registration, custom routes, multiple-user/agent authorization, event streaming and
  operational lifecycle remain planned. Do not import the prototype JS as an SDK
  or install a presentation into `web/assets/`.
- Existing `docs/`, textbook and bundled Skill files remain authoritative. The
  library reads these local sources without copying them into another store.

For future reusable presentation work, first discover actual available utilities
and contracts. Use the documented capability and data contracts. Recipe,
retention and presentation remain separate units; neither a consumer registration
nor a browser visit authorizes executable extensions or collection.

## Verification

```sh
.venv/bin/python -B -m unittest discover -s tests -p 'test_web_preview.py'
.venv/bin/python -B -m unittest discover -s tests -p 'test_site.py'
.venv/bin/python -B -m unittest discover -s tests -p 'test_installation_storage.py'
node --check web/assets/workbench.js
node --test tests/test_web_i18n.mjs tests/test_site_assets.mjs tests/test_workspace.mjs
.venv/bin/python -B -m unittest discover -s tests -p 'test_workspace_web.py'
```

The optional tests skip when FastAPI is absent. They exercise routes, assets,
private-path rejection, unsupported operational writes, site edit capabilities,
origin/revision/image gates, Host restrictions and the explicit
preview contract through ASGI. Browser review must additionally check desktop and
mobile layouts, Profile selection, source rendering and list navigation. These checks
provide no SSH, authorization or remote-cleanup evidence.

Implementation references: [FastAPI static files](https://fastapi.tiangolo.com/tutorial/static-files/)
and [file responses](https://fastapi.tiangolo.com/advanced/custom-response/#fileresponse).


## Console block river and human replies

Live `/console/{sid}` and read-only `/console/{sid}/history` pages have explicit
session/target/task breadcrumbs and browser titles. History opens in a separate
tab, makes no SSE subscription or form submission, and bounds expanded content to
the loaded byte sizes. Block pages preserve the view mode. Opening a page never
creates or takes over a shell. See [reader-mode contracts](../docs/console-records.md#separate-live-interaction-from-historical-reading).



Below the latest visible block, the river distinguishes execution progress from **Agent 思考中…**. Successful
worker results report thinking; the next input or an explicit idle report before
chat output clears it. Thinking expires without renewal and respects reduced
motion. See [the activity handoff](../docs/console-records.md#agent-thinking-and-chat-handoff)
for integration limits; the page cannot observe another application's chat.

The real host detail's **Console 紀錄** tab now lists saved human-directed and
agent-led sessions for the selected Profile/host, with timestamps, recorded
block states, manual refresh and older-page loading. Each row opens the existing
river; browsing never connects or retries work. See [history discovery](../docs/console-records.md#discover-saved-console-history-by-host)
for exact matching, administrator-only enumeration and limitations.

The separate [Console blocks 0.2.0 service](../docs/console-records.md) supplies
`/console/{sid}` and `/console/{sid}/blocks/{bid}` with login-only access, streamed
bounded previews, UTF-8 range reads and authenticated typed form responses.
`opsfeast.console_client wait/responses` receives durable replies; no SSH adapter,
stop channel, model wakeup or arbitrary HTML/media renderer is provided. The old
0.1 chunk database remains untouched but is not served. Existing exact-plan
`/interactive` also loads directly with administrator login; its execution gates
remain separate. Read [the agent skill](../skills/opsfeast-console-records/SKILL.md).

## System profiling viewer

Host details now include **系統全貌**, backed by authenticated GET
`/api/v1/profiling/catalog` and `/api/v1/profiling/host`. The shared
[profiling service](../docs/profiling.md) supplies capability gaps and latest
retained property attempts/values with original sample times. Browser modules only
render/escape/paginate; they do not collect, infer freshness/health or own domain
rules. See `tests/test_profiling_web.py` and `tests/test_profiling.mjs` for synthetic
HTTP and rendering coverage. New routes need a server reload; preserve its original
installation data/port/options and active Console work during maintenance.


## Policy source basis

The profiling viewer now labels configured/effective/runtime/context evidence and
shows expandable source scope plus safe native query metadata. It still uses the
same authenticated read-only shared API; it cannot run a policy query or turn a
configuration projection into effective host security. The [policy guide](../docs/linux-policy-profiling.md)
records supported recipes, source semantics, limits and tests.

## Recipe menu and human-confirmed execution

The [recipe menu 0.1.0](../docs/web-recipe-menu.md) now delivers the planned
Web selection workflow: recipe purpose/limits, suggested combinations, the shared
39-capability blueprint, exact targets and inputs, review/confirmation, serial
runner progress/stop and saved receipts. This is separate from read-only saved-data
and profiling views. Opening a viewer or history never collects or retries work.
The original profiling blueprint remains the Bundle target, not a claim that all
current capabilities are complete.

## Inventory scope and report artifacts

The [recipe menu](../docs/web-recipe-menu.md) now supports choosing inventory jobs,
individual fields and explicit temperature/fan sensors. Confirmation preserves
exact scope and uses the common collector/retention flow. Completed and historical
reports have declared-artifact readers, static HTML/inert-text/raster previews and
verified-original downloads. Preview/download is read-only and Profile scoped;
no report replay, arbitrary file serving, scripts or external preview resources.

## Category-first recipe layout preview

The [main recipe page](../docs/web-recipe-menu.md#current-category-first-selection-preview-2026-11-10)
now groups scope summaries and Bundle/User recipes by domain, then shows sets,
individual/group/All host picks and a two-column plate. Search/history/report-index controls remain outside the main selection layout. Selection synchronizes exact references/host sets locally; the plate offers field scope and explicit review/confirmation before execution. Saved run/report URLs and APIs
remain available. Host login accounts are omitted from the menu data/view.


## Recipe library pages and owner selections

Recipe titles now open their [dedicated page](../docs/web-recipe-menu.md#recipe-pages-defaults-categories-and-user-meals), including declared collection fields, retained data, report links and editable nonsensitive Profile defaults. User/external recipes support builtin/custom assignments; custom categories can be renamed. Meals expand their members; the plate can be saved as a user meal, edited or deleted. Selection drafts survive same-tab navigation using Profile-scoped sessionStorage. Writes require administrator/owner capability and current revisions; they never start collection.


## Field-tree navigation

Recipe links now open separate tabs. Category scopes are directly visible; Bundle/User lists stack vertically and empty User lists are hidden. Dedicated pages present dotted fields as native closed disclosures with exact-name input editors at their field and shared options below. New category forms live only in the menu manager. See the [menu contract](../docs/web-recipe-menu.md#recipe-pages-defaults-categories-and-user-meals) and the implemented [inventory composition contract](../docs/recipe-routines.md).


## Executable plate and shared inventory connections

The Recipes plate now offers per-recipe field scopes and explicit review/confirmation. Compatible routine recipes are grouped per host, with conditional login/root permissions visible before start. Progress/stop and independent child result links use the existing owned-worker APIs. User meals additionally save validated nonsecret selectors. Recipe-specific retained pages keep source times and actor/cleanup evidence. See [routines](../docs/recipe-routines.md) and [menu](../docs/web-recipe-menu.md).

*Last modified: 2026-11-11 15:55:36*
