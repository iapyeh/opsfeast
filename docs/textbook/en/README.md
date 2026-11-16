# The OpsFeast textbook

**First edition · October 2026 · English**

[Textbook languages](../README.md)

Learn how to understand, operate and assess OpsFeast with your own AI agent. Start with a goal, select an existing capability, run a reviewed operation within its authorized scope, and examine the evidence. Keep the resulting knowledge reusable.

This directory is a standalone Markdown reading vault. Open `docs/textbook/en/` as a vault in Obsidian, or read these files in your editor or repository browser. No plugin, account, generated operational data or Obsidian configuration is required. Links to canonical reference material leave this directory and resolve inside the same checkout; some readers restrict navigation outside an opened vault. In that case, open the linked file from the checkout or consult the [repository documentation index](../../README.md). The book remains readable without those links, while exact contracts live in the reference documents.

This teaching vault is maintained with the product. A profile's `vault/` is a separate content application containing operational views and human notes. Do not point a profile's content publisher at this textbook.

## Read in order

| Chapter | What you will learn |
| --- | --- |
| [1. Intent, agents and reusable work](01-intent-and-agents.md) | Describe goals, define scope and assess an agent's plan. |
| [2. Architecture and the data journey](02-architecture.md) | Relate instances, profiles, recipes, observations, retention, consumers and services. |
| [3. Set up and take over an environment](03-setup-and-profiles.md) | Prepare a new installation or safely inspect an inherited one. |
| [4. Configure and connect one host](04-hosts-and-access.md) | Understand host IDs, authentication, jumps and execution identity. |
| [5. Discover and execute recipes](05-recipes-and-results.md) | Select a precise recipe, review its effects and revisit saved results. |
| [6. Inventory, freshness and scheduling](06-inventory.md) | Query properties, keep comparisons and opt into periodic collection. |
| [7. Read data and use the operational Vault](07-data-and-vault.md) | Separate current views, historical evidence and authoritative structured data. |
| [8. Consumers, notifications and todos](08-consumers-and-services.md) | Follow an event through policy, lifecycle, presentation and delivery. |
| [9. Reports and repeatable work](09-reports-and-reuse.md) | Generate offline artifacts and preserve reviewed invocations. |
| [10. Author, share, transfer and archive](10-portability.md) | Preserve reusable knowledge and move data with reviewed plans. |
| [11. Complete case: daily backup checks](11-backup-case.md) | Connect configuration, collection, interpretation, policy and recovery. |
| [12. Troubleshooting by evidence](12-troubleshooting.md) | Find the failing stage and choose the smallest appropriate recovery. |
| [Desk reference](reference.md) | Find commands, concepts, storage and authoritative guides quickly. |

## Choose a reading path

- **First use:** chapters 1–5, then chapter 11. Use the setup proposal before authorizing installation or initialization.
- **Daily operator:** chapters 5–8 and 12. Keep the desk reference open.
- **Recipe or report author:** chapters 1–2 and 9–11, then follow the linked recipe skill and contracts.
- **Taking over someone else's installation:** chapter 3, followed by chapters 7, 8 and 12. Inspect before making changes.
- **“The check finished, but something looks wrong”:** chapter 12, then the saved result and its separate persistence/delivery receipts.

## How to use the examples

Shell examples run from the OpsFeast checkout. `python` means the interpreter selected for that installation; it does not mean an arbitrary system Python. Examples use the synthetic profile name `main`, host IDs such as `server-01` and `backup-example`, and reserved example addresses. Substitute actual values before use. Identifiers such as `RESULT_ID`, `RECORD_ID`, `OBJECT_ID` and `PLAN_SHA256` must come from the preceding real command output.

Read each command's effects before running it. Inspection, configuration, connection, privilege acquisition, execution, scheduling, deletion and external delivery have different effects. Reuse authorization already given; ask for missing consequential scope rather than repeating approvals for the same work. A documented command is an instruction for a future operation, not evidence that it has run.

Agent prompts are examples of how a human can express intent. Have the agent supply actual paths, interpreter, profile, targets and returned IDs in its handoff. Keep credentials and private bindings local. The book uses synthetic examples and does not require a connection to learn the model.

Each chapter provides a practical workflow, interpretation and a checkpoint. Precise command syntax, schemas and extension interfaces remain in the linked canonical references; avoid copying their definitions into a competing manual.

## Edition boundaries

This edition follows the October 26, 2026 checkout's implemented interfaces, including SSHScript 7.0.0 support, recipe bundle 0.2.0 and independent recipe/observation/retention portability. Individual contract versions remain in their owning references. After an OpsFeast release update, agents must reread the installed release's current schemas and contracts, including the hosts guide; see [the update procedure](../../skill-updates.md).

TUI's intended role is independent human operation. This edition explains its current entrypoint and links its existing guide; full task walkthroughs will be added after the corresponding TUI updates and verification. There is no general bundled scheduler, live OpsBuffet exchange, todo executor or general logging service. Inventory has its own implemented scheduler. SMTP support exists, but actual SMTP delivery is not established by the evidence cited in this book.

For the exact scope of this edition's checks, read [verification notes](reference.md#edition-verification).

*Last modified: 2026-10-26 12:55:26*
