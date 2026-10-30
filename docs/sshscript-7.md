# SSHScript 7.0.1 release support

OpsFeast execution now uses the published `sshscript==7.0.1` package. The official [GitHub release](https://github.com/iapyeh/sshscript/releases/tag/v7.0.1) was published on 2026-10-30; [PyPI 7.0.1](https://pypi.org/project/sshscript/7.0.1/) supplies the wheel and source distribution. Release source is `b8d7c8fe88b4096e8a58e6609ba805ee2bf41049`.

The release wheel's 32 package/type files match the exact official source. Compared with reviewed 7.0.0, only `_version.py` changes; the command, connection, Console and cleanup implementations are unchanged. The [7.0.1 changelog](https://github.com/iapyeh/sshscript/blob/v7.0.1/CHANGELOG.md) adds maintainer release/documentation tooling and clarifies agent status guidance: use `result.exitcode`, `session.exitcode` and `$.exitcode`; `subprocess.CalledProcessError` still uses its native `returncode`.

At update time the official website skill ZIP still documented 7.0.0. The complete eight-file 7.0.1 skill was therefore generated with `tools/sync_ai_docs.py outputs()` from the exact public release commit. All upstream bytes are preserved. SOURCE.json records the release source, generated bundle digest and separately observed website bundle identity. Release availability is established by official tag/PyPI metadata, not inferred from documentation wording or a version label.

| Artifact | SHA-256 |
| --- | --- |
| sshscript-7.0.1-py3-none-any.whl | `54ee743010ec896379780b0445a3a24ace2a654704413ca034cbb85d7017a73c` |
| sshscript-7.0.1.tar.gz | `feb9e9dd5b5a99480151cefb673912e65d153f534ade84171ee196390ee30a04` |
| Complete skill ZIP | `17c6bf7236e70a3f7c73b28b730c6df0c46d5c3936e8a68fc24fab9578d71019` |

## Dependency, identity and update

`requirements.txt`, the execution extra in `pyproject.toml` and built package metadata use `sshscript==7.0.1`. Python 3.11+ is required. The release declares Paramiko >=2.11,<5 and packaging >=21; do not upgrade unrelated dependencies as part of this update.

Within an authorized selected environment:

```sh
SELECTED_PYTHON -m pip install -r requirements.txt
SELECTED_PYTHON -B tools/check_environment.py --json
SELECTED_PYTHON -m pip check
```

An existing source installation with the same version may need an explicit reviewed reinstall from the verified release wheel. A version comparison alone cannot establish replacement. Follow [the complete package/skill update procedure](skill-updates.md#update-sshscript-with-one-prompt), including backups and reloads. The update workflow does not connect to managed hosts or authorize privilege tests.

[Runtime manifest](../schemas/sshscript-runtime.json) records release source identity, exact requirement, wheel digest, complete skill digest and 32 package/type hashes. [Skill provenance](../skills/sshscript/SOURCE.json) binds the complete payload to the release source. Core, runner and standalone test-connection retain strict version/source checks before Session creation; same-version file drift remains a failure. Base init/offline metadata capabilities remain independent of execution dependencies. Guards never install, retry or migrate data. Checks read files on disk; already-running Python/agent processes must reload their cached modules/knowledge explicitly.

Checkout helper `sshscript_runtime.source_identity()` returns source_commit, source_matches, expected_files, checked_files or a safe error_type. Internal `require_source(module)` enforces it; runtime receipts carry `sshscript_source`. This is a compatibility identity, not a sandbox or independent publisher signature. Review future package changes before updating hashes.

## Compatibility and existing private recipes

OpsFeast now strictly requires 7.0.1. Update package, complete skill and this checkout together; 7.0.0 and mismatched versions remain rejected before execution. Existing private recipes/packages that explicitly pin `==7.0.0` need their own reviewed dependency update before reuse; this product update does not rewrite installed private recipe copies or historical records. Regenerate/review portable backup recipes only under their installation scope. Host connection keys and stored observations need no migration.

The selected environment update removed stale duplicate 5.0.0 and 7.0.0 package metadata with pip before installing the verified 7.0.1 wheel with no dependency upgrades. Package and skill backups remain in the local ignored staging area; unrelated environments/profiles are preserved. See [verification evidence](../tests/README.md#sshscript-701-update-verification).

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

Use [the matching skill](../skills/sshscript/SKILL.md), [Agent Guide](../skills/sshscript/references/agent-guide.md), [API guide](../skills/sshscript/references/api-guide.md), [version policy](../skills/sshscript/references/versioning.md) and [embedded Console contract](../skills/sshscript/references/embedded-console.md). Console(existing_session, ownership="borrowed") preserves explicit ownership and Session reuse evidence. Hidden input, entered-program exits, diagnostics and TTY output behavior are unchanged from reviewed 7.0.0. Without an exit sequence a program can stay in waiting_input; silence/reminders do not prove cleanup. Script CLI TTY output defaults are separate from Python library capture.

Public tests cover release dependency/metadata consistency, strict version/file-drift rejection, current resolver arguments and native local borrowed Console/jobs/cleanup, alongside OpsFeast recipes, packaging and retained data. New package application and credential-free checks do not establish real-host SSH/su/sudo/database compatibility. Historical host results remain historical; run target verification only within separate operational authorization.

*Last modified: 2026-10-30 16:38:14*
