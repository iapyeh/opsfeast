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
There are no default credentials. The human may provide a password in the agent
conversation or ask for generation; do not invent a change or save secrets in argv,
river records, scripts or repository files.

## First-use Web guide

When no administrator exists, `/` and `/login` show the first-use guide; `/setup`
is its stable route. It explains how to ask the launching agent to create the
administrator, provides a copyable prompt with the website origin, and offers a
progress recheck button. It never asks for a token file or displays the owner token.
After the agent confirms the saved account, the human logs in, then optionally sets
appearance. Reload derives progress from `GET /api/v1/setup` and its
[Boolean schema](../schemas/setup-status.schema.json), including
agent_control_available. Unknown progress never counts as success. No recipe,
managed-host connection or profile is created by this guide.

## Account lifecycle and recovery

1. Start the existing installation with `python -B -u -m opsfeast.web --agent-control`.
   Keep its private stdin/controller alive; see [controls](agent-owner.md).
2. The human asks the agent to set the administrator username/password, supplying
   the password or requesting generation. The agent uses admin.password; no old
   password is needed by its independently authenticated owner identity.
3. Passwords accept exact nonempty Unicode strings, with no character-count or
   composition requirement; normal request-size bounds still apply. Username stays
   3–64 ASCII letters/digits/dot/hyphen/underscore. Password hashing is unchanged.
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

*Last modified: 2026-11-05 16:06:59*
