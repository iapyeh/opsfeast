# Connect your first host

Console summaries use tables when stdout is a terminal; add `--json` to supported inspection/diagnostic/check/profile commands for structured output. Non-TTY formats, execution scope and stored data remain unchanged. See [the command-specific console policy](cli.md#terminal-tables-and-json).

Start with one host and one successful connection. You do not need recipes, groups, su or sudo for this step. This guide provides small examples first; the [hosts.yaml reference](hosts-yaml.md) defines the complete configuration contract.

## 1. A minimal remote host

After [initial setup](first-use.md), open the reported hosts.yaml (normally `feasts/main/hosts.yaml`). For a new, disposable setup, this is a complete minimal file using your existing SSH agent/default keys:

```yaml
hosts:
  server-01:
    connection:
      hostname: server.example
      user: operator
```

Replace `server.example` with your server's DNS name or IP and `operator` with its SSH login account. `server-01` is your own stable host ID; commands use this ID, not the address. Use spaces for YAML indentation. This example assumes your existing key/agent authentication is already available; it does not create keys or configure the server. For password login, use the next example instead.

For an existing management environment, add or update only the intended host in its defining file; preserve localhost, other hosts, includes and human comments. Do not replace an existing file wholesale or add a duplicate host ID. The initial `host-01` / `host.example` is synthetic and not ready to connect: replace it or remove that example from a new setup. Do not select all hosts for a first test.

For password login, use this complete alternative:

```yaml
hosts:
  server-01:
    connection:
      hostname: server.example
      user: operator
    users:
      operator:
        password: "REPLACE_LOCALLY_WITH_LOGIN_PASSWORD"
```

Fill the password locally in your private management file, never in chat. The placeholder is not a usable credential. Passwords are stored as plaintext in the current format; keep this file private and out of public Git. With a password and no identity_file, the connection test disables agent/default-key lookup. Do not use `dump` to share settings: it can print passwords.

## 2. Check settings, then test the connection

Commands below assume an initialized `main` profile and the checkout's `.venv`. Replace the quoted path once with your actual clone path; use your selected interpreter/profile if different. Run each step separately and stop when it fails.

```sh
cd "/absolute/path/to/opsfeast"
.venv/bin/python -B tools/opsfeast.py check --profile main
```

Exit zero means configuration validation passed; it does not prove the host is reachable or credentials work. Errors identify the source/field to correct.

You can also use the interactive Home. With Textual installed in the selected checkout environment, a Bash/Zsh terminal can run `source tools/activate.sh`, then `python -B tools/opsfeast.py` from the checkout. Use `source`, not `sh tools/activate.sh`; other environments can call their selected Python directly. If Textual is missing, request an installation plan using `requirements-tui.txt`. In Home, choose **Hosts**, highlight **server-01**, press Enter and select **test-connection**. Opening Home is local browsing; selecting that action connects to the host and required jumps. See [the terminal guide](terminal-ui.md) for prerequisites and result interpretation. The agent should supply the actual checkout/interpreter/profile/host rather than leave these example values in your handoff.

When ready to connect to server-01, run:

```sh
.venv/bin/python -B tools/opsfeast.py test-connection server-01 --profile main
```

This connects to the selected host and required jumps, and runs `hostname` and `date`. It does not run recipes, su or sudo. With --json, expect JSON with `connected: true`, `success: true`, successful command results and exit zero. Review the returned hostname to confirm the intended server. A connected session alone is not a successful test if either command fails.

| If it fails | Next check |
| --- | --- |
| Configuration error | Correct the reported YAML file/field; repeat check. |
| Name resolution, refusal or timeout | Confirm address, port, VPN/network and SSH service availability. |
| Authentication failure | Confirm the login account and selected authentication method locally. |
| Host-key trust failure | Verify the server identity through your trusted channel; do not bypass verification. |
| Connected but a command failed | Inspect the command status and account restrictions before proceeding. |

For safe diagnostics, add `--verbose`; use the [diagnostic reference](cli.md) for other options. Do not paste credentials or raw sensitive logs into chat. No connection to these synthetic examples was performed for this guide.

If you prefer agent assistance, paste:

> Read docs/first-host.md and the hosts skill. Help me configure one host, asking only for missing address, login account, authentication method and jump-host information. Preserve existing settings and tell me where to enter secrets locally. Validate configuration without connecting. Give me copyable commands using the actual checkout, interpreter, profile and host ID.

Once settings pass, paste:

> Test only server-01 in profile main. I authorize its configured SSH connection, any configured required jumps, and hostname/date commands. Do not run su, sudo or recipes. Explain the result and give me the next applicable command.

## 3. Practical cases: choose only what you need

Each YAML block is a complete alternative example, not a fragment to append to another `hosts:` mapping. Replace synthetic values locally. Run the same check and connection test before advancing. The full environment expects SSHScript 5.0.0; use [environment checks](getting-started.md) before diagnostics.

### Reuse an existing SSH config alias

```yaml
hosts:
  server-01:
    connection:
      ssh_config_alias: production-web
```

`production-web` is a `Host` alias in your SSH config. Keep hostname/user/key settings there; do not combine those explicit YAML connection fields with the alias. Check does not validate SSH config, keys or reachability. If the alias already specifies a jump, do not also add YAML via. See [SSH config rules](hosts-yaml.md).

### Use an explicit RSA key for a direct connection

```yaml
hosts:
  server-01:
    connection:
      hostname: server.example
      user: operator
      identity_file: /home/local-user/.ssh/server_rsa
```

Use the actual absolute path on the computer running OpsFeast. This field uses SSHScript pkey_path and loads an RSA key; do not assume arbitrary key formats or encrypted-key passphrases are supported. It does not expand `~`. Prefer an existing working SSH config/agent when that better fits your authentication. See [identity_file limitations](hosts-yaml.md).

### Connect through a jump host

```yaml
hosts:
  jump-01:
    connection:
      hostname: jump.example
      user: jumpoperator
    users:
      jumpoperator:
        password: "REPLACE_LOCALLY_WITH_JUMP_PASSWORD"
  server-01:
    connection:
      hostname: internal.example
      user: operator
      via:
        host: jump-01
    users:
      operator:
        password: "REPLACE_LOCALLY_WITH_TARGET_PASSWORD"
```

Test server-01 with the command above; authorization includes its required jump. Each hop uses its own login credentials. If replacing passwords with identity_file, the target key is read on the preceding jump host, not automatically on your local computer. Review the [complete connection rules](hosts-yaml.md) before adapting keys/proxies.

### Test sudo as the SSH login account

```yaml
hosts:
  server-01:
    connection:
      hostname: server.example
      user: operator
    users:
      operator:
        password: "REPLACE_LOCALLY_WITH_LOGIN_PASSWORD"
        vars:
          sudo:
            password: "REPLACE_LOCALLY_WITH_OPERATOR_SUDO_PASSWORD"
```

Here operator logs in, operator authenticates sudo, and root is the requested execution target. The sudo password normally belongs to operator, not root. Omit the operation-specific override when the account password should be used. If using SSH keys, omit the login password and retain a needed sudo override.

After a successful connection test, and only when you want to authorize sudo shell/identity testing:

```sh
.venv/bin/python -B tools/opsfeast.py test-sudo server-01 --run-as root --profile main
```

This tests sudo entry, identity and restoration. It does not grant or prove every command-specific sudo privilege. Inspect per-test status, matched username/UID and cleanup/restoration evidence; see [credential precedence and diagnostics](host-diagnostics.md).

### Test su to a different account

```yaml
hosts:
  server-01:
    connection:
      hostname: server.example
      user: operator
    users:
      operator:
        password: "REPLACE_LOCALLY_WITH_LOGIN_PASSWORD"
      appuser:
        vars:
          su:
            password: "REPLACE_LOCALLY_WITH_APPUSER_SU_PASSWORD"
```

Operator is the SSH login account; appuser is the su target. This operation-specific credential belongs to appuser. It can alternatively use `users.appuser.password` as its fallback; no account is created by this configuration.

Only when you authorize su shell/identity testing:

```sh
.venv/bin/python -B tools/opsfeast.py test-su server-01 appuser --profile main
```

Review entry, identity and restoration separately. A skipped or incomplete test is not success. Listing users alone does not authorize switching accounts. For chains or sudo as a different actor, follow the [diagnostic guide](host-diagnostics.md).

## 4. Collect inventory when ready

After the connection test succeeds, choose whether to authorize read-only system inventory. This requires the full environment, reviewed recipe code and supported target platform; connection success alone does not establish recipe applicability.

```sh
.venv/bin/python -B tools/opsfeast.py recipes run system/inventory/overview --host server-01 --profile main
```

Explicit recipe selection works without adding a hosts.yaml recipes list. The runner obtains missing platform facts, selects an implementation and saves reports in the selected Feast. Read its JSON summary and reported saved paths; zero requires complete inventory success. Partial, unsupported, skipped and failed results remain visible. See the [inventory guide](../recipes/system/inventory/overview/README.md) for operations and verification limits.

Agent prompt:

> Review system/inventory/overview for server-01 in profile main and explain its operations and applicability. Give me the exact command and expected result. Execute only if inventory is already within my authorization; otherwise prepare it for my decision.

## Complete references

- [hosts.yaml reference](hosts-yaml.md): every supported field, authentication and path rules, includes, groups and recipe selections.
- [CLI reference](cli.md): exact arguments, output, storage and exit codes.
- [Host diagnostics](host-diagnostics.md): credential precedence, platform facts, su/sudo and result interpretation.
- [Profiles](profiles.md) and [recipe sources](recipe-sources.md): expand after your first host works.

Documentation examples are synthetic. Configuration validation and automated mock tests do not prove native SSH, su or sudo behavior on your host.

_Last modified: 2026-10-20 11:22:14_
