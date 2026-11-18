# Web design and review

OpsFeast serves framework-free HTML, CSS and JavaScript modules from `web/`,
through its Python Web adapter. Svelte/SvelteKit integration remains planned.
Read [the Web guide](../web/README.md) and the
[owner-centered identity principle](vision.md#make-the-users-workspace-the-protagonist).

## Supported design target

The current product design and acceptance target is the desktop browser. Review
ordinary laptop/desktop widths (1280px, 1440px and wide desktop) and large browser
zoom. Dedicated mobile/tablet layouts and device test matrices are deferred.
Existing responsive CSS is retained where useful, without a mobile support claim.
Do not add fixed minimum page widths or clip long content just to enforce desktop.

Keep components reusable, widths flexible, long host IDs/paths/IPv6 readable and
controls semantic. Essential actions must work through standard buttons/forms and
keyboard focus; no hover-only recovery of hidden values. These fundamentals keep
later mobile/tablet design feasible without promising that it is implemented.

## Shared visual system

The approved host-page direction now applies to the complete shipped Web surface:

| Surface | Shared treatment |
| --- | --- |
| Welcome/login and first-use guide | Owner identity, quiet surfaces, labelled controls and clear actions |
| Workspace overview | Readable host count, independent notification/todo cards and navigation links |
| Hosts and host details | Filtered inventory, explicit configuration state, separated saved evidence, settings/notes/history/accounts |
| Recipes, saved data, work and logs | Consistent filters, wrapping tables, textual status badges and result links |
| Settings, site, administrator and Profiles | Shared cards, fields, dialogs, validation feedback and action rows |
| Skills, textbook and document library | Searchable document cards and inert, wrapping source readers |
| Operations and application guides | Common navigation, panels and documented capability boundaries |
| Console live/history/block readers | Light workspace context with a contrasting terminal transcript |
| Exact-plan `/interactive` | Shared panels/controls without changing execution or approval semantics |

`web/assets/design-tokens.css` owns internal `--ui-*` font, surface, text, muted,
border, control, accent, danger, warning, spacing and terminal roles. Both
`workbench.css` and `console-reader.css` import it locally. The host variables
alias these roles. Maintain the existing stylesheets/components instead of
creating a parallel theme per page. These private tokens are not a presentation
SDK, versioned appearance contract or owner theme editor.

Use white cards, a restrained green accent and an 8px spacing rhythm. Body text
uses local/system sans-serif fonts; command/evidence content uses a local
monospace stack. No remote fonts, CDN, animation library, frontend build step or
new product dependency is introduced. The SVG navigation icons are a local,
decorative set with text labels supplied by the native links.

Preserve the owner's installation name and images in prominent positions, with
OpsFeast attribution in the footer. Presentation changes never alter installation
identity, private Profile bindings, permissions or saved observations.

## Compact desktop controls

Desktop fields use the shared `--ui-control-height` (38px minimum); ordinary
buttons use `--ui-button-height` (36px minimum). Reduce vertical padding rather
than fixing every control's height: wrapped button text and multiline textareas
must still grow. Host controls use the same compact sizing; decorative plus signs
use a single line so their inherited line box does not inflate the button.
Navigation links and terminal layouts retain their own sizing.

Inline label/control groups use an 8px gap and 4px horizontal insets. Existing
classed grid/stacked labels keep their layout through low-specificity defaults.
The execution plate content has 16px block margins, separating the grey selected
host/recipe panels from both the header action buttons and the execution-review
button below. Keep this structural spacing independent of compact button height.

Action rows use centered cross-axis alignment with 8px vertical / 12px horizontal
gaps, preventing tall labels from stretching neighboring buttons. Standalone
sibling buttons also have an 8px inline-start margin. Do not add margins to every
100%-width input: that can overflow its container. Keep full-width fields within
their parent and provide spacing through labels, wrappers and action-row gaps.

Browser verification on a separate synthetic installation measured Recipes
search/select controls at 38px and buttons at 36px; host filters and the add button
measured 38px. Recipe/meal forms retained an 8px label gap and multiline textarea
height. Recipes and host views had no document-level horizontal overflow at the
reviewed desktop viewport. This does not establish mobile/tablet or every page's
layout. The previous 44px minimum plus 10px vertical padding originated in local
CSS; consulting UI UX Pro Max did not install or render third-party components.

## Recipe information boundaries

Keep business title/description in their own header. Show the collection purpose,
operator-editable options, readable execution conditions and recent outcomes/reports
before technical content. Move raw data/contracts, routines, protocol field codes
and the definition/composition overview into the lower **Technical details and
composition** area. Place reference, ID, version,
static state and update/change metadata in a separate card; the latest change note
is a closed disclosure. Execution conditions explain why a recipe cannot run.
The composition overview shows missing and optional components before the grouped
content previews. Semantic role names and resource titles are primary; filenames
are secondary source information. Distinguish provided text, existing files and
declared settings from passed execution checks. Read [the shared content contract](recipe-definition-authoring.md#human-readable-purpose-metadata-and-composition).

## Interaction and account editing

Native fields have visible labels, usable boundaries, keyboard focus and retained
drafts on errors. Buttons distinguish primary and destructive actions. Tables
wrap long values and retain column headings. Status badges always retain text;
unknown/partial/failure/empty states must not become success or fabricated counts.
Console source/identity, folding, follow/history mode and private reply behavior
keep their existing contracts. Do not open live sessions merely for visual review.

The host **設定** page now includes account-declaration add/edit/remove through
[host settings 0.2.0](web-hosts.md#account-declarations-020). Existing account names
are read-only; edits change sudo policy, preserve hidden fields and use revisions
and private backups. Creation defaults sudo off in the Web form. Removal is a
separate dialog and removes that declaration's private settings, not the remote
OS account or connection identity. Password/rename editing is not offered.
Do not test mutations against real host configuration for visual verification.

UI text stays in its existing Traditional Chinese locale catalogs; source
operational text is not translated. Reuse i18n date formatting with Asia/Taipei
and seconds while retaining unknown and invalid-source evidence. New human/agent
documentation remains English under the repository convention.

## Design reference and judgment

This work consulted [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/4f2dbb67e64969a9a30ab00742f2d55d66ddec2b),
`main` snapshot `4f2dbb67e64969a9a30ab00742f2d55d66ddec2b`, on 2026-11-08.
Instructions, search scripts and catalogs were acquired in temporary storage;
no upstream skill was installed into an agent loader or vendored into the product.
The optional upstream search can reproduce the development guidance:

```sh
python -B /path/to/upstream/src/ui-ux-pro-max/scripts/search.py \
  "internal operations dashboard" --design-system --density 8 --variance 2 -p OpsFeast
python -B /path/to/upstream/src/ui-ux-pro-max/scripts/search.py \
  "data table filtering" --domain ux -n 2
python -B /path/to/upstream/src/ui-ux-pro-max/scripts/search.py \
  "badge chip label wraps" --domain ux -n 2
python -B /path/to/upstream/src/ui-ux-pro-max/scripts/search.py \
  "form labels error clarity" --domain ux -n 2
```

Minimalism & Swiss Style, table handling, contextual counts, semantic controls,
text layout and contrast informed implementation. Marketing-page composition,
blue/orange branding, external fonts and motion suggestions were not adopted.
Search results are product-design inputs, not authority over repository contracts
or proof of accessibility. Upstream tooling is optional for future maintenance.

## Verification

From the checkout with the approved Python environment and Node.js:

```sh
node --check web/assets/workbench.js
node --check web/assets/workspace.mjs
node --check web/assets/host-accounts.mjs
node --test tests/*.mjs
.venv/bin/python -B -m unittest discover -s tests -p 'test_*.py'
```

`test_host_manager.mjs` covers search, exact groups, enabled filters, escaping,
unknown/empty/failed evidence and source-time display. `test_host_accounts.mjs`
covers the narrow payload, default-off additions, edit/remove dialogs, revision
handoff, duplicate/conflict handling, draft preservation and decorative SVGs.
`test_host_settings.py` and `test_web_preview.py` verify real synthetic local
add/update/remove persistence, defining-source selection, preserved secrets,
backups, validation, authentication/origin gates and stale revisions. Existing
workspace/Console tests preserve scope, data states and reader semantics.

Browser review must cover the routes above with the existing installation's normal
login, using synthetic fixtures for mutations or missing states. Review desktop
layout, zoom, long text, keyboard focus, error feedback and Console history without
executing commands or submitting private human forms. Temporary fixtures belong
outside product routes and user Profiles. Never reset a real password for review.

Text/accent token pairs meet the 4.5:1 normal-text threshold; input/focus boundaries
are checked separately. This is a light-only interface. No full accessibility
certification, assistive-technology matrix, mobile/tablet support or remote host
health claim is implied. Preserve the existing Web service after verification.

## Local verification evidence

For the full pending UI/account change on 2026-11-08, 1,316 Python tests passed;
the expanded Web API checks and account-source/secret-preservation cases were
also rerun successfully after their final additions. All 70 JavaScript tests
passed. Wheel/sdist builds succeeded with the updated host service and without
private installation/Profile data in the wheel.

Desktop Chrome review opened all ordinary route families listed above, including
welcome/login/setup, settings categories, library/source readers, saved data,
host accounts and Console history/block pages. Add/edit/remove account dialogs
were opened and cancelled against a real host; writes were exercised only in
synthetic tests. The exact-plan page was inspected without creating or executing
work. Live command execution and mobile/tablet verification were outside scope.
The existing Web service was restored on its saved endpoint and returned HTTP 200.

*Last modified: 2026-11-17 16:21:06*
