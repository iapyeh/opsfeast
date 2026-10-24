# SSHScript 7.0.0 source support

This development checkout targets the **unreleased** SSHScript 7.0.0 public source
commit `7a3b43594eca50cf1600d4f8a1dc67cb266df19e`. It does not claim that 7.0.0 is
published on PyPI or GitHub Releases. The matching complete bundled skill is the
library reference; do not replace it with the maintained website's latest ZIP.

- [Pinned source](https://github.com/iapyeh/sshscript/tree/7a3b43594eca50cf1600d4f8a1dc67cb266df19e).
- [Matching API guide](../skills/sshscript/references/api-guide.md),
  [version policy](../skills/sshscript/references/versioning.md) and
  [Console contract](../skills/sshscript/references/embedded-console.md).
- [Runtime manifest](../schemas/sshscript-runtime.json) contains the source SHA,
  exact dependency URL, skill ZIP digest and 32 package/type-file SHA-256 values.
  [Skill provenance](../skills/sshscript/SOURCE.json) records the matching bundle.

## Dependency and identity

`requirements.txt`, the execution extra in pyproject.toml and built wheel metadata
use the full-source archive requirement, not `sshscript==7.0.0`. A new installation
needs access to that source and its declared build dependencies. Follow the
selected interpreter/setup authorization policy before installation. Existing
working environments are not reinstalled automatically.

For an explicitly authorized source install, from the trusted checkout:

```sh
SELECTED_PYTHON -m pip install -r requirements.txt
SELECTED_PYTHON -B tools/check_environment.py --json
SELECTED_PYTHON -m pip check
```

Replace SELECTED_PYTHON with the actual selected interpreter. The readiness command
is read-only. The full scope verifies import/distribution 7.0.0 and all 32 module,
.pyi and py.typed hashes, plus matching skill provenance/references. Base init scope
does not import SSHScript or require its native dependencies. Core sessions,
runner execution and standalone test-connection reject unsupported versions and
same-version source drift before Session creation. No runtime check installs,
downgrades, retries or migrates anything. Diagnostics omit arbitrary exception
text and secrets. Source inspection verifies files on disk, not a running
process's previously cached imports; reload old agent/Python processes explicitly.

The source identity helper is checkout-level `sshscript_runtime.source_identity()`;
its receipt includes expected SHA, source_matches, expected_files and checked_files
(or safe error_type). `require_source(module)` is the internal execution guard.
These do not create a new Core method or versioned result dataset. The runner adds
source evidence under runtime.sshscript_source; proxy policy evidence remains per
hop. Manifest checks establish a reviewed compatibility identity, not a sandbox or
independent publisher signature. Updating the supported commit requires review of
code, pins, complete skill, manifest and tests together. Never edit hashes merely
to suppress a mismatch or accept a new same-version build without review.

## Breaking changes and preserved configuration

| Previous Python argument/setting | 7.0 name |
| --- | --- |
| host argument | hostname |
| pkey_path | parent_key_filename |
| proxyCommand / proxyJump | proxy_command / proxy_jump |
| policy | missing_host_key_policy |
| known_hosts strategy | known_hosts_source |

Only hostname may be positional in Session.connect/resolve_connection. OpenSSH
config files still use ProxyCommand/ProxyJump; they are not Python argument names.
The resolver's returned dictionaries use current names too. No old aliases or
compatibility paths are provided by OpsFeast.

Host YAML retains `identity_file`, `proxy_command` and `proxy_environment`. The
adapter maps identity_file to parent_key_filename: a direct key is read on the
local calling Session; a nested key is read on its parent host through SFTP. It
never silently switches to local key_filename or changes users/account policy.
The first-hop proxy and environment launcher now pass proxy_command throughout;
argv, protocol streams, exec PID continuity, timeout and strict cleanup are
preserved. The [child environment policy](process-environment.md) remains in force.

SSHScript 7 can use password as the parent-key decryption fallback when passphrase
is omitted. This YAML schema does not expose an independent passphrase, so a key
passphrase differing from login password needs another explicitly authorized,
supported authentication configuration. Do not reinterpret another user's
credential as an actor/key credential or retry with alternate credentials.

Existing private/custom Python connection code needs the same argument migration.
Current bundled identity/network/inventory/database recipes use supplied Sessions.
The MySQL/MariaDB recipe's argv, secret stdin, command_timeout and structured
exit/truncation checks remain valid. Database configuration, replication SQL,
retention normalizer/schema bytes and old observations are unchanged by this
migration; there is no profile initialization, data migration or historical rewrite.

## Console and verification boundaries

Console(existing_session, ownership="borrowed") remains the public handover API.
Use structured state/result/session_reuse, one creator thread and explicit account
policy. New hidden input and entered-program exit controls are described in the
matching Console guide: leaving a program without an exit sequence can retain it
in waiting_input instead of silently abandoning it. Do not treat a reminder as
successful restoration. Script CLI TTY output defaults changed; code that prints
captured output should use the documented --quiet option to avoid duplicate display.
OpsFeast recipes use Python modules, not that script CLI output as a data contract.

Public regression checks include version/source rejection, package/type drift,
actual 7.0 resolver names, source dependency/metadata consistency and native local
borrowed Console state/job/cleanup/Session reuse. Existing replication and proxy
integration tests run against the actual selected 7.0 package. Local subprocesses
and protocol failure fixtures are native; connection/account/jump tests are
synthetic. They do not establish successful real SSH, wstunnel, native su/sudo,
MySQL/MariaDB connectivity, or the prototype browser UI on this snapshot. Prior
6.1.0 real-host results remain historical. Revalidate those targets only under
separate host/UI authorization. The old Console prototype is not a formal product
adapter and is not shipped in the tested release artifact.

*Last modified: 2026-10-24 22:26:13*
