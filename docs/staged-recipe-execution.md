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

The bundled System configuration Inventory Recipe opts in. Its normal
`recipes run system/inventory/system --host HOST ... --json` and saved standalone
`inventory run` or `inventory query --save` paths manage a Python stage
automatically. The inventory dispatcher creates one execution per enrolled
staged Recipe for its due hosts and returns an `executions` array. The existing
schedule opt-in, due windows, result/retention handling and retry policy still
apply. Dry-run, no-due schedules and unsaved queries keep their existing behavior.
Recipe code should use these shared entrypoints instead of creating a river per
worker. Broader adoption by other Recipes, offline reports and grouped Web meal
workers is outside this version. A Web worker invoking a standalone migrated
Recipe uses the same CLI executor within its existing invocation scope.

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

Public tests use temporary Profiles, fake sessions and a credential-free Web
API. They cover multi-threaded CLI and scheduled Inventory, cancellation,
exclusive claims, changed bindings, sequential Agent/Agent/Python/Agent
handoff and live-to-history activity links. They do not run billing, contact
managed hosts or send email.




*Last modified: 2026-11-18 10:35:29*
