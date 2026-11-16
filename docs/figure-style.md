# Figure style for textbooks and Vault content

Apply this project convention when adding or revising figures in the OpsFeast textbook or consumer-generated operational Vault pages. It records the approved layout so another author or agent can reproduce it without conversation history. It does not constrain unrelated presentation tools or override a user's explicit design choice.

## Textbook illustration timing

Review and settle the chapter content first. Generate a new textbook figure only when the owner then requests illustration; do not create figures or impose a per-chapter figure count during prose review. Keep existing requested figures, and avoid spending time redesigning drafts before the content is confirmed. The visual rules below apply when figure work is requested. This timing preference concerns textbook review, not unrelated consumer development or its verification.

## Shared visual rules

- **Use Mermaid for these diagrams.** Keep editable text definitions with the document or reusable consumer renderer. Obsidian needs no Diagrammo community plugin. Retain explanatory text and data tables so unsupported diagram rendering does not hide the meaning or evidence.
- **Give the whole figure a visible outer border.** Use a thin, neutral, preferably rounded frame with a transparent background that works in light and dark reading themes. A flowchart can use a surrounding subgraph with a blank label. Other diagram types need a suitable presentation wrapper/style; do not insert XY-chart syntax into a flowchart subgraph merely to obtain a frame.
- **Fit the prose column.** The figure must not exceed the surrounding text width or require horizontal scrolling in normal reading. Preserve its aspect ratio. Shorten labels, reduce unnecessary edge labels/loops, arrange compactly or split a complex figure before shrinking text to an unreadable size. Do not widen the prose column to accommodate a diagram.
- **Put a caption outside the border.** Prefer immediately above it; below is acceptable when the layout calls for it. Use `附圖：` in Traditional Chinese and `Figure:` in English, followed by a descriptive title. Do not repeat the caption inside the frame or crowd the first diagram node.
- **Align the caption with the actual border.** Use left alignment and account for the SVG's own inset, rather than aligning blindly with the paragraph edge. In the approved overview, an 8px caption inset aligns with the border; this is a starting value, not a universal offset for every renderer or scale.
- **Keep the caption attached to its figure.** Leave only a small gap between caption and border, about 8–12px in the reference reading layout. Preserve a larger gap before the caption and after the figure, around 2rem, so it is separate from adjacent prose. Avoid default paragraph margins that make the caption look like unrelated text.

## Reuse the working reference

The [Chinese overview](textbook/zh-TW/01-overview.md) is the approved example. Its caption is a separate HTML paragraph with the `opsfeast-figure-caption` class and a bold title. The Mermaid subgraph supplies the frame with a blank label; a nonempty subgraph title would put the title back inside the border.

Reuse the canonical [reader style](../templates/vault/opsfeast-mermaid-fit.css), also supplied as [mermaid-fit.css](textbook/zh-TW/mermaid-fit.css) for textbook readers, for width fitting, caption alignment and spacing where the reader supports that stylesheet. The [installation chapter](textbook/zh-TW/02-installation.md) explains Obsidian snippet use. The overview also keeps its two essential caption adjustments inline (zero bottom margin and 8px left inset) for readers that have not refreshed the stylesheet. Adapt the inset when the actual SVG geometry changes.

For other Markdown readers, preserve the same visible outcome using supported rendering and styling. [Full bundled Vault publication](host-vault.md#automatic-obsidian-reader-setup) installs the owned style and enables it on first adoption, preserving later reader disabling. User-created/textbook Vaults still need their agent to configure the supplied style. Do not assume that a running reader has loaded written settings. Keep reader-local `.obsidian/` preferences and workspace files out of public source/package delivery; ship reusable assets and instructions separately.

## Apply to consumer output

Make layout changes in the reusable consumer renderer/template and its owned presentation assets, not by hand-editing generated pages. Follow [Vault ownership and regeneration](host-vault.md#directory-and-ownership). Keep captions and labels literal/escaped when built from operational data. Preserve units, zero/unknown/partial states, source times and table/report links; styling must not change retained evidence or suggest unverified topology or health.

This is the design requirement for future textbook and consumer-Vault figure work. The existing overview demonstrates the complete layout; the current bundled consumer's Mermaid output does not yet implement all of its frame/caption/spacing rules. The separate reader-setup implementation configures the shared stylesheet; it does not retrofit absent frames/captions in existing generated diagram definitions. When adapting a consumer, deliver and verify the needed renderer/assets, document how they become active, and preserve human notes and unrelated reader settings. Do not recollect hosts to restyle existing evidence.

## Visual verification

Render the actual output, check both a normal and narrow prose column (700px and 400px are useful fixtures), and inspect border/title separation, left alignment, readable labels, aspect ratio and absence of horizontal overflow. Test representative special labels when changing a renderer. Prefer a native Obsidian check for Obsidian-facing changes; identify standalone rendering separately when native verification is unavailable. Verify that the intended stylesheet is actually active rather than inferring it from a settings file. Keep those verification records outside reader-facing chapter prose.

*Last modified: 2026-10-26 19:45:56*
