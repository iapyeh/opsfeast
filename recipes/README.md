# Recipes

This directory will contain reusable SSHScript tools for host inventory, state collection, inspection, maintenance, and repair.

Each recipe should document its purpose, supported and tested platforms, SSHScript compatibility, dependencies, required permissions, inputs, outputs, side effects, and verification method.

Collection recipes should retain observation sources and timestamps and distinguish success, permission denial, unsupported operations, timeouts, and parsing failures.

[inventory-system](inventory/system/README.md) now provides Linux system collection and a minimal runner. Linux collection is covered by synthetic tests; real Linux/SSH validation remains pending.

The first result contract and synthetic example live with that recipe. The runner currently supports only the exact inventory-system bundle, not arbitrary recipe execution.
