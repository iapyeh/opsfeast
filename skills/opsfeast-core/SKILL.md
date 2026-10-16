---
name: opsfeast-core
description: Use the bundled OpsFeast Python API for installation identity, profiles, runtime hosts loading, scoped sessions and Recipe su/sudo, or read-only instance inspection. Use for standalone agent programs and python-recipe authoring; logging and notification services remain unavailable.
---

# Operate and compose OpsFeast Core

Terminal summaries now use tabulate when stdout is a TTY. For agents, explicitly add `--json` to supported diagnostic, instance, profile/check, recipe/job execution and utility commands; non-TTY output retains existing contracts. Dump/raw results/artifacts/exports remain structured. Check-access retains its existing default table. Read [the command-specific output policy](../../docs/cli.md#terminal-tables-and-json); flags change presentation only, not authorization or saved-job inputs.

After every OpsFeast release update, reread the installed release's current object schemas/data contracts, including hosts.yaml, before resuming work, regardless of diffs or earlier reading. Follow the [mandatory release reading list](../../docs/skill-updates.md#required-schema-reread-after-a-release-update). No reading receipt or completion verification is required.

Read the [Core API contract and examples](../../docs/core-api.md) for exact signatures, installation, lifecycle, storage, errors and verification limits. API/identity schema 0.1.0, python-recipe runner 0.1.0, descriptor 0.3.0; Python 3.11+, PyYAML 6.0.3, and matching SSHScript 5.0.0 only for execution. Use the selected interpreter and trusted installation; do not install/upgrade solely to inspect.

## Identify the instance and scope

An instance is an installation/checkout, not feasts/ or an individual management root. Open with `Instance.open(installation=...)`; inspect and select its active or explicit profile. Selection is fixed for an operation even if another process switches active profile. Multiple installations/profiles may coexist in a program; never change a process-global default to select one.

A new clone or copy into another directory must receive a new UUID. Use explicit initialization on that copy, never relocate its identity. Copy detection uses the recorded resolved path; same-path copies on another machine require explicit renewal. Only an actual move of the original installation uses relocate_identity to preserve UUID. The UUID ending in 000000000001 is reserved for the original development installation; it must not propagate to copies. Missing UUID uses the standard all-zero placeholder, with inspection exposing placeholder/reason; the user accepts duplicate-identity risk. Name is required/default UUID and description optional; names are not unique or authentication evidence. Assigned identity persists through normal init/profile changes. Do not rewrite identity during a read-only handover.

## Reuse configuration and sessions

Effective hosts and declared users include resolved icon fields (built-ins 🍎/👤). Entry hosts.yaml supports global default.icon.host/user. Entry and included YAML support per-group groups.<name>.icon.host/user. Explicit host/account icons override defaults; default.users.<account>.icon then precedes group user defaults. Each remaining field independently takes the first defined value in host group order, then the global default. Include files inherit defaults; explicit values must be one Unicode Symbol code point, not a multi-code-point glyph. Optional default.users.<account>.email stays in source metadata and is not merged into host-account snapshots. This is display-only and does not rewrite YAML; see [icon rules](../../docs/hosts-yaml.md#host-icon).

Use profile.hosts.list/get and explicit reload rather than another YAML parser or frozen addresses/credentials. Reads are masked copies; reveal_secrets=True is explicit and must never enter logs/shared examples. Masking is key-based and cannot sanitize arbitrary strings. A profile/connection uses a validated snapshot; fresh inspection does not replace that execution snapshot.

Use `with profile.recipe(host_id, vars=..., timeout=...) as recipe` for standalone operation logic; sessions.connect is the narrower connection entry. For runner recipes declare python-recipe 0.1.0 and define execute(recipe). Reuse the supplied Recipe, do not reconnect or close borrowed sessions. The [complete identity recipe](../../recipes/check/identity/README.md) is a minimal template. Legacy python-session recipes keep execute(session, *, context, timeout); migrate explicitly.

Use recipe.session.exec_command(argv) or start(argv), read actual CommandResult/job states, and finish/stop owned jobs within scope. For privilege use `with recipe.sudo(user="root") as privileged` or `with recipe.su("declared-user") as privileged`, then privileged.session. Parent commands are unavailable while a nested scope is active. No host-init/privilege probe happens just by connecting. Read [SSHScript skill](../sshscript/SKILL.md), its Agent Guide and relevant API sections before command/job automation; Core's facade exposes only the documented subset.

Credentials follow existing account policy with one selected source, no retry; su requires a declared target and credential. Verify authorized target/privilege scope before entry. Failed identity restoration disables the execution; preserve cleanup evidence and do not catch the error to claim success. Core is not a Python sandbox or approval enforcement mechanism.

## Inspect and perform explicit local operations

Instance/profile inspection reads local metadata/configuration/paths and dependency versions, never creates identity, connects, repairs or dispatches. Inspect success/partial, component errors, placeholder identity and available/configuration states separately. Dependency metadata is not runtime/native readiness. Reuse profile.results/jobs and existing artifact verification rather than scanning guessed filenames. Missing service paths are not implemented services: logging and notification remain deferred.

Metadata init/update/renew/relocate, profile init/attach/use/detach are explicit writes with their own scope. Preserve existing roots/data and human notes. This API does not edit hosts YAML or delete history. Public configuration/inspection methods do not authorize host operations. Catch ConfigError/CoreError at the boundary, preserve stable reason codes and safe error types, and avoid arbitrary exception/settings output.

## Select explicit SSH authentication sources

Read [the canonical authentication policy and examples](../../docs/hosts-yaml.md#ssh-authentication-sources)
before configuring or executing SSH hosts. connection.allow_agent and
connection.look_for_keys are strict Booleans, both default false on every hop,
including SSH config aliases; they are not allowed on local/reference objects.
Preserve the user's intended sources: explicit login passwords/identity files
remain usable, agent or default-key discovery requires an explicit true.
Do not infer flags from password presence or bypass the shared planner in a recipe.
Inline hops are independent; referenced hops use the referenced host's settings.

Use check for local type validation. Missing all sources after alias/account resolution
fails before that target chain opens any Session, with missing_authentication_source
and a safe hint; check alone cannot confirm usable credentials. For an authorized
connection test use test-connection HOST --json --debug to inspect effective flags
and results without printing secrets. Configuration changes do not authorize probes.
See [migration](../../docs/migration.md#explicit-ssh-authentication-sources) before
resuming configurations that relied on ambient keys. Policy tests are synthetic;
real SSH/agent authentication requires separate authorized evidence.

## Group catalog and bulk host definitions

Read [the canonical group schema and example](../../docs/hosts-yaml.md#host-groups).
Use top-level groups.<id> for optional label (default ID), description (default empty
string), icon.host/user and hosts. Bulk hosts use the ordinary host schema and enter
the same effective host map; the enclosing group is prepended and memberships are
deduplicated. First membership is primary. Keep host IDs globally unique and explicit
group definitions unique across includes; use membership to share hosts across groups.
Labels never substitute for IDs in selectors. Missing group definitions get default
metadata. Defaults/icon resolution happens after all includes, with existing named-user
and explicit host/account precedence. No connection/vars/recipe inheritance is added.

Prefer `profile.hosts.groups()` for a copied runtime catalog, existing hosts.get and
session/recipe methods for bulk hosts, and check / dump groups for local inspection.
Catalog hosts are member ID lists, not nested raw host mappings. Inspect can show a
fresh catalog without changing the execution snapshot; reload explicitly. See [Core
examples](../../docs/core-api.md#host-group-catalog). The TUI shows labels plus IDs and
read-only group descriptions/member IDs, including empty groups. Group rows do not
start host actions. Old default.groups fails with a migration hint; follow [migration](../../docs/migration.md#group-catalog-and-bulk-host-definitions)
without silently rewriting private configuration. Preserve source-relative paths,
notes, authorization and skipped/failure states. Tests are synthetic; no SSH/privilege
behavior follows from group parsing or display.

## ESXi SSH-exec identity evidence

Read [the shared ESXi diagnosis workflow](../../docs/host-diagnostics.md#diagnose-esxi-identity-failures)
when SSH succeeds but identity fails. The adapter handles exit 127 and the narrowly
recognized exit 2 / empty stdout / shell missing-id stderr form only after verifying
VMkernel; do not broaden it to arbitrary failures. Inspect identity_probe.id_exitcode,
identity_error.reason_code and configured_identity_probe.actual/expected/matched.
access.actual_identity records the observed shell actor even when account comparison
fails; connection_identity is not verified in that case. The ESXi connection-level root-shell model can accept different numeric UIDs with a known successful final-hop SSH login, verified VMkernel and consistently observed UID 0. Keep both identities and the acceptance rule visible; other platform and privilege-target mismatches remain failures. Do not rewrite private bindings to root. Existing authorized
check-access --host HOST --root ROOT --json --quiet is the reusable CLI; Core and runner
use the same probe without new APIs/configuration. No raw command output is retained.
Native two-hop evidence covers a root missing-id exit 2 path and an ordinary login accepted with an effective root shell; other ESXi/privilege scenarios remain outside this evidence. These diagnostics do not
change retained inventory schemas.

## Distinguish SSH login from an ESXi root shell

Read [the canonical identity model and JSON example](../../docs/host-diagnostics.md#ssh-login-and-esxi-root-shell-identity).
Reuse the shared CLI/Core/runner verifier: login_identity comes from the successful
final-hop connection; shell_identity is the observed execution account. Verified
VMkernel and a stable UID 0 shell may accept an ordinary account as esxi_root_shell.
Numeric matched=false is then accepted with status=success and accepted_by explaining
the policy; do not relabel it as failed or silently change hosts.yaml to root.
Account policies, credential selection and extra-user exclusion use the SSH login;
restoration uses the original shell. Explicit privilege targets, other kernels,
non-root mismatches and unknown-principal cases remain strict. No configuration
bypass or new invocation is added. check-access --host HOST --root ROOT --json --quiet
returns the full evidence within an authorized host scope. Human tables explain the
root shell and show sudo already_root. Native evidence covers the two tested two-hop
paths; additional ESXi releases, role assignments and su/sudo remain unverified.

_Last modified: 2026-10-16_
