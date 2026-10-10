# Tests

This directory will contain public, reproducible verification for recipes, data contracts, and operational workflows.

Verification should cover result parsing, failure status, supported platforms, and repeated updates that preserve human notes. Tests and fixtures must use synthetic data rather than private host details or credentials.

## Configuration utility tests

With Python 3.11+ and PyYAML installed, run:

```sh
python -m unittest discover -s tests -p 'test_*.py'
```

`test_my_ops.py` checks connection-test credential/key/jump mapping, fixed commands, failure reporting and cleanup with mocked Sessions, per-hop diagnostics, credential omission and frames-only tracebacks, JSON dumps of merged and nested settings, dump error handling, initialization preservation, cross-file references, duplicate definitions, include and jump-host cycles, recipe selection, and path boundaries using temporary directories and synthetic values. The default tests do not contact hosts; real connection tests are invoked separately with `test-connection`.

## Inventory and runner tests

`test_inventory_system.py` covers Linux synthetic outputs, safe os-release parsing, missing-file fallback, permission denial, unsupported platforms, command and transport failures, timeout partial output, strict cleanup, recipe selection and bundle matching, output symlink rejection and repeated result preservation. These tests never contact SSH targets. The actual macOS unsupported-platform path and SSHScript 5.0.0 credential-free quickstart were checked locally; full Linux and SSH collection remain unverified.

CLI recipe selection tests cover `--recipe` precedence, absent/empty host selections, invalid host selections bypassed by a valid override, management-root relative paths with includes, absolute paths, invalid overrides without fallback, recipe/descriptor symlink escapes, and CLI argument forwarding.
