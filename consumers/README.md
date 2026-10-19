# Retention consumers

Consumers react to retained-data changes independently of collection recipes. Start with the [consumer contract, activation and recovery guide](../docs/retention-consumers.md).

- [vault](vault/README.md): the default bundled local Markdown content consumer, using public retention read interfaces and Vault ownership rules.

User consumers live in `<profile-root>/consumers/NAME/` and require explicit `feast.yaml` registration. List dependencies with `opsfeast.py consumers list --recipe inventory/system --profile NAME --json` or `recipes show inventory/system`. Discovery does not execute code.

_Last modified: 2026-10-19 14:55:28_
