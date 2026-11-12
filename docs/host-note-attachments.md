# Host-note document bundles 0.1.0

A host note can own immutable document bundles: an entry Markdown/HTML document and
its relative images, scripts, styles, libraries and data. The note body stays escaped
plain text and carries the summary, evidence time, limitations and proposed actions.
Use a new note/bundle for a later analysis rather than overwriting an earlier report.
These are private Profile data, not bundled recipes or retained observations.

## Human workflow

Open **Hosts → select host → 主機筆記**. Save a note first, then choose **加入文件包**
on that note. Upload a ZIP, a single `.md`/`.html`, or a directory. Directory selection
removes the browser's outer selected-folder name; ZIP paths are preserved exactly.
Enter a title and the entry's case-sensitive relative path, such as `index.md`,
`report/analysis.md` or `index.html`. Review configuration snapshots/reports for
credentials and other private material before choosing what to preserve.

The attachment opens in a separate reader tab with host/note navigation, file list,
SHA-256 values, source view, individual downloads and full ZIP export. Markdown
supports headings, lists, tables, fenced code and PNG/JPEG/GIF/WebP images. Raw HTML
in Markdown is text; external images, SVG and unsupported image formats are not
loaded in this reader. Bundle-local document links download rather than execute.
HTTP/HTTPS text links open separately. Missing/blocked images are listed visibly.

HTML is not executed on upload or opening the reader. Select **開啟隔離互動預覽**
to run it in the sandbox, or use source/download without running it. The reader
reports statically detectable missing/external resource references; this scan is
bounded and cannot establish every JavaScript-generated URL or successful rendering.
Do not automatically download missing libraries or silently replace CDN references.
A report requiring external APIs/CDNs must be deliberately made self-contained or
remain source/download only.

**停止預覽** removes the executing iframe. Closing/navigating away from the reader
also removes it. A reader timer stops the frame when its 15-minute grant expires;
background-tab timer throttling can delay that UI action. Server resource access
expires independently. Reopening creates a fresh scoped grant. Already loaded JS
is browser execution, not a remote host command or a server subprocess.

Deleting an attachment requires explicit confirmation. Deleting a note also removes
its bundles. Merge preserves the union on the surviving note, subject to the
32-attachment limit. Plain note edits preserve attachments. Attachment add/remove updates the note modification
time; the bundle creation time is import time, not proof of analysis/sample age.
Record original collection/analysis times in the summary/report. These are local writes,
never host connections or permission to run recipes.

## Files, storage and preservation

```text
<profile-root>/
  .host-notes.json
  .host-note-attachments/
    <bundle-uuid>/
      manifest.json
      files/
        index.md                 # or index.html
        images/topology.png
        scripts/app.mjs
        vendor/three.module.js
        vendor/three.core.js
        data/topology.json
```

The note stores read-only `attachments` references; callers cannot inject them via
ordinary note changes. Each reference contains UUID, title, entry, kind, file count,
total bytes, manifest SHA-256 and UTC creation time. The manifest owns exact paths,
byte counts and SHA-256 for every copied file plus static resource warnings. Import
never rewrites the user's source or executes it. Downloads reproduce original file
bytes; ZIP container bytes/timestamps need not match the imported ZIP. Relative query
strings select the same immutable resource, not a dynamic server operation.

A missing attachment field means no attachments; reads do not rewrite old notes.
Current note APIs return the additional list. This extends the current note 0.1.0
object; older strict readers must be updated before writing these notes. No automatic
migration, compatibility shim or initialization is performed. Preserve **both**
`.host-notes.json` and the entire attachment directory on backup/update/replacement;
reuse the same resolved Profile root. See [update preservation](update-preservation.md).
Nothing belongs under replaceable product `web/` or agent temporary directories.

Writes use the Profile registry lock and the existing profile-wide note revision.
An upload validates first, copies into a private staging directory, publishes its
immutable UUID directory and atomically links it to the note. A failed metadata commit
rolls back a new directory only after a fresh read proves it is unreferenced;
uncertain writes preserve linked or unreadable-state bytes. A process crash can leave unreferenced staging/UUID
files. Do not guess which files to remove or run automatic garbage collection.
Review the current note references and private backup before targeted cleanup.

Deletion commits the reference removal first, then cleans only the selected bundle
IDs. Receipts distinguish `cleanup.deleted` and `cleanup.failed`; note deletion uses
`attachment_cleanup`. A cleanup failure does not restore the reference or erase its
receipt: preserve the original source and report the remaining private bytes for
explicit repair. Future resource reads require a current note reference and stop
working on deletion. Already loaded frames require stopping/closing independently.

