For login-to-river handoff, use [browser readiness 0.1.0](browser-events.md): open the exact river so login retains its scoped next URL, then continue already-authorized work without waiting for a "logged in" reply. The reader reports `reader.opened` and the owner controller pushes `browser_event` on its existing stdout; this is readiness evidence, never approval or automatic model wakeup. Separate installations use namespaced authentication/editing cookies.

# Local administrator and profile settings

The Web installation has one administrator account. `/settings/site` is named
**站台設定** in the Traditional Chinese UI and includes presentation plus account
setup. `/settings/profiles` shows current profile state and supports create,
attach and switch through the existing Core interfaces.

The Profiles page remains at `/settings/profiles` when signed out and shows an
explicit login prompt (or account setup link if no administrator exists). It
does not expose profile data or mutation forms before login. Its login link
returns to Profiles after authentication; unsupported return destinations use
the workspace. Server restart invalidates the in-memory administrator session.

A valid human administrator session opening `/login` receives HTTP 303 to
`/workspace` (the signed-in landing page), or to its supported local `next`
destination using the same allowlist as successful login. External, unsupported
and self-referencing destinations fall back to `/workspace`. Anonymous, expired,
revoked or credential-invalidated sessions still see login; agent and site-edit
capabilities alone do not trigger this redirect. Responses remain `no-store`.

This is loopback-only single-administrator login plus an independent
[agent owner capability](agent-owner.md), not multi-user RBAC or public hosting.
The human administrator owns decisions; the agent can perform all Web operations
with its memory-only capability only within the human's instructions and consent.
There are no default credentials. Use the private first-account Web form by default; do not ask for credentials
in the agent conversation. Explicit agent reset/generation remains available when
the human specifically requests that workflow; do not invent a change or save secrets in argv,
river records, scripts or repository files.

## First-use Web guide

For agent-led installation, immediately issue the private Web form after readiness,
using the retained controller. The human enters credentials in the browser; the
agent reads only completion status. Do not wait for a copied prompt, ask for secrets
in chat, or reset existing accounts. Follow the procedure below.


