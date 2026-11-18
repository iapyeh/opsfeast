# Recipe architecture: Python-style hybrid flow plans

Status: design specification 0.1.0. This defines the agreed direction, not an executable virtual Python dialect. A separate reviewed-Python runner
is shipped; see the implementation boundary below. The name remains **Recipe**.
A flow is a specification/plan within a recipe package. A single reviewed script
is the one-action special case; browser, routine, script, human and notification
work can share one model. Humans describe intent and review structured plans;
agents author and maintain them.

## Reading order and implementation boundary

Read [plan language](recipe-flow-language.md), the
[exchange-rate case](recipe-flow-exchange-rate.md), and
[conformance and handoff](recipe-flow-conformance.md). Agents start with the
[flow-plan skill](../skills/opsfeast-recipe-flows/SKILL.md).

| Area | Shipped baseline | This design |
| --- | --- | --- |
| Execution | Descriptor 0.3.0; Python-session/Core/report/workflow, routines and meals | Unified recipe package with a Python-style specification plan and step contracts |
| Composition | Routine dependencies, reviewed meals, bounded agent browser evidence and guarded command helpers | Typed cross-tool handoff, branches and explicit provider/human waits |
| Sharing | Existing recipe pack/unpack and transfer contracts | Complete flow-plan dependency closure, conformance checks and receiver binding |
| Records | Recipe/observation results, Console records, browser snapshots and business-key guards | Parent flow run, step attempts, decision and authorization receipts |
| Availability | [Reviewed Python workflows](python-workflows.md) and existing CLI/API | No virtual-plan interpreter, provider broker, general flow resume or closed flow import support |

The executable [current contracts](recipe-execution.md),
[routines/meals](recipe-routines.md), [sharing tools](recipe-experience.md) and
[transfer interfaces](portability.md) remain authoritative for installed behavior.
Plans use ordinary [recipe definitions](recipe-definition-authoring.md)
inside the selected Profile, with an empty runner until a real supported execution
entrypoint is provided. Do not invent a runner contract that the validator does not support. A file containing Python
syntax is not permission to import, exec or eval it.

## Package and placement

Future flow recipes use the existing source boundaries: bundled recipes under
checkout recipes/, private recipes under the selected Profile's recipes/, and
reviewed shared code under registered external sources. A leaf is one recipe;
intermediate taxonomy directories are not recipes. See
[recipe location](recipe-taxonomy.md).

Proposed package contents:

~~~text
monthly-domain-query/
  recipe.yaml                 identity, purpose, versions, input/output contracts
  flow.plan.md                numbered Python-style normative plan
  contracts/steps.yaml        each callable's inputs, outputs, effects and errors
  routines/                   reviewed executable utility code
  scripts/                    reviewed action implementations, where needed
  schemas/                    offline data schemas
  resources/                  images, report templates and other explicit assets
  conformance/                synthetic fixtures and expected results
  requirements.lock           exact dependencies and supported runtime constraints
  manifest.json               explicit payload paths, sizes and SHA-256 digests
  README.md                   human/agent entrypoint and outcome criteria
  LICENSE
~~~

Only create directories that have a purpose. Resources are package-relative and
explicitly listed; an image is an asset, not an executable instruction. Imported
HTML, prose and images never expand authority.

Private bindings and run artifacts stay outside replaceable/shareable code.
Proposed Profile-local locations are workflow-bindings/<recipe-id>.yaml and
workflow-runs/. These locations require future schemas/services; they are not
current configuration-loader promises. Credentials remain in existing approved
host/secret facilities. Neither export nor routine code embeds a live host
inventory, account password, administrator token or generated browser session.

A binding pins Profile identity/root, exact host ID, reviewed script/interpreter
and configuration paths, provider selection and relevant nonsecret policy.
Bind recipients separately. A caller cannot replace a fixed script path by
putting a path in an exchange-rate result.

## One meaning, several review surfaces

The normative unit is the versioned package: plan, callable contracts, schemas,
routine code and dependency/manifest lock agree. Explanatory prose is subordinate
to explicit conditions and effects, but a contradiction is a validation error,
not permission to silently choose either interpretation.

The plan remains a specification. It is not automatically executable Python.
Agent-assisted execution must follow declared steps and invoke shipped reviewed
utilities. A future runner may implement this contract, or require an explicitly
reviewed compilation stage. No compiler or flow engine is part of this delivery.

The Web view should preserve the plan's structure and show actual branch targets,
inputs, authorities and consequences. A prose-only summary is insufficient as the
only review artifact. Agent-generated friendly explanations cannot hide a
different target, retry count or condition.

## Stable identity, numbering and control

