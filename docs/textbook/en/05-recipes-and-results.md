# 5. Discover and execute recipes

[Book home](README.md) · Previous: [Hosts](04-hosts-and-access.md) · Next: [Inventory](06-inventory.md)

A recipe is reusable operational knowledge with declared inputs, an implementation and an output contract. Before execution, learn what it does, where it comes from, which platforms it declares and which evidence actually supports that declaration.

## Discover before writing or running

These commands inspect metadata without executing recipe candidates:

```sh
python -B tools/opsfeast.py recipes list --checkout-only --json
python -B tools/opsfeast.py recipes list --profile main --json
python -B tools/opsfeast.py recipes show system/inventory/overview --profile main --json
python -B tools/opsfeast.py inspect-recipe system/inventory/overview --platform linux --platform freebsd --json
```

Checkout-only discovery works before profile setup. Profile discovery includes its accessible sources. Declared support and a syntactically valid entrypoint do not prove native target applicability, dependencies or safe behavior. Read the selected recipe's README, implementation and verification limits before authorized execution.

## Use precise source references

| Reference form | Source |
| --- | --- |
| `system/inventory/overview` or `bundle:system/inventory/overview` | Bundled checkout recipe |
| `:backup/files/check/daily-backups` | Selected profile's `recipes/` tree |
| `team:database/mysql/check/replication` | An explicitly registered external source named team |

A descriptor ID is useful metadata, but equal IDs can exist at different paths or sources. Prefer exact references for configuration, jobs and consumer subscriptions. Registered source roots must be declared through the entry `hosts.yaml`; an acquired recipe cannot widen allowed roots by declaring its own registration.

## Understand selection and inputs

`default`, group and host recipe mappings use exact references. Settings merge by leaf, host settings win, lists replace, and first resolved group precedence matters where group leaves overlap. `enabled`, `vars` and supported `execution` policy are distinct controls. CLI inputs are typed through descriptor declarations; they do not override account policy.

Bulk/group execution requires enabled host, source and recipe. Recipes default disabled; new init explicitly enables bundled inventory. An explicit recipe `--host` overrides those three enabled gates for that target. Disabled jump hosts and invalid inputs or paths still fail. Therefore, do not use explicit `--host` as a test of whether bulk policy is enabled.

Before running, the agent should explain the exact selection, connection/privilege policy, operations, required dependencies, variable meanings and persistence/delivery effects. Do not pass secrets in `--var`; use private supported configuration.

For an authorized inventory example:

```sh
python -B tools/opsfeast.py recipes run system/inventory/overview --profile main --host server-01 --json
```

This connects, collects with inventory's documented actor policy, saves operational evidence and attempts retention plus enabled downstream processing. It is not an inspection command. For narrow properties or jobs, use [chapter 6](06-inventory.md).

## Read completion as evidence

Fixed execution states are `success`, `partial`, `failed`, `skipped` and `unsupported`. A recipe may additionally provide a label, severity and summary describing its findings. `PASS` describes successful execution; it is not a universal health verdict. A backup scanner can succeed while reporting cleanup findings, and an offline report can succeed while describing failed operations.

Read command outcome, per-target status, actual identity/restoration, retention and `content_update` separately. A custom assessment cannot hide platform failures. Severity alone does not change exit code or create a notification. Exit behavior is command-specific: operational non-success or downstream failures can yield nonzero; successfully reading a failed historical result normally yields zero.

Terminal summaries favor readability. Agents should request `--json` where supported instead of parsing wrapped tables. Preserve reason codes and unknown states rather than inferring missing data from display omissions.

## Revisit a batch or one host result

These reads use existing data and do not reconnect or retry:

```sh
python -B tools/opsfeast.py observation --profile main --json
python -B tools/opsfeast.py observation latest --status failed partial --profile main --json
python -B tools/opsfeast.py observation result --host server-01 --profile main --json
python -B tools/opsfeast.py observation result RESULT_ID --profile main --json
python -B tools/opsfeast.py observation result RESULT_ID --detail --profile main --json
python -B tools/opsfeast.py observation result RESULT_ID --raw --profile main
```

Use returned IDs from the original root. `observation` browses explicit batch membership and effective outcome; `observation result` browses host results and defaults to focused diagnosis when an ID is selected. `--detail` exposes complete structured detail, while `--raw` returns original JSON. A failed connection can be recorded in the batch without a usable raw host result. Old nearby files are not reconstructed into a batch.

Short IDs shown in local views are convenient selectors. Keep full returned result IDs for durable automation and disambiguate within the same root. Offline report history uses `recipes results`; host history uses `observation result`.

Agent prompt:

> Inspect the latest failed or partial batch in profile main without executing anything. Separate collection, identity/restoration, retention and content failures. Use saved host result IDs for focused diagnosis, and propose the smallest recovery for each failing stage.

**Checkpoint:** Given a result label and exit code, explain what they establish and what still requires per-target evidence. Find both the batch ID and a saved host result ID without another host connection.

Canonical guidance: [recipe skill](../../../skills/opsfeast-recipes/SKILL.md), [sources and policy](../../recipe-sources.md), [execution](../../recipe-execution.md), [results and accounts](../../recipe-results-and-accounts.md), and [CLI](../../cli.md).

*Last modified: 2026-10-26 12:55:26*