## Limits and errors

| Limit | Current value |
| --- | --- |
| Attachments per note | 32, including the union after merge |
| Files per bundle | 256 |
| Total uncompressed file bytes | 64 MiB |
| Individual file | 16 MiB |
| UTF-8 Markdown/HTML entry | 2 MiB |
| ZIP upload | 65 MiB, allowing export of a full uncompressed bundle |
| Expansion ratio per ZIP member | At most 200:1 |
| Static text scan | 2 MiB per file, 4 MiB per bundle |
| HTML preview grant | 15 minutes; at most 128 unexpired grants per server |

Absolute paths, `..` path members, backslashes, hidden path components, percent/query/
fragment characters in filenames, Windows-reserved/trailing-dot-or-space names,
duplicate case-folded names, symlinks, encrypted
archives and special files are rejected. References may use `../` only when resolving
inside the bundle. Archive entries never extract into arbitrary filesystem paths.
An entry must exist and use `.md`, `.html` or `.htm`. SVG may be an isolated HTML
resource but is not exposed as an active image/document on the management origin.

Typed failures include `note_revision_conflict` (HTTP 409), missing note/bundle/file
(404), invalid paths/archive/entry, limits, digest mismatch or unavailable storage
(422), and unavailable auxiliary listener (503). The API also enforces bounded body
sizes (413), supported content type (415), administrator/owner authentication (401)
and same-origin writes (403). Do not retry an uncertain write automatically: reread
notes and check attachment identities before deciding whether another write is needed.
Missing/malformed storage fails visibly instead of returning empty report content.

## HTML isolation and three.js

The main app's authenticated reader lazily starts an auxiliary HTTP listener on a
separate available loopback port. Its origin differs from the management app; the
transient port is not a new installation Web port. It stops with Web. Failure to
start leaves source/download usable and reports preview unavailable; it does not
weaken isolation or stop another listener.

Each preview URL grants read-only access to **one current bundle** through a random
256-bit path token. It is private, transient and not an administrator/owner token.
Do not share it publicly or save it as a durable link. The listener ignores cookies;
ports alone do not isolate cookies, so both iframe sandbox and HTTP CSP force an
opaque origin with `allow-scripts` and **without** `allow-same-origin`. The frame
cannot read parent DOM or `document.cookie`; authentication never uses a browser
cookie or a main-app capability at this listener.

The reader's CSP allows frames only from its exact auxiliary origin. Resource CSP
allows that package's assets and inline HTML scripts/styles, with no `eval`, worker,
service worker, frame, plugin, form or arbitrary network target. CORS `*` without
credential support permits opaque-origin ES modules, textures and package-local
`fetch()`; the narrow token and current note reference authorize the bytes. All
resources use `nosniff`, `no-store` and `no-referrer`. Direct top-level HTML/SVG
navigation is refused; SVG is allowed only as an image or sandboxed frame resource.

For three.js, include the reviewed library and dependencies under `vendor/`, preserve
its licence, and use relative imports or a local import map. Package models, textures,
fonts and JSON too. Standard ES modules, WebGL and package-local JSON are supported;
Web Worker/Service Worker, Wasm requiring eval, external CDN/API, authenticated API
and arbitrary server code are unsupported. Browser/GPU availability still matters.
This isolates the management interface and constrains ordinary resource/fetch
connections through CSP; it is not OS-level network isolation across every browser
API, a CPU/memory quota, or protection against a compromised browser/OS. Open only
reviewed interactive documents. The server never runs uploaded JavaScript or HTML.

Verification: synthetic service/HTTP tests cover limits, traversal, revisions,
preservation, deletion, authority, MIME and scoped grants. A clean headless Chromium
session additionally exercised ZIP upload, Markdown/table/image/code rendering,
three.js **r180**, local ES modules/JSON and WebGL, and observed blocked parent/cookie/
management API access and off-origin navigation. This is not a claim about every
three.js version, extension, browser or GPU.

## Reproduce browser verification

The ordinary targeted tests are local and synthetic:

```sh
python -B -m unittest discover -s tests -p 'test_note_bundle*.py'
node --test tests/test_note_bundles.mjs tests/test_host_notes.mjs tests/test_profile_navigation.mjs
```

For the optional full browser path, use a local Chromium executable, Node with a
built-in WebSocket client (verified with Node 24), and reviewed local three.js r180
`three.module.js`/`three.core.js`. The fixture never downloads them or uses human
Profiles/browser state. From the actual checkout, start the synthetic fixture with
the selected Web interpreter, then run the smoke in another terminal:

