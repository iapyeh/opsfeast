For login-to-river handoff, use [browser readiness 0.1.0](browser-events.md): open the exact river so login retains its scoped next URL, then continue already-authorized work without waiting for a "logged in" reply. The reader reports `reader.opened` and the owner controller pushes `browser_event` on its existing stdout; this is readiness evidence, never approval or automatic model wakeup. Separate installations use namespaced authentication/editing cookies.

# Agent-owned Web control 0.1.0

For two or more host workers sharing one timeline, follow [shared task river 0.1.0](shared-console.md). `worker.start` accepts optional `session` (an existing shared task UUID). The worker validates its exact profile/host membership before returning created; a starting acknowledgement is not attachment success. Display that session once, then route commands by worker_id independently of the selected host TAB.

The human is the website administrator and decision maker. The launching agent has
an independent owner capability with the highest Web API authority, including
administrator creation/password replacement, presentation, profiles, host settings,
notes, Console records/feedback, private input and enabled interactive operations.
Capability possession is not permission to act: use the human's actual task and
applicable consent; do not invent approval or broaden authorized effects.

## Launch and lifetime

For normal first-use installation, include this launch/lifetime scope in the
[approved setup plan](getting-started.md#include-and-launch-the-web-workspace).
After approval the agent starts and HTTP-verifies Web, supplies its actual URL and
keeps this controller/process handle open after the reply. Do not leave startup
as homework or request the same startup approval again. Explain an actual process-
persistence limitation while planning; no controller lifetime across tool/app exit
is implied. See [persistent alternatives](web-server.md#persistent-launch-choices)
for an explicitly selected browser-only service after administrator setup.

Follow [per-installation Web endpoints](web-server.md): use the saved port in
external installation-data `web-server.json`, or let the first launch allocate and persist one. `--port N`
persists an explicit choice; `ready.url` is authoritative, never a hard-coded port.

Use the approved checkout/interpreter with requirements-web.txt installed:

```sh
.venv/bin/python -B -u -m opsfeast.web --agent-control
```

Use `--data-root /existing/installation-data` only for an explicitly selected
installation. Preserve its identity, administrator, profiles and records. The
launcher generates a fresh random 256-bit token in its agent controller, gives it
directly to `create_app(agent_token=...)`, and keeps the token in process memory.
The Web verifier retains only SHA-256 of it. No capability is printed, placed in
argv/environment, browser storage, URLs, river content, logs or token files.
Restart creates a new capability and invalidates prior capabilities and cookies.
The token belongs to this controller lifetime, not a durable model memory.

Keep the controller stdin open using the execution tool's persistent interactive
mode (PTY input is made noncanonical and echo is disabled). Its JSON-lines stdout
starts with `{type:"ready",protocol_version:"0.1.0",url,capability:"memory_only"}`.
Neither that event nor any response exposes the token. Preserve this process handle
across turns. Send one control after the previous result; worker events can arrive
asynchronously. EOF or shutdown closes owned workers, then stops the server.
Worker `cleanup_unknown` is reported rather than asserting remote termination.
A disconnected agent cannot rediscover a token from disk: reconcile active work
and restart under existing authority. Do not kill an unrelated listener.

Keep the user-facing server running across development, commit and push work;
Git operations alone require no shutdown. If a necessary maintenance step stops
this task's server, preserve the original checkout/interpreter, port, data-root
binding and launch options, reconcile active workers/private input, then restart
and verify an HTTP response before handing back. Keep the new controller handle
available. Do not replay host commands or claim old workers survived a restart.
An explicit human instruction to stop or keep the server stopped takes precedence.
Report restoration failures and their concrete cause; do not silently switch
ports, installation data or terminate another process to make startup succeed.

Without `--agent-control`, the launcher runs a browser-only foreground service for
an existing administrator, with no capability delivery channel. Initial setup and
agent password recovery require the agent-controlled launch. Both modes create no
token files. The server remains loopback-only. Existing data is unchanged on upgrade.

## Controls and evidence

Every control needs a unique `request_id` (1–100 characters); duplicates are
rejected without replay. Input lines are bounded to 64 KiB. Mutating HTTP controls
and password controls require a nonempty `authorization` description of an existing
human grant. This is an agent report, not a machine-verifiable human approval.

```json
{"op":"request","request_id":"status-1","path":"/api/v1/admin"}
{"op":"admin.password","request_id":"password-1","username":"synthetic","generate":true,"authorization":"Human requested account creation with a generated password"}
{"op":"worker.start","request_id":"start-1","worker_id":"inspection","host":"web-01","title":"Authorized inspection"}
{"op":"worker.send","request_id":"connect-1","worker_id":"inspection","control":{"op":"connect","request_id":"connect-1","purpose":"Inspect the authorized host"}}
{"op":"worker.send","request_id":"close-1","worker_id":"inspection","control":{"op":"close","request_id":"close-1"}}
{"op":"shutdown","request_id":"shutdown-1"}
```

`request` accepts method GET (default), POST, PUT, PATCH or DELETE and a same-server
`/api/v1/...` path, optional JSON `body`, or `body_base64` with `content_type` for
binary image uploads (never both bodies). It supplies Bearer authorization privately,
bypasses ambient HTTP proxies and rejects redirects/foreign targets and returns `{status,body}`. Non-JSON responses
are returned as base64. Responses are bounded to 4 MiB and 30 seconds; use existing
record range/feedback endpoints for bounded reading, not an endless SSE request.
No automatic HTTP mutation retry occurs. On an uncertain result, read current
revision/evidence before deciding whether another operation is authorized.

`admin.setup-form` requires a nonempty `authorization` and no credentials. It issues
an owner-authorized ten-minute, single-use browser form via POST
`/api/v1/agent/setup-form`. Use this as the default first-account workflow and
present the returned exact private link immediately after startup. Only status
returns to the agent; do not ask for passwords in chat or read browser fields.
See [private form lifecycle and failures](web-administrator.md#private-first-account-form-010).
This narrow link goes to the browser; the owner capability stays in the controller.

`admin.password` accepts either `password` supplied by the human or `generate:true`.
Username can be omitted when an administrator exists; initial creation requires it.
The controller reads the current administrator revision and calls the agent-only
reset endpoint once. Provided passwords are not echoed; generated passwords are
returned only after confirmed success so the agent can deliver the requested value
to the human. Never put either kind of password in durable Console blocks, saved
scripts, tool argv or repository files. No password change is implied by merely
starting the controller. Passwords are exact, nonempty Unicode strings; there is
no character-count or composition rule. Request-size limits still apply.

`worker.start` accepts host, optional profile/title, or `local:true` instead of host.
Omit profile to use the checkout default. It starts the shipped worker with its
capability supplied through an inherited anonymous pipe (`--token-fd`), never a
credential file or command argument. Its events are wrapped as
`{type:"worker_event",worker_id,event}`; wait for `event.type=created` and immediately
show its exact reader URL before sending connect. `worker.send` forwards `control`
to that worker's stdin, returns sent, and does not certify command completion;
wait for its actual result event. Keep remote task/privilege authorization separate.
Closing a worker keeps the website/controller alive. Worker IDs cannot be reused in
one controller. Local mode does not connect to a managed host.

## HTTP capability and identity

Trusted embedded launchers may generate the token themselves and call
`create_app(..., agent_token=token)`. Keep it within the launching execution
environment and send only as `Authorization: Bearer ...`. Do not expose it to a
model prompt or borrow a human browser cookie. Same-origin and host checks remain.

`PUT /api/v1/agent/administrator` requires this capability, with exactly username,
password and expected_revision. Human administrator cookies, edit cookies and
scoped Console tokens do not authorize this endpoint. A successful write returns
nonsecret account status and actor=agent, changes salt/hash/revision atomically and
invalidates all administrator sessions, including other processes on their next
revision check. Incorrect revision returns 409 with no write; invalid/empty input
returns 422; missing capability 401; foreign Origin 403. No original password can
be recovered. Human account updates retain their current-password requirement.

The owner token is accepted throughout existing Web authorization gates without
creating a human login. `auth/status` reports human authenticated separately from
agent_authorized; responses identify the actor with `X-OpsFeast-Actor`. Host-note
writes use source=agent, form responses use actor=agent and
authority=agent_capability, and exact-plan work records use agent_owner. These
records do not prove human consent. Enabled-target and data revision checks still
apply; there is no new general audit service or automatic host authorization.
Scoped Console and interactive credentials remain available to explicit embedded
integrations/tests; this launcher no longer generates or persists those tokens.

## Verification limits

`tests/test_agent_owner.py` covers owner-only reset, short passwords, cookie
revocation, revision/origin rejection, token replacement, form actor provenance and
real loopback controller startup/EOF with no token files. Existing Web, records,
interactive and worker tests cover the shared gates and cleanup. This is local and
synthetic evidence, not protection against a hostile process controlling this OS
account, process memory or server code. No email recovery, external identity system
or multi-administrator management is implemented.



Before updating/replacing a checkout, follow [update preservation](update-preservation.md): preserve the same external port/admin/data root and every Profile root. A necessary restart uses the saved external endpoint, never a fresh initialization or a guessed port. The one-time old-registry port transfer is explicit; do not reset credentials, rewrite menu preferences or replay host work.

*Last modified: 2026-11-12 10:55:28*
