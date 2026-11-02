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

This is a loopback-only local administration foundation, not multi-user RBAC,
per-agent credentials, public hosting, SSO or an operational approval service.
There are no default credentials. The human owner must enter a username/password
in the page or their own private terminal; agents must not invent or provision a
real default password, expose credentials in chat, or pass passwords on argv.

## First-use Web guide

When no administrator is configured, `/` and `/login` present the first-use guide
directly; `/setup` is its stable route. No settings-menu navigation or manual lookup
is needed. The three stages are local authorization, administrator creation, and
optional owner appearance. The page explains what to do next, includes a copyable
agent-assistance prompt, and offers inline instructions for manually locating the
per-launch token in the launcher's Installation data directory. The token filename
uses the current port; actual token text and private data-root paths are not exposed
by public endpoints or included in the prompt.

`GET /api/v1/setup` returns only versioned Boolean progress/availability flags;
see [schema](../schemas/setup-status.schema.json). The guide uses this server evidence
to resume after reload. A failed/unknown status never counts as account completion.
After token verification, the existing 30-minute edit cookie authorizes the
account form. The human enters and submits their own credentials. Only the real
saved account response advances to appearance; it does not automatically log in.

Appearance reuses the existing site editor and image contract; Save appearance
and finish commits all selected appearance fields. Skip performs no write and
preserves any existing appearance. The completion page offers login (or workspace
for an already logged-in administrator). An existing account with no edit/login
session is directed to login before resuming `/setup`. Once an account exists,
the ordinary welcome/login pages return; the guide remains accessible at `/setup`.
No new onboarding database, default account/password, profile, host connection,
recipe execution or installation identity is created by the guide.

Agents must keep the human at the credential-entry step: help obtain local edit
capability within authorized scope, never invent a password or self-submit real
credentials. Real Chinese IME behavior remains subject to the input-method limits
below. The guide is currently authored only in Traditional Chinese.

## Account lifecycle and storage

1. Start the local server using the selected persistent installation data root.
2. On `/settings/site`, unlock local editing using the per-launch token from that
   data directory. It can edit site presentation and bootstrap the first admin.
   Unlock exchanges the token for a 30-minute HttpOnly site-edit session, so page
   navigation/reload restores the form without pasting the token again. Ending
   editing, logout, expiry or server restart ends this local capability. This is
   independent of administrator login and cannot change an existing account.
3. The owner enters a username, new password and confirmation. Username allows
   3–64 ASCII letters/digits/dot/hyphen/underscore; passwords require 12–256 Unicode
   code points (not UTF-8 bytes or UTF-16 units). Chinese and emoji are accepted.
   Click **Create administrator**, separately from **Save site appearance**. Only
   a confirmed saved response advances the badge to configured and offers login.
   Username/length/mismatch failures are explicit, focused error messages. The
   signed-out settings panel distinguishes absent accounts from existing accounts
   that require login; saving public site settings never creates an account.
4. Log in at `/login`. The page uses actual authentication when configured;
   before setup it directs the owner to site settings and disables login fields.
5. Account changes require an authenticated administrator, the current password,
   new username/password and the current administrator revision. Changes invalidate
   all existing sessions, including sessions from another running Web process when
   they next check the stored revision. Log in again afterward.

The token cannot change an existing account or inspect/manage profiles. It is not
an account-recovery backdoor. A logged-in admin can also unlock site presentation
editing without a token. No account deletion, password reset/recovery, delegated
agent credential or multiple-admin management is implemented.

To change credentials, sign in and open `/settings/site`, then the administrator
section. Supply the current password, desired username, new password and its
confirmation, and save that section. The account-change login link returns here
after authentication. Account changes invalidate all sessions; login is required
again. Merely unlocking public site editing cannot change an existing account.

For a forgotten username, a local owner can inspect nonsecret account status with
`python -B -m opsfeast.settings admin show` using the same installation/data root.
For a forgotten password, this release has no recovery/reset command or Web flow.
Do not delete or edit administrator metadata, suggest a default password, or use
the presentation token as a bypass. Preserve the data and establish an explicitly
authorized local recovery design before implementing any reset. Password hashes
cannot recover the original password. The login page exposes these limits in its
account-help disclosure.

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

Checkout APIs are `opsfeast.admin.status/verify/configure` and
`opsfeast.profile_settings.inspect/create/use/attach`. These are local trusted-code
interfaces, not an authorization sandbox. `configure` has required username,
password and expected_revision, with current_password for updates. Profile APIs
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

*Last modified: 2026-11-01 23:38:13*
