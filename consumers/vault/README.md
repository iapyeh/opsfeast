# Vault retention consumer

This bundled consumer implements [consumer contract 0.1.0](../../docs/retention-consumers.md). Its source is `builtin:vault`, ID `vault`, with default activation. It subscribes to observation creation/deletion and operation creation across recipe sources. It delegates current-state Markdown generation to `host_vault.rebuild`; `vault_content.build/render_observation` supplies the renderer. This separation lets explicit `vault rebuild` use the same application without manufacturing or acknowledging events.

Requirements: Python 3.11+, OpsFeast initialization dependencies, a namespace-enabled profile with valid hosts.yaml, writable local Vault output and retention read access. No network, SSHScript execution, model or Obsidian plugin is required. It consumes the installed public retention envelopes, including registered inventory-observations 0.1.0, host-values 0.2.0 and operation journals. Preserve partial/unknown values and identity evidence when extending presentation.

The consumer rebuilds all current retained views on each event. Its writes replace owned Markdown outputs, remove stale owned pages and preserve unmanaged human notes. Repeated events safely rebuild current state through the existing ownership publisher. See [Vault paths, collision policy and verification limits](../../docs/host-vault.md). Publication is atomic per file, not across the whole Vault.

Disable automatic delivery with `consumers: {vault: {source: builtin:vault, enabled: false}}` or `vault: {auto_refresh: false}` in feast.yaml. Other consumers remain independent. Initialize/rebuild output with `python -B tools/opsfeast.py vault rebuild --profile main --json`; inspect/retry events with `consumers inspect` and `consumers dispatch vault`. Rendering or ownership failures leave retention committed and a retryable delivery receipt. Enabling after a disabled period processes matching journal backlog.

To add another content application, declare a separate consumer and source, use its own output location/ownership and enable it explicitly. Do not add per-application branches to runner or retention storage. Synthetic tests verify dispatch integration, replay, ownership and repeated output; no external hosting or native access evidence is implied.

_Last modified: 2026-10-19 14:55:28_
