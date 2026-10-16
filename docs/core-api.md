# Core Python API 0.1.0

Console summaries use tables when stdout is a terminal; add `--json` to supported inspection/diagnostic/check/profile commands for structured output. Non-TTY formats, execution scope and stored data remain unchanged. See [the command-specific console policy](cli.md#terminal-tables-and-json).

OpsFeast bundles a public Python package for user agents, standalone programs and recipes. Python 3.11+, PyYAML 6.0.3 and tabulate[widechars] 0.10.0 are package dependencies; connection and privilege operations additionally require matching SSHScript import/distribution 5.0.0. Configuration and inspection do not import SSHScript or contact hosts. Logging and notifications are deferred and have no callable Core service yet.

## Installation, instance and profile

An **instance** is the entire OpsFeast installation/checkout. Its ignored `.opsfeast-instance.json` contains schema_version `0.1.0`, UUID `id`, required nonblank single-line `name`, optional string `description`, and the absolute `installation_path` used for copy detection. A **profile** selects one management root, usually `feasts/NAME/`, possibly an externally attached directory. `feasts/` is a container, not an instance. Existing `feast.yaml` definitions and profile registries retain their current formats.

First successful CLI `init` creates the installation UUID; subsequent init and profile changes preserve it. `Instance.initialize()` initializes identity only; `Instance.init_profile()` explicitly scaffolds and registers a profile and initializes identity. Reads never initialize storage. Metadata writes use a POSIX advisory lock, a private temporary file and atomic replacement. Cooperating Core metadata writers serialize; this is not a multi-file transaction or protection from unrelated editors.

| Identity situation | Behavior |
| --- | --- |
| Missing metadata or missing id field | Nil UUID `00000000-0000-0000-0000-000000000000`, `identity_status: placeholder`; operations remain available |
| Explicit nil UUID | Placeholder; caller accepts collisions; initialize replaces it with UUID v4 |
| Assigned identity at recorded location | `identity_status: assigned`; init preserves it |
| Metadata copied to a different path | Reads expose nil/placeholder with `installation_location_changed`; init generates a new UUID v4 |
| A newly cloned checkout | Ignored metadata is absent; init generates a new UUID v4 |
| Original installation moved | Explicit `relocate_identity()` preserves its UUID and records the new path |
| Invalid UUID/schema/metadata | ConfigError; inspection reports a partial result, not silent fallback |

A copy into another directory must obtain a different UUID. Use initialize on the copy; do not use relocate for copies. The default name follows a regenerated UUID; custom name and description survive. Copy detection compares resolved absolute paths, so a symlink alias is the same location. Independent physical copies mounted at the same absolute path cannot be detected: explicitly renew their identity. UUIDs identify records, not authenticated communication peers. Existing retained-observation source IDs and host identities remain separate contracts; this installation UUID does not rewrite historical identity. Names need not be unique. Nil UUID use explicitly accepts duplicate-identity risk.

The UUID ending in `000000000001` is reserved for the original OpsFeast development installation. Normal initialization uses UUID v4; copies must not inherit that reservation. The development assignment is private local metadata, never a tracked default.

## Import and package delivery

From the checkout root, `from opsfeast import Instance` works without adding tools/ to sys.path. To use the package from an arbitrary directory, install the trusted checkout into the selected environment under installation authorization:

```sh
python -B -m pip install --no-build-isolation /absolute/trusted/opsfeast-checkout
```

The dependency-free PEP 517 backend builds a wheel/sdist using an explicit public-directory/extension allowlist; it excludes registries, Feast data, private guidance and caches. The package requires PyYAML and tabulate[widechars] (wcwidth supplies Unicode table alignment); use the `execution` extra for SSHScript or `tui` for Textual when authorized. No separate PyPI publication is provided. This is a regular install, not editable mode: reinstall after updating source. Do not install or upgrade an existing environment merely to inspect it.

The wheel includes public recipes, schemas, documentation, skills and referenced public test sources. Run the complete regression suite from the source checkout/sdist. Installed library callers should explicitly supply the installation checkout and management selection. Default resource lookup in an installed wheel points to bundled product resources, not a discovered user's checkout. Continue using the chosen checkout's CLI for profile operations. Existing tools imports remain compatibility surfaces; the package internally bridges trusted bundled tool modules. This is not a plugin loader or a promise that every legacy helper is a stable API.

## Open, inspect and select

```python
from opsfeast import API_VERSION, Instance

instance = Instance.open(installation="/srv/opsfeast")
status = instance.inspect()
profile = instance.profile()                 # Snapshot of the active selection.
other = instance.profile("inventory")        # Does not change active profile.
external = instance.profile(root="/srv/feasts/other")  # Explicit root; name may be None.
settings = profile.hosts.list()              # Independent, masked dictionaries.
host = profile.hosts.get("host-01")
icon = host["icon"]                         # Resolved explicit/global/built-in host symbol.
profile.reload()                             # Explicitly replace configuration snapshot.
```

Instance.open requires an existing directory and writes nothing. Missing identity/profiles do not prevent instance inspection. Profile selection validates the existing management entry/definition; configuration loading uses the same Validator as the CLI, including includes, duplicate/path and connection checks. It does not statically validate every selected recipe or prove connectivity. Invalid/missing configuration raises ConfigError. Failed reload retains the previous valid snapshot.

`hosts.get(host_id, reveal_secrets=True)` explicitly returns raw values for a caller that actually needs them. Neither form changes live configuration; returned dictionaries are copies. Masking is key-based, not a guarantee that arbitrary strings contain no secrets. Do not print entire settings or treat masked values as execution credentials. Effective hosts and declared accounts include resolved icon fields. Entry hosts.yaml uses global default.icon.host/user; entry and included YAML use groups.<name>.icon.host/user, with built-ins 🍎/👤. Explicit host/account icons override defaults; default.users.<account>.icon then takes priority for accounts. Each remaining field independently takes the first configured group value in host group order before the global default. An explicit icon must be exactly one Unicode Symbol code point; invalid values fail loading. Defaults do not rewrite source YAML. Optional default.users.<account>.email remains source metadata readable through CLI dump; it is not merged into host-account snapshots. See [host icon semantics](hosts-yaml.md#host-icon). Connection creation privately copies the selected configuration snapshot. Configuration edits take effect after reload/new profile selection, never halfway through a connection scope.

`instance.inspect()` returns API version, UTC inspection time, installation identity, profiles/active selection, configuration validity/host counts, installed dependency versions and safe component error types. Status is success or partial; missing identity is a usable placeholder. Dependency metadata is not proof of import/native runtime readiness. `profile.inspect()` freshly reads local configuration, returns masked hosts, loaded paths/time, standard storage paths and unimplemented service states. Its fresh inspection does not replace the profile's execution snapshot. Invalid profile inspection raises ConfigError; instance inspection captures per-profile failures.

Both inspection methods are read-only: no init, repair, migration, connection, privilege test or provider probe. Report/job/result locations may not exist yet. Report artifacts live under `reports/RUN_ID/artifacts/`; obtain actual verified paths through existing result/artifact tools instead of guessing them. `profile.results(recipe=..., host=..., status=...)` and `profile.jobs()` reuse existing read contracts and preserve partial/error states. They do not execute anything.

## Explicit local writes

```python
instance.initialize(name="Operations", description="Production controller")
instance.update_metadata(name="Primary operations")
profile = instance.init_profile("main")
instance.profiles.attach("/srv/feasts/inventory", name="inventory")
instance.profiles.use("inventory")
instance.profiles.detach("inventory")
```

`profiles.list()` returns roots, available/unavailable states and active flags. Attach validates and preserves existing data; conflicting names/roots fail. Init reuses a registered name rather than creating another directory. Main cannot detach; detaching active switches to valid registered main and preserves files. Local writes do not authorize host operations. Existing Profile objects keep their selected roots when the active profile changes. Registry writes use existing atomic save and Core writers serialize; legacy CLI/external-editor concurrent registry changes are not a transactional guarantee. No public hosts editor, arbitrary file writer, history deletion or migration API is included.

## Standalone session and Recipe scopes

Within already authorized host/command scope:

```python
with profile.recipe("host-01", vars={"purpose": "identity"}, timeout=15) as recipe:
    result = recipe.session.exec_command(["id", "-un"], check=True)
    with recipe.sudo(user="root") as privileged:
        uid = privileged.session.exec_command(["id", "-u"], check=True)
    # Original actor is available again only after verified restoration.
```

`profile.sessions.connect(host_id, timeout=30)` yields the same scoped Recipe capabilities without invocation vars. Recipe is a per-execution object; do not construct it directly or share across threads. It provides host_id, vars, timeout, run_id, instance_id, selected Profile, connection_owner (core or runner), session, sudo(), su() and a copied report. Standalone vars must be plain JSON-compatible mappings; runner vars additionally use descriptor validation/defaults.

The session facade provides exec_command and start. It applies a finite default command/job timeout and quotes argv for privileged consoles; privileged commands require string argv sequences. CommandResult/managed-job interpretation follows SSHScript 5.0.0, including truncation and unknown remote termination. Caller-owned jobs must finish/stop within scope; returned raw job objects are not lifetime-sandboxed. Shell/connect/settings and direct privilege factories are not exposed through this facade. Existing legacy recipes retain their full borrowed SSHScript Session.

Core owns standalone connection cleanup, including jump ancestors. Recipe/session close is rejected with CoreError `session_not_owned`; leaving the outer scope closes the owner strictly. Scope expiry, wrong-thread use, use of a parent while a nested privilege scope is current, or uncertain restoration raises `session_scope_unavailable`. Python introspection/private attribute access is not sandboxed. Disabled hosts/jumps are rejected, with no fallback, implicit host-init or su/sudo on connect. Timeout is per stage/command, not a total recipe deadline.

## Privilege transitions and evidence

`recipe.sudo(user="root")` changes the current actor through sudo; `recipe.su("app")` changes to a declared hosts users account. Both return a child Recipe with the same run/instance context and a scoped command facade. Nested transitions are supported. Verify the caller's authorized accounts before entry; available methods are not grants of privilege.

Credentials reuse canonical OpsFeast policy: sudo checks the current actor's Boolean policy (false disables; true/omission enables; strings are rejected) and canonical sudo-password presence/null/empty/"false" rules, then legacy credential precedence. Host-level credentials apply only to the actual connection account. Su uses the target's vars.su.password then account password; missing su credentials fail before entry. Explicit empty strings stay empty. No lower-priority credential retry occurs. Sudo policy is not bypassed simply because the actor is already root.

Core probes effective identity before entry, verifies target UID inside the authenticated SSHScript console, and verifies original username/UID after exit. Each attempt records operation, target, password source (never value), status, actual identity and restoration evidence. A rejected entry does not execute the body. Failed exit or uncertain restoration poisons the shared execution; further commands fail and runner cannot save claimed success. Command failures inside a scope still unwind it. When cleanup also fails, preserve the original exception and attach a safe note; otherwise raise CoreError. Connection cleanup and privilege cleanup remain distinct recorded evidence. No remote process-termination guarantee follows from successful channel cleanup.

## Runner integration and migration

New recipes use descriptor 0.3.0 with this runner declaration:

```yaml
runner:
  contract: python-recipe
  version: 0.1.0
  entrypoint: main.py
```

```python
VERSION = "0.1.0"

def execute(recipe):
    result = recipe.session.exec_command(["id", "-un"], check=True)
    return {
        "status": "success", "reason_code": "identity_observed",
        "message": "Observed the connection account.",
        "data": {"account": result.stdout.strip()},
    }
```

See the complete bundled [check/identity example](../recipes/check/identity/README.md). Runner validates static signature/version/inputs without importing recipes during discovery, creates one Recipe per host execution over its existing connection, invalidates the scope on return/error, and closes the connection. Outputs use the same strict result fields/statuses as python-session. Raw files additionally record installation identity, selected profile (or null for an unregistered root), run ID and privilege evidence. Cleanup failure overrides claimed success. Generic results retain explicit no_retention_adapter; no inventory identity/sudo preflight is added.

Existing python-session 0.1.0 `execute(session, *, context, timeout)`, python-report and inventory contracts remain unchanged. Migrate deliberately by changing the declared contract and entrypoint together; no signature guessing or automatic conversion. New recipes receive Recipe; legacy context does not suddenly acquire root/config/service fields.

## Errors, versions and verification

Catch ConfigError for invalid configuration/inputs and CoreError for Core lifecycle/policy failures (stable `.code`). Transport/authentication, command, filesystem and storage errors may propagate from existing owners; do not log exception text containing arbitrary secrets. Runner stores safe error type/stage only. Notable codes: identity_verification_failed, host_disabled, session_not_owned, session_scope_unavailable, sudo_disabled, missing_su_password, identity_restoration_failed, session_cleanup_failed.

API and identity schema are 0.1.0; recipe runner contract is separately python-recipe 0.1.0, descriptor 0.3.0, and product version remains VERSION. Additive compatibility is preferred; incompatible behavior requires a new declared contract and migration guidance. Core currently supports POSIX controllers; native Windows controller locking is unsupported.

Public tests cover temporary identities/configuration, copies/moves, isolation, concurrency, synthetic local/jump transports, privileged identity/credential/restoration cases, runner/static discovery and wheel/sdist boundaries. Native SSH/su/sudo validation is separate; synthetic identity probes do not establish PAM, sudo policy or every platform's behavior. SSHScript source is the bundled public documentation contract 5.0.0 with provenance/digest in skills/sshscript/SOURCE.json; this feature does not update that upstream snapshot.

Delivery verification (2026-10-15): 456 tests passed on each of Python 3.11.15, 3.13.13 and 3.14.4, including headless Textual checks. Older interpreters reused the selected environment's pure-Python dependencies; these runs do not establish native SSHScript dependency readiness. Matching SSHScript 5.0.0 and credential-free local Core/identity execution were verified on 3.14. Wheel build, pip installation into a temporary target, import/session use outside the checkout, public resource inspection, skill validation and changed-document checks passed. Native SSH/su/sudo remain unverified. An existing TUI regression test now waits for deferred refresh completion instead of fixed short sleeps.

## SSH authentication source policy

Profile sessions and Recipe execution reuse the shared connection planner without a
new import or method. Configure connection.allow_agent/connection.look_for_keys in
hosts.yaml; both default false per hop, including aliases. See [canonical examples
and interpretation](hosts-yaml.md#ssh-authentication-sources). Explicit passwords and
keys remain usable. Missing all sources raises ConfigError during planning before
session creation; diagnostic/runner reports include missing_authentication_source
and a safe hint. Static configuration loading alone does not establish usable credentials.
This intentionally changes ambient-key-dependent configurations; see [migration](migration.md#explicit-ssh-authentication-sources).

## Host group catalog

`profile.hosts.groups()` returns a deep-copied catalog keyed by group ID, including
explicit and implicit groups. Every value has label, description, icon (declared
host/user defaults only), and hosts (a unique ordered list of member IDs). It contains
no nested host credentials. Like hosts.list/get, it reads the profile's current
snapshot; reload updates both atomically and a failed reload preserves both.
`profile.inspect()` freshly returns groups alongside masked hosts without replacing
the execution snapshot. No connections or writes occur.

```python
from opsfeast import Instance

profile = Instance.open("/srv/opsfeast").profile("main")
for group_id, group in profile.hosts.groups().items():
    print(group_id, group["label"], group["description"], group["hosts"])
```

Use the public method instead of reconstructing membership or parsing nested YAML.
Bulk hosts work with existing hosts.get, sessions.connect and profile.recipe by host
ID; no alternate execution API is needed. See [configuration, ordering, validation
and migration](hosts-yaml.md#host-groups). Metadata is user-authored display text,
not identity or authorization evidence.

## Authentication principal and execution shell

Core connection reports record the successful final-hop login_identity, including
aliases. On first privilege validation the shared connection identity model can accept
an ordinary ESXi login with a verified UID 0 shell; report shell_identity and
identity_model explain that relationship. Policy/credential lookup uses the original
login for the unprivileged facade, while nested privileged scopes use their actual
actor. Restoration compares shell identities. Explicit su/sudo targets remain strict,
and recipe.sudo still enforces that actor's sudo policy even when already root.
ESXi authenticated-console support is not added. Existing profile.recipe/session calls
need no new arguments. See [rules, fields and evidence](host-diagnostics.md#ssh-login-and-esxi-root-shell-identity).

_Last modified: 2026-10-16_
