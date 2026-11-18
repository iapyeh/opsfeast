# Explain partial inventory and saved-result failures

Terminal execution summaries now list the exact incomplete properties under
each job/reason count. A count of four means four distinct requested property
paths, not necessarily four devices or four failed commands. For example,
`network.interfaces.kind` and three `storage.block_devices.*` properties may
share successful source commands whose output omitted some values.
`value_not_reported` means the selected output did not supply the value; it does
not prove a permission problem. Use the printed `observation result ID` command
for saved source commands, exit codes and bounded stderr; add `--limit 50` for
more diagnosis groups. These inspections do not connect or rerun collection.


`partial` means the requested collection is incomplete. Successfully collected
values remain useful; missing fields are not a host-health verdict. Unsupported
platform properties, failed commands, parsing errors, permissions and time/output
limits must remain distinguishable. A successful IP query does not establish that
all other requested properties succeeded.

## Human entrypoints

- After `recipes run`, the terminal keeps `PARTIAL` and adds counts of incomplete
  properties grouped by reason, plus an exact saved-result diagnosis command.
- On Web **Hosts → host summary**, the **最近盤點結果** panel shows the latest
  saved inventory status and a **查看結果與未完成原因** link.
- On Web **活動與紀錄**, open a Recipe batch and choose a host under
  **主機結果**. Web plate timestamps open the original execution
  page with its shared river, task results and incomplete-stage summaries.
  CLI-only observations retain their summary/diagnosis entrypoints. The diagnosis page lists job, incomplete properties,
  reasons and source times, followed by bounded command/error evidence. For
  saved inventory results, **本次採集結果** lists successful field values and
  their sample times from the exact execution, including values in partial runs.
- Direct CLI inspection is read-only:

  ```sh
  python -B tools/opsfeast.py observation result RESULT_ID --profile NAME
  python -B tools/opsfeast.py observation result RESULT_ID --profile NAME --limit 50 --json
  ```

The default diagnosis shows at most five issue groups and five coverage groups;
use `--limit` (1–50) or the Web **載入更多** button for more. Omitted counts remain
explicit. Complete original evidence is available via `observation result ID --raw`.
Diagnosis never connects, recollects, retries or repairs a host.

## Reusable interfaces

Reuse checkout-level `result_diagnostics.diagnose(root, identifier, limit=5,
kind='operation')` for saved results. Its existing diagnosis 0.1.0 response now
adds `coverage_gap_count`, `coverage_gaps` and `omitted_coverage_groups`. Each gap
has job, properties, reason_code, source_id and observed_at. Unsupported/unattempted
properties are included in coverage gaps even when excluded from command-failure
issues. The pure `coverage_gaps(raw)` helper supplies the same classification to
live completion summaries; `recipes run --json` includes `collection_gaps` per host.
These are derived views, not another authoritative log or a new health policy.

The administrator/owner-protected Web adapters are:

- `GET /api/v1/results/latest?profile=NAME&host_id=HOST`: latest configured-host
  inventory metadata, or `result: null`; invalid stored-result counts stay visible.
- `GET /api/v1/results/diagnosis?profile=NAME&result_id=ID&limit=5`: the same saved
  diagnosis plus selected Profile. IDs use the existing safe short/relative-path
  lookup. The Web response includes `collected_samples` with up to 50 successful
  inventory samples per page, `total` and `next_offset`. Pass `sample_offset`
  for a later page. Values longer than 2,048 characters are explicitly clipped.
  The original result remains available via `observation result ID --raw`.
  No arbitrary file access or cross-Profile fallback is introduced.

Unauthorized reads return 401; invalid arguments/IDs/configuration return 422;
diagnosis storage failures return 503. Web links retain the Profile. Command output
is escaped and bounded by the existing diagnosis excerpts; it is not executed as
HTML. The result's collection, retention and content outcomes remain distinct.

## ESXi source interpretation

An `esxcli network ip interface ipv4 get` source establishes IPv4 information only.
Current collection marks IPv6 properties `ipv6_not_collected`. Diagnosis also
recognizes this limit in older saved results that incorrectly marked an empty IPv6
set complete. It does not rewrite those raw or retained records. Other incomplete
properties remain explicit rather than being hidden behind a successful IPv4 probe.

Reference IP recovery is a separate local metadata operation documented in
[reference addresses](host-reference-ips.md); it does not make an overall partial
inventory complete. Public tests use synthetic platform output and saved evidence.
Offline diagnosis/recovery of real saved observations is not a new SSH execution
or verification of current host condition.

*Last modified: 2026-11-18 14:14:40*
