# SSHScript 7.0.0 release support

OpsFeast execution now uses the published `sshscript==7.0.0` package. The official [GitHub release](https://github.com/iapyeh/sshscript/releases/tag/v7.0.0) was published on 2026-10-25; [PyPI 7.0.0](https://pypi.org/project/sshscript/7.0.0/) supplies the wheel and source distribution. Release source is `a1c76d016419484b6ffb930bf2b16f30bae61208`.

The release wheel's 32 package/type files are byte-identical to the previously supported development snapshot. The complete eight-file skill ZIP generated from the release source is also identical to the official website ZIP and the previous bundled payload. Upstream documents still use the wording “source contract”; their bytes are preserved. Release availability is established separately by the official release and PyPI metadata, not inferred from that wording or a version label.

| Artifact | SHA-256 |
| --- | --- |
| sshscript-7.0.0-py3-none-any.whl | `43e8d010065aca3aa137de308e0d4ea31a2792f313e7e728f29317c834fda278` |
| sshscript-7.0.0.tar.gz | `0446d2f8698f17e9aa5794ccc6d7ce8f2900979e8fb37028d4fe46d4790345d8` |
| Complete skill ZIP | `943984702b6bef752811f92f607272157c815b2a6d968846d21a4cb571cd5b3f` |

## Dependency, identity and update

`requirements.txt`, the execution extra in `pyproject.toml` and built package metadata use `sshscript==7.0.0`. Python 3.11+ is required. The release declares Paramiko >=2.11,<5 and packaging >=21; do not upgrade unrelated dependencies as part of this update.

Within an authorized selected environment:

```sh
SELECTED_PYTHON -m pip install -r requirements.txt
SELECTED_PYTHON -B tools/check_environment.py --json
SELECTED_PYTHON -m pip check
```

An existing source installation with the same version may need an explicit reviewed reinstall from the verified release wheel. A version comparison alone cannot establish replacement. Follow [the complete package/skill update procedure](skill-updates.md#update-sshscript-with-one-prompt), including backups and reloads. The update workflow does not connect to managed hosts or authorize privilege tests.

[Runtime manifest](../schemas/sshscript-runtime.json) records release source identity, exact requirement, wheel digest, complete skill digest and 32 package/type hashes. [Skill provenance](../skills/sshscript/SOURCE.json) binds the complete payload to the release source. Core, runner and standalone test-connection retain strict version/source checks before Session creation; same-version file drift remains a failure. Base init/offline metadata capabilities remain independent of execution dependencies. Guards never install, retry or migrate data. Checks read files on disk; already-running Python/agent processes must reload their cached modules/knowledge explicitly.

Checkout helper `sshscript_runtime.source_identity()` returns source_commit, source_matches, expected_files, checked_files or a safe error_type. Internal `require_source(module)` enforces it; runtime receipts carry `sshscript_source`. This is a compatibility identity, not a sandbox or independent publisher signature. Review future package changes before updating hashes.

## Connection contract and preserved configuration

| Previous Python name | 7.0 name |
| --- | --- |
| host argument | hostname |
| pkey_path | parent_key_filename |
| proxyCommand / proxyJump | proxy_command / proxy_jump |
| policy | missing_host_key_policy |
| known_hosts strategy | known_hosts_source |

Only hostname may be positional in Session.connect/resolve_connection. OpenSSH configuration keeps ProxyCommand/ProxyJump. No compatibility aliases are added. Host YAML keeps identity_file/proxy_command/proxy_environment; identity_file maps to caller-host parent_key_filename, preserving key ownership for local and nested Sessions. Proxy argv, environment, protocol streams and strict cleanup follow the [existing policy](process-environment.md).

When passphrase is omitted, SSHScript can use password to decrypt a caller-host key. OpsFeast host YAML exposes no independent passphrase field; a different key passphrase needs an explicitly authorized supported configuration. Do not substitute other actors' credentials or retry alternate passwords.

Recipes using supplied Sessions retain their argv, stdin, command_timeout and capture contracts. The release switch adds no host configuration rewrite, observation migration, privilege-policy change or historical reclassification. Custom code that still uses pre-7.0 connection names needs review before execution.

## Console and verification boundaries

Use [the matching skill](../skills/sshscript/SKILL.md), [Agent Guide](../skills/sshscript/references/agent-guide.md), [API guide](../skills/sshscript/references/api-guide.md), [version policy](../skills/sshscript/references/versioning.md) and [embedded Console contract](../skills/sshscript/references/embedded-console.md). Console(existing_session, ownership="borrowed") preserves explicit ownership and Session reuse evidence. Hidden input, entered-program exits, diagnostics and TTY output behavior are unchanged from the reviewed snapshot. Without an exit sequence a program can stay in waiting_input; silence/reminders do not prove cleanup. Script CLI TTY output defaults are separate from Python library capture.

Public tests cover release dependency/metadata consistency, strict version/file-drift rejection, current resolver arguments and native local borrowed Console/jobs/cleanup, alongside OpsFeast recipes, packaging and retained data. New package application and credential-free checks do not establish real-host SSH/su/sudo/database compatibility. Historical host results remain historical; run target verification only within separate operational authorization.

*Last modified: 2026-10-26 12:14:33*
