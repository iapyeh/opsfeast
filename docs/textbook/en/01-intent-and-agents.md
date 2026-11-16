# 1. Intent, agents and reusable work

[Book home](README.md) · Next: [Architecture](02-architecture.md)

OpsFeast turns operational intent into reviewed, repeatable work. A human chooses the goal and consequential scope. An agent discovers existing tools, prepares the configuration and execution plan, handles implementation details, and explains the evidence. Repeated work should run saved programs and settings rather than require another conversation to recreate the same logic.

## Start with a question you can verify

“Check the backups” leaves several decisions unresolved. A useful request names the destination host, expected files, date/timezone policy and what a successful check establishes. For example:

> In profile main, check whether today's two database dump files are present on backup-example. Use the saved filename patterns and Asia/Taipei deadline. Read directory metadata only. Preserve the result and explain missing files, incomplete scans and old or unexpected entries separately. Do not delete anything or send mail.

The agent should reuse the shipped backup-check capability before writing another scanner. If the necessary policy is already saved, it should use that policy and ask only about missing or conflicting details. It should provide a concrete plan that can be reviewed: exact target, existing recipe/reference, account, operations, persistent output and expected interpretation.

## Divide the work sensibly

| Human supplies or decides | Agent discovers or prepares |
| --- | --- |
| Desired outcome and operational importance | Suitable existing CLI/module/recipe and its limits |
| Allowed targets, accounts and effects | Resolved profile, recipe reference and input configuration |
| Missing business rules, such as a backup deadline | A proposed precise rule with examples and boundary cases |
| Decisions such as enabling mail or deleting data | The concrete reviewed change and recovery procedure |
| Whether evidence satisfies the goal | Source times, actual identity, partial states and unresolved gaps |

You should not need to design framework code, manually assemble SQL storage or learn every CLI flag. Product interfaces and agent skills should supply that reusable support. If a basic need lacks a usable interface, record the gap instead of hiding it behind a private workaround.

## Make scope concrete without repeated approvals

A setup request may authorize installing disclosed local dependencies and initializing a profile. It does not automatically authorize SSH connections. A recipe run may authorize the necessary configured jumps and its stated read operations. It does not authorize repairs, deletion or ongoing execution. Enabling a scheduled job introduces future operations; enabling a delivery route introduces future external effects.

Once you have approved a concrete plan, the agent should complete that plan without asking the same question at every step. New questions are appropriate when correctness or risk depends on missing information: an ambiguous target, a destructive change, a new recipient or a privilege requirement outside the agreed scope.

Useful request patterns:

> Inspect profile main without connecting. Explain the available recipes, configuration gaps and where previous evidence lives.

> I authorize one read-only inventory run on server-01 with the recipe's documented bounded privilege policy. Show the command, run it, and report execution, retention and publication separately.

> Turn this reviewed investigation into a profile-local recipe, typed settings, retained data and tests. Preserve private bindings locally and supply an exact rerun command. Do not add scheduling or delivery.

## Judge the result at several levels

Ask whether the program ran, whether its observation is complete, what the finding means, whether the evidence was stored, and whether consumers or delivery succeeded. These are related questions with different answers. A successful metadata scan can discover expired files; a report can successfully describe a failed operation; retained data can survive a failed Vault update.

The agent's handoff should state the actual profile and targets, executed operation, observed account, original observation time, result locations, separate failed stages and remaining verification limits. “PASS” alone is insufficient to decide that a service is healthy or a backup can be restored.

## Keep the learning reusable

After a useful one-time investigation, preserve reviewed logic as a recipe or report, parameters as private configuration, findings as interpretable data and human context as notes. A saved invocation can make reruns convenient. Scheduling still needs an explicit scope and a real scheduler.

**Checkpoint:** Explain what your next request permits the agent to change, how you will recognize success, and which facts are still unknown. If you cannot, refine the goal before broadening execution.

Canonical guidance: [vision](../../vision.md), [agent capability map](../../agent-capabilities.md), [skill index](../../../skills/README.md), and [exploration to reusable recipe](../../../skills/opsfeast-recipes/references/exploration-to-recipe.md).

*Last modified: 2026-10-26 12:55:26*
