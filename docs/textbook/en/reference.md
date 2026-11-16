# Desk reference

[Book home](README.md) · Previous: [Troubleshooting](12-troubleshooting.md)

Use this page after reading the relevant workflow chapter. Commands run from the actual checkout with its selected interpreter. Use actual profile/host names and IDs returned by prior commands; the examples below use synthetic values. Read `--help` for the selected command and use `--json` where supported for agent parsing.

## Find an operation

| I want to… | Start here | Effects |
| --- | --- | --- |
| Check the interpreter/packages | `python -B tools/check_environment.py` | Read readiness; no install or host connection |
| Find registered roots | `python -B tools/opsfeast.py profiles` | Read locator availability |
| Validate a profile | `python -B tools/opsfeast.py check --profile main --json` | Read configuration; no connectivity proof |
| Inspect bundled recipes before setup | `python -B tools/opsfeast.py recipes list --checkout-only --json` | Read metadata; no candidate execution |
| Inspect one recipe | `python -B tools/opsfeast.py recipes show system/inventory/overview --profile main --json` | Read metadata/dependencies |
| Test one connection | `python -B tools/opsfeast.py test-connection server-01 --profile main --json` | Connect and run hostname/date; no privilege test |
| Discover inventory properties | `python -B tools/opsfeast.py inventory describe --json` | Read definitions; no profile needed |
| Query capacity without storage | `python -B tools/opsfeast.py inventory query --host server-01 --property storage.filesystems.used_percent --profile main --json` | Connect/probe with bounded actor policy; no OpsFeast persistence |
| Save a capacity observation | `python -B tools/opsfeast.py inventory run --host server-01 --job storage-capacity --profile main --json` | Connect, save and attempt downstream processing |
| Read batch history | `python -B tools/opsfeast.py observation --profile main --json` | Read explicit saved membership/outcomes |
| Diagnose a host result | `python -B tools/opsfeast.py observation result RESULT_ID --profile main --json` | Read focused saved evidence |
| Find retained records | `python -B tools/opsfeast.py retention list --profile main --json` | Read structured data |
| Read one retained record | `python -B tools/opsfeast.py retention show RECORD_ID --profile main --json` | Read full record/provenance |
| Inspect content state | `python -B tools/opsfeast.py vault inspect --profile main --json` | Read bundled Vault status |
| Regenerate bundled content | `python -B tools/opsfeast.py vault rebuild --profile main --json` | Write owned content; no recollection |
| Inspect downstream attempts | `python -B tools/opsfeast.py consumers inspect --profile main --json` | Read consumer receipts |
| Inspect service availability | `python -B tools/opsfeast.py services inspect --profile main --json` | Read static configuration/status; no send |
| Read todos | `python -B tools/opsfeast.py services list --kind todo --profile main --json` | Read lifecycle objects |
| Inspect transfers/archives | `python -B tools/opsfeast.py transfer receipts --profile main --json` | Read recovery receipts |

Configuration writers, consumer/service dispatch, scheduling, replay application, recipe installation, import and archive application have consequential effects beyond these reads. Follow their chapters and canonical references instead of inferring behavior from the command name. In particular, dispatch may run configured external delivery, and archive-plan writes a frozen local plan.

## Resolve an identifier

| Identifier | Meaning | Use it with |
| --- | --- | --- |
| Profile name | Registration selecting one management root | `--profile` |
| Host ID | Logical host within configuration/history scope | Target or data selectors |
| Exact recipe reference | Source plus filesystem recipe path | Settings, execution, jobs, subscriptions |
| Recipe ID | Descriptor identity that can be ambiguous across paths/sources | Metadata and documented ID filters |
| Observation run ID | Explicit batch membership and outcomes | Observation/run interfaces |
| Result ID | Saved host or report result location/selector | `observation result` or `recipes results` according to kind |
| Record ID | One authoritative retained record | `retention show` |
| Source observation ID | Original execution identity carried into retention | Provenance and documented replay/deletion selectors |
| Service object ID + revision | Current notification/todo and concurrency token | `services show/update` |
| Transfer unit ID | Origin-preserving portable observation or retention unit | `transfer show/export` |
| Plan SHA-256 | Fingerprint of reviewed package/target/selection state | Matching transfer apply operation |
| Receipt ID | Durable record of an import/archive/recipe installation | Corresponding recovery/resume/rollback plan |

Never interchange these IDs just because two happen to have a UUID shape. Short result aliases are root-scoped conveniences; full IDs and provenance are more appropriate for durable automation.

