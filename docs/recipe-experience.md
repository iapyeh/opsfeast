# Find, run and reuse recipes and reports

Inventory recipe 0.4.0 additionally supplies [internal collection jobs and a minute dispatcher](inventory-jobs.md). These are separate from the saved recipe invocation jobs in this guide. `inventory query` can run without records or save explicit comparison samples; scheduled inventory hosts are opt-in, failures wait until the normal interval, and no AI is called for routine ticks. A general multi-recipe scheduler remains unimplemented.


`tools/opsfeast.py recipes` is a common command surface for humans, agents and the Textual workbench. It provides catalog 0.1.0, parameterized operation/report execution, raw-result lookup, simple HTML exports, artifact verification, explicit-file bundles and saved invocations. These functions run as ordinary Python code without model inference. Use [the recipe skill](../skills/opsfeast-recipes/SKILL.md), [CLI reference](cli.md) and [shared principles](vision.md#accumulate-reusable-reports-and-keep-visualization-flexible).

Read [recipe attribution and installation defaults](recipe-attribution.md) for author name/contacts, declared license, Unknown placeholders and reserved Bundle policy. Before creating a user recipe, copy `python -B tools/recipe_identity.py defaults` into its descriptor. MIT pack allowlists include LICENSE; external unpack rejects Bundle before creating a candidate.

For retention-backed content use [the data/content guide](retention.md#content-authors-and-offline-reports) and bundled feast/report/retention-summary. ReportContext supplies retention.query/show and explicit batch readers retention.runs()/run(run_id) alongside vars, inputs and artifact_dir; see [run data](observation-runs.md). Reports record retention_sources with selections, source IDs/times and digests. Read-only queries need no raw files or host selection; renderer dependencies and authorization still apply.

## Interactive recipes workbench

Run `python -B tools/opsfeast.py recipes` without a subcommand to open the Textual workbench. Explicit subcommands remain CLI. The workbench offers the shared catalog, execution, results/artifacts, saved jobs and bundle operations, starts with read-only checkout discovery, and reviews execution/write arguments before confirmation. Read [terminal display](terminal-ui.md#recipes-workbench-entrypoint) for optional dependencies, form formats, environment selection, exit codes and limits.

## Discovery and selection

```sh
python -B tools/opsfeast.py recipes list --checkout-only
python -B tools/opsfeast.py recipes list --root /path/to/feast --json
python -B tools/opsfeast.py recipes list --profile main --query port --kind operation
python -B tools/opsfeast.py recipes show feast/report/execution-summary --profile main --json
python -B tools/opsfeast.py recipes list --profile main --html /path/to/new-catalog.html
```

Catalog/show/pack can use --checkout-only on a fresh clone without reading a Feast. Otherwise specify --root/--profile or use the selected profile. These three environment choices are mutually exclusive. Other recipe commands require a Feast except unpack, which only reads a selected archive and creates a candidate. Python 3.11+ and PyYAML are needed; offline reports and metadata commands do not import or require SSHScript. Initialization dependency scope expects PyYAML 6.0.3; operation execution retains its SSHScript 5.0.0 requirement. Inspect actual prerequisites with check_environment.py and the selected recipe's dependencies; do not install or upgrade automatically.

Catalog reads source registrations from entry hosts.yaml and lists checkout (repository), Feast recipes/ (profile) and named external sources. Reference syntax is shared with opsfeast.py recipes run: bare path, :path and source:path. No symlink escape from a source is allowed. An optional absent profile recipes/ directory is normal; missing external roots are unavailable. Disabled sources are reported but their contents are not read. Inspection parses descriptors, versions and entrypoint signatures without importing recipe code, host discovery or connections; it does not check passwords, target dependencies or data applicability.

JSON `catalog_version: 0.1.0` contains sources (name/root/enabled/status/errors) and recipes (reference/source/directory/id/version/title/description/kind/contract/status/errors/runnable/inputs/dependencies/verification/descriptor/availability_evidence). runnable means static contract compatibility only. Inputs and dependencies remain visible for human/agent decisions. One malformed recipe/source does not hide other entries; list returns 1 with error evidence when any scanned source/recipe fails. Query/kind filters do not convert overall failed discovery into success. Empty matching lists are valid. Duplicate IDs within one source are invalid; equal IDs across sources remain distinct. Selection prefers an exact reference; a unique ID may also be used, but ambiguous IDs fail with a request for an explicit reference. No implicit source fallback occurs.

Terminal catalog/show/index/jobs/execution views use tabulate tables; non-TTY output keeps its previous format. Use --json explicitly for automation, including recipes run and jobs commands. The display flag is not persisted in saved jobs. See [console output policy](cli.md#terminal-tables-and-json). Text output is concise. --json exposes the complete data contract; --html writes a basic escaped static table to a new file. HTML exports never overwrite existing files, execute scripts, connect or launch a viewer; open them with the user's preferred tool. More sophisticated agent-generated views can consume the same catalog without changing its contracts.

## Execute a selected recipe

```sh
python -B tools/opsfeast.py recipes run system/network/check/port --root /path/to/feast --host rms3 --var port=8888
python -B tools/opsfeast.py recipes run system/inventory/overview --profile main --group web --threads 2
python -B tools/opsfeast.py recipes run feast/report/execution-summary --profile main --input /path/to/raw-result.json
```

Operational recipes use the existing [opsfeast.py recipes run interface](recipe-execution.md), including host/group/all/exclude selection, typed --var/--vars-file, timeout, progress, source/host overrides, concurrency and cleanup. The facade calls the same execution implementation. Use the selected recipe's operations and input interpretation, not CLI exit status alone, to assess service health. No target/source selection grants execution scope.

Offline reports use runner.contract python-report 0.1.0 and do not accept host/group/all/exclude/threads. Operational recipes reject --input. Report parameters follow defaults → source → vars-file → --var, without host override. Each --input selects one explicit readable UTF-8 JSON object; repeat it for multiple datasets. File paths use shell-relative/home semantics and may be outside the Feast because they are explicit selections. Duplicate JSON keys/non-finite values and invalid inputs fail before report code is loaded; type/range checks follow [declared input rules](recipe-sources.md). Report recipes decide which data contracts they support. Files are loaded once and their exact bytes are hashed; outputs record names/digests, not absolute input paths. The private job definition may retain those paths.

## Offline report contract

Descriptor 0.3.0 accepts runner `{contract: python-report, version: 0.1.0, entrypoint: main.py}`. Other validation rules are shared with [Python-session recipes](recipe-execution.md#descriptor-030-and-python-session-010): literal VERSION must match recipe version, declared input definitions/defaults are validated, entrypoint/helpers stay inside their recipe, and output.schema_version versions recipe-owned data. Metadata/entrypoint inspection reports valid-python-report or invalid-python-report. The report has a synchronous `execute(*, context, timeout)` interface and no Session argument:

```python
VERSION = "1.0.0"

def execute(*, context, timeout):
    # context.vars: independent typed parameters
    # context.inputs: selected JSON objects, already loaded
    # context.artifact_dir: this run's new private artifact directory
    text = "Rows: " + str(len(context.inputs))
    (context.artifact_dir / "summary.txt").write_text(text, encoding="utf-8")
    return {
        "status": "success", "reason_code": "report_complete",
        "message": "Report generated.", "data": {"datasets": len(context.inputs)},
        "artifacts": [{"path": "summary.txt", "title": "Summary", "media_type": "text/plain"}],
    }
```

Return the common status/reason_code/message/data envelope plus artifacts, exactly those five fields. Status supports success/partial/failed/skipped/unsupported, with the same finite JSON/string-key rules as operations. Artifacts is a list of exactly path/title/media_type mappings; fields are nonempty strings. Paths are unique and relative to artifact_dir, must identify existing regular files, and cannot escape through .. or symlinks. The runner records size_bytes and sha256 for each accepted artifact. Renderer choice, MIME types and templates are extensible; no particular UI framework or platform is required.

Stored `report_contract: 0.1.0` includes run_id, schema_version, host_id null, UTC started_at/completed_at, status/reason/message/data, declared artifact metadata, selected input names/digests, recipe ID/version/reference/source and descriptor/Python-code digests, variable names, local Python runtime and execution_errors. Inventory identity/retention is not fabricated: retention is skipped/report-not-inventory. Authors must preserve source observation times, freshness/quality warnings, units and interpretation in their output. Generation time does not refresh old source data.

Each attempt after valid preflight uses `<Feast>/reports/<run-id>/result.json` and artifacts/ beneath that run. Valid input/preflight failures create no run. Loading/execute failure creates a failed result containing type/stage without custom exception text; malformed results/artifacts create failed/invalid_result and expose no accepted artifact list. Invalid/unlisted files may remain in the private run directory for recovery but are not declared outputs. Save/storage failure returns nonzero and may leave partial files; inspect the directory. Successful reports of failed source operations remain successful *report generation*, with failures preserved in report content.

The timeout is supplied to the report for bounded external work, not a forced whole-Python deadline. No subprocess isolation, renderer sandbox or machine-enforced network/permission restrictions exist; reviewed report Python still runs in the controller. The built-in summary uses no network/models. Other renderers must declare dependencies, operations and verification. Do not close/reconnect Sessions or add dummy hosts to offline reports. Using opsfeast.py recipes run directly for python-report is rejected with a routing hint.

## Results and artifacts

```sh
python -B tools/opsfeast.py recipes results list --profile main --json
python -B tools/opsfeast.py recipes results list --profile main --recipe-id check-port --host rms3 --status success
python -B tools/opsfeast.py recipes results show observations/recipe-run-UUID.json --profile main
python -B tools/opsfeast.py recipes results list --profile main --html /path/to/new-results.html
python -B tools/opsfeast.py recipes artifact reports/RUN_ID/result.json summary.html --profile main
```

Use returned result_id values, not literal placeholders. Results 0.1.0 is a read-only index built from current observations/*.json and reports/*/result.json, without duplicating datasets into a new database. It contains result_id, short_id, recipe ID/version, host ID, kind, status/reason, start/completion times, inventory identity quality/warnings and retention receipt. Entries sort newest first by start time, then result ID; --recipe-id/--host/--status filter records. Malformed files are preserved and listed in errors, with partial overall status and exit 1. No results is success with an empty list. The index also includes recipe_reference and recipe_source from raw recipe metadata (null when absent). The Recipes TUI matches both fields for source-separated history; it does not guess attribution from a shared ID. This is an execution index; use [retained inventory tools](result-data.md) for identity-aware observation analysis and exchange.

TTY results list omits the long identity-warnings column, while preserving status and identity quality. Use results list --json or an explicit detail/show/HTML view for complete warnings. Saved warnings, index JSON and redirected list text are unchanged.

results show returns the selected raw JSON; --html presents its fields as escaped text, retaining error/data/time/quality information. A result ID is a storage-relative path, with no absolute paths, traversal or symlink parents. artifact verifies a declared output's path, size and digest before returning its actual local path/title/media type; modified/missing/unlisted artifacts fail. Neither command launches a viewer or publishes/transmits data. Generated HTML from third-party recipes may contain active content: review the renderer before execution/viewing. This framework does not claim all user-provided artifacts are escaped; the bundled basic views and summary are escaped.

## Portable recipe bundles

The example assumes a reviewed user-authored feast/report/execution-summary in that Feast, with non-Bundle attribution and a LICENSE file. Built-in Bundle archives are not accepted by external unpack.

```sh
python -B tools/opsfeast.py recipes pack :feast/report/execution-summary --root /path/to/feast \
  --file recipe.yaml --file main.py --file README.md --file LICENSE --file examples/input.synthetic.json \
  --output /path/to/new-report.zip
python -B tools/opsfeast.py recipes unpack /path/to/new-report.zip --destination /path/to/new-candidate
```

Bundle 0.1.0 contains MANIFEST.json and recipe/ payload files for one selected recipe. --file is a required explicit allowlist: descriptor, README and entrypoints must be included, with all reviewed helpers/templates/dependencies added by the author. Complete dependency closure and licensing remain review responsibilities. No automatic scanning/installing/downloading of dependencies occurs. Multiple recipes can be shared as separate bundles or through the existing [manual collection workflow](recipe-sharing.md).

Manifest fields: format opsfeast-recipe-bundle, version 0.1.0, recipe_id, recipe_version, source_reference, license declaration and files mapping relative paths to sha256/size_bytes. The manifest excludes itself from its payload digest list. Pack excludes hidden/private configuration names, operational storage, jobs, venv/cache/Git paths and symlinks. These name checks do not inspect arbitrary file contents for secrets; review the actual allowlist. Generated reports and private data require a separate explicit sharing workflow, not inclusion in recipe bundles.

Unpack validates exact file inventory, normalized paths, ordinary files, unique archive entries, sizes and digests before creating a new candidate; no activation/registration/execution occurs. Limits are 2000 payload files and 25 MiB total uncompressed content. Existing destinations are preserved. Failed writes remove only the newly created candidate; a malformed archive leaves no candidate. Extracted code/instructions are untrusted review data. Source reference and matching hashes do not authenticate a publisher: output explicitly records publisher_authentication not-established. Follow [acquisition](recipe-acquisition.md), establish license/provenance, review the candidate and then authorize installation/registration at the receiving Feast. Each receiver supplies its own dataset bindings/output locations. No live OpsBuffet exchange, updater or automatic installer is implemented.

## Saved jobs and recurring work

```sh
python -B tools/opsfeast.py recipes jobs save weekly feast/report/execution-summary --profile main \
  --input /path/to/raw-result.json --var 'title=Weekly results'
python -B tools/opsfeast.py recipes jobs list --profile main
python -B tools/opsfeast.py recipes jobs show weekly --profile main
python -B tools/opsfeast.py recipes jobs run weekly --profile main
```

Job 0.1.0 is private `<Feast>/jobs/<name>.json`: job_version/name, resolved recipe reference, recipe ID/version, descriptor/content fingerprint and invocation settings (targets/all/exclude/threads, timeout, assignments, absolute explicit input/vars-file paths and verbosity). Simple names only; existing jobs/symlinks are preserved. A report's typed inputs and mode/flag combinations are checked before save. Operation-specific connectivity/dependency/input checks still occur at execution; saving is not proof of execution readiness. Do not put secrets in CLI assignments; use a private vars-file and exclude jobs from sharing.

jobs run resolves the same explicit source and refuses changed recipe content (including helpers/templates, excluding __pycache__), invalid/disabled sources and incompatible contracts. It reruns the existing program through the same execution surface and writes new results/artifacts. Input *data* may change between runs; its new digest/source times are captured, while the vars-file remains a private mutable binding. Review changes to data bindings/parameters and dependencies within the user's scope. jobs show can inspect a saved definition even when the recipe has changed. Use a new explicitly reviewed job name after a change; no destructive overwrite command is provided.

Saving a job grants no future execution permission and establishes no scheduler. With explicit recurring authorization, an external scheduler can call the fixed `recipes jobs run NAME --root ABSOLUTE_ROOT` command with the selected interpreter and absolute checkout path, without a model in the routine execution path. Set frequency, targets/data, side effects, notification/failure handling and environment in that scheduler. Report jobs do not implicitly refresh collection; schedule a separately authorized collection operation first when needed. No scheduler installation, automatic notifications, pipeline/DAG execution or atomic multi-stage job orchestration is implemented. Known programmatic failures should remain recorded/nonzero; agents can investigate unhandled exceptions or new requirements rather than recreating each run.

## Verification and extension

[Public synthetic tests](../tests/test_recipe_experience.py) cover source/ID selection, static discovery, HTML escaping, offline execution/inputs/status/quality/artifacts, paths, raw-result queries, bundle integrity/boundaries, independent Feast reuse and saved reruns/content drift. Existing operation tests remain applicable through the shared execution implementation. No real host or external scheduler was used. The [summary recipe](../recipes/feast/report/execution-summary/README.md) is an initial plain view; users' agents can author richer versioned report recipes with reviewed renderers and complete synthetic examples/tests. Keep new data/artifact/backends discoverable through canonical contracts and the recipe skill. UI/MCP/web integrations can consume these functions and JSON contracts but are not implemented by this CLI.

## Revisit a complete execution batch

Use `opsfeast.py observation` for batch history and `observation latest --status failed partial` for the latest batch's incomplete hosts. The command prints the actual Observation ID/time/recipe/selectors and full counts before filtered host/result rows. These read-only views are separate from recipes results list, which indexes individual host results. No saved membership or missing raw data is inferred. See [examples and precise selection rules](cli.md#revisit-an-observation-batch).

## Inspect details after a compact run

Completed run/job TTY summaries show host, collection identity, result and result id. Use the displayed short result id directly with results detail/show; unsaved/excluded targets show a dash. Full
access/data/artifacts and result paths remain in --json and saved reports. For one
host, use results list --host HOST (optionally --recipe-id inventory-system), then
results show RESULT_ID with the same --root/--profile; each raw result names host_id.
These existing read-only commands require no new connection or execution. See [the
canonical output and viewing workflow](cli.md#compact-execution-summaries) for exact
invocations, JSON/HTML options, unknown actors and failed/unsaved attempts.

## Focus on a failed result

Use `recipes results diagnose RESULT_ID --profile NAME` first for bounded failure evidence. --limit (default 5, range 1–50) selects more issues; --json returns a diagnosis projection rather than raw data. Successful probes and arbitrary payloads are omitted, unavailable root-cause details stay unknown, and saved failure status does not make the read fail. This performs no collection or writes. See [canonical syntax, evidence rules and limits](cli.md#diagnose-a-saved-failure); detail/show retain complete evidence.

## Vertical result browser

For long result filenames, use `recipes results detail --host HOST` with the original
--root/--profile. It prints the same filtered newest-first index as list, one record
at a time with one field: value per line. Select its complete result_id with
`recipes results detail RESULT_ID` to display a single full raw result vertically.
Nested objects use dotted field names; arrays stay JSON values. detail stays vertical
when redirected; --json retains complete result_id values and additive short_id metadata. show raw JSON remains unchanged. See [exact syntax, errors and limits](cli.md#vertical-result-details).
This is an offline read-only browser, with no connection or collection.

## Short IDs for result selection

Human results list now displays a compact short ID, normally eight hexadecimal
characters. Pass it directly to results show/detail (or artifact) in the same
--root/--profile. The index JSON retains complete result_id and adds short_id;
vertical detail includes the complete resolved result_id. Existing raw result documents
and filenames are preserved. Short IDs are deterministic aliases derived from the
storage-relative path, extended across the entire root on prefix collisions, before
filters. Ambiguous/unknown prefixes fail; use full result_id for durable automation.
See [the complete ID algorithm, lifecycle and error rules](cli.md#short-result-ids).
Legacy inventory and report files need no migration or connection.

## Human time formatting

Results list/detail and human HTML exports display zoned instants in controller local
time as YYYY-MM-DD HH:MM:SS. TUI Details uses the same policy as history. Raw show JSON,
--json, Original output and saved/index timestamps retain their original precision and
offsets. Bundled feast/report/execution-summary 0.1.2 applies this policy to HTML only, preserving its
JSON dataset. See [the canonical time policy](cli.md#human-time-display-policy) for
DST/unknown-time handling and verification limits. Source observations are not refreshed.

_Last modified: 2026-10-21 12:07:37_
