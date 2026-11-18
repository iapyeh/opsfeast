# Recipe flow plan language 0.1.0

Status: normative design notation; no parser, interpreter, compiler or runner is
implemented. Read [architecture](recipe-flow-design.md) first. A .plan.md file
is a specification containing metadata, step contracts/references and a fenced
Python-style plan. Do not run it with Python, exec, eval or an agent's shell.

## Plan header and numbered steps

A standalone plan declares recipe ID/version, plan contract
recipe-flow-plan/0.1.0, source package digest, input/binding schema references,
callable contracts and utility/runtime lock references. A draft may mark digests
uncomputed, but then it is not an execution-ready package.

Each step is listed once in the index:

| Number | Stable ID | Title | Bound callable |
| --- | --- | --- | --- |
| 01 | acquire_table | Read the rendered source table | browser.rendered-table/0.1.0 |
| 02 | parse_table | Normalize verified table columns | bot-usd-table/0.1.0 |
| 03 | select_quote | Apply the monthly date rule | monthly-usd-quote/0.1.0 |
| 04 | run_monthly | Execute the bound monthly action | monthly-query-command/0.1.0 |
| 05 | report_result | Explain the recorded outcome | result-explanation/0.1.0 |

Use comments such as "# step 03 id: select_quote" immediately before the
corresponding call. Index, comments, contract and actual call must agree.
Renumbering changes review labels, not step identity. Real branch receipts use
stable IDs and the original display number. Human reviewers can say "step 3";
the agent resolves it within that exact plan revision.

A recipe may contain only one script step. A display title is not an execution
identifier or a dependency resolver.

## Core syntax and meaning

| Construct | Plan meaning |
| --- | --- |
| assignment | Bind an immutable typed value or step output |
| named call | Invoke the exact contract/provider/routine named in the package |
| if / elif / else | Evaluate a Boolean expression and select one path |
| stop(reason_code, message) | Terminal control operation; record and prevent later steps |
| finish(...) | Terminal outcome with execution/business/retention states kept distinct |
| return | Return a declared output; cannot relabel failed required work as success |
| comment | Explain intent or attach the numbered step marker; cannot grant permission |

The plan is Python-style, not all of Python. Do not imply availability of normal
imports, arbitrary functions, object mutation, reflection, filesystem access,
networking, shell statements, eval/exec, dynamic attribute construction or
arbitrary method calls. Utilities may use reviewed ordinary Python internally
under a separate implementation/runtime contract.

The initial sequential plan needs no general loop engine. A future finite for
loop needs a frozen ordered collection, maximum iterations, per-item step/
attempt IDs and stop semantics. while loops, recursion, parallel joins and
arbitrary exception handlers require separately versioned semantics. Do not
encode an unbounded retry as a loop or turn an action exception into success.

## Names and calls

All data names come from declared inputs, bindings or earlier immutable outputs.
Dotted access reads declared data fields. A callable must have a static binding
to an exact routine/script version or an agent/provider contract before
execution readiness. Names such as agent.get_rate() can communicate intent
during design but have no implicit operational meaning.

Use the roles agent, routines, script, human and notify for readable calls.
These roles are not hard-coded agent brands or executable Python modules.
Human/notification providers are subject to the same schema, effect and
authorization requirements as browser/SSH providers.

A missing callable, unknown field, unavailable provider, unsupported contract,
expired grant or incompatible runtime blocks readiness. Never generate a new
implementation during routine execution to make the plan appear runnable.
Revise and review a separate package revision instead.

## Expressions

Allow typed literals, declared field references, comparisons, membership,
parentheses, and/or/not and explicitly declared pure conversion functions.
Evaluation is side-effect-free. A future evaluator uses a restricted parser;
this design does not authorize evaluating strings as Python.

~~~python
quote.validation == "passed"
30 < decimal(quote.sell_rate) < 40
quote.currency == "USD" and not quote.ambiguous
result.state in ["failed", "outcome_unknown"]
~~~