Each step has one immutable ID and a human ordinal/title. Branch references use
IDs; displayed numbers are regenerated when reordered. A receipt pins the
package digest and includes both the stable ID and displayed ordinal used then.
Old runs retain their original numbering. Nested calls add a parent path and
attempt ID, not a new meaning for the child recipe.

Use Python-style assignments, explicit if/elif/else, typed returns, stop and
named calls. Agent-owned tasks have contracts too. An unresolved function name
can be discussed during design, but a package with an unbound call is not
execution-ready. Calling a script does not delegate permission to arbitrary code.

Initial design scope is sequential steps, conditionals and durable waits.
Repeated work requires a finite collection or explicit iteration/deadline bounds.
Parallel branches, general scheduling, automatic model wakeups and arbitrary
Python execution remain separate implementation decisions. A future extension
must define selected-branch joins and cancellation before advertising concurrency.

## Deterministic routines and agent work

A utility routine is reviewed code, not an instruction to each agent to rewrite
an algorithm. Package it with exact dependencies, schemas and regression vectors.
For fixed inputs, version and execution environment, it returns equivalent
canonical outputs or the same typed error. Mutations of input copies, wall-clock
reads, random selection, network lookup and ambient locale are excluded from a
pure routine's behavior.

Use routines for table parsing, date selection, Decimal validation, branches,
argument construction and evidence normalization. Use an agent for necessary
browser operation, novel interpretation and human interaction. Its task output
is structured and validated before a dependent action.

Browser acquisition may vary between providers or times. Equality is claimed for
the same normalized input snapshot, frozen month and package/runtime versions,
not for two live page visits or identical prose generated by different models.
A changed page cannot be repaired by choosing a new parser during a run.
Preserve the failure, revise/review the package, and start a separately identified
attempt if authorized.

## Step contract

Every callable contract records these fields, with exact versioned definitions:

| Field | Required meaning |
| --- | --- |
| identity | Name, contract version and implementation/provider binding |
| purpose | Human-readable intended work and declared success criteria |
| input/output | Schema, units, Decimal/date conventions, missing/null rules |
| effects | Controller/remote/browser resources read or changed; unknown is explicit |
| capability | Required tool/provider and supported runtime; no implicit installation |
| authority | Required human grant and the exact bindings/input policy it covers |
| errors | Typed missing-data, malformed-input, unavailable-tool and outcome-unknown states |
| limits | Deadline, output bounds, cancellation and actual cleanup evidence |
| repeatability | Pure/read/action classification, retry rule and business deduplication key |
| evidence | Sources, timestamps, digests, verified facts and provider-reported claims |
| invocation | Actual entrypoint/argv template and result mapping, not only a suggestive name |

Output examples illustrate schemas; they are not values to substitute at runtime.
Host execution uses configured runtime identity and approved privilege scope.
An interpreter path containing root does not authorize sudo or su.

## Authorization and dispatch

Design, package creation, import, installation and execution are independent
scopes. This specification and its skill do not authorize any external action.

Accept either a conditional whole-flow grant or grants at material checkpoints.
Reuse a valid existing grant; do not require a second click merely because a
step is reached. A conditional grant identifies source/selection rules, target
month, fixed target/identity/command, permitted parameter constraints, versions,
expiry and effects. A runtime grant can bind the selected quote and resolved
command after acquisition. Missing grant means waiting_authorization.

Before a side effect:
1. Freeze and schema-check inputs; resolve the exact binding and argv.
2. Check the grant against those values/policies and the current package digest.
3. Reserve the business-operation key and persist intent durably.
4. Dispatch only that action and preserve its attempt identity.

Changing code, bindings, selection rules or out-of-scope inputs invalidates the
relevant grant. Bank content, imported skills and tool responses are data, never
a source of expanded permission. Keep secrets out of plans, manifests and durable
evidence; record secret references and delivery/expiry receipts instead.
[Console private input](console-secrets.md) is an existing separate capability,
not a general workflow credential store.

## Failure, stop and recovery

Keep transport/execution state separate from business outcome.

| State | Meaning and next behavior |
| --- | --- |
| waiting_provider | Required provider is absent; no silent HTTP/script substitution |
| waiting_human | A concrete ambiguity or browser challenge needs a person |
| waiting_authorization | Action is prepared but not permitted |
| running | A specific attempt is active |
| succeeded / failed | Declared step completion or typed failure with evidence |
| not_selected | An unchosen branch; not successful and not failed |
| cancelled | No further steps will be dispatched; active action outcome is separate |
| outcome_unknown | Dispatch may have happened; reconciliation is required |

A stop records why, blocks dependents, preserves earlier data and does not undo
completed effects. Never turn conversion/read/condition errors into false.
No available quote differs from malformed data; neither permits the remote step.
Default action retry is never. Read retries, if allowed, have explicit bounds.