If an unconfigured installation was launched without agent control, onboarding
shows a copyable recovery instruction and tells the human to send it in the
original agent chat, then return and recheck after completion. Copying does not
contact an agent or restart anything. Follow [Web startup verification](getting-started.md#include-and-launch-the-web-workspace):
preserve the existing data/port, reconcile active work, and verify agent control
before inviting the human to configure an account. Failed status requests retain
the generic retry message rather than claiming a known launch problem.


The normal [first-use setup plan](getting-started.md#include-and-launch-the-web-workspace)
already includes selecting the installation's loopback port, starting Web, verifying
HTTP and providing the actual URL. This browser guide handles the remaining account
choices; it does not replace that agent startup/handoff responsibility. Preserve
an existing administrator; startup alone never grants a password reset.

When no administrator exists, `/` and `/login` show the first-use guide; `/setup`
is its stable route. A dedicated link opens the account form. A plain visit explains
how to obtain that link, with a copyable instruction only for interrupted setup.
After creation, the human logs in and optionally sets appearance. Reload derives
progress from `GET /api/v1/setup` and its [Boolean schema](../schemas/setup-status.schema.json).
No managed-host operation or Profile creation occurs.

## Private first-account form 0.1.0

1. After authorized first-use startup, send the retained controller:
   `{"op":"admin.setup-form","request_id":"setup-form-1","authorization":"Human approved first-use Web setup"}`.
   This calls owner-only `POST /api/v1/agent/setup-form` with `{}` and returns
   `{schema_version:"0.1.0",url,expires_in:600}`. Present that exact link to the human;
   the narrow setup secret is distinct from the owner capability. Treat the link
   as private first-account authority, not a public share link. Existing accounts
   return 409 and must be preserved.
2. The link uses `/setup#setup-token=...`. Fragments are not sent in HTTP requests;
   Web removes it from the current history entry before claiming it via same-origin
   JSON `POST /api/v1/setup/claim` with `{token}`. Successful claim consumes the link,
   sets an installation-scoped HttpOnly SameSite=Strict cookie and returns a CSRF
   value kept only in this page's memory. The grant expires ten minutes after issue;
   claiming does not extend it. Reissue revokes the old link and browser grant.
3. The form sends `{username,password,csrf}` to `POST /api/v1/setup/administrator`.
   Both the browser cookie and CSRF value plus an exact Origin are required. The
   server atomically creates revision 1 using `admin.configure(expected_revision=0)`;
   a successful response is only `{configured:true}`. Password confirmation stays
   browser-side. No account/password is returned to the agent, Console, browser
   storage or URL, and only salted scrypt metadata is saved in installation-data.
   The first-account API cannot reset an existing account. This is the local Web
   security boundary, not protection against compromised same-origin code or OS.
4. Validation errors allow correction within the remaining lifetime; password fields
   are cleared after failed submissions. Success consumes the grant and clears
   fields; the human signs in normally. Invalid/missing/replayed/expired grants
   return 401, foreign/missing Origin 403, malformed requests 422 (or 415 for
   non-JSON), existing accounts 409. Concurrent success is bounded by both the
   grant lock and administrator revision check. Errors never echo credentials.
5. Agent reads `GET /api/v1/setup` for `admin_configured: true`; it does not retrieve
   credentials. Pending human input is not failure and does not authorize creating
   an account in chat. Reloading/closing the form, expiration or restarting Web can
   require a fresh `admin.setup-form`; never reinitialize data as recovery. All grants
   are bounded to one outstanding form per server and exist only in memory.

See [transient grant responses](../schemas/setup-form.schema.json),
[controller interface](agent-owner.md) and `tests/test_setup_forms.py` plus
`tests/test_first_use.mjs`. Tests use synthetic credentials, not the user's account.

## Account lifecycle and recovery

1. Start the existing installation with `python -B -u -m opsfeast.web --agent-control`.
   Keep its private stdin/controller alive; see [controls](agent-owner.md).
2. For an absent administrator, issue `admin.setup-form` and use the private Web
   workflow above. Do not ask for passwords in chat. Existing accounts are preserved.
3. Explicitly requested agent resets/generation can still use `admin.password`;
   this alternate path involves the agent channel and is not private Web entry.
   Account usernames require 3–64 ASCII letters/digits/dot/hyphen/underscore.
   Passwords must be nonempty; salted scrypt storage is unchanged.
4. The human logs in at `/login`. Account settings on `/settings/site` still allow
   human changes with the current password and current revision.
5. For a forgotten password, ask the launching agent to set a new one. The owner
   capability can replace an existing password without the old password. Successful
   changes invalidate all login sessions; log in again. Public/browser-only callers
   cannot invoke the agent-only reset endpoint.

Starting/upgrading the service alone never resets the existing administrator or
other saved data. Existing password hashes remain valid. The startup token files
are no longer created; new launches use a private memory-only controller. Scoped
edit-token integration remains distinct and cannot reset an existing account.

`<installation-data>/.opsfeast-admin.json` stores schema 0.1.0, account revision,
username, fixed scrypt algorithm identifier, random salt and derived digest.
[The private schema](../schemas/administrator.schema.json) is not a public response
schema. Passwords are hashed with Python hashlib.scrypt (N=16384, r=8, p=1, dklen=32)
and a new 32-byte random salt on each credential update. Metadata is written 0600
under a cooperating lock with atomic replacement. No plaintext password, salt or
digest is returned by account status APIs. Malformed storage fails rather than
being treated as an unconfigured account. Back up this private file with the
persistent installation data; it is not a recipe asset or presentation export.

Session tokens are random, represented only by their hashes in server memory,
expire after eight hours, and are invalidated on logout, account revision changes
or server restart. The cookie is HttpOnly, SameSite=Strict, with Secure on HTTPS;
the current launcher is HTTP on loopback only. Credential mutations and login/logout
reject foreign Origin/cross-site fetch headers; inputs are bounded JSON. Each
server accepts at most five login attempts per minute and 100 active sessions.
The attempt limit is process-wide, not a distributed brute-force defense.
Same-OS-account programs can access private files; this does not provide OS-user
isolation or authorize exposing the service through a proxy/external bind.

| Endpoint | Access and behavior |
| --- | --- |
| `GET /api/v1/auth/status` | Public configured/authenticated flags; username only when authenticated |
| `POST /api/v1/auth/login` | JSON username/password; generic 401 on failure, 429 on attempt limit |
| `POST /api/v1/auth/logout` | Revokes the current session and clears its cookie |
| `GET /api/v1/admin` | Administrator, or local token before first setup; nonsecret status/revision |
| `POST /api/v1/admin/bootstrap` | Local token, only unconfigured state; username/password/expected_revision=0 |
| `PUT /api/v1/admin` | Admin session; username/password/current_password/expected_revision |

Configured installations redirect unauthenticated workspace/operational-preview
pages to login. Public site/learning/planning pages remain available. Profile
settings always require login. Private profile APIs never accept the site token.
No host execution service or machine-enforced per-command approval is added.

## Unicode password entry and input-method research

The server hashes the exact UTF-8 encoding. It does not trim, normalize or truncate
passwords. Canonically equivalent Unicode sequences remain distinct credentials;
existing accounts keep their current password semantics. The Web creation form
counts code points consistently with Python and does not use the native UTF-16
`maxlength` attribute for passwords. JSON login, bootstrap and password changes
are tested with synthetic Chinese/emoji values. This verifies data handling, not
native IME behavior on every OS/browser or password-manager compatibility.

[utf8passwordinput](https://github.com/iapyeh/utf8passwordinput) is a feasible basis
for an IME-oriented masked text editor. Source reviewed: commit
`d1ae2f770dca54f53c3112fa1c9ea66624e1288b`, root `utf8inputpassword.js`, v2 header
2024-11-16, MIT license (Hsin Yuan Yeh, 2024). Its text-input replacement handles
composition events and synchronizes a hidden native password field. No external
library or CDN is loaded by OpsFeast in this delivery.

Source-review findings to resolve before integration:

- Paste handling iterates `InputEvent.data`, which can be null; read the supplied
  paste text safely and test selection replacement without losing secret text.
- The value setter splits UTF-16 units while insertion uses code points; align
  emoji storage, mask positions, selection and deletion across both paths.
- Programmatically clearing the original password field does not clear the
  replacement widget's stored value. All submit/failure/pagehide paths need one
  clear operation covering both fields and internal state.
- The press-to-reveal span needs keyboard access, an accessible name, and safe
  hide behavior for pointer cancellation, lost focus and window blur. Labels must
  point at the replacement editor.
- Verify real Traditional Chinese IME composition, paste, autofill, repeated
  show/hide, mobile input and password managers on supported browsers. A DOM/unit
  simulation is insufficient evidence of OS input-method behavior.

These are integration requirements inferred from source review. The upstream
library has not been changed, installed or enabled. A reviewed local module with
its MIT notice and source pin can be bundled after these cases are addressed;
credential hashing and authentication remain server-side.

## Profile state and changes

The [profile-status schema](../schemas/profile-settings.schema.json) describes
the administrator-only response. Profile operations use `opsfeast.profile_settings` with `Instance.profiles` and
`Instance.init_profile`; no second registry parser or storage is introduced.

| Endpoint | Access and behavior |
| --- | --- |
| `GET /api/v1/profiles` | Admin; default profile, registered roots, basic availability, namespace and registry revision |
| `POST /api/v1/profiles` | Admin; name/namespace/expected_revision; creates a new root under installation-data/profiles/NAME |
| `PUT /api/v1/profiles/default` | Admin; name/expected_revision; switches the shared default |
| `POST /api/v1/profiles/attach` | Admin; name/root/expected_revision; validates/registers an existing absolute root |

Availability is basic local configuration evidence, not connection/account/recipe
verification. Missing/invalid states remain visible. Read-only status does not
create a registry, scaffold or lock file. Reads detect registry changes by digest;
cooperating Core/Web updates check that digest under the existing registry lock.
External editors/noncooperating writers are not prevented from changing files.

Creation refuses registered names and occupied target directories. It does not
reinitialize existing profiles. Initialization/registration is not a multi-file
transaction: a late conflict or failure can leave a new candidate directory;
inspect it before retrying, and never delete it automatically. Attach preserves
existing files and existing name/root conflict rules. Switching defaults affects
later CLI/default selections, not a running job or explicitly selected profile.
No profile rename, root relocation, namespace rewrite, detach or deletion is added
to Web. Existing [profile CLI](profiles.md) remains available.

Existing registry locations and existing management roots remain unchanged. New
Web-created roots are external to product code, but the profile registry is still
checkout-local. Preserve that registry and all existing roots separately when
replacing a checkout; storage binding currently preserves identity/site/account
files, not profile registrations automatically.

## CLI and module use

```sh
.venv/bin/python -B -m opsfeast.settings admin show
# Private terminal: prompts for password/confirmation, and current password on update.
.venv/bin/python -B -m opsfeast.settings admin set --username YOUR_USERNAME --expected-revision 0
```

The CLI follows local filesystem authority; it does not need a Web session.
Noninteractive account updates require explicit `--password-stdin`: bounded private
JSON with `password` and optional `current_password`. Username/revision remain CLI
arguments. Do not put password literals in shell history, shared commands or
public examples. A missing flag in a nonterminal fails without waiting for input.
Outputs contain only nonsecret account status. Existing account updates still
require the current password and correct revision.

Checkout APIs are `opsfeast.admin.status/verify/configure/set_by_agent` and
`opsfeast.profile_settings.inspect/create/use/attach`. These are local trusted-code
interfaces, not an authorization sandbox. `configure` has required username,
password and expected_revision, with current_password for human updates.
`set_by_agent` is a trusted local function, not an independently authenticated API;
Web callers must use the owner-only endpoint. Profile APIs
require the registry digest for writes. See existing CLI/Core guides for operational
scope; only owner-authorized configuration changes are appropriate here.

## Verification and references

Synthetic tests cover salted password storage, absent defaults, invalid/corrupt
metadata, current-password/revision gates, session cookie/logout/expiry/revision
invalidation, login limits, unauthorized/foreign-origin rejection, profile status,
creation/attachment/default changes and preservation of occupied directories.
They do not configure a real administrator, connect to managed hosts or prove
public-network readiness.

Implementation references: [Python hashlib](https://docs.python.org/3/library/hashlib.html#hashlib.scrypt)
and [Starlette response cookies](https://starlette.dev/responses/#set-cookie).

*Last modified: 2026-11-12 10:57:17*
