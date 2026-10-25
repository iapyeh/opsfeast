# Check MySQL and MariaDB replication

`database/mysql/check/replication` (ID `mysql-replication`, version 0.1.0) checks all channels of explicitly configured database instances through the runner-provided Core Recipe. SSHScript supplies exact argv/stdin, finite command budgets and SSH/jump/session ownership. The recipe uses target-side mysql/mariadb clients in batch XML mode; no persistent Console or database Python driver is required. It never repairs replication or changes database data/settings.

## Configure and execute

Read the [recipe settings contract](../../../../../docs/recipe-sources.md), [execution guide](../../../../../docs/recipe-execution.md) and [synthetic hosts.yaml](examples/hosts.yaml). Use the actual selected profile; do not initialize or migrate an existing profile. Connection/SSH account settings remain ordinary OpsFeast settings. Database credentials are independent of SSH credentials.

```yaml
hosts:
  replica-example:
    # Existing SSH connection, users and group settings remain here.
    recipes:
      database/mysql/check/replication:
        vars:
          instances:
            main:
              transport: socket
              user: replication_monitor
              password: "REPLACE_IN_PRIVATE_CONFIGURATION"
              expected_source: source.example.invalid
          max_delay_seconds: 60
          command_timeout_seconds: 20
```

Within authorized host and database read scope:

```sh
python -B tools/opsfeast.py recipes show database/mysql/check/replication --profile NAME --json
python -B tools/opsfeast.py recipes run database/mysql/check/replication --profile NAME --host HOST --json
python -B tools/opsfeast.py recipes run database/mysql/check/replication --profile NAME --host HOST --var max_delay_seconds=0 --json
python -B tools/opsfeast.py retention list --profile NAME --recipe database/mysql/check/replication --host HOST --json
```

Default/group/host exact-reference recipe vars merge using existing rules; invocation vars override without rewriting YAML. Source-qualified references differ for profile (`:database/mysql/check/replication`) and registered shared recipes. Explicit host selection does not require bulk opt-in; group/all execution requires enabled host/source/recipe. This recipe defaults disabled and adds no schedule.

## Inputs and requirements

Controller: Python 3.11+, normal OpsFeast dependencies, SSHScript 7.0.0 and registered mysql-replication retention 0.1.0. Target: python3 plus mysql or mariadb client on PATH, or an explicit absolute client path. Server support is MySQL 5.7+ and MariaDB 10.2+; a declared version range is not a native test matrix. Required database permissions include REPLICATION CLIENT on MySQL or the applicable MariaDB replication-monitoring privilege; provision the least privileges separately. This recipe grants no privileges and never escalates OS accounts.

`instances` is a required mapping of 1–32 named instances. Each name is 1–63 letters, digits, underscores or hyphens. All configuration is validated before executing the first remote helper. Instance options:

| Option | Meaning |
| --- | --- |
| client | auto (mysql then mariadb on PATH), mysql, mariadb, or absolute executable path |
| transport | socket by default, or tcp; always passed explicitly to the client |
| socket | Optional absolute Unix socket path; absent uses the client socket default |
| host / port | TCP requires an explicit host; port defaults to 3306. These options are invalid with socket transport |
| user / password | Both explicitly required unless option_file is selected. Empty password is intentional; missing is failure |
| option_file | Absolute existing client option file, mutually exclusive with user/password. It must be a nonsymlink regular file owned by the SSH effective user with no group/other permissions. It is never changed or removed |
| tls | TCP-only `{ca: /absolute/ca.pem}`; uses product-specific client certificate/hostname verification flags. Never silently downgrades TLS |
| expected_source | Optional exact comparison with the replica-reported source hostname; not a DNS, host-ID or UUID equivalence assertion |
| expected_sources | Optional mapping from channel name to exact expected source; overrides expected_source for those channels. Empty string names the default channel. Missing explicitly expected channels are unhealthy |

Top-level `max_delay_seconds` defaults 60, accepts finite nonnegative values; zero requires reported zero delay. `command_timeout_seconds` defaults 20 (1–120), capped by the runner timeout per instance. Instances execute sequentially; the total may be the sum of their budgets. A small additional SSH command budget allows normal helper cleanup, not guaranteed cleanup after transport loss or process death. No automatic account/credential/transport/query retry occurs. Newline/control characters in configuration strings are rejected; quote/backslash characters in passwords are encoded as option-file values.

## Fixed operations and transparency

The remote call is `recipe.session.exec_command(["python3", "-c", <bundled probe.py source>], input=<JSON instance settings>, check=False, command_timeout=...)`. Review [main.py](main.py) and [probe.py](probe.py); payload credentials travel as SSH stdin, never argv, an environment variable, SQL or source text.

For inline credentials the helper creates a mode-0600 temporary file, writes only `[client]` user/password options, runs clients and unlinks the file in finally. A secure file is still a temporary remote write, and credentials necessarily enter authorized process memory. Existing option files remain caller-owned. Cleanup failure or lost transport is unknown, never restored success. Unexpected client errors are not treated as alternative-credential opportunities.

The helper executes an identity SELECT for version/version_comment/hostname/server_id/CURRENT_USER(), then exactly one version-specific status statement: MySQL 8.0.22+ SHOW REPLICA STATUS; earlier supported MySQL SHOW SLAVE STATUS; MariaDB SHOW ALL SLAVES STATUS. TLS selection additionally calls client --no-defaults --version locally on the selected target, without a database connection. SQL is fixed; no configurable statements or shell fragments are accepted.