```sh
PYTHONPATH=. python -B tests/browser/note_bundle_fixture.py --three-dir /private/reviewed-three-r180 --metadata /private/tmp/bundle-fixture.json
node tests/browser/note_bundle_smoke.mjs /absolute/path/to/chrome /private/tmp/bundle-fixture.json
```

Use a fresh fixture for each smoke run. The metadata destination must not already
exist. The foreground fixture prints its
random local URL; the smoke uses only this fixture, creates its own temporary browser
profile, and returns JSON evidence. Stop the fixture with Ctrl-C when finished; its
auxiliary preview closes too. Browser-library availability is a real prerequisite,
not permission to install/download packages or connect to a human installation.

## Shared Python and CLI interfaces

Use checkout module `opsfeast.note_bundles`, not a new Core SDK method. First read
`host_notes.inspect(...)` to select the exact note UUID and current revision.
Saving requires the human's reviewed note/attachment scope; local reads do not
provide host connection or recipe authorization.

```python
from opsfeast import host_notes, note_bundles

state = host_notes.inspect(installation, profile='lab', host_id='node')
receipt = note_bundles.create(
    installation, profile='lab', host_id='node', note_uuid=reviewed_note_uuid,
    expected_revision=state['revision'], title='Nginx configuration analysis',
    entry='index.md', source='/private/reviewed-report')  # directory or ZIP
scope = dict(profile='lab', host_id='node', note_uuid=reviewed_note_uuid,
             bundle_uuid=receipt['bundle']['uuid'])
metadata = note_bundles.inspect(installation, **scope)
original = note_bundles.read_file(installation, **scope, path='index.md')
zip_bytes = note_bundles.export(installation, **scope)
```

`create` accepts exactly one of `source=Path`, `archive=bytes` or
`files={relative_path: bytes}`. `delete` requires the current `expected_revision`
and exact UUID `confirmation`; it returns the cleanup receipt. All imports/exports
are local copies; there is no library installer, publisher or server-side runner.

```sh
python -B -m opsfeast.note_bundles --installation /absolute/product --profile lab --host node --note NOTE_UUID add --source /private/reviewed-report --entry index.md --title 'Nginx analysis' --expected-revision REVISION
python -B -m opsfeast.note_bundles --installation /absolute/product --profile lab --host node --note NOTE_UUID show BUNDLE_UUID
python -B -m opsfeast.note_bundles --installation /absolute/product --profile lab --host node --note NOTE_UUID export BUNDLE_UUID --output /private/report.zip
python -B -m opsfeast.note_bundles --installation /absolute/product --profile lab --host node --note NOTE_UUID delete BUNDLE_UUID --expected-revision REVISION --confirm BUNDLE_UUID
```

CLI output is JSON; export refuses to overwrite an existing output file. Its source
entry files are not executed or evaluated. Read metadata first, then only necessary
report/source files; notes search covers attachment titles/entry names, not full text
inside packages. Report analysis age separately from the current host state.

## Web API

All main-app routes require administrator or agent-owner authentication; Console
writer tokens do not suffice. Scope is `profile`, `host_id`, `note_uuid`, `bundle_uuid`.

- POST `/api/v1/note-bundles?profile=...&host_id=...&note_uuid=...&expected_revision=...&title=...&entry=...`:
  `application/zip` body, or JSON `{files:[{path,base64}]}`. JSON body bound is 90 MiB;
  decoded file limits above apply before storage. Returns metadata and new revision.
- GET `/api/v1/note-bundles`, `/markdown`, `/export`, `/file`, `/image` with the scope
  query; file/image additionally require `path`. Metadata returns reference, files,
  warnings and note revision. Markdown returns safe HTML and blocked image warnings.
  Files download as octet-stream attachments; only verified raster images render
  directly on the management origin. Export returns ZIP.
- DELETE `/api/v1/note-bundles`: JSON scope plus `expected_revision`, `confirmation`.
- POST `/api/v1/note-bundles/preview`: JSON scope; returns private URL, expiry and
  required sandbox. Creating the grant does not itself execute the HTML.
- GET `/note-attachments` with scope: human reader, retaining the exact destination
  across login. Main-app CSP is never relaxed to execute uploaded scripts.

See [bundle schema](../schemas/host-note-document-bundle.schema.json),
[notes](host-notes.md), [agent capability map](agent-capabilities.md) and tests
`test_note_bundles.py`, `test_note_bundle_web.py`, `test_note_bundles.mjs`.

*Last modified: 2026-11-12 13:48:53*
