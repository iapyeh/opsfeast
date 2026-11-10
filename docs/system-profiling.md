# System profiling and persistent services architecture

## Product responsibility

OpsFeast is a human-owned workspace for managing systems together with the
human's chosen agents. Humans choose goals, targets, permissions and consequential
changes. Bundled product capabilities must discover, collect, retain and present
broad system information without requiring each user to assemble their own probes.
Agents investigate new needs and exceptions; reviewed programs carry repetition.

A supported platform has a documented coverage matrix, not an unconditional claim
that every field can be obtained. Root access does not expose hypervisor hardware
inside every guest, recover unrecorded events or create missing device interfaces.
Report unavailable, unsupported, denied, uncollected, partial and failed evidence.

## Architecture and responsibility boundaries

```text
Human / Agent
  -> Web UI / CLI / documented Python interfaces
    -> shared product services
       - host/account configuration and conflict handling
       - profiling capability discovery and collection coordination
       - execution, retention queries and data lifecycle
       - policies, notifications and delivery
    -> recipes / other reviewed collectors
      -> retention (versioned observations and provenance)
        -> consumers / shared read projections
          -> Web views, reports, notifications and todos

OpsFeast daemon (target architecture)
  - HTTP hosting
  - scheduled/background acquisition and consumer work
  - notification outbox delivery
  - optional IRC client and server integration
  - health, restart/recovery and work-state management
```

These are logical boundaries, not a requirement for one process. Blocking or failed
collectors and communication providers must not block the Web viewer. Product
services remain callable by CLI and agents; the browser must not implement domain
rules independently. Consumer-generated artifacts are optional projections, not
the authoritative observations. Interactive Web reads may use shared read services
without generating a new artifact for each request.

### Profiling and collectors

The product owns discoverable capability IDs, domain routing and reviewed provider
bindings. Providers own acquisition methods and their declared versioned data
contracts. The inventory recipe remains a foundational collector; it is not the
limit of profiling and does not own the product's entire coverage model.

Collection coordination must eventually discover platform, available tools,
privileges and instances, then select applicable deeper probes within the existing
human grant. Missing methods become product gaps, rather than permanent user-side
scripts. Provider registration does not authorize code execution, install tools,
connect to targets or schedule work. New execution adapters require reviewed code,
data contracts, bounded execution and public failure/boundary tests.

### Retention and consumers

Preserve source times, sampling windows, units, stable object keys, actor scope and
original success/partial/failure states. A new failed attempt must not become an
old successful value. Successful empty enumeration differs from failed collection;
only complete enumeration supports disappearance claims. Rates require comparable
counter samples and reset/restart handling.

Do not put presentation templates in recipe data contracts. Consumers and shared
read projections can combine retained datasets, preserve mixed-age evidence and
show coverage gaps. Acquisition, raw saving, retention, consumer processing and
external delivery need independent outcomes. Rebuilding views cannot manufacture
new observations or current incidents from imported history.

Configuration, schedules, delivery outboxes and human decisions have their own
persistent service state; they are not all inventory observations.

### Daemon and agents

The intended long-running daemon survives individual agent conversations. It runs
explicitly configured work without a continuously active model. Agents attach,
inspect evidence and submit authorized work; known policies and reviewed programs
continue after they leave. Unknown situations remain recorded for human/agent
review. A received message does not accept work or authorize a command.

HTTP is one daemon function. Scheduler, delivery and communication workers share
product services and durable work state. A scheduler must define overlap, missed
runs, cancellation, restart and retry semantics. Delivery must preserve pending,
failed and unknown outcomes; uncertain sending cannot promise exactly once.
Existing agent-owned Console controllers are interactive services, not this future
independent daemon lifecycle. Preserve them until a tested replacement exists.

Mail initially reuses SMTP delivery and persistent outbox semantics; accepting SMTP
submissions is a separate interface. IRC keeps standards-based interchangeable
servers and explicit capability checks. An optional managed external IRC server
is acceptable; no requirement to implement a new protocol server. IRC work remains
later-stage; persistent receiving never implies automatic model interpretation or
work acceptance.

## Profiling scope

The product catalog groups capabilities into eight domains. Every domain may have
inventory, configuration, state, metrics and event observations; baseline analysis
consumes them across domains rather than becoming another collector.

