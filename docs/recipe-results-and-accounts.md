# Recipe assessments and execution accounts

OpsFeast supplies recipe-assessment 0.1.0 and recipe-execution 0.1.0. They separate a recipe's interpretation of its findings from platform execution evidence. Start with [execution](recipe-execution.md), [Core](core-api.md), [configuration](recipe-sources.md) and [CLI](cli.md). These features require an updated OpsFeast installation; SSHScript execution uses the matching supported 7.0.1 distribution and skill snapshot.

## Execution state and recipe assessment

The fixed `status` values remain `success`, `partial`, `failed`, `skipped` and `unsupported`. They control existing execution/exit-code behavior. The default terminal success label remains `PASS`: it means the operation completed successfully, and does not establish that its findings need no attention.

Operational and offline report recipes can optionally return an assessment:

```python
def execute(recipe):
    return {
        'status': 'success',
        'reason_code': 'checked',
        'message': 'Completed a read-only check.',
        'data': {'expired_files': ['synthetic-old.sql']},
        'assessment': {
            'label': 'CLEANUP NEEDED',
            'severity': 'warning',
            'summary': 'One expired file requires review.'
        }
    }
```

All three assessment fields are required. `label` is stripped nonblank plain text up to 80 characters; `summary` up to 1024. Control characters and Unicode line/paragraph separators are rejected. `severity` is `info`, `warning`, `error` or `critical`. Extra keys, invalid values or malformed assessments fail result validation. See [schema](../schemas/recipe-assessment.schema.json). An assessment is optional; existing domain-specific displays remain available when absent.

Terminal examples are `CLEAN`, `WARNING · CLEANUP NEEDED` and `PARTIAL · ERROR · BACKUPS MISSING`. Non-success platform state stays visible even when a recipe claims a reassuring label. Retention/content/cleanup failures retain their platform failure display and exit behavior. Severity alone does not change exit code or send a notification. Recipes choose the appropriate fixed status, and enabled consumers manage notification/todo policy separately.

The [backup module](backup-file-checks.md) returns `BACKUPS OK` for complete scans with daily files and no hygiene findings; `BACKUPS OK · CLEANUP NEEDED` with warning severity for expired/unexpected entries; `BACKUPS PENDING`, `BACKUPS MISSING` or `CHECK INCOMPLETE` otherwise. Hygiene findings alone keep `status: success`. Pending/missing/incomplete checks remain partial. Presence is not checksum, content or restore verification, and no label authorizes deletion.

## Configure a whole-recipe execution account

For `runner.contract: python-recipe`, the runner supplies the selected scoped `Recipe` before calling `execute(recipe)`. Recipe code continues using `recipe.session`; no per-recipe su/sudo implementation or root flag is needed.

Add `execution` beside `enabled` and `vars` under an exact recipe reference in `hosts.yaml`. This example assumes an existing, authorized host/account configuration:

```yaml
hosts:
  backup-example:
    recipes:
      ':backup/files/check/daily-backups':
        execution:
          via: sudo
          user: root
```

Merge this fragment into existing settings, preserving connection, users, vars and other bindings. It is not a complete host file. Credentials belong to the existing host `users`/credential policy, never to `execution` or recipe vars.

| Field | Meaning |
| --- | --- |
| `via: login` | Default. Run as the verified connection account. Optional `user` asserts the expected UID; it does not switch accounts. |
| `via: sudo` | Use the current login actor's configured sudo policy/credential to acquire the explicit target `user`. |
| `via: su` | Acquire the explicit target `user`, declared in host users, using its configured su credential. |

`via` and `user` inherit independently through default → groups → host, with the existing first-group precedence. Missing effective policy means `{via: login, user: null}`. Effective su/sudo requires a target. `execution: null` resets the whole inherited policy; `{via: login, user: null}` is an explicit reset. An empty mapping inherits existing leaves. Source vars and CLI `--var` are recipe inputs and cannot override this operator policy. No new CLI account flags are provided.

`check` validates effective configuration and supported recipe contracts without connecting. Invalid policy fails before connection/code loading. A nondefault policy is rejected for native inventory, legacy `python-session` and offline report runners. Inventory keeps its own documented actor-selection rules. An offline report can return an assessment but does not acquire a host account through this setting.

## Acquisition, identity and cleanup

