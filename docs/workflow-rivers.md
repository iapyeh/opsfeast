# Live workflow rivers 0.1.0

A reviewed `python-workflow` recipe can opt into the existing Console river:

```yaml
runner:
  contract: python-workflow
  version: 0.1.0
  entrypoint: main.py
launch:
  mode: agent
  river: true
  prompt: |
    Review targets, inputs and effects and obtain the required human confirmation.
    Start exactly one CLI run with --verbose. Immediately show its river URL
    in the conversation and open that exact URL in the browser before supplying
    any browser response that permits host dispatch. Never rerun to obtain a river.
```

`launch.river` is an optional Boolean, default false. A configured runner must be
`python-workflow`; a definition without a runner can declare the future intent.
Other launch fields retain [their contract](python-workflows.md#agent-conversation-as-the-launch-surface).
The normalizer returns the effective Boolean. Discovery/static readiness does not
establish that the Web endpoint is currently available or authorize execution.

## User and agent sequence

For a two-stage browser/command recipe, finish its quote and exact-command
confirmations first. Run the existing `recipes run ... --verbose --json` command
once. The runner creates the river before loading/executing the workflow entry,
prints `river http://localhost:PORT/console/UUID` to progress, and records the
same session ID/reader/history URL in the saved result and compact CLI JSON.
The active agent must show that exact URL immediately and open it in the browser
before responding to the pending browser step. A login screen must retain the
river destination; do not require another execution grant or a logged-in reply.
There is no automatic agent wakeup or automatic browser opening in the runner.
Browser request and command deadlines continue; never restart a run to extend them.

This river uses the Console reader and its normal live/history views. It records
progress, actual connection identity supplied by the runner, reviewed argv,
stdout/stderr and completion/failure. The finite command does not become a
persistent interactive SSH shell, nor does this integration add arbitrary input
or a Web command-cancel control. Use the existing Console worker for human-directed
shell interaction. Stop requests, local job cleanup and confirmed remote process
termination remain distinct evidence.

## Runtime interfaces

The checkout-level `opsfeast.workflow_river.create(installation, config, *,
host_id, title, reference, run_id)` resolves the existing installation data root
and registered Profile, reads the saved Web port and checks its loopback setup
endpoint. It never starts Web, changes accounts, opens an SSH connection or
allocates another port. An absent/unavailable endpoint or unregistered Profile
fails before entry execution/host dispatch. Authentication remains the existing
Web reader authentication; no token/credential files are created.

The runner owns `context.river` (`None` without opt-in).
`context.progress(message)` forwards to both the river and the existing CLI
progress sink. Connection identity is recorded only after the runner's actual
connection scope opens; configured actors are not fabricated as verified login.
No extra identity or host inspection command is run by this integration.

`WorkflowRiver.execute(session, argv, *, timeout)` executes one reviewed nonempty
string argv through the supplied Session's SSHScript 7.0.1
`start(argv, timeout=timeout, check=False)`, preserving selected-host connection
ownership. It records the command before dispatch, polls public bounded
`job.stdout`/`job.stderr` buffers while `job.done` is false, waits for the original
result and always calls the owned job's `stop()` for cleanup. It does not open a
new Session or retry a command. The installed 7.0.1 public job stubs/source
(`sshscript/commandjob.pyi`, `commandjob.py`) supplement the bundled managed-job
guide for these buffer properties; no private source checkout is required.

The shared `browser_command_workflow.run` uses this method when `context.river`
is present; ordinary reviewed workflows may call it explicitly. Other commands
that bypass the river interface are not automatically intercepted. The original
business-key guard still persists uncertain intent before dispatch and blocks
repeated/unknown/completed attempts across recipe versions. River recording does
not authorize bypassing that guard or repeating a billing action.

`WorkflowRiver.complete(report, result_path)` ends the progress block and links
the final saved result after the normal connection cleanup and content processing.
A final recording failure is an explicit failed `river_recording_failed` result,
with prior execution status retained; it does not replay the completed command.
Progress recording errors propagate. Browser requests are closed if publishing
their initial progress fails, rather than leaving an apparently active request.

## Evidence, storage and limits

Reuse Console blocks 0.2.0 through `Records`, never direct SQLite writes or copied
host transcripts. Sessions declare the exact Profile/host participant, so the
canonical river appears in that host's Console history. Storage remains private
installation-data `console-records/console-blocks.sqlite3`. Cross-process readers
observe the existing committed event journal. UTF-8 append offsets are byte counts;
appends use bounded chunks under the Console service limits.

Capture buffers are bounded (SSHScript defaults: 1 MiB per stream). A rotated tail
or source truncation is flagged; an incomplete output block is never marked
completed. Output may be buffered by the remote application; a silent command
has empty output blocks, not invented progress text. Application stdout/stderr
are recorded in the private river and may contain operational data: review the
command's output and access/retention expectations before opting in. This is not
a generic secret-redaction service. Credentials/config file contents are never
read by this integration. Command completion does not establish invoice creation
or mail delivery; partial/unknown business outcomes remain unchanged.

This is a prospective execution feature. Existing completed runs are not
backfilled as if they had a live river, and enabling the feature never reruns them.
Public fake-job tests cover early recording, streaming, errors, partial results,
UTF-8 offsets and exact host history. A credential-free local SSHScript process
checks actual local job/record integration. These tests do not connect to a
managed host, execute billing or prove remote cancellation/mail delivery.

## Workflows that declare stages

[Staged Recipe execution 0.1.0](staged-recipe-execution.md) creates the river
before the first Agent stage. The runner claims the pending Python stage using
`recipes run --execution-id ID` and attaches to the existing river. The
`launch.river: true` availability check still applies before the workflow can
dispatch. The single-runner flow above applies to workflows without
`execution` stages.

*Last modified: 2026-11-18 10:35:29*
