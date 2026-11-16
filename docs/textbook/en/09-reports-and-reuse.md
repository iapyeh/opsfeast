# 9. Reports and repeatable work

[Book home](README.md) · Previous: [Consumers](08-consumers-and-services.md) · Next: [Portability](10-portability.md)

An offline report reads selected existing evidence and produces local artifacts. It lets you combine data, explain findings and create a reusable presentation without reconnecting to hosts. The report's source times remain the times of its inputs.

## Generate a report from retained observations

Review the bundled [retention-summary recipe](../../../recipes/feast/report/retention-summary/README.md). Within authorized local report scope:

```sh
python -B tools/opsfeast.py recipes show feast/report/retention-summary --profile main --json
python -B tools/opsfeast.py recipes run feast/report/retention-summary --profile main --json
```

The first command reads metadata. The second executes reviewed controller-side Python and writes a new report result and artifacts. This bundled recipe uses no connection, Session, network service or model. Arbitrary third-party report Python has no general sandbox and must be reviewed separately.

Typed selection variables include title, recipe references and host IDs. Empty selector arrays select all retained data in scope; specify selectors if you want a narrower report. A private JSON vars file can hold the selection:

```json
{
  "title": "Backup evidence review",
  "recipes": [":backup/files/check/daily-backups"],
  "hosts": ["backup-example"]
}
```

After saving that selection locally, use its actual path:

```sh
python -B tools/opsfeast.py recipes run feast/report/retention-summary --profile main --vars-file /absolute/path/to/selection.json --json
```

The recipe writes `retention.md` and `retention.html` under its new run's artifacts directory. Outputs preserve source envelopes, field states and warnings. No records can be a successful empty selection, not a failure or proof that the hosts have no relevant state.

## Retrieve validated artifacts

```sh
python -B tools/opsfeast.py recipes results list --profile main --json
python -B tools/opsfeast.py recipes results show RESULT_ID --profile main --json
python -B tools/opsfeast.py recipes artifact RESULT_ID retention.html --profile main
```

Use the report result ID returned by execution or listing. Artifact lookup verifies the declared path, size and digest before returning its local path. It does not publish, transmit or launch a viewer. A successful report says generation succeeded; its content may correctly describe failed or old source observations.

For raw-result summaries, the bundled `feast/report/execution-summary` accepts explicitly selected JSON inputs with `--input`. This differs from retention-summary's retained-data reader. Read the chosen recipe's contract before mixing input types. Host/group selectors belong to operational recipes and are not accepted by offline reports.

## Save a repeatable invocation

After reviewing the recipe and parameters, an authorized local saved job can preserve the invocation:

```sh
python -B tools/opsfeast.py recipes jobs save backup-review feast/report/retention-summary --profile main --vars-file /absolute/path/to/selection.json
python -B tools/opsfeast.py recipes jobs show backup-review --profile main --json
```

Saving writes a private job definition without running it. A later authorized rerun is:

```sh
python -B tools/opsfeast.py recipes jobs run backup-review --profile main --json
```

Jobs pin recipe source/content and fail if code changes. Input data and private vars files may change, so review current bindings and new source digests. Use a new reviewed job name after recipe changes; do not overwrite drift checks to force execution. Jobs can contain private paths and parameters and should not be included in public recipe bundles.

## Keep repetition independent of a model

A saved job is not a schedule. If recurring execution is desired, define frequency, targets/input data, controller environment, side effects and failure handling. An explicitly authorized external scheduler can call the fixed reviewed job command. OpsFeast currently has no general job scheduler, pipeline/DAG engine or automatic notification behavior for all jobs. Inventory scheduling is a separate implemented feature.

For a custom report, let the agent reuse `context.retention.query/show`, validated artifact handling and the existing recipe runner. Preserve units, source times, origins, partial/unknown states and renderer dependencies. Basic tables should remain useful without a specific visualization product. Save the report code/templates and selection policy so routine generation reruns reviewed work.

Agent prompt:

> Prepare a reusable offline report combining the selected backup and inventory records. Use the existing report reader and artifact interfaces. Keep source timestamps, identity/coverage warnings and units visible. Bind private selectors at runtime, provide synthetic examples and tests, and give me one exact rerun command. Do not collect new data or publish the report.

**Checkpoint:** Find the report result and its validated artifact. Explain what generation time means, which observation times supply the report, and why saving a job does not authorize future runs.

Canonical guidance: [recipe experience](../../recipe-experience.md), [retention content interfaces](../../retention.md), [report authoring](../../recipe-authoring.md#report-recipes-and-reusable-visualization), and [report sharing](../../recipe-sharing.md#share-report-recipes-across-feasts).

*Last modified: 2026-10-26 12:55:26*
