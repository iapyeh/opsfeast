---
name: opsfeast-interactive
description: Operate a persistent SSHScript shell with a human through chat and a visible Web river; use the shipped Console worker for incremental instructions or the separate exact-plan executor when that approval mode is selected.
---

# Use the interactive Console service

## Choose the interaction mode

For “connect to a host; I want to interact,” use the shipped chat-owned worker,
not the exact-plan executor below. Read [the chat-shell procedure](references/chat-shell.md)
and [worker protocol 0.1.0](../../docs/console-agent.md). Default to execution plus a brief acknowledgement; do not proactively analyze or repeat visible output. Analyze only when the human explicitly requests it. The human can supply details
one step at a time; do not demand a complete plan or repeat approval for already
explicitly authorized connection, sudo or read-only commands.

For an operator-selected exact plan with Web approval/checkpoints, follow the
separate procedure below. Never switch modes to bypass an existing approval gate.

## Exact-plan executor

Read [protocol 0.1.0](../../docs/interactive-console.md) and the installed release's
[SSHScript skill](../sshscript/SKILL.md), agent guide and embedded Console contract.
This is a checkout-level service, not a recipe retention producer or an agent-task
launcher. The CLI/HTTP interfaces are shared across agent products.

1. Establish the human's goal, exact profile/namespace/host scope and permitted
   effects. Obtain the work UUID created by the operator. Read the server's enabled
   targets and current snapshot. Work IDs do not authorize execution. No connection
   occurs merely from reading. Never switch profile or host to bypass a failure.
2. Use `python -B -m opsfeast.interactive_client --token-file FILE list|show|events`.
   The agent token is distinct from the operator token. Do not read/use the operator
   credential to self-approve, expose either token, or paste credentials in prompts.
3. Propose a bounded exact plan using `plan --work UUID` with JSON on stdin:
   title, approval_mode (`each` or `plan`), and steps containing command, purpose,
   checkpoint Boolean and timeout (1–60 seconds). State targets, privileges,
   side effects and expected evidence. No arbitrary Python or program stdin is
   supported. Each command must be one line without CR/LF, even inside shell
   quotes; encode a literal backslash-n as `\\n` in JSON for printf output.
   `command_must_be_single_line` rejects the whole plan before connection.
   Commands are not a sandbox: separate consequential actions into steps.
4. Wait for operator approval. Do not invoke another SSH tool or direct Session
   to bypass Web confirmation. Approved exact steps may continue to a checkpoint;
   new commands, privilege changes or exceptions require a revised reviewed plan.
   Never infer approval from feedback text, elapsed time or a browser closing.
5. Consume sequence-ordered events. Preserve unknown/failure/partial states and
   original output. Check snapshot seq; deduplicate repeats; recover gaps with a
   snapshot, never by rerunning commands. Only report actual returned identity.
6. Append analysis through `analysis --work UUID`, e.g. stdin JSON
   `{"content":{"kind":"table","columns":["Finding","Evidence"],"rows":[["Example","source step ID"]]}}`.
   Text uses `{"content":{"kind":"text","text":"..."}}`. Analysis is distinct from
   execution output; cite relevant step IDs and uncertainties. Tables/text are
   supported; charts, HTML and executable presentation code are not.
7. Treat stop_requested as a request, not a confirmed remote termination.
   Inspect the job result and cleanup separately. Never replay failed/unknown
   commands automatically or retry credentials. Report the typed failure and
   required decision. A restarted server preserves history but interrupts work;
   any new execution needs a fresh explicitly authorized work/plan.

Human feedback is an event, not shell input. Exact action retries must reuse the
same request_id and identical body; ambiguous work creation must be reconciled
through recent works rather than retried blindly. Host settings/credentials and
arbitrary program output may be sensitive: no passwords, private keys or secret
input in this first version. No su/sudo UI, raw stdin, general scheduling,
retention ingestion or automatic agent wakeup is delivered.

Examples and errors are defined by the canonical protocol; a fresh agent must
read it before operating. An external agent may need the user to provide the
reachable server/checkout and agent-token file path; never assume localhost refers
to the same machine across remote agent environments.

*Last modified: 2026-11-02 17:49:53*
