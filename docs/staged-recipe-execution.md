# Staged Recipe execution 0.1.0

OpsFeast owns the lifecycle of a staged Recipe execution. A run has one UUID and
one Console river with the same UUID from before the first stage until it ends.
Result retention and the river preserve different evidence. A linked observation
batch and the per-host result IDs retain their existing contracts. The execution
and river can be created without a running Web service.

## Declare the stages

A Recipe descriptor 0.3.0 can declare ordered stages:

```yaml
execution:
  version: 0.1.0
  stages:
    - id: gather
      executor: agent
    - id: review
      executor: agent
    - id: process
      executor: python
    - id: explain
      executor: agent
```

Use up to 32 unique stage IDs. IDs start with a lowercase ASCII letter and may
then contain lowercase ASCII letters, digits and hyphens, up to 40 characters.
The first stage matches the launch mode. Use `launch.mode: agent` and a
suggested prompt for an agent-first Recipe. Use direct launch and one Python
stage for a standalone Inventory Recipe. Recipe instructions define the typed
business meaning of stage output and when to request human approval. Python
workflows access the claimed snapshot through `context.execution` and use the
existing `context.progress`, `context.connect`, browser-step and river services
for managed I/O. Existing inventory runners use their scoped collection/session
interfaces.

Stages run sequentially. A later Python stage uses the same reviewed entrypoint
and can select its behavior from the active stage ID at
`context.execution['stages'][context.execution['cursor']]['id']`. An executor
may claim only the current waiting stage with the same executor type. Claiming is
serialized and a second simultaneous claim fails. Success advances to the next
stage; partial, failed, cancelled and unknown outcomes end the run. A Python
stage can run multiple host workers in threads. Each worker writes to its target
in the same river. Console event sequence is commit order. Python stages return
an exit code and link saved results through the observation batch and host
result receipts. Full Recipe results remain in their normal stores.

## Start and hand off an Agent stage

These examples show the CLI shape using a synthetic Recipe reference and Profile.
They assume a reviewed installed Recipe, a selected host, and authorization for
the stated stage. Execute through the selected OpsFeast Python environment:

```sh
python -B tools/opsfeast.py recipes execution begin :example/flow --profile demo --host fixture
python -B tools/opsfeast.py recipes execution claim RUN_ID gather --profile demo
python -B tools/opsfeast.py recipes execution progress RUN_ID gather --profile demo --text "Awaiting human review" --awaiting-human
python -B tools/opsfeast.py recipes execution finish RUN_ID gather --profile demo --status success --output approved.json
python -B tools/opsfeast.py recipes execution show RUN_ID --profile demo
```

Create the run and open its `river.reader_url` before the first browser or other
Agent operation. Record observable progress, outcomes and human decisions.
Do not store secrets, private thinking or unreviewed page dumps in progress or
output. Progress is a UTF-8 message up to 8 KiB. Stage output is a JSON object
and the combined outcome payload must fit 8 KiB. The CLI returns the run JSON
with current cursor, IDs, stage outcomes, timestamps and URLs. Release a stopped
Agent stage with `finish --status cancelled` or the observed failure status.
Claim another Agent stage when it is the next waiting stage.

When the next stage is Python, continue with the original scope:

```sh
python -B tools/opsfeast.py recipes run :example/flow --profile demo --host fixture --execution-id RUN_ID --verbose --json
```

Use the same Recipe reference, version, bundle fingerprint and ordered host set.
The runner claims the next Python stage itself. Its return code describes that
Python invocation. Read the execution status to distinguish completed from waiting
for a later stage. The execution ID and saved approval JSON are local coordination
data. The local CLI account is trusted to report actual human authorization.
A Recipe requiring approval checks the saved business inputs against the
effective operation; the execution service does not independently attest that a
human clicked or approved. For write operations continue to use the Recipe's
existing dispatch guards and verification. Never retry because a process
disappeared or a recording step failed. An abrupt process loss can leave a claimed
stage running, with its observed progress preserved for manual reconciliation.
There is no automatic lease takeover, replay, Agent wakeup, or multiprocessing
stage orchestration.

## CLI, inventory scheduling and activity

All 28 bundled Recipes declare staged execution. Host operations, the eleven
Inventory children and Overview use one Python stage while retaining their existing
runner contracts. The stage coordinates lifecycle and evidence; it does not replace
Core Recipe scopes, routine permission phases, selectors or retention schemas.
Normal `recipes run` creates the stage automatically across the selected hosts.
Standalone saved `inventory run` and `inventory query --save` do the same. The
inventory dispatcher creates one execution per enrolled staged Recipe for its due
hosts and returns an `executions` array. Existing schedule opt-in, due windows,
result/retention handling and retry policy still apply. Dry-run, no-due schedules
and unsaved queries do not create executions.

### Offline reports

