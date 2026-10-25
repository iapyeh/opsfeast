# Service adapters 0.1.0

Read [platform objects and lifecycle](services.md) first. Multiple presentation adapters and multiple delivery channels may be enabled. There is no lifecycle adapter: only platform APIs mutate notification/todo state with revision checks.

## Configuration and bundled adapters

Merge into the selected profile's `feast.yaml`; do not replace its identity, namespace, Vault or consumer settings. The [configuration schema](../schemas/services.schema.json) defines the `services` mapping, and [object schema](../schemas/service-object.schema.json) defines versioned objects.

```yaml
services:
  presentations:
    vault:
      source: builtin:vault
      enabled: true
  deliveries:
    mail:
      source: builtin:smtp
      enabled: true
      retry:
        max_attempts: 5
        delay_seconds: 60
      config:
        host: smtp.example.invalid
        port: 587
        security: starttls
        sender: ops@example.invalid
        recipients: [operator@example.invalid]
        username: ops
        password_env: OPSFEAST_SMTP_PASSWORD
        timeout: 15
  routes:
    - minimum_severity: error
      channels: [mail]
```

This synthetic configuration is not a working relay. Mail requires an authorized destination and the named environment variable in the actual dispatcher process. It is never inferred from host-account email metadata. `services inspect` validates configuration/source availability without contacting the relay; it cannot verify environment secrets or delivery. No mail is configured by default.

Adapter IDs start with a lowercase letter and contain lowercase letters, digits, underscores or hyphens, maximum 63 characters. `source` and Boolean `enabled` are required; `config` defaults to `{}`. Routes name configured enabled delivery channels and use severity thresholds `info`, `warning`, `error`, `critical`. A notification/channel pair has one stable outbox identity. A later reconciliation can queue a persistent active notification after a route is added; configuration editing alone does not generate incidents or reminders.

`builtin:vault` accepts no nonempty config and requires the Vault destination. It is enabled by default when presentations are omitted; `presentations: {}` selects none. `vault.auto_refresh: false` suppresses this automatic service presentation too. `builtin:smtp` accepts only host, port, security, sender, recipients, username, password_env and timeout. Sender and a nonempty recipient list are required when enabled. Security is `starttls` (default, port 587), `tls` (port 465) or `plain`; TLS uses normal certificate verification. Authentication requires TLS and an environment-variable secret, never a literal password in this mapping. Timeout defaults to 15 seconds, at most 120. Retry defaults to max_attempts 5 (range 1–100), delay_seconds 60 (0–86400).

Missing secrets or known pre-submission failures produce failed receipts. Uncertain submission or partial recipient rejection produces unknown, requiring an explicit decision before retry. Receipts persist safe reason codes/types rather than arbitrary provider exception text or credentials. Header fields are sanitized. These checks do not replace destination review or authorization to send.

## Reviewed local modules

Keep user modules under `<profile-root>/service-adapters/`. Configure a `local:service-adapters/NAME.py` source with its reviewed lowercase SHA256 digest. Relative paths must remain inside the profile and cannot traverse symlinks. Inspect/discovery checks source bytes and digest without importing; dispatch compiles the same reviewed bytes and requires `API_VERSION = "0.1.0"`. Source changes require review and a matching updated digest. Digests pin the entrypoint only; imported dependencies remain trusted Python code. No download, automatic installation, code sandbox, custom timeout or resource quota is implemented.

Compute the digest with the selected Python, for example:

```python
import hashlib
from pathlib import Path
print(hashlib.sha256(Path("/path/to/profile/service-adapters/dashboard.py").read_bytes()).hexdigest())
```

Presentation interface:

```python
import html
API_VERSION = "0.1.0"

def render(snapshot, config):
    rows = "".join("<li>" + html.escape(obj["title"]) + "</li>"
                   for obj in snapshot["objects"])
    return {"index.html": "<!doctype html><meta charset=utf-8><ul>" + rows + "</ul>"}
```

`render(snapshot, config)` receives copies of the coherent service snapshot and adapter configuration and returns a mapping of safe relative paths to UTF-8 text. Snapshot contains `objects`, `history`, `deliveries` and `contract_version` plus `generated_at`; inspect the source/schema rather than inventing fields. Escape values for the chosen output format. This is a pure presentation interface; never mutate authoritative objects from a renderer.

```yaml
services:
  presentations:
    vault:
      source: builtin:vault
      enabled: true
    dashboard:
      source: local:service-adapters/dashboard.py
      sha256: REPLACE_WITH_REVIEWED_64_CHARACTER_SHA256
      enabled: true
      destination: files
      config: {}
```

`destination: files` writes owned text files into `services/presentations/dashboard/` with an ownership manifest; it supports HTML, JSON and other text. The default destination `vault` uses the protected Vault publisher with owner `service-<adapter-id>` and Markdown paths. Each adapter has independent output receipts; unmanaged files, path escapes and conflicting ownership fail instead of being overwritten. Both adapters may run together. The placeholder digest intentionally requires replacement before configuration is usable.

Delivery interface:

```python
API_VERSION = "0.1.0"

def deliver(notification, config, delivery_id):
    # Submit to the user's reviewed provider using delivery_id as an idempotency key.
    # This illustrative provider is intentionally not implemented.
    return {"status": "failed"}
```

`deliver(notification, config, delivery_id)` returns a mapping with status `delivered`, `failed` or `unknown`. Report unknown when submission might have succeeded. The platform owns outbox claim/retry/receipts and does not trust adapter messages as lifecycle updates; arbitrary receipt fields are not persisted. An adapter must implement its provider, validate its private settings and document dependencies, destination, credentials, external effects and verification evidence. Provider calls run outside SQLite transactions; dispatch is serialized per profile. An exception can mean unknown delivery, so do not claim an exception proves that nothing was sent.

*Last modified: 2026-10-25 14:06:31*