```text
System profiling
|-- hardware: identity, CPU/RAM, expansion, firmware, sensors and health
|-- storage: media/paths, layers, filesystems, capacity, health and I/O
|-- software: OS/kernel, packages/tools, runtimes/modules and libraries
|-- network: interfaces, addressing, DNS/routes, policy, endpoints and traffic
|-- workloads: services/apps, databases, schedules, processes and resource pressure
|-- identity: accounts/groups, authentication, privileges and access events
|-- observability: logs/audit, retention/forwarding and monitoring agents
`-- analysis: configuration drift, performance baselines and behavior correlation
```

Full review also includes manufacturing identifiers, device relationships, firmware,
per-environment language packages, active-versus-installed libraries, service
instances, time synchronization, partition/inode/thin-pool limits, inbound/outbound
activity, authentication failures and process lifecycles. Software package lists
are not automatically a full SBOM. Listening is not external reachability. Deleted
executables and unusual login times are evidence, not automatic maliciousness.
Never collect passwords, private keys or community strings as ordinary profile data.

Long-lived configuration uses initial discovery and periodic/event-triggered
refresh; utilization uses explicit sampling windows; short-lived processes,
connections and login activity need event/incremental/continuous sources where
supported. Faster snapshots cannot guarantee complete event history.

## Host identity and human responsibility

An entity is the management object identified by a user-chosen Host ID within a
retention namespace. VM hosts and guests are separate objects connected by hosting
relationships. No installation-entity hierarchy or automatic physical matching is
required. MACs, serials, machine-id and host keys are evidence, not identity keys
that silently split or merge hosts. Titles/descriptions help human recognition.
Users choose whether reinstall, replacement or restoration continues an ID.

- Reject duplicate active configuration for the same ID in the same scope.
- On contradictory evidence, show the conflict and block the conflicting write;
  do not guess which machine owns the history. Undetectable clones remain a stated
  limit, with correct naming/binding the user's responsibility.
- If configuration was removed but history remains, creation must preview old
  identity/context, dates and data quantity. Explicit continuation associates old
  history with the newly configured host; cancel or choose another ID otherwise.
- Continuation preserves original observations and records the decision. It does
  not implicitly restore credentials, schedules or privileged authorization.
- Import conflicts require an explicit rename, merge or skip decision. No silent
  overwrite. Noninteractive operations need explicit scoped choices too.

These are agreed target behaviors, not a claim that all current create/import
interfaces implement these checks. Existing administrator-assigned identity_key
behavior requires a separate reviewed decision before removal or reinterpretation;
this design does not rewrite old identity bindings.

## Host/account data lifecycle

Deletion needs a concrete preview, not an ambiguous delete-host button:

| Choice | Scope |
| --- | --- |
| Remove configuration | Registration, host-specific connection settings and scheduling; preserve history and human content. |
| Clear history | Selected period or all observations/raw results and corresponding generated content; preserve configuration. |
| Full removal | Configuration, history and explicitly selected exclusive records/content, with retained exceptions listed. |

Preview namespace/Host ID, periods, counts/bytes, human notes, credentials,
notifications/todos, shared artifacts, active work and automation. Reconcile active
writes and schedules before executing deletion. Shared multi-host Console records,
reports and credentials need explicit choices; never delete another host's data by
implication. External exports, backups, delivered mail and IRC messages are not
silently erased. Logical deletion is not forensic secure erasure. Report partial
failure and residual data; recreate-from-empty is true only if no retained history
remains. Any residual data must be disclosed when reusing the ID.

Account removal separately means removing OpsFeast configuration, deleting its
exclusive saved credentials, or an explicitly authorized remote OS operation.
Identify direct login, jump-host, sudo/su, scheduled and active-work dependencies.
Offer replacement or disable affected work. Preserve historical actor identity
unless history deletion was also selected; never store secret values in history.
Deleting a host/configuration does not delete remote OS users or home directories.

## Delivery sequence and implemented boundary

1. **Capability and read-model foundation (delivered):** a shared data-only
   profiling catalog, inventory provider integration, CLI/Python discovery and
   saved host evidence in Web. All current inventory properties are routed;
   missing integrations are visible. Existing acquisition, retention schemas and
   execution/schedule authorization remain unchanged.
2. **Acquisition expansion (first batch delivered):** the
   [seven-recipe baseline review](profiling-coverage.md) separates acquisition and
   integration gaps. Existing disk/RAID and configured MySQL data now have adapters;
   two new Linux recipes supply local account/group and visible process snapshots.
   Deeper collectors, event sources and capability-aware collection planning remain
   subsequent work, with reproducible platform tests required.
3. **Identity and data lifecycle:** implement history-continuation/import decisions,
   conflict checks and deletion plans across stores, including accounts/dependencies.
4. **Persistent services:** implement independent daemon lifecycle, durable work
   dispatch, consumer/delivery workers and general scheduling with recovery tests.
5. **Broader communication:** add mail submission if needed and IRC integration
   through the shared services. Existing SMTP/inventory cron remain separate current
   capabilities, not evidence that a general daemon already exists.

Each stage ships interfaces, Web/CLI behavior, skills, failure semantics and public
tests together. Static catalog integration is not platform applicability, fresh
collection, complete coverage or an anomaly detector. The first inventory adapter
reads existing retained observations; it cannot show raw-only acquisition failures
as retained property attempts. Use saved-result diagnosis for those failures.


## Policy/settings acquisition increment

The [next acquisition batch](linux-policy-profiling.md) now supplies five scoped
policy/configuration recipes using the same acquisition service, portable retention,
consumer delivery and Web projection. It closes first integrations for SSH, sudo,
firewall, time state/configuration and logging settings. This does not implement
host deletion, independent daemon/scheduling, effective cross-source reconciliation
or native verification. Remaining partial details and twelve unintegrated capability
areas remain explicit in the [coverage review](profiling-coverage.md).

## Recipe menu and human-confirmed execution

The [recipe menu 0.1.0](web-recipe-menu.md) now delivers the planned
Web selection workflow: recipe purpose/limits, suggested combinations, the shared
39-capability blueprint, exact targets and inputs, review/confirmation, serial
runner progress/stop and saved receipts. This is separate from read-only saved-data
and profiling views. Opening a viewer or history never collects or retries work.
The original profiling blueprint remains the Bundle target, not a claim that all
current capabilities are complete.

*Last modified: 2026-11-09 16:21:20*
