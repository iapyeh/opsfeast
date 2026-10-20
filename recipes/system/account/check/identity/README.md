# Observe the connection account

## Declared retention and bundled content

In a namespace-enabled profile this read recipe retains declared safe scalar result fields through host-values 0.2.0 with dataset/field semantics. The separate bundled vault author can render a per-host state page. Failed/mock results are excluded; missing values remain unavailable. Read [vault setup and output rules](../../../../../docs/host-vault.md). Profiles without namespace retain raw-only behavior. Read [retention query/content interfaces](../../../../../docs/retention.md); Markdown templates are not part of the recipe contract.

This minimal Core example uses descriptor 0.3.0 and python-recipe 0.1.0. The runner supplies a per-execution Recipe; the entrypoint uses its scoped session and returns the existing common result fields. It never reloads credentials, opens another connection or closes the runner's transport.

## Prerequisites and invocation

Use Python 3.11+, PyYAML 6.0.3, matching SSHScript import/distribution 5.0.0 and a configured enabled host with POSIX id. Within authorized connection/command scope, from the trusted checkout:

```sh
python -B tools/opsfeast.py inspect-recipe system/account/check/identity --json
python -B tools/opsfeast.py recipes run system/account/check/identity --profile main --host host-01
```

Inspection is static and connection-free. Execution connects and runs id -un, with the runner timeout as the default command budget. No sudo/su or platform initialization is requested by this recipe. Runner stores raw JSON under observations; inventory retention is not used; namespace-enabled profiles save the declared scalar dataset.

## Results and failure behavior

Success data.account is the observed nonempty single-line account name, not proof of sudo ability, host health or trusted installation identity. Command/transport errors fail execution. Truncated or invalid output returns failed with output_truncated or invalid_identity_output. Connection cleanup failure overrides claimed success. Read raw status/reason_code and cleanup evidence separately.

## Implementation choice and extension

[main.py](main.py) uses SSHScript 5.0.0 through the Core facade for one argv command. Core supplies connection planning/lifecycle and a default finite command budget. This fits the existing execution foundation without another backend. See [Core API](../../../../../docs/core-api.md), [recipes skill](../../../../../skills/opsfeast-recipes/SKILL.md), and [public tests](../../../../../tests/test_core_delivery.py). For privileged recipes use explicit Recipe sudo/su scopes and document authorized accounts/effects; do not simply run sudo inside a command string.

Synthetic runner/result tests and a temporary local credential-free execution are validation evidence. Remote SSH and native su/sudo are unverified; listed platforms are declared applicability, not all-platform execution evidence. Attribution is Bundle, MIT; include LICENSE when packaging.

_Last modified: 2026-10-20 11:22:14_
