# Installation presentation 0.1.0

The installation's human owner is the primary identity of its Web workspace.
Use `/settings/site` to set a site name, slogan, logo and representative avatar.
A favorite character, a comforting machine mascot or a snack image can occupy
this space; no character artwork, external image search or remote image loading
is bundled. Operators supply their own PNG/JPEG files. OpsFeast keeps discreet
attribution in the footer rather than occupying the owner's title/image positions.

## Identity and storage

Reuse [installation identity](core-api.md#installation-instance-and-profile).
UUID, `name`, `description` and copy/move rules remain unchanged. `site_name` is
an explicit presentation override, not another installation identity. Null inherits
an assigned non-UUID instance name; otherwise the UI shows a localized neutral
placeholder. Profile `namespace` is independent and is never changed here.

The schema is [site-presentation.schema.json](../schemas/site-presentation.schema.json):

| Field | Contract |
| --- | --- |
| `schema_version` | Exactly `0.1.0` |
| `revision` | Nonnegative integer; each successful save increments once |
| `site_name` | Null to inherit, or nonblank single-line text up to 80 characters |
| `slogan` | Single-line text up to 160 characters; empty selects the UI's neutral default |
| `logo` | Null for bundled default, or normalized immutable image asset ID; navigation/login identity |
| `avatar` | Null for bundled default, or normalized immutable image asset ID; public welcome/login-page companion |

Settings live in `<installation-data>/.opsfeast-site.json`; normalized images
live in `<installation-data>/.opsfeast-site-assets/`, outside replaceable product
code. Select/attach the root through [persistent installation data](installation-storage.md).
Product-local originals from the earlier prototype are preserved recovery copies,
never a runtime fallback. These are installation-local, not profile
retention, consumer outputs, a user directory or recipe source. Newly created
files are mode 0600; the asset directory is created mode 0700. Cooperating writers
use `.opsfeast-site.lock`, revision checks, temporary files and atomic replacement.
Malformed/unknown data and symlinks fail rather than silently resetting. The lock
is not protection against another program running as the same OS account.

All displayed site settings are **public before user login**, including an inherited
installation name. The settings page warns before saving. Administrator credentials on the same page
are separate private data, never part of this public projection. Only the currently
referenced logo/avatar IDs are published, not the entire asset directory. Restoring the bundled default or replacing a reference stops public retrieval of
the old uploaded ID but preserves its file. Null references use the bundled product
mark until the owner selects an image; they do not copy product assets into user storage. Already downloaded copies cannot be revoked. Unused uploaded images remain
local; no automatic deletion/cleanup is implemented.

Uploads accept at most 2 MiB, actual PNG/JPEG content, dimensions at most 4096 on
each side and at most 16 million pixels. Pillow decodes, applies orientation,
selects the first frame, scales to fit 1024 × 1024, and creates a metadata-free RGBA
PNG. The normalized bytes determine the SHA-256 asset ID. SVG, HTML, arbitrary
paths/URLs and executable theme code are not accepted. Choosing a file previews
it locally; the shared **Save site appearance** action below both columns uploads
and commits name, slogan, logo and avatar together. Image previews explicitly mark
their pending state; selecting a file does not upload or save it. The shared save
bar stays visible while scrolling the appearance section. Administrator credentials
have a separate save action below it. An upload followed by a failed
settings save can leave an unpublished asset, while the previous settings remain.

## Local Web editing capability

The foreground launcher `python -B -m opsfeast.web` binds to 127.0.0.1:8740 and
creates a random per-launch token in the selected installation data root at
`.opsfeast-web-edit-8740.token` (0600).
A different port uses its own token filename. Read that file from the data root locally and paste its
contents into the settings page's edit-token field, then unlock. Do not paste it
into chat, URLs, screenshots or public examples. The browser exchanges it through `POST /api/v1/site/unlock` for a separate random
HttpOnly, SameSite=Strict session cookie (Secure on HTTPS). The original token
text is cleared from the input and application memory after exchange and is never
stored in localStorage/sessionStorage. The server stores only a hash of the
cookie capability, bounds active sessions to 100, and expires each after 30 minutes.

The editing session survives navigation and reload within that window. Opening
site settings revalidates it and restores editing plus the first-account form.
Explicit unlock focuses the username field. `POST /api/v1/site/lock` revokes the
current editing session and clears the cookie; administrator logout also revokes
it. Browser session-cookie policy governs browser close/restore; the server's
30-minute expiry is authoritative. Server restart invalidates all editing sessions.
The next startup needs its new per-launch token; saved appearance is unaffected.
An administrator's independent login session can still authorize site editing.
Credentials typed into the account form are never restored on navigation.

The launcher prints the filename, never the token. Clean foreground shutdown
removes it. A leftover token file blocks startup: check that its server has stopped
before explicitly removing the stale file. Tokens from an earlier server do not
authorize a later server. An occupied port does not silently select another port.
Calling `create_app()` without `edit_token` disables local-token bootstrap/editing;
an already configured administrator can still log in and use authorized settings.
An initialized data root or valid checkout binding remains required.

This authorizes site presentation editing and first-administrator bootstrap, not
a user session, profile management, host access or operation approval.
[The single-administrator service](web-administrator.md) provides real login and
account changes; multiple user/agent identities remain unimplemented. Same-account programs can read the token file;
this does not provide isolation between agents sharing that OS account. Do not
publish the preview through an external bind/proxy. There is no CORS allowance;
mutation/private-settings requests require an administrator session, original Bearer
capability or valid site-edit cookie, and reject foreign
Origin/cross-site fetch headers. Public output never includes UUID, description,
installation paths, profile data or the edit token.

| Endpoint | Contract |
| --- | --- |
| `POST /api/v1/site/unlock` | Same-origin authorized request; issues a 30-minute site-edit session, not admin login |
| `POST /api/v1/site/lock` | Same-origin; revokes current site-edit session and clears cookie |
| `GET /api/v1/site` | Public presentation; resolved display name, with null for neutral UI default |
| `GET /api/v1/site/settings` | Token required; raw settings plus read-only instance ID/name/description/status |
| `PUT /api/v1/site/settings` | Token, JSON `{settings, expected_revision}`; full replacement and revision check |
| `POST /api/v1/site/images` | Token, raw PNG/JPEG body with matching image media type; returns asset ID and normalized dimensions |
| `GET /site-assets/{asset_id}` | Current referenced images only; no credentials required |

Failed authentication returns 401; foreign origin 403; stale revision 409; oversized
body 413; unsupported media type 415; invalid data 422; unavailable/unpublished
image 404. Storage/configuration failures never imply a successful save. The UI
keeps input after failure and asks users to reload after conflicts. This service
never initializes or edits installation identity and has no management-root writes.

## CLI and settings area

The shared [settings area](web-settings.md) groups site, hosts, recipes, defaults
and retention configuration. Site and profile management are currently available there.
Use `python -B -m opsfeast.settings catalog`, `site show` and `site update` for
credential-free local CLI/agent composition under filesystem authority. The guide
defines exact flags, selected-field preservation, revision checks and planned
domain boundaries. The Web token still authorizes site presentation only.

## Reusable Python interface for agents

These are checkout module APIs, not additions to the Core instance schema.
`installation` below can be the persistent data root or a bound product checkout:

```python
from opsfeast import site

settings = site.read_site(installation)  # no initialization or connections
image = site.upload_image(installation, png_or_jpeg_bytes)  # authorized local write
updated = site.save_site(
    installation,
    dict(settings, site_name="Synthetic lab", slogan="Reviewed operations", avatar=image["asset_id"]),
    expected_revision=settings["revision"],
)
public = site.public_site(installation)  # same projection used by the Web
```

Use existing settings and explicit fields; preserve other choices and always pass
the read revision. On `site.SiteConflict`, reread and reconcile rather than retrying
an old full replacement. `site.image_path()` resolves only published images. Do
not write JSON, rename asset files or copy private bindings into `web/assets/`.
Pillow is required only for image ingestion; it is pinned in `requirements-web.txt`.
The Web serves saved settings on each navigation/reload; this is not a background
subscription or live cross-browser synchronization service.

## Delivery and verification limits

The UI authoring catalog remains Traditional Chinese. Private site names/slogans
are user content and are not translated by locale selection. The framework-free
preview remains checkout-only; no presentation SDK, arbitrary extension routes,
custom theme editor or multiple-user/per-agent authorization is delivered. The avatar is a
static image, not an animated agent or autonomous worker.

Public tests `test_site.py` cover inheritance, preserved identity/namespace,
revision conflicts, malformed input, symlinks, image normalization/metadata and
publication revocation without deletion. `test_web_preview.py` covers route/token/
origin/media/size gates and publication. The locale tests cover independent UI
language and time formatting. No remote systems, external transmission or native
privilege changes are exercised.

*Last modified: 2026-11-01 23:39:52*