Each instance result includes safe client argv (option-file path masked), exact SQL/input description, exit code, allowlisted parsed stdout, error category, observation time and cleanup state. Arbitrary stderr and Last_IO_Error/Last_SQL_Error text are omitted because they can contain credentials, SQL or row values; error codes and redaction markers remain. Evidence is explicitly sanitized, not a complete raw client-output transcript. Configured passwords are scrubbed from final results. Never print effective vars or dump input payloads. A process killed outside the helper can leave its temporary file; unknown cleanup must not be described as confirmed.

## Interpretation and retention

For each channel preserve source, I/O/SQL states, reported delay, configured SQL delay, error codes, filtering, file/position coordinates and product-specific GTID fields. Missing values stay null. All threads must be Yes, error-free, within the delay policy and match any expected source for healthy. Stopped/connecting threads, errors, exceeded lag and source mismatch are unhealthy; insufficient status is unknown. Empty status is not_configured, distinct from healthy. Configured intentional SQL delay is recorded; adjust the explicit lag policy rather than automatically subtracting it.

Recipe success means all instances are healthy with confirmed cleanup. Collected unhealthy/unknown/not_configured or mixed-instance results are partial, remain retainable and make the CLI nonzero. If no instance identity could be collected, execution fails with raw evidence only. Never turn a permission/query/parse/cleanup error into healthy or zero lag. The status contract does not prove row equality, source catch-up or successful future writes.

`expected_source` never connects to that source. Source-side binlog/GTID correlation is not implemented here and requires its own bounded collection design, configuration and authorization. Zero Seconds_Behind_Source and equal read/execute positions only describe replica-side observations; no position arithmetic across rotated files is performed. PostgreSQL is outside this recipe and belongs in a separate product recipe.

The recipe owns [mysql-replication 0.1.0 schema](retention.schema.json) and [reviewed normalizer](retention.py). Retained data includes per-instance identity/time, channels, saved lag policy/findings, sanitized probe evidence and explicit source_verification=not_performed. No secret inputs or rendered Markdown are retained. Normalization is registered platform code, not a dynamically imported candidate module. [Retention/replay](../../../../../docs/retention.md) keeps digest-bound provenance; schema or normalizer drift is explicit.

Authoritative history lives under profile-root/retention/hosts/HOST/YEAR/observations.sqlite3. The existing builtin:vault consumer renders a MySQL replication current page and full historical report under profile-root/vault/hosts/GROUP/HOST/. Current pages show every instance/channel, lag and health; full reports include positions, GTIDs, filters and sanitized query evidence. Rebuild preserves saved findings and does not query hosts. Raw collection, retention and consumer receipts remain independent. Existing namespace/Vault activation rules apply; this recipe does not initialize profiles or enable consumers.

## Routine handoff

After authorized instance settings are saved in the actual host-definition YAML, routine execution needs only the recipe/profile/host invocation above; no password argument or temporary vars file is needed. Agent authors should apply already-authorized private settings from exploration, preserving includes and unrelated content, and give the actual installation-specific copy/paste command. Human TTY completion prints existing raw JSON and a readable Vault current/host entrypoint on successful delivery. --json/pipe output remains unchanged. If publication fails or is disabled, inspect the raw result and separate receipt; an old Vault page is not proof of this run.

## Verification

[Public tests](../../../../../tests/test_mysql_replication.py) cover both dialects, channel lists, version selection, lag/source/empty/unknown/error cases, option-file permissions and cleanup failure, secret redaction, configuration inheritance, repeated retention and Vault rendering with synthetic local fixtures. Historical SSHScript 6.1.0 native Linux SSH execution against MySQL 8.0.46 passed fixed queries, root database authentication, protected-file cleanup, retention and enabled Vault delivery on 2026-10-24. That real-host result has not been repeated on the pinned 7.0.0 source. The 7.0.0 migration is covered by native local/synthetic fixtures only; native MariaDB/TLS and least-privilege account behavior remain unverified. Interactive exploration of one MySQL host is separate from execution of this packaged recipe. See the [exploration workflow](../../../../../skills/opsfeast-recipes/references/exploration-to-recipe.md).

## Completion account identity

The collection identity column displays each instance's server-reported
CURRENT_USER() as `DB: monitor@localhost` for one instance, or
`DB main: monitor@localhost` with the vars.instances key for multiple instances, plus an observed OS actor or
explicit `SSH: operator` login fallback. This uses already collected evidence;
it does not infer the database grant account from configured user, assume an OS
UID, or reconnect. Multiple instances keep independent accounts and unknowns.
Read-only observation batch views show the same identities from saved raw results.
Retention data/schema and existing observations need no rewrite for this display.

## Prominent health status in Vault

Current pages put an overall status and instance counts before Contents. HEALTHY,
UNHEALTHY, UNKNOWN and NOT CONFIGURED have distinct symbols/text and native
Obsidian callout colors; failures do not depend on spotting a lowercase table cell.
Each instance and channel has its own status, clear failure explanations and a
narrow two-column detail table. Observed zero delay is preserved; unavailable delay
is Not reported. Original reason codes and full sanitized historical evidence remain.

The renderer summarizes retained findings rather than rerunning SQL or changing
lag/source policies. Partial/unknown cleanup cannot produce a healthy overall
banner. Existing views can be regenerated with authorized vault rebuild; no new
recipe run, data migration, reader CSS/plugin or global font change is required.

Replication completion and observation tables use recorded health findings rather
than PASS. See [health labels and failure semantics](../../../../../docs/cli.md#replication-completion-health). Preserve the collection status, exit code and
retention/content failure evidence; UNKNOWN is not healthy.

*Last modified: 2026-10-25 06:27:41*