The platform verifies the connection identity, acquires exactly the selected method/target, and verifies effective UID before the recipe body starts. There is no fallback to another account/method after failure. Existing disabled-sudo and credential selection policies apply; this setting grants no authorization and bypasses no host policy. It is not a sandbox against arbitrary Python using other tools.

Failed acquisition is reported as `execution_identity_failed`; the body does not run. Operation, restoration and connection-cleanup failures remain separately visible. Returning a custom success label cannot hide them. Account restoration is verified before the scope is released; an unsafe session is disabled. The saved `execution_identity` object includes requested policy, observed login and actual identity, verification and restoration flags, and a safe exception type where applicable. See [evidence schema](../schemas/recipe-execution-evidence.schema.json). Terminal OS identity and retained collection identity prefer the verified execution actor, while SSH login identity remains separately identified.

Whole-recipe su/sudo uses a Bash pipe console (`get_pty=False`) to preserve independent stdout/stderr and machine-readable input/output. It requires a target shell/privilege policy compatible with that transport. Policies requiring a terminal can fail acquisition. OpsFeast does not silently switch transport or retry credentials. Existing explicit `recipe.su()`/`recipe.sudo()` scopes also default to pipes now; manual interactive scopes may explicitly request `get_pty=True`, with PTY stream merging and terminal semantics.

## Shared Python interfaces

```python
from opsfeast import Instance

profile = Instance.open('/absolute/opsfeast').profile('example')
with profile.recipe('backup-example', execution={'via': 'sudo', 'user': 'root'}) as recipe:
    result = recipe.session.exec_command(['id', '-u'], check=True)
```

`Profile.recipe(host_id, *, vars=None, timeout=30, execution=None)` accepts an explicit call policy, defaulting to login; it does not select a recipe reference or inherit a reference's settings. The CLI runner resolves those settings. Lower-level code holding a login-scoped Recipe can use `with recipe.execution(policy) as selected:`. `recipe.root()` reuses an already verified root execution scope; it retains its existing bounded acquisition policy from a login scope. Acquiring root inside a selected nonroot console is unsupported. Borrowed runner sessions remain owned by the runner.

In a selected console, `recipe.session.exec_command(argv, input=..., command_timeout=..., check=..., capture_limit=...)` and `start(argv, input=..., timeout=...)` preserve quoted argv, managed-job capture evidence and original argv result metadata. Text input is UTF-8; bytes, including NUL, are exact. Empty input and absent input terminate with EOF; commands cannot consume the console control channel. Multiline arguments are encoded into one Bash command line. No target temporary files are created by this adapter. It is a finite stdin interface, not interactive streaming. Explicit PTYs have their native terminal limitations. Pipe-console timeout/stop may leave remote termination unknown and disable the console; retain SSHScript's termination evidence rather than claiming successful cancellation.

## Saved evidence and portability

Raw results, retained envelopes and saved batch targets carry assessment and execution identity without changing recipe-owned data schemas. Views use evidence saved for that exact run; archived/removed raw files can still leave the batch's saved assessment/account evidence available. Old results without these fields retain their existing displays. Vault presents the assessment and saved account evidence; historical replay/import does not recompute them or create current incidents.

Portable recipes can declare required feature versions:

```yaml
portability:
  api: 0.1.0
  python: '>=3.11'
  features:
    recipe-assessment: 0.1.0
    recipe-execution: 0.1.0
    portable-retention: 0.1.0
```

The installation plan checks supported feature versions without executing candidate code. Unknown/unavailable versions fail readiness. Receivers need the updated product before installing a recipe that declares these features; older installers may reject the new field. Private account settings are never carried in the recipe package. See [portability](portability.md).

## Human-agent workflow and verification

An operator can say: “Inspect this recipe and its current policy. Configure this approved recipe to run as root through the declared login account's sudo policy, preserve other settings, validate locally, then run on the named host within my authorization. Report execution state, findings, actual account and cleanup separately.” The agent should inspect/reuse these platform interfaces instead of rewriting account-switching loops. Configuration-only authorization stops before host execution.

[Public tests](../tests/test_recipe_execution_assessment.py) cover configuration inheritance/rejection, default login, synthetic su/sudo success/failure, UID mismatch, disabled policy, body suppression, restoration failure, result precedence, history and standalone Core use. Native local Bash pipe tests cover scanner JSON, multiline argv, exact stdin/EOF, independent stderr, capture flags and managed jobs. They do not establish new real-host SSH, su or sudo policy compatibility; verify those only within explicit operational scope.

*Last modified: 2026-10-30 12:17:33*
