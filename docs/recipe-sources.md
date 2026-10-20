# Recipe sources, inputs and execution controls

Operational execution selects one explicit recipe reference and host targets; it does not execute every configured recipe. Configuration, source registration, code review, installation and execution are separate scopes. Use [execution](recipe-execution.md) and the [CLI reference](cli.md#operational-recipe-execution) for commands, outputs and authorization.

## Register sources at the entrypoint

Only the management root's `hosts.yaml` may register `recipe_sources`; included files can reference registered sources. External entries accept a local `path`, Boolean `enabled` (default true) and `vars` mapping. Relative paths resolve from the entry file; absolute paths and `~` are accepted. Registration downloads nothing and does not validate publisher trust. A referenced enabled source must exist.

```yaml
recipe_sources:
  bundle: {enabled: true}
  profile: {enabled: true}
  community:
    path: /srv/reviewed-recipes
    enabled: true
    vars: {command_timeout_seconds: 15}
```

`bundle` and `profile` have fixed roots. Their optional `path` asserts that same resolved root; it cannot redirect it, even when disabled. Named-source registration does not widen include/output boundaries. Descriptors remain within their source after symlink resolution; executable recipe entrypoints/helpers remain within their individual recipe. These checks are not a Python sandbox.

## Reference forms

| Reference | Root |
| --- | --- |
| `system/inventory/overview` | OpsFeast bundle's `recipes/` |
| `bundle:system/inventory/overview` | Same bundled recipe; canonicalized to the bare reference |
| `:system/inventory/overview` | Selected profile's `recipes/` |
| `community:system/inventory/overview` | Registered community root |

References preserve the filesystem directory path, including hyphens; there is no conversion to a flattened ID. Discover exact references with `recipes list --profile main --json` or `recipes show REFERENCE --profile main --json`. Descriptor IDs, such as `inventory-system`, remain metadata and are not mapping keys unless that exact directory exists. Catalog CLI selection can resolve an unambiguous ID; configuration always uses exact references.

A bare reference always means bundle, even when a profile/external copy has the same path. Quote keys starting with `:`. Unknown source names, path escapes, absolute mapping keys and globs in mapping keys fail; no source fallback occurs. `bundle:PATH` and `PATH` normalize before inheritance. Using both within one layer is an error; using one in default and the other in host overrides the same recipe. `profile:PATH` is not an alias for `:PATH`. Init does not copy recipes or create the optional profile recipes directory.

## Three configuration layers

Use `recipes` as a direct mapping from reference to `enabled` and/or `vars` at `default`, group and host levels:

```yaml
default:
  recipes:
    system/inventory/overview:
      enabled: true
      vars:
        attention:
          enabled: true
          thresholds:
            filesystem_used_percent: {warning: 80, critical: 85}
            cpu_utilization_percent: {warning: 90, critical: 95}
            memory_available_percent: {warning: 10, critical: 5}
            load_5m_per_cpu: {warning: 1, critical: 2}
groups:
  production:
    recipes:
      bundle:system/inventory/overview:
        vars:
          attention:
            thresholds:
              filesystem_used_percent: {warning: 70}
      system/network/check/port:
        enabled: true
        vars: {port: 443}
    hosts:
      web-01:
        connection: {hostname: web-01.example}
        recipes:
          system/inventory/overview:
            vars:
              attention:
                thresholds:
                  filesystem_used_percent: {warning: 65, critical: 70}
          system/network/check/port:
            enabled: false
      web-02:
        connection: {hostname: web-02.example}
```

Precedence is **host > first resolved group > later groups > default > internal defaults**. Groups are the ordered `group` memberships; a host nested in `groups.NAME.hosts` has NAME prepended as its primary membership. Overlapping leaves from the first group win, while other leaves from later groups remain available. Nested mappings merge by field, lists replace the complete inherited list, and scalars/Booleans replace the inherited value. Explicit false is not absence. Each resolved value is copied independently for concurrent hosts.

Every recipe defaults to `enabled: false`. A newly generated hosts.yaml explicitly enables `system/inventory/overview` under `default.recipes`; existing files are preserved and need their own opt-in before bulk execution. `enabled` controls execution, not historical retention or visibility. Removing/disabling a recipe does not remove its data or current page. Inventory `vars.attention.enabled` independently controls threshold evaluation; see [Attention rules](inventory-jobs.md#attention-thresholds).

`check` validates all mapping references, including disabled entries and settings in unused groups: missing source/recipe files are errors. It checks declared input names and basic types/bounds without running recipe code. Effective required inputs and recipe-specific business rules are validated before execution by the input preparer and recipe owner. Unrelated invalid reference settings are not expanded by a CLI invocation selecting a different recipe. An unavailable selected recipe fails preflight for that target; batches retain explicit failure evidence and continue other hosts. No unavailable code is executed.

### Existing selection lists

Existing host selection lists remain readable for static selection and first-matching input overrides. Strings and mappings with exactly one `recipe`, `directory` or `glob` are supported; `directory` alone may add `recursive`. Legacy YAML `recipes/PATH` denotes bundle content; CLI rejects that prefix. Legacy `./recipes/PATH` is instance-relative; new settings should use `:PATH`. These list forms do not opt a recipe into bulk execution: use a direct mapping, or enable its exact reference in default/group settings. A CLI invocation still executes one explicitly selected recipe.

Directory/glob matches sort by source-relative path. Repeated physical directories retain their first selection/vars. Duplicate descriptor IDs in different directories within one source fail static selection; identical IDs across different sources remain distinct. Do not use globs or selector objects in the new reference mapping.

## Variables and implementation context

Preparation merges recipe input defaults → source vars → resolved default/group/host recipe vars → invocation vars. Nested mappings merge, lists/scalars replace, and each execution gets a deep copy. Within invocation inputs, `--var NAME=...` replaces that variable from `--vars-file` before preparation; it does not merge with that file's same variable. CLI inputs never rewrite hosts.yaml. Host/account `vars`, environment variables and shell interpolation are not implicitly recipe inputs.

A recipe owns its accepted variables and validates business rules. Declare names/types under `inputs.variables`:

```yaml
inputs:
  variables:
    command_timeout_seconds: {type: number, minimum: 0, exclusive_minimum: true}
    label: {type: string, required: true}
    options: {type: object, default: {mode: basic}}
```

Supported types are string, integer, number, boolean, object and array; optional definition fields are required, default, minimum/maximum and exclusive_minimum. Null satisfies none. Undeclared keys, wrong types, nonfinite values, recursive YAML aliases and missing effective required values fail before a Session/code load for that host. Shared source vars must be recognized by the selected recipe. See [literal strings and JSON inputs](recipe-execution.md#select-a-recipe-and-provide-inputs).

New Core recipes read `recipe.vars`; Python-session recipes read `context.vars` with `context.host_id`. Inventory jobs use the [job collector](inventory-jobs.md), not the removed snapshot execution interface. Result provenance records variable names, not arbitrary effective values. Inventory intentionally snapshots its validated nonsecret Attention policy in raw/run evidence. Recipe authors must keep passwords and other secrets out of their own logging/results.

## Enabled flags and explicit targets

| Selection | Execution rule |
| --- | --- |
| `recipes run ... --all` or `--group` | Host, source and resolved recipe must all be enabled |
| Scheduled inventory | Same three gates, plus explicit inventory.yaml host/job opt-in and due time |
| `recipes run ... --host HOST` or single-host inventory query/run | Explicit target overrides those three enabled gates for that target |

A host appearing through both explicit host and group selection uses the explicit rule. This override does not permit an unknown recipe, invalid vars, path escape or disabled jump host; it does not change configuration on disk. A disabled host cannot be a jump host, even when it is also a requested target. Standalone Core sessions and host diagnostic commands retain their own controls; the override describes recipe/inventory execution only. Offline report recipes have no host-target policy to merge.

Bulk source/recipe skips use `source_disabled`/`recipe_disabled`, with no raw result path. Disabled group/all hosts appear in `excluded_hosts` and in a persisted batch's target outcomes. An all-disabled selection can produce a successful journaled batch containing only skipped targets; success then means completion of that selection, not collection. Selected source/recipe skips make `recipes run` exit nonzero; omitted disabled hosts do not fail other successful targets. See [batch evidence](observation-runs.md), including partial, failed and interrupted states.

## Exclude hosts for one invocation

```sh
python -B tools/opsfeast.py recipes run system/inventory/overview --all --exclude host9 host10
```

`--exclude` requires `--all` and exact known host IDs. It affects targets only: an excluded enabled host may still be a jump host. CLI exclusions appear as `cli_excluded` and are not persisted as selected batch members. Unknown exclusions and an entirely CLI-excluded selection fail before execution. Configured host/source/recipe flags are not rewritten.

## Verification and compatibility

Synthetic tests cover reference normalization, duplicate detection, deep inheritance/list replacement, input isolation, explicit/bulk gates, disabled jumps and durable batch outcomes. These tests do not establish third-party safety, native SSH or privilege-policy behavior. Existing bulk workflows must explicitly enable recipes; existing nested object overrides now merge rather than discard inherited siblings. Update private settings deliberately, preserve retained data, and use [migration notes](migration.md#recipe-policy-and-observation-runs) before rerunning authorized work.

_Last modified: 2026-10-20 23:06:43_
