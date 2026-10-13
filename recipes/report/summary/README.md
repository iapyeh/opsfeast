# Plain execution-result report

Create a simple offline HTML table and JSON dataset from explicitly selected raw inventory/general execution results. This is a reusable python-report recipe: no LLM, SSHScript Session, SSH, sudo, network access or external renderer is needed. It does not refresh source observations or prove that services are healthy.

## Use

From the checkout with the selected Python interpreter and an existing Feast:

```sh
python -B tools/opsfeast.py recipes show report/summary --root /path/to/feast
python -B tools/opsfeast.py recipes run report/summary --root /path/to/feast \
  --input /path/to/result-one.json --input /path/to/result-two.json --var 'title=Weekly results'
python -B tools/opsfeast.py recipes results list --root /path/to/feast --recipe-id report-summary
python -B tools/opsfeast.py recipes artifact reports/RUN_ID/result.json summary.html --root /path/to/feast
```

The last command verifies the stored artifact's digest and prints its local path; open that file in a browser or the user's preferred viewer. It does not execute or publish HTML. Use the returned result_id rather than the literal RUN_ID. For an isolated synthetic run, supply [example input](examples/input.synthetic.json) as --input. No host selection is accepted for reports.

## Input and result contracts

This implementation supports raw result objects with recipe metadata, host_id, status, source run timestamps and recipe-owned data or inventory observations. It does not accept retained exchange datasets or arbitrary undocumented JSON. Each --input is a JSON object; repeat it to combine explicitly selected results. No input files means an empty report, recorded as success/empty_selection rather than claiming an inventory was collected.

The optional title input is a string, default OpsFeast execution results. Source result status/reason, original times and identity quality/warnings remain visible. Expand Data and provenance to inspect source recipe/schema versions, evidence kind, data and observations; the JSON artifact preserves all row fields. Unknown values remain null; a successful port check with reachable false remains a refused observation. Source timestamps are not refreshed by report generation. This report makes no freshness or cross-host identity inference and performs no cross-time deduplication.

Common report schema/artifact contract is 0.1.0. It produces summary.html (text/html) and summary.json (application/json), with generation time and rows; [the common runtime](../../../docs/recipe-experience.md#offline-report-contract) records input digests, recipe/runtime provenance, output sizes/digests and execution status. Results/artifacts live in the selected Feast reports/<run-id>/, separately from original observations. Unsupported input returns failed/unsupported_input with no declared artifacts. Runtime/parser/output failures remain explicit in result.json. Inventory SQLite retention is not applied.

## Reuse and share

Save a reviewed invocation with `recipes jobs save weekly report/summary --root /path/to/feast --input /path/to/result.json`, then rerun it with `recipes jobs run weekly --root /path/to/feast`. Each rerun creates new artifacts. Jobs pin recipe files and preserve private local source bindings; saving a job neither schedules nor authorizes future execution. External scheduling requires explicit user scope.

Package the portable recipe with an explicit allowlist:

```sh
python -B tools/opsfeast.py recipes pack report/summary --checkout-only \
  --file recipe.yaml --file main.py --file README.md --file examples/input.synthetic.json \
  --output /path/to/new-report.zip
python -B tools/opsfeast.py recipes unpack /path/to/new-report.zip --destination /path/to/new-candidate
```

Unpack verifies content and creates a review candidate, without installation/registration/execution. Recipients review the candidate, choose their own data bindings and authorize use. No real data, generated report or job binding is included by this allowlist. Publisher authentication and distribution licensing must be established independently; the repository currently declares no distribution license.

## Implementation and verification

Python standard-library JSON and HTML escaping render a plain table without script dependencies; source text and titles are escaped. User-created report recipes can use other renderers and declared output types, with their own dependencies and verification. See [implementation](main.py), [common report contract](../../../docs/recipe-experience.md) and [public synthetic tests](../../../tests/test_recipe_experience.py). Tests cover empty/unsupported/failed/unknown data, identity warnings, source-time preservation, injection escaping, repeat runs and cross-Feast bundle reuse. No real host data, SSH or service probes were used.

_Last modified: 2026-10-13_
