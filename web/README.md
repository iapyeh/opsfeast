# OpsFeast Web preview

For real chat-owned incremental interaction, use the shipped [Console worker 0.1.0](../docs/console-agent.md). It creates a reader URL before SSH, automatically publishes Console output through the existing block/SSE handlers, and accepts fixed agent controls. It does not turn browser draft buttons into execution endpoints.


The [first-use Web guide](../docs/web-administrator.md#first-use-web-guide) opens directly on the homepage before an administrator exists. [Real host configuration](../docs/web-hosts.md) now provides administrator-only host creation, basic settings/group autocomplete and confirmed deletion through shared CLI/Python/HTTP interfaces. The old host draft helpers are test fixtures, not the active `/hosts` route.


This checkout-only prototype provides a concrete landing page for design review.
It provides local administrator login, site/profile settings and real host configuration. The optional isolated exact-plan Console and chat-owned worker execute through their documented authorization boundaries; roadmap execution/history examples remain synthetic. General recipe execution, retained-data management and consumer hosting are not connected to those roadmap controls. Saved site personalization is implemented through the separate
[installation presentation 0.1.0 guide](../docs/site-presentation.md). The UI is
Traditional Chinese for the current review.

## Real isolated interactive Console

The optional `/interactive` page now provides a real execution service when the
launcher receives explicit `--interactive-profile` and `--interactive-host` flags.
Without them the API returns 503 and no execution target is enabled. This is
separate from the synthetic host-page Console/recipe drafts below. Read
[interactive protocol 0.1.0](../docs/interactive-console.md) and the
[agent skill](../skills/opsfeast-interactive/SKILL.md) for credentials, exact approval,
SSE/durable state, CLI and native validation limits. The existing landing pages
remain design previews; no draft button is silently connected to real execution.

## Human-centered management roadmap preview

The Web design now foregrounds overview, hosts/groups, recipes, work/issues,
activity/logs, applications, reference material/Skills and settings. This is a
reviewable information architecture, not new domain services. UI copy remains
Traditional Chinese until English translation is explicitly requested.

- `/workspace`: synthetic priority notifications and todos; no live service query.
- `/hosts`: real administrator-only host listing/editing, with profile selection,
  ID/group filters, saved inventory IPs, create, group autocomplete and confirmed
  delete. See [host settings 0.1.0](../docs/web-hosts.md). No synthetic records or
  connection tests are substituted in this route.
- `/recipes`: user examples above bundled examples, search, recipe detail tabs
  for description/parameters, execution/logs, observations and retention/results.
  `/recipes?recipe=ENCODED_REFERENCE` is a reloadable detail link with the recipe
  name in the breadcrumb and its own synthetic observation history.
- `/recipes/data`: cross-recipe data exchange/archival planning. `/retention`
  remains a directly reachable preview, but is absent from first-level navigation.
- `/work`: todo, issue and notification tabs, with lifecycle/action placement.
- `/logs`: time/source/summary list of synthetic interactive SSHScript, recipe
  and future IRC records. Times include seconds and an explicit Asia/Taipei zone.
  Click a time to open `/logs?entry=ID`; individual views provide a standard
  new-window link for independent side-by-side comparison. General logging and IRC integration are not delivered by this preview.
- `/skills`: user/bundled examples with expandable synthetic guidance. No real
  skill files are served, and availability never proves an agent used a skill.
- `/settings`: version/update panel with explicit unavailable version readings
  and disabled check/upgrade controls. No update check, download or upgrade runs.

Breadcrumb ancestors provide return navigation; content pages do not duplicate
parent/overview return links. Host, settings, recipe, work and log navigation
updates the displayed route. Recipe/work tab selection updates a reloadable
`tab` query parameter and breadcrumb. Body
copy uses a readable 16px base with restrained 26px page headings.
The recipe filters, recipe detail tabs, work tabs and Skills disclosure use
browser memory. Their roadmap records are synthetic and visibly labeled.
Operational archive, restore, deletion, import/export and execution controls
remain disabled with pending labels. Synthetic user/recipe draft CRUD is the
explicit browser-only exception described below. No fixture is written to the installation, profiles or services.
Existing site/account/profile features and the real host route retain their APIs and authorization.
The added workspace routes follow existing account-setup/login protection.

Future implementation must reuse canonical [services](../docs/services.md),
[portability](../docs/portability.md), [retention](../docs/retention.md), host and
recipe contracts rather than introduce Web-only storage or transfer formats.
Recipe/observation/retention are independent transfer units. Import never grants
execution, and historical imports must not create current incidents. Archive,
export and deletion must be distinct, with scope/conflict previews and clear
ownership. Users need management options for their notifications, todos and logs;
any existing protected-evidence restrictions must be reconciled explicitly before
claiming unrestricted deletion support. Multi-file verification, protected-data
rules and source cleanup continue to follow the existing portable archive contract.

Human-centered system administration includes collaboration, work and issue
tracking, as well as operations. Transparency includes inspectable skill sources
and evidence of who requested an action, target/identity, progress, stop/cleanup
states and outcome uncertainty. Credentials must be handled before log persistence.
These are design requirements, not new enforcement guarantees.

### Historical host draft fixtures

The original `host-draft.mjs` / `host-model.mjs` helpers remain public synthetic
fixtures for regression tests of earlier layouts. They are no longer mounted by
`workbench.js` at `/hosts`. The active `host-manager.mjs` and HTTP adapter use the
[real profile configuration service](../docs/web-hosts.md). Account/recipe editors
inside the historical draft do not imply those operations are implemented by the
real host page; current extension/verification limits are in that contract.

## Persistent data before startup

Use [installation storage 0.1.0](../docs/installation-storage.md) before startup.
Web now requires a marked external data root or a valid checkout binding. Existing
product-local site files are not a fallback. For the current prototype's first
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
.venv/bin/python -B -m opsfeast.web
```

Open <http://127.0.0.1:8740/>. The launcher binds only to IPv4 loopback; override
the port with `--port 8741`. An occupied port fails without automatic replacement.
The launcher creates a private per-launch site-edit token file in the external
data root; see the guide
above for unlocking settings and stale-token handling. Run in the foreground and press Ctrl-C to stop. There is no daemon, owner monitor,
automatic agent-lifetime cleanup or restart recovery. Closing a browser tab does
not stop the server. Python dependencies are optional and existing CLI entrypoints
remain unchanged. Node.js and a frontend build are not needed for this prototype.

## Available interfaces

| Path | Current behavior |
| --- | --- |
| `/` | First-use guide until an administrator exists; ordinary welcome afterward |
| `/setup`, `/api/v1/setup` | Three-step first-use guide and nonsecret progress status |
| `/login` | Administrator login; first-use guide when no account exists |
| `/workspace` | Workspace layout preview; login required after account setup, no execution metrics |
| `/operations` | Planned workflow plus browser-only play/stop demonstration |
| `/hosts` | Real host configuration; [CRUD/group/backup contract](../docs/web-hosts.md) |
| `/recipes`, `/recipes/data`, `/retention`, `/work`, `/logs`, `/skills`, `/apps` | Synthetic management roadmap previews; see above |
| `/learn`, `/docs` | Preview of learning/reference entrypoints, not document readers |
| `/settings` | Shared settings hub; site/profiles/hosts available, version/update panel and other categories planned |
| `/settings/hosts` | Link to real host settings in `/hosts` |
| `/settings/recipes`, `/settings/parameters`, `/settings/retention` | Planning pages, no private configuration reads/writes |
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
profile/account APIs; a local capability can edit site presentation and bootstrap
the first administrator. OS-user isolation and per-agent identities are not provided. Do not expose this preview through a
proxy or external bind. Further domain authorization is required before executable host operations are connected.

## Language and authentication previews

The authoring language is Traditional Chinese (`zh-TW`). English translation is
deferred until explicitly requested after content review. Only `zh-TW` is
registered; no empty or machine-translated English catalog is shipped.

All rendered UI copy, including page descriptions and playback messages, lives in
`assets/locales/zh-TW.mjs`. `assets/i18n.mjs` owns locale resolution, whole-message
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
private profile interfaces. Operational previews still do not execute commands.

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
- The Python app factory is `opsfeast.web.app.create_app()`. Its paths currently
  assume this checkout layout; wheel packaging is not delivered.
- Svelte/SvelteKit integration, versioned presentation SDK, shared public UI
  libraries, extension registration, custom routes, multiple-user/agent authorization, event streaming and
  operational lifecycle remain planned. Do not import the prototype JS as an SDK
  or install a presentation into `web/assets/`.
- Existing `docs/` and textbook files remain authoritative. No document sources
  are copied into this prototype.

For future reusable presentation work, first discover actual available utilities
and contracts. Do not infer implementation from the preview cards. Recipe,
retention and presentation remain separate units; neither a consumer registration
nor a browser visit authorizes executable extensions or collection.

## Verification

```sh
.venv/bin/python -B -m unittest discover -s tests -p 'test_web_preview.py'
.venv/bin/python -B -m unittest discover -s tests -p 'test_site.py'
.venv/bin/python -B -m unittest discover -s tests -p 'test_installation_storage.py'
node --check web/assets/workbench.js
node --test tests/test_web_i18n.mjs tests/test_site_assets.mjs tests/test_web_roadmap.mjs
```

The optional tests skip when FastAPI is absent. They exercise routes, assets,
private-path rejection, unsupported operational writes, site edit capabilities,
origin/revision/image gates, Host restrictions and the explicit
preview contract through ASGI. Browser review must additionally check desktop and
mobile layouts, navigation and the synthetic playback/stop behavior. These checks
provide no SSH, authorization or remote-cleanup evidence.

Implementation references: [FastAPI static files](https://fastapi.tiangolo.com/tutorial/static-files/)
and [file responses](https://fastapi.tiangolo.com/advanced/custom-response/#fileresponse).


## Console block river and human replies

The separate [Console blocks 0.2.0 service](../docs/console-records.md) supplies
`/console/{sid}` and `/console/{sid}/blocks/{bid}` with login-only access, streamed
bounded previews, UTF-8 range reads and authenticated typed form responses.
`opsfeast.console_client wait/responses` receives durable replies; no SSH adapter,
stop channel, model wakeup or arbitrary HTML/media renderer is provided. The old
0.1 chunk database remains untouched but is not served. Existing exact-plan
`/interactive` also loads directly with administrator login; its execution gates
remain separate. Read [the agent skill](../skills/opsfeast-console-records/SKILL.md).

*Last modified: 2026-11-02 23:43:02*
