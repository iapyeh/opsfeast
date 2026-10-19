# Recipe sources, inputs and execution controls

Recipe paths support more than two levels; follow [classification and location](recipe-taxonomy.md). Current bundle selectors include system/network/check/port and system/inventory/overview. Prefix the complete classified path with : for the selected profile or NAME: for a registered external source. Moving the bundle does not move an existing profile/external copy. Old bundle paths are removed; exact historical retention references remain unchanged.

OpsFeast resolves recipes from the checkout, the selected profile, or explicitly registered local source directories. Registration, configuration checking, installation/update and execution are separate operations. Registering a clone does not authenticate it, install its dependencies, update Git or authorize its code to execute.

Use the [CLI reference](cli.md#toolsrun_recipepy-inventory-execution) for the runner. It requires one explicit inventory-system or compatible Python-session recipe and explicit targets; it does not execute a host's whole recipes list or arbitrary incompatible programs. Read [general execution](recipe-execution.md) for descriptor 0.3.0, the execute contract and raw results. Host lists define configuration selections and per-recipe input overrides. A CLI recipe bypasses unrelated selectors, but uses the first matching selector's vars.

## Register sources at the entrypoint

Only the management root's hosts.yaml may declare recipe_sources. Included YAML files may reference those sources but cannot register, replace or extend them.

```yaml
recipe_sources:
  bundle:
    enabled: true
  profile:
    enabled: true
  community:
    path: ~/Download/recipes
    enabled: true
    vars:
      command_timeout_seconds: 15
  company:
    path: /opt/company-recipes
    enabled: false

hosts:
  host1:
    enabled: true
    connection: {hostname: host1.example}
    group: web
    recipes:
      - system/inventory/overview
      - ":system/inventory/overview"
      - recipe: community:system/inventory/overview
        vars:
          command_timeout_seconds: 10
```

External source entries accept path (required), enabled (boolean, default true) and vars (mapping, default empty). The predefined bundle and profile entries accept enabled/vars and an optional path assertion. Their roots are fixed: a supplied path must resolve to the same default root, including symlink normalization; a different path is rejected even when enabled is false. Relative assertions use the entry hosts.yaml directory, exactly like external source paths. Omitted entries default to enabled with empty vars. These configuration keys do not add bundle:/profile: recipe aliases: use bare names and :names respectively. External names match `[A-Za-z][A-Za-z0-9_-]*`; bundle/profile are predefined configuration keys and repository is reserved for provenance. Path is local: absolute paths and `~` are accepted; relative paths resolve from the entry hosts.yaml directory. No URLs, implicit Git downloads or dependency installation are supported. An enabled source directory must exist when referenced. An unused registration is not proof that its directory or recipes are valid.

## Reference forms

| Reference | Root |
| --- | --- |
| system/inventory/overview | This OpsFeast checkout's recipes/ |
| :system/inventory/overview | The selected management/profile root's recipes/ |
| community:system/inventory/overview | The registered community path |
| recipes/system/inventory/overview | Legacy YAML spelling for checkout content; CLI rejects the recipes/ prefix |
| ./recipes/custom-system | Legacy instance-relative form; YAML uses its declaring file directory, CLI uses the management root |

Quote a YAML reference starting with `:` for clarity. A qualified reference requires a nonempty relative path; absolute paths, unknown source names and escapes are errors. There is no fallback to another source. Neither `:` nor named-source paths depend on where an included YAML file lives. Init does not copy checkout recipes or automatically create the optional profile recipes directory.

A recipes item can be a string for one recipe or a mapping with exactly one of recipe/directory/glob. Mapping forms may add vars; recursive is a boolean for directory only.

```yaml
recipes:
  - community:system/inventory/overview
  - directory: community:system/inventory
    recursive: true
    vars: {command_timeout_seconds: 10}
  - glob: company:inventory/*
```

Directory/glob expansion uses the selected source root and the existing wildcard rules. A selector with no matching active recipes is an error. Matches sort by source-relative path. Selecting the same physical directory repeatedly retains its first occurrence, including its vars. Different sources may declare the same recipe ID; duplicate IDs in different directories within one source are errors. There is no implicit preference between sources or search by recipe ID.

Recipe descriptors and selected paths must remain in the chosen source after resolving symlinks. Supported recipe entrypoints and Python helpers additionally remain inside their individual recipe directory. Include and output paths remain confined to the management root; external source registration does not widen those boundaries. These path checks are not a general execution sandbox: reviewed custom code still executes in the controller process.

## Variables and implementation context

Variable precedence is recipe input defaults → source vars → matching host recipe vars → invocation --vars-file → invocation --var. CLI overrides do not rewrite configuration. See [CLI input parsing](recipe-execution.md#select-a-recipe-and-provide-inputs) for literal strings, JSON types, duplicates and input-file paths. Overrides replace whole first-level values; nested mappings are not deep-merged. Each execution gets an independent deep copy, so concurrent hosts cannot share mutations. Host vars, account vars, environment variables and shell interpolation are not automatically involved.

A recipe declares accepted variables under inputs.variables in recipe.yaml:

```yaml
inputs:
  variables:
    command_timeout_seconds:
      type: number
      minimum: 0
      exclusive_minimum: true
    label:
      type: string
      required: true
    options:
      type: object
      default: {mode: basic}
```

Supported types are string, integer, number, boolean, object and array. A definition accepts type (required), required (boolean), default, minimum/maximum for numbers, and exclusive_minimum (boolean). Missing required variables, wrong types, out-of-range values and undeclared supplied keys fail before creating a Session for that host. Null does not satisfy any supported type. Values must be basic finite YAML/JSON-like data, without recursive aliases or dates. Sources containing different recipes must use inputs recognized by each selected recipe; source vars do not guarantee that every recipe understands them.

General Python-session recipes use execute(session, *, context, timeout), with the same isolated context.vars; see [the execution contract](recipe-execution.md). Inventory implementations with vars must accept a context keyword:

```python
def collect(session, report, timeout, facts, *, context=None):
    command_timeout = context.vars.get("command_timeout_seconds", timeout)
    # Pass context explicitly to helpers that need the same inputs.
```

The context contains host_id and vars. Legacy four-argument collectors remain usable when no effective vars are supplied. Static preflight checks context support before executing custom code. Context is not injected into Python process globals or the OS environment. The bundled inventory implementations support command_timeout_seconds for collection only; the CLI --timeout still controls connection stages and host discovery.

Completed reports record source name/root, reference, resolved recipe location, recipe/implementation versions, descriptor SHA-256 and code digests. They record variable names, not effective values. Recipe authors must also avoid exposing sensitive inputs in command output, exceptions or their own result fields; the runner cannot conceal arbitrary custom logging.

## Disable a source or host

Predefined sources can be controlled without a path:

```yaml
recipe_sources:
  bundle:
    enabled: false
  profile:
    enabled: false
```

Bundle controls bare checkout references and legacy checkout YAML/absolute paths. Profile controls :references and legacy management-root relative/absolute forms. Disabling either leaves external named sources independent. Both accept vars with the same recipe-default → source → matching-host precedence. They cannot redirect their fixed roots. For entry hosts.yaml in checkout/feasts/main/, optional path confirmations would be bundle.path: ../../recipes and profile.path: ./recipes, not checkout-relative recipes/ and feasts/main/recipes/. Absolute paths are also accepted when they resolve to the defaults. Omitting path is the simplest portable form.

Setting a source enabled: false skips its references with source_disabled. Check validates its fields and selector structure but does not require the source directory/recipe to exist or read its descriptor. Unknown sources remain errors. No fallback occurs.

Host enabled defaults to true. With enabled: false, --all and --group omit that host and list host_disabled in excluded_hosts. Explicit --host HOST produces a skipped host_disabled result. Disabled hosts cannot participate in connection plans, including as jump hosts. Configuration structure, references and cycles remain checked; disabled host recipes do not require their files to exist.

Source/host skips occur before runtime loading or connections and return result_path: null; no inventory file is fabricated. The CLI reports skipped status and returns 1, because no successful inventory was collected. By contrast, hosts omitted from a selection are not attempted inventories; remaining successful targets may return 0 while exclusions remain visible. Session cleanup failure is distinct from these configuration skips.

## Exclude hosts for one invocation

```sh
python -B tools/run_recipe.py system/inventory/overview --all --exclude host9 host10
```

--exclude requires --all and accepts exact configured host IDs, without group guessing or wildcard expansion. Unknown excluded IDs fail before execution. Disabled hosts are filtered first; CLI exclusions then remove enabled targets. Repeated names do not duplicate entries, and settings are not rewritten. excluded_hosts lists host_disabled or cli_excluded reasons. If no target remains, the CLI returns 1, prints an empty hosts list and exclusion evidence, and reports the empty selection on stderr.

Exclusion removes collection targets only. An excluded enabled host may still be used as another target's jump host; enabled: false disables its participation entirely.

## Review and verification

Use check to validate configuration/selection without executing code. To inspect an external candidate, pass its resolved absolute recipe directory to inspect-recipe; that command currently does not resolve named-source references or profile shorthand. Review complete code, helpers and dependencies before executing it. Source paths and digests do not establish publisher trust.

Synthetic tests cover sources, include restrictions, path/symlink boundaries, scalar/mapping selection, input precedence/types/isolation, disable/exclude behavior and inventory collection through mocked Sessions. Real SSH, native privilege transitions and third-party recipe behavior remain unverified.

_Last modified: 2026-10-19 15:24:36_