## Choose the knowledge source

| Question | Canonical source |
| --- | --- |
| Product intent and human/agent roles | [Vision](../../vision.md) |
| Exact CLI flags, output and exit codes | [CLI reference](../../cli.md) |
| Current reusable tools/modules | [Capability map](../../agent-capabilities.md) |
| Agent task routing | [Skill index](../../../skills/README.md) |
| Installation and first use | [Getting started](../../getting-started.md), [first-use walkthrough](../../first-use.md) |
| Profile storage and registration | [Profiles](../../profiles.md) |
| Host fields, include/path semantics and credentials | [hosts.yaml](../../hosts-yaml.md), [first host](../../first-host.md) |
| Privilege diagnostics and collection scope | [Diagnostics](../../host-diagnostics.md), [inventory access](../../inventory-access.md) |
| Recipe references, inheritance and enablement | [Sources and policy](../../recipe-sources.md) |
| Recipe discovery, reports, artifacts and saved jobs | [Recipe experience](../../recipe-experience.md) |
| Operational entrypoints, inputs and output | [Execution](../../recipe-execution.md) |
| Finding assessment versus execution account/status | [Results and accounts](../../recipe-results-and-accounts.md) |
| Property/job selection, freshness and cron | [Inventory jobs](../../inventory-jobs.md), [collection table](../../../recipes/system/inventory/overview/collection-plan.md) |
| Structured history and reusable readers | [Retention](../../retention.md), [Core API](../../core-api.md), [result-data guide](../../result-data.md) |
| Content paths, notes and generated ownership | [Operational Vault](../../host-vault.md) |
| Offline raw recovery | [Retention replay](../../retention-replay.md) |
| Events, activation and retries | [Consumers](../../retention-consumers.md), [consumer catalog](../../../consumers/README.md) |
| Notification/todo state and presentation/delivery | [Services](../../services.md), [adapters](../../service-adapters.md) |
| Backup presence/date policy and complete portable code | [Backup checks](../../backup-file-checks.md) |
| Recipe authoring, acquisition and sharing | [Authoring](../../recipe-authoring.md), [acquisition](../../recipe-acquisition.md), [sharing](../../recipe-sharing.md) |
| Origin-preserving transfer, installation and archival | [Portability](../../portability.md), [portable contracts](../../portable-contracts.md) |
| Release/schema/skill update procedure | [Skill updates](../../skill-updates.md) |
| Currently implemented TUI | [Terminal UI](../../terminal-ui.md) |

## Vocabulary for interpreting evidence

**Success** describes the operation's contract, while a **finding** describes what it observed. **Partial** preserves incomplete useful evidence; **unknown** must not be converted to healthy or empty. **Skipped** means an operation did not run for its recorded reason, and **unsupported** identifies a coverage gap.

**Sample time** belongs to the measurement; **generation time** belongs to its presentation. **Retention** preserves structured history; **projection** is a rebuildable view. **Replay** interprets saved raw without recollection; **import** validates already saved portable evidence; **archive** verifies a package before authorized source cleanup.

**Acknowledgement** records a human interaction. **Resolution** follows condition lifecycle. **Delivery** records adapter/provider outcome. **Verified work completion** requires the relevant operational evidence; a todo state alone does not supply it.

## Edition verification

This first edition is documentation-only. Its local verification checks chapter/navigation/reference links and heading targets, one modification footer per touched document, Markdown fences, synthetic example configuration, and documented CLI examples against the current argument parser. The parser check stops immediately after argument parsing, before command execution; help invocations also exit without performing operations. No textbook example runs a host operation, initialization, configuration mutation, report generation, dispatch, import, archive or schedule during those checks. No rendering claim for native Obsidian or every Markdown reader follows from link checking.

The book's claims follow owning guides and current parser/code where required. Links to public product tests explain existing evidence; they do not mean this documentation task reran the full product test matrix or established new SSH, privilege, SMTP, scheduler or restore evidence. Product code, schemas, dependencies and operational skills are unchanged. The skill index only gains a route to the human learning path.

Maintain this book with relevant product changes. Update explanations, interaction examples and checkpoints; keep exact contracts in canonical references. Add fuller TUI workflows only after implementation and verification. Include original source-time and partial/unknown interpretation in future examples, and preserve the separation between public synthetic teaching material and private runtime data.

*Last modified: 2026-10-26 12:55:26*
