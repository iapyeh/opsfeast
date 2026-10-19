# Retained observations content example

This bundled offline python-report 0.1.0 recipe uses `context.retention.query` to produce Markdown and escaped HTML from retained observations. It is a content application, not a host collection recipe. Both outputs preserve full source envelopes, field states, source times, origins and quality warnings. Generation does not refresh observations or establish health.

Prerequisites: Python 3.11+, PyYAML 6.0.3, current OpsFeast with the report retention reader, and an initialized namespace-enabled profile. No extra renderer, model, Session, SSH, sudo or network service is used. Explicit local report execution writes only the new report result/artifacts; no collection or publication occurs.

```sh
python -B tools/opsfeast.py recipes run report/retention --profile main --json
python -B tools/opsfeast.py recipes run report/retention --profile main --vars-file recipes/report/retention/examples/selection.synthetic.json --json
```

Typed inputs: title is a string, recipes is an array of exact source-qualified references, hosts is an array of host IDs. Empty arrays select all. Non-string/empty selectors fail with invalid_selection. Multiple recipes and hosts can be combined; individual missing fields stay unknown and different field units are not silently reconciled. Source record order follows UTC observation time then record ID. No records produces successful empty_selection with empty report artifacts.

Outputs are retention.md (text/markdown) and retention.html (text/html), validated through the shared artifact mechanism under reports/RUN_ID/artifacts. Report data contains row count and selected record IDs. The report result also records retention_sources selection/digests and original source times. Use recipes results list/show and recipes artifact with the returned result ID to retrieve outputs. Generation/storage errors remain explicit; success is content generation, not operational success or host health.

The same retention records feed the bundled vault without reading these artifacts. Copy the approach for user-authored graph or web renderers; declare renderer dependencies, preserve source/quality evidence, bind private data at runtime and use ordinary reviewed programs for repeat runs. Web hosting, automatic installation, scheduling and transport are not implemented. Sharing built-in Bundle archives as external recipes is prohibited; user authors supply their own attribution/license and reviewed portable files.

[Source](main.py), [descriptor](recipe.yaml), [synthetic multi-recipe selection](examples/selection.synthetic.json), [public tests](../../../tests/test_retention_content.py), [retention interfaces](../../../docs/retention.md).

_Last modified: 2026-10-19 11:41:37_