Use == for value equality; reserve is None / is not None for the missing-value
sentinel when the schema permits null. Bare enum words such as passed must be
declared constants or quoted strings, never guessed names. and/or/not require
Boolean operands and produce Booleans; no Python-style operand-value return.
Comparisons require compatible declared types; string/number coercion and
Boolean-as-integer coercion are errors. Chained comparisons evaluate each
operand once. Short-circuiting is left-to-right and recorded without evaluating
unused operands.

Missing field, invalid date, failed conversion, non-finite number or an invalid
condition is condition_error and stops dependents. It is not false and does
not select else. Optional fields must be handled explicitly by their schema.
An unsuccessful prerequisite cannot supply a fabricated default output.

Decimal amounts are encoded as non-exponent base-10 strings. Do not use binary
float, int(rate), locale-based comma replacement, rounding or an agent's
mental arithmetic for exchange rates. The quote routine in the case defines
canonical output and validation. Dates are ISO Gregorian dates; the target
month is YYYY-MM frozen from the approved Asia/Taipei run clock/input.

## Step readiness and returned state

A call can succeed, fail with a typed error, wait for a named resource/person/
grant, be cancelled, or have outcome_unknown. Waits preserve the same attempt;
they do not imply success, create a grant or automatically wake an agent.

Before dispatch, validate input schemas, prerequisite states, provider support,
grant, runtime binding and business deduplication state. Store intent first for
actions. Missing support results in an explicit wait/error, not a tool fallback.

Required utility failure stops downstream work. not_selected marks an unchosen
branch. If future joins are added, only selected prerequisites can satisfy a
join; skipped/unselected branches cannot fabricate successful outputs.

## Data and decision receipts

Each output envelope contains contract/version, step and attempt IDs,
package/runtime identity, input digests, output digest/reference, acquisition/
source times and evidence classification. Data fields belong to their schema;
receipt metadata is not injected into a Decimal argument.

A decision receipt saves expression text/version, evaluated nonsecret operands,
short-circuit information, Boolean result and stable branch target.
Agent explanation prose may vary; canonical decisions, dates, numbers, targets,
commands, effect scope and error codes must not.

An acquired snapshot is immutable. Approval and action refer to the same
selected quote digest. A routine never reopens a live page as a hidden input.
Refreshing source data requires a separately identified acquisition/selection
attempt and authorization recheck.

## Errors and stopping

Use stable machine codes with human explanations; messages are not the branch
API. Distinguish no_available_date, coverage_incomplete, schema_changed,
ambiguous_rate, invalid_rate, provider_unavailable, authorization_missing,
action_failed and outcome_unknown. Each callable declares its possible errors.
Unknown codes remain visible and block execution rather than being mapped to an
optimistic success/default branch.

A stop records completed/unchosen/pending work and the cause. A stop after an
external action does not undo it. Timeout or lost acknowledgement may mean
outcome_unknown. Reconciliation uses saved evidence and explicitly authorized
queries; it never automatically repeats the action.

## How humans and agents review the plan

Read step numbers and branches, then open a referenced routine only if needed.
Keep important target/column/date/retry rules visible either in the plan or an
immediately linked contract. An agent cannot hide a three-attempt policy behind
a title saying "execute once". The review view must derive actual values from
the same bindings/contracts and identify contradictions.

Use [conformance](recipe-flow-conformance.md) to compare receiving agents without
executing a live workflow. No claim of native execution support follows from a
plan being valid Python syntax or from another agent understanding its intent.

## Executable binding

A numbered virtual plan remains a review artifact. A reviewed ordinary Python
entrypoint may implement it using [python-workflow 0.1.0](python-workflows.md),
including explicit browser evidence and delayed SSH. This does not make the plan
itself executable or define a general virtual-language interpreter.

*Last modified: 2026-11-17 17:19:19*
