# Recipe authors, licenses and installation defaults

Recipe attribution contract **0.1.0** adds the same fields to inventory descriptor 0.3.0 and Python-session/report descriptor 0.3.0:

```yaml
author:
  name: Example author
  contacts:
    - https://example.invalid/contact
license: MIT
```

Author requires exactly a nonempty name and a nonempty list of contact strings. License is a nonempty declared identifier or `Unknown`; it is not interpreted as a legal grant or verified publisher evidence. Missing fields normalize to `author: {name: Unknown, contacts: [Unknown]}` and `license: Unknown` without changing the descriptor. New recipes should write both fields explicitly. Additional author keys, empty/wrong-type values and duplicate YAML fields are rejected. Catalog/Info expose these fields and static inspection errors.

## Installation defaults

Each checkout can have `.opsfeast-author.yaml` at its root, separate from `.opsfeast.yaml` profile registration:

```yaml
schema_version: 1
recipe_defaults:
  author:
    name: Unknown
    contacts: [Unknown]
  license: Unknown
```

In Home, under **Defaults for New Recipes**, Tab to **Recipe Author**, **Author Contact Info** or **Default Recipe License**, then press Enter or click to open an Input dialog. Enter or **Save** validates and saves that field immediately; Escape or **Cancel** discards the edit. Contacts uses a JSON list, for example `["name@example.org", "https://example.org/contact"]`; name and license use plain text. Empty values and reserved Bundle names/contacts are rejected with an inline error. Saving updates this local, Git-ignored file atomically, preserves the other fields, and refreshes Home. A missing file is created only on successful Save. Failed writes leave the previous file intact; invalid existing files must be repaired directly before editing through Home. Existing recipes are never rewritten.

You can also edit this file directly to your public author identity/contact and intended license. One installation shares these defaults across all profiles; switching profiles does not change authorship. Do not store passwords/tokens or credential-bearing contact URLs here. The file must be regular, not a symlink; invalid schemas or reserved names fail with safe errors. A missing file returns Unknown defaults and creates nothing. Home explains that these defaults apply to newly authored recipes, alongside product version/download time. Unset fields display **Not configured — click to set** while file/API placeholders remain `Unknown`; invalid files show the unconfigured display with an explicit unavailable/error-type notice, never silently overwrite the file.

Before writing a new user recipe, the agent reads the defaults with `python -B tools/recipe_identity.py defaults` (JSON) or `recipe_identity.defaults()`. Copy the returned author/license fields into the new descriptor, keeping contacts as a list. The Python function returns a fresh copy. Defaults are a starting point, not an immutable identity: a user can choose different non-reserved attribution per recipe. Editing defaults never changes existing recipes. No automatic recipe-create CLI is implemented; this is the callable data interface and agent authoring workflow. Unknown license means unspecified permission, not permission to publish; resolve it before authorized sharing.

## Reserved Bundle attribution

The product's built-in `system/network/check/port`, `system/inventory/overview` and `feast/report/execution-summary` recipes declare exactly:

```yaml
author: {name: Bundle, contacts: [Bundle]}
license: MIT
```

Each includes its MIT LICENSE text. The validator recognizes these product directories from the owning checkout's recipe root and explicit built-in allowlist. Recipes outside those locations cannot claim Bundle in either name or any contact. Installation defaults also reject this reserved value. Comparison trims surrounding whitespace and ignores case. Source/profile shorthand does not grant Bundle identity; a same-named recipe copied outside the owning product paths is external and must use truthful non-reserved attribution. Preserve original license/copyright/attribution when preparing a reviewed derivative; do not automatically rewrite someone else's authorship to make an import pass.

This is product policy, not cryptographic publisher authentication or a sandbox. A local owner who can edit the checkout/validator can change the policy. No identity can be authenticated merely because its descriptor contains an author string; source review and actual execution authorization remain necessary.

## Packaging and external import

`recipes pack` includes author/license in MANIFEST.json and checks them against the descriptor actually being packed. A descriptor changed since catalog inspection fails before output creation. MIT recipes must explicitly include LICENSE in their file allowlist; filenames do not verify a license's correctness or ownership. Other declared/custom licenses need their own reviewed license files and obligations. The bundle format remains 0.1.0 with additive author metadata.

`recipes unpack` is the current external review-candidate import surface, not an installer. It validates the descriptor with the duplicate-key-rejecting loader and rejects reserved Bundle author/contacts before creating the destination. A manifest author/license mismatch is also rejected. File inventory/digest/path/size checks still apply; rejection leaves no candidate directory. Unknown attribution is accepted as explicit missing evidence, not verified authorship or permission. Complete review before registration/execution/publication.

Packing a built-in recipe for inspection is possible, but its Bundle archive cannot be unpacked through the external import path. Obtain built-ins through the OpsFeast product checkout. There is no bypass/force-import option, automatic installation or future Exchange importer implemented. All future acquisition paths must use the same reserved-attribution validation before activation; registering an external clone does not bypass descriptor/runtime validation.

Public tests cover keyboard/mouse editing, cancellation, atomic save failures, invalid-file/symlink preservation, defaults and copy preservation, case/whitespace reservation, author/contact types, all built-in identities/LICENSE files, required MIT packaging, rejected Bundle archives before extraction, ordinary candidate imports and manifest spoofing. Synthetic user-copy fixtures explicitly use synthetic authors rather than pretending to be Bundle. No real download, third-party execution or publication is performed.

_Last modified: 2026-10-20 11:24:28_