The journal distinguishes intent_recorded, dispatch_started, acknowledged,
completed and business_verified. A crash between dispatch and acknowledgement is
uncertain, not evidence that nothing ran. Neither leases nor local locks deliver
exactly-once remote effects. Need a target-side idempotency key or a verified
business-result query before claiming safe repeat execution.

Resume requires explicit scope, the original package and input digests, valid
authorization, and provider/resource reconciliation. Do not automatically replay
a remote command, browser submission, notification or whole recipe after restart.
Re-fetching mutable input produces a new attempt and revalidates any conditional
grant. Cancellation request, actual termination and cleanup remain separate.

## Records, retention and Web

Use a Profile-owned durable parent run and append-only attempt/decision events,
with references to child recipe results and verified artifacts. A future shared
service must provide atomic compare-and-set for claims, dispatch intent and
deduplication; clients must not directly patch journal files. Proposed storage:
workflow-runs/index.sqlite3 plus workflow-runs/<run-id>/artifacts/.
This is a design target, not a database created by these documents.

Record exact versions/digests, frozen month/timezone, step IDs/numbers, provider
identity, data handoff digests, branch expression/operand values/result,
authorization source and scope, command/identity, bounded output, exit code,
business verification and cleanup. Redact sensitive operand values before
persistence while retaining a nonsecret decision explanation and private reference.
Log capture failure before dispatch blocks writes; post-dispatch capture failure
preserves outcome uncertainty and forbids automatic replay.

A parent may finish command_completed while business outcome remains unverified.
A zero exit code is not the monthly job's business postcondition. Retention and
downstream content/notification receipts remain independent.

The future Recipes/Activity page should show one parent flow, numbered step
states, selected branches, waits and human-readable causes, with child host
cards and evidence links. Console rivers can carry actual command output through
their existing services; they are not the workflow authority or scheduler.

External exchange quotes are Profile/external-source data, not fabricated host
observations. Defining a Profile-scoped retention contract and consumer events
is implementation work; do not force quotes into a host-only schema.
Use existing child-result/retention interfaces where they fit. There is no new
retention producer or subscription implemented here.

## Export and import

The receiving agent must need no originating chat or private checkout history.
Export includes the plan, exact callable contracts and dependency closure,
routines/scripts, schemas, explicit resources, license/provenance, language
semantics, conformance vectors and requirements/manifest locks. A link to an
unavailable skill is not a closed dependency; include its required versioned
references or identify a prerequisite that must be satisfied before readiness.

Use normalized relative payload paths, reject traversal, escaping symlinks,
duplicate/case-colliding paths and unlisted payloads, and enforce declared size
limits. manifest.json lists payload sizes/digests; the manifest itself is excluded
from its payload list. The bundle identity is SHA-256 of the canonical manifest
(JSON using sorted keys, ensure_ascii=False, allow_nan=False and separators
(",", ":"), encoded as UTF-8 without a trailing newline). Publisher identity
requires independent verification; hashes alone do not authenticate the author.

Import is static candidate inspection, with no module import, flow execution,
dependency installation, browser opening or host connection. Check contracts,
runtime compatibility, all payload hashes and offline vectors. Bind private
targets/credentials locally, review effects and grants, then report readiness
or the exact unresolved dependency. Transport conformance is not installation
or execution permission.

Existing pack/unpack/transfer support is not extended merely by naming these
files. New feature prerequisites, descriptor support, package-validation code
and tests must ship together before current commands can claim flow support.
During development, prefer the unified design over legacy compatibility layers;
report affected descriptors/recipes/jobs and required user actions. Preserve old
data and evidence; no automatic rewrite/deletion is authorized.

## Delivery sequence and open decisions

1. This documentation/skill and offline design vectors: no runner or live case.
2. Review the flow semantics, task contracts, reference routines and case.
3. Build a private candidate recipe only under a separate concrete scope.
4. Implement shared product validators/providers/journal/import support with
   public success/failure/boundary tests and updated human/agent references.
5. Independently verify receiving agents using only exported material; exercise
   native browser/SSH/business-result behavior only when specifically authorized.

Before implementation, choose the actual descriptor/feature versions, provider
protocol, persistent journal service and quote-retention scope. Review the
monthly script's effects, idempotency and business postcondition. The fixed
remote invocation alone does not establish any of these properties. Notification
and alert steps need their own contracts, recipients, effects and authorization;
they are extension points, not delivered workflow features.

## Executable implementation available separately

[Python workflows 0.1.0](python-workflows.md) now supplies a narrow executable
`python-workflow` contract with explicit delayed host connection, browser evidence
handoff, fixed USD utilities and guarded command dispatch. It executes reviewed
Python, not this document's virtual flow language. Closed flow import validation,
general branching/resume execution and automatic browser providers remain proposed.

*Last modified: 2026-11-17 17:22:47*
