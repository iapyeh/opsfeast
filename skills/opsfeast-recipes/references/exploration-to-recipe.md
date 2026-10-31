# From interactive exploration to reusable operations

Use this workflow when a user and their agent discover an operational method and want future runs to use saved recipes, configuration, retention and content programs. It supplements the [recipes skill](../SKILL.md); it does not replace the versioned contracts it links. The completion criterion is a fresh agent rerunning reviewed artifacts without the original conversation or exploration Session.

## Transparency first; prefer failure to damage

Apply the [human-trust principle](../SKILL.md#human-trust-during-exploration-and-recipe-execution) throughout exploration and subsequent recipe runs: **看得見、停得下來、查得到發生過什麼事。** Visibility, control and traceable evidence let the user assess operations and build trust progressively.

Use the user's agreed approval unit: a reviewed plan, a recipe invocation, individual writes or every step. In step-confirmation mode, show the proposed operation, wait for approval, execute only that unit, show its result and wait before continuing. Under an agreed read-only allowance, reads may proceed within scope; writes and unclassified effects require confirmation. Reassess authorization when the target, identity, command or effects change. A recipe invocation does not supply internal approval checkpoints automatically; disclose that limit if the user requests finer control.

Identify how progress/output will be visible, where execution can pause or be interrupted, and what evidence will remain. Use incremental output when supported; explain when the tool only returns output after completion. A stop request prevents further dispatch; report interruption, remote termination and cleanup as separate outcomes, preserving unknown states. If the agreed control is unavailable, resolve that gap with the user before starting.

Before executing, show the actual command or API call with target, purpose and expected effects. Long reviewed code can be identified by its file plus the invocation and input structure; make the source available for inspection. Show changed commands and explain retries. Preserve time, target, identity, sanitized inputs, stdout/stderr or structured results, exit/error state, truncation and cleanup evidence. Do not describe a sanitized summary as a complete raw transcript. Platform/agent tool history can supply exploration records; a recipe must return or save its own repeatable, safe evidence. Secrets are placeholders with their source/transmission method, never literal arguments, history or report data. Mark redacted or omitted fields explicitly, including database error messages that can contain row values.

Record the approval or existing authorization that covered each execution unit, linking it to the actual operation and outcome where the available tools permit. Give the user retrievable evidence locations and state missing events or outputs. Recipe raw results, retained data and agent history have different coverage; none alone guarantees a complete interaction log. This procedure does not introduce a new logging service or machine-enforced approval mechanism.

Judge actual effects before running, including shell expansion, subprocesses and configured hooks. A check label or SELECT keyword alone is not evidence of safety. Deletion, overwriting system files, important configuration changes, database writes, service interruption and comparable destructive actions require explicit authorization covering concrete targets, commands and effects. Prepare reviewable changes first; explain rollback/backup limits where applicable. Reuse authorization already granted for the same scope; an exploratory read does not authorize repair, source-host access, privilege escalation or scheduling. Stop on uncertain targets or unbounded damage. Offer a safer alternative and refuse execution when risk cannot reasonably be controlled, even if a broad request was given.

For temporary Python/Core exploration, use the [authorized operation example](../../../docs/core-agent-operations.md) before writing a shell invocation. Preserve literal dollar signs across local Python and remote shell boundaries, use public imports and host-ID dictionary iteration, and distinguish per-command timeout, original operation failure and cleanup evidence. Do not automatically retry uncertain writes.

## Discover, then explore within scope

Read [capabilities](../../../docs/agent-capabilities.md), the [catalog](../../../recipes/README.md) and applicable tool skills first. Reuse reviewed recipes, configuration loading, account policy, connections and result/retention/consumer lifecycles. State the missing capability before creating code. Select only task-relevant contracts, not every guide.

Establish the question, health/unknown criteria, targets/instances and allowed effects from the user and trusted runtime configuration. Ask only for material missing information. Prefer SSHScript where suitable; use its version-matched public skill and [Core](../../../docs/core-api.md). A retained Console can support exploration; it is optional. Preserve its Session, thread ownership and cleanup rules. Interactive programs use enter(); shell jobs do not accept arbitrary stdin. Do not infer verified identity or state from prompt text.

Keep bounded evidence of the calls that answered the question, actual SSH/effective/service identities, output fields/units/sample times, errors and cleanup. Diagnose environment, proxy, connection, authentication and service failures separately. Do not blindly retry passwords, change accounts or widen operations. A temporary process-level environment correction is not permission to modify global configuration. Distinguish tested behavior from a general product guarantee.

## Propose the complete reusable design

Before implementation, describe recipe classification/support, inputs and private bindings, execution/results, retention schema, consumers/output ownership, and validation limits. Identify product/version/multiple-instance differences. Do not encode the current host, password or observations into public artifacts. A successful interactive command is evidence for the design, not a portable implementation by itself.

Use [taxonomy/location](../../../docs/recipe-taxonomy.md): users normally write profile-root/recipes/<classified-path>; product developers add reusable bundled capabilities. Keep domain-specific semantics in product recipes rather than forcing incompatible systems behind a nominally generic path.

## Implement config and deterministic execution

Use the [authoring guide](../../../docs/recipe-authoring.md) and current [runner contract](../../../docs/recipe-execution.md). Prefer finite batch/API operations when they replace the exploratory REPL cleanly. Use the supplied Recipe/session, existing credential/privilege policies and strict cleanup, not independent reconnect or account-selection loops. The executable recipe must work from a fresh process without the exploration's variables, cwd or environment.

Declare typed inputs. Put bindings under exact-reference default/group/host `recipes.REFERENCE.vars`, following [input precedence](../../../docs/recipe-sources.md#variables-and-implementation-context); ordinary host/account vars do not implicitly become recipe inputs. Separate controller/SSH host from service endpoint and instance. Distinguish missing, empty, zero and false. Validate all intended operations before starting them. No hidden credential prompt in routine execution. Keep secrets in private configuration or an explicitly supported secret source, and document temporary writes, ownership and cleanup uncertainty. Never put credentials in executable argv or model-generated source.

## Define retention and consumption together

The recipe creator owns the retained schema/version, meanings, units, provenance, sample times, saved policy/findings and limitations. Reuse [supported contracts](../../../docs/retention.md); scalar host-values cannot represent arbitrary nested multi-instance data. Do not stringify a dataset to evade its schema. General recipes can use registered structured retention. Registration requires reviewed schema/normalizer/platform integration and tests; arbitrary candidate modules are not loaded by replay. If a required platform facility is missing, ordinary users report the concrete gap. Product developers supply a reusable facility instead of assigning each user repeated infrastructure work.

Successful collection and unhealthy service are distinct: preserve a valid adverse observation with partial execution where appropriate; failed queries remain failures, not empty healthy samples. Collection, retention and content delivery have separate receipts. Preserve null/partial/unknown and independently sampled sources. Do not infer upstream catch-up or data equality from local status alone.

Consumers read public retention APIs without reconnecting or parsing raw output. Prefer the bundled Vault when suitable. Extend its supported renderer or create an explicitly registered consumer with declared subscriptions and owned paths; do not put content templates in retention. Read [consumer contracts](../../../docs/retention-consumers.md) and [Vault ownership](../../../docs/host-vault.md). Protect human notes, preserve complete safe historical evidence and show readable current results. Only deliver the consumption the user needs, and state any unavailable/disabled pieces.

## Verify, hand off and maintain

Use credential-free success/failure/boundary fixtures first, then authorized real targets. Finalize executable code and the retention schema/normalizer before final operational acceptance: snapshots bind their digests. If they change later, preserve earlier evidence and repeat the necessary checks; never rewrite old successful receipts to match the new artifact. Test observable behavior, not generated headings or code spelling. Verify input resolution, command failure/timeout, safe evidence, secret exclusion, resource cleanup/unknown, raw-to-retained validation/replay and consumer output through the real entrypoints. Use fresh temporary profiles for synthetic tests; do not migrate existing profiles to make a test pass. State mocks/local PTY/real SSH/database evidence separately. Never turn source-side checks, repair or installation into implied authorization.

Deliver discoverable code, canonical instructions, private config examples, data contracts, consumer requirements/output locations and reproducible tests. Show the exact next invocation, how to inspect results/history and what nonzero/partial/unknown means. Confirm a new process can repeat the operation. Update the skill routing/capability map and relevant human guides; do not claim a prototype or documented procedure is a shipped API. Commit/push/publication remain separate scopes.

### Finish the user handoff, not just the program

Do not make the user reconstruct configuration from the exploration or copy secrets out of the conversation into a template. Reuse confirmed host/instance/credential/expectation facts to prepare the actual target-specific settings. Resolve the definition source through Validator: a host can originate in an included YAML, so do not assume the entry hosts.yaml owns it. Explain the exact change and secret-storage method; apply when authorized without asking again. Important configuration changes still require concrete authorization. Back up privately, preserve unrelated bytes/settings, use protected atomic replacement and validate/restore on failure. Entry hosts.yaml and included YAML have different policies; a temporary filename is not a substitute entrypoint for Validator. Prevalidate the added typed inputs and validate the real entrypoint after replacement with rollback available. Do not create duplicate host definitions or move secrets into a public bundle. Report what was applied versus left pending.

Give a copy/paste-ready invocation for the actual installation/interpreter, selected profile, recipe and hosts. Include the real cd command or absolute paths when needed and any verified process-local environment requirement. Once private configuration is applied, the routine command should not need pasted passwords, a regenerated script, --var secrets or manual recipe reconstruction. Do not leave generic HOST/NAME/PATH placeholders when the facts are already known. Scope-specific details belong in the private handoff, not shared skill examples.

State where this execution's results can be read: raw result, readable consumer entrypoint and retained history. Explain separate execution/retention/publication failures. In human TTY mode recipes run prints existing raw paths and successful Vault entrypoints; batches use the raw directory and Vault index. A current page is latest state, whereas raw/result IDs identify the particular attempt. Do not point to an old page as newly published after disabled/failed delivery. JSON/pipe output remains structured. Reuse host_vault.result_locations(root, host=..., record_id=...) for read-only manifest-owned Vault entrypoints; never hand-code group/filename paths. Give a usable fallback if content is unavailable. Verify the routine command from a fresh process using the saved configuration when target execution is authorized; otherwise identify the untested scope explicitly.

When use reveals a repeated decision failure, update this workflow or its canonical reference and add a meaningful regression scenario. Interface/config/retention/consumer changes require a routing/example review. Preserve evidence and replace obsolete guidance rather than accumulating special cases. Evaluate whether a fresh agent can choose existing capabilities, avoid dangerous scope expansion and complete the workflow without the originating chat. This maintenance procedure is not an automatic monitor or enforcement service.

The [MySQL/MariaDB replication recipe](../../../recipes/database/mysql/check/replication/README.md) is a worked implementation: interactive discovery became fixed SQL, per-instance private configuration, mysql-replication 0.1.0 retention and builtin:vault views. It is an example, not a mandatory database dependency or a complete cross-product validation claim.

## Verify the actual completion path

For completion/output changes, test the actual public CLI entrypoint through its
runner, compact-summary projection and terminal renderer, plus forced JSON and
non-TTY output. A renderer test fed the full saved raw report can hide fields lost
by an intermediate summary. Compare fresh completion and history with the same
recorded identity evidence; never repair a display gap by guessing configured
accounts or reconnecting. Keep synthetic backend boundaries explicit when testing
the real CLI so tests cannot accidentally execute a managed-host operation.

*Last modified: 2026-10-31 06:55:32*
