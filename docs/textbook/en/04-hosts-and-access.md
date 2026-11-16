# 4. Configure and connect one host

[Book home](README.md) · Previous: [Setup](03-setup-and-profiles.md) · Next: [Recipes and results](05-recipes-and-results.md)

Start with one host and a narrow connection test. Host configuration defines how the selected profile reaches a target. Account declarations describe available credentials and policy; listing an account does not authorize using its privileges.

## Add a stable logical host

For a new disposable example, this is a complete minimal `hosts.yaml` using existing agent/default-key authentication:

```yaml
hosts:
  server-01:
    connection:
      hostname: server.example
      user: operator
```

`server-01` is the stable ID used in commands. `server.example` is the address, and `operator` is the SSH login account. Replace synthetic values locally. For an existing profile, merge the intended host into its defining file, preserving includes, comments and other hosts. Do not append another top-level `hosts:` key or duplicate an ID.

Passwords belong in private account configuration, entered locally. Current password fields are plaintext; never place real credentials in chat, public recipes, CLI assignments or textbook examples. `dump` can expose secrets. An explicit `identity_file` has key-format and key-location constraints; jump-host keys may be read on the preceding hop. Follow the complete [hosts guide](../../hosts-yaml.md) rather than guessing key or proxy behavior.

For an SSH config alias, the connection can instead use `ssh_config_alias`; it must not be combined with conflicting explicit YAML connection fields. Use the [first-host alternatives](../../first-host.md) for complete password, alias, RSA-key and jump examples.

## Validate locally, then test within scope

```sh
python -B tools/opsfeast.py check --profile main --json
```

This loads and validates configuration without connecting. Correct errors in the reported source. A passing check does not validate credentials, network reachability or every recipe's business rules.

When the selected host and necessary jumps are authorized:

```sh
python -B tools/opsfeast.py test-connection server-01 --profile main --json
```

This connects and runs `hostname` and `date`, without su/sudo or recipes. Examine `connected`, command results, `success`, hop evidence and cleanup. A connected session with failed commands or cleanup is not a successful test. Verify that the reported hostname belongs to the intended server. Stop and diagnose before expanding to a group.

Agent prompt:

> Validate profile main locally. Then perform the already-authorized hostname/date connection test only on server-01 and its required configured jumps. Explain the actual target, selected authentication source and cleanup evidence without exposing credentials. Do not run recipes or switch accounts.

## Choose the diagnostic that answers your question

| Need | Tool and effect |
| --- | --- |
| Validate local configuration | `check`: no connection |
| Check login and two basic commands | `test-connection`: actual connection |
| Explicitly refresh platform facts | `host-init`: actual connection and cache update |
| Check configured account capabilities | `test-host`: may test enabled sudo and independent su targets |
| Test one login actor's sudo to root | `test-sudo`: privilege entry, identity and restoration |
| Test su to declared users | `test-su`: independent targets, or explicitly selected chains |

`test-host` can reuse valid platform facts and can report skipped tests even with exit zero. Inspect each state and reason. Explicit `host-init` requests fresh facts. Broad capability testing is a larger operation than checking basic SSH login.

## Separate login from execution identity

The SSH login account, sudo actor and effective execution account can differ. Sudo normally authenticates the actor; su uses the target's configured credential. Account sudo is enabled unless Boolean false, and password selection depends on field presence. Null, empty strings and the literal policy string `"false"` have defined meanings. Use [inventory access](../../inventory-access.md) and [diagnostics](../../host-diagnostics.md) before editing these settings.

For a supported `python-recipe`, an operator can select whole-recipe execution policy under the exact recipe reference:

```yaml
execution:
  via: sudo
  user: root
```

This is a fragment beside that reference's `enabled` and `vars` fields, not a complete host file. The platform verifies the selected identity before the body and checks restoration afterward; failure does not silently fall back to login. Keep credentials in account policy. Native inventory has its own bounded actor policy, and offline reports do not acquire a host account this way. Pipe-console sudo requires a compatible target policy; terminal-only policies can fail.

**Checkpoint:** Identify the login account, intended execution account, permitted privilege method and observed UID. Explain any skipped or unknown identity evidence before describing a collection as root-verified.

Canonical guidance: [hosts skill](../../../skills/opsfeast-hosts/SKILL.md), [first host](../../first-host.md), [configuration](../../hosts-yaml.md), [results and accounts](../../recipe-results-and-accounts.md), and [CLI](../../cli.md).

*Last modified: 2026-10-26 12:55:26*