The three bundled `python-report` Recipes use one Python stage. `run_report` and
`recipes run REPORT` create it automatically with `scope: controller`, no host
targets and `trigger: report`. No SSHScript session or live Web service is required.
The Console session is labelled as controller work, without inventing a host.
Progress and the saved report result ID are recorded in that river. The normal
report JSON/CLI result adds `execution_id`, `execution_status` and `river`; artifacts
remain under the same report directory. Report Python, inputs and artifact validation
keep their existing contracts. A report may not declare multiple stages or an Agent
stage, and report CLI invocations still reject `--execution-id`. Use ordinary
workflow Recipes for Agent/Python handoffs. A failure outside normal result handling
ends the claimed stage as unknown; incomplete evidence never permits replay.

### Web execution plates and grouped routine workers

Every confirmed Web plate creates one `feast/plate` execution, using the saved
Web run UUID as its execution and Console session UUID. It has one Python stage
and records the ordered selection as `members` (reference, host_id, fingerprint).
It declares every selected host, or controller scope for a report-only plate.
The existing Profile-scoped `/api/v1/recipe-runs/ID` response includes `execution_id`,
`execution_status` after completion and `river`. This generated plate is a saved
selection, not an installable Recipe reference or a new CLI resume target.

The coordinator appends received worker progress to one common streaming log
block with receive time, host and Recipe references, preserving the timestamped
plate log as well. It does not create one Console block per output chunk or task.
The Console copy keeps its first 128 KiB (UTF-8) plus an explicit truncation
notice, then continues work; the plate view independently retains its newest
bounded progress. Full per-task receipts stay in the saved plate record. Grouped routine workers keep shared connections and
independent child results; they no longer miss the parent execution lifecycle.
Standalone migrated Recipes invoked by a worker can additionally retain their
own Recipe execution receipts. These are child work, not replacement parent
rivers. Local reports within an operation likewise keep their report receipts.
Stop preserves skipped/terminated task evidence; uncertain local/remote outcomes
remain unknown. A recording failure is explicit and never triggers an automatic
rerun. The existing plate UI remains one continuous receive-order log across hosts.
Activity merges the staged parent with its worker batches into one row, retaining
the parent river link and independent host result links.

### Post-collection execution receipts

Saved standalone inventory and internal single-host operation results store the
final stage receipt in `execution_receipt` 0.1.0: `schema_version`, `execution_id`,
`execution_status` and `river`. Their invocation return values additionally project
those three receipt values at the top level, matching the normal batch CLI.
The [additive raw schema](../schemas/raw-retention-context.schema.json) documents
this field. It is excluded from `retention_replay.raw_digest`, just like existing
retention/content receipts, so finalizing a stage does not invalidate the saved
observation's provenance or replay idempotency. Pre-existing top-level workflow
river and execution identity remain part of the original digest; historical
records are not rewritten or reinterpreted. Offline report files are not retained
host observations and keep their execution receipt values at the top level.

### Adoption and compatibility

The other 27 bundled Recipe versions were incremented when their stage declarations
were added; System configuration already declared its stage. Exact references,
inputs, permissions, result payloads and retention contracts are unchanged.
Fingerprint-bound previews, saved invocations and transferred packages need review
against the new definitions; regenerate a stale preview rather than bypassing its
checks. Existing observations, report artifacts and execution histories are not
rewritten or replayed. User/external Recipes are not automatically modified. Recipes
without a stage declaration retain their explicit supported runner contract; the
virtual-plan interpreter remains unimplemented. Reload Web after reconciling active
work to load the coordinator/report changes; preserve its port/data/controller.

Registered Profiles use installation-local Console storage and store execution
state under their management root in `.recipe-executions/`. An unregistered
CLI root stores its river locally under that directory; it has no Web visibility
until a supported registered execution is created. Projects without a Web port
return relative river paths. Normal Inventory execution does not need Web.
When a workflow still declares `launch.river: true`, the runner checks that its
registered Profile has a live Web endpoint before host dispatch. The authenticated
Activity and Logs page opens a staged run's live or history river and can link to
its retained host results. It continues to show historical observation batches.
Existing runs keep their recorded evidence.

The shared service is available in the checkout as
`opsfeast.staged_execution.Executions` and `PythonStage`. Use the CLI from an
Agent so it follows catalog resolution, explicit host validation and scope
binding. Check `recipes show RECIPE --json` for `descriptor.execution` and
`recipes execution --help` for local availability. On storage failure, preserve
the incomplete evidence and use the existing business guard before any repeat.
Console block and byte budgets apply. Execution state and Console events are
published to separate stores; a failed write can leave an incomplete view.

Public tests include `tests/test_recipe_stage_adoption.py`, `tests/test_recipe_runs.py`
and `tests/test_inventory_execution_river_pilot.py`, using temporary Profiles, fake sessions and a credential-free Web
API. They cover multi-threaded CLI and scheduled Inventory, cancellation,
exclusive claims, changed bindings, sequential Agent/Agent/Python/Agent
handoff and live-to-history activity links. They do not run billing, contact
managed hosts or send email.

*Last modified: 2026-11-18 16:09:45*
