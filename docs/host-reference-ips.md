# Host reference IP addresses

OpsFeast keeps the last successfully saved inventory interface addresses for each
configured host. These are reference information: they never replace
`hosts.yaml` connection settings, select SSH endpoints or trigger DNS lookups.
Users decide when to refresh inventory and accept the age/accuracy of these
references. There is no expiry policy, automatic refresh or connectivity claim.

## Read without collecting

```sh
python -B tools/opsfeast.py hosts list --profile main --json
python -B tools/opsfeast.py hosts show node --profile main --json
```

Both commands read only. They do not connect, query retained history, initialize
storage or modify files. `list` includes every configured host, including disabled
and never-inventoried hosts. `show` requires a configured host ID. Each response
has `schema_version: "0.1.0"` and a `hosts` array containing `host_id`, `label`,
`groups` and `reference_ips`. Human terminals show a shared table; agents should
select `--json`. Labels/groups come from current configuration, while addresses
and their timestamps come from the last successful saved interface enumeration.
No credentials or connection settings are returned.

The Core API reads the same data:

```python
from opsfeast import Instance

profile = Instance.open().profile("main")
addresses = profile.hosts.reference_ips("node")
print(addresses["ipv4_addresses"], addresses["observed_at"])
```

Prefer this API or CLI over parsing recipe output, scanning observations or
writing SQL. `Hosts.list/get` keep their existing configuration-only return
values. Recipes can use `recipe.profile.hosts.reference_ips(HOST_ID)` when their
context provides the documented Core profile; do not assume a different context
has that attribute. Offline report authors can use the selected Core profile
without connecting; retained-history analysis continues to use retention APIs.

## Automatic updates

`system/inventory/overview` 0.4.1 emits an optional raw `reference_ips` projection when
its interface probe succeeds and every address can be parsed. A shared interface
probe supplies both address families even if only an IPv4, IPv6, MAC, MTU or
interface-state property was requested. No additional probe is introduced.

| Execution | Effect on saved reference IPs |
| --- | --- |
| Successful interface enumeration, durable raw save and successful retention | Replace both address lists and the source timestamp |
| Other selected probes fail, but interfaces succeed | Update from the successful interface probe |
| Interface command/parse failure, truncation or unsupported output | Preserve previous values and timestamp |
| No interface probe in this selection | Preserve previous values and timestamp |
| `inventory query` without `--save` | Return the projection when available, but write nothing |
| Connection/actor/cleanup failure, or retention failure | Preserve previous values and timestamp |
| Successful complete enumeration with no addresses | Save empty lists with status `known` |

This applies to `inventory query --save`, `inventory run`, inventory execution
through `recipes run`, and scheduled inventory dispatch. Scheduling still
requires its own explicit opt-in. One manual refresh example (a real connection,
requiring target/privilege authorization) is:

```sh
python -B tools/opsfeast.py inventory query --profile main --host node \
  --property network.ipv4.address --save --json
```

The result's `reference_ips_update` receipt reports `updated`, `skipped` with a
reason, or `failed` with a safe error type. An update-storage failure preserves
collection and retention outcomes but makes execution exit nonzero. It never
turns a successful collected sample into a failed historical sample. The receipt
is delivery metadata excluded from the raw evidence digest, like retention and
content receipts. After repairing a local storage problem, run a newly authorized
saved network query; there is no separate cache-repair command.

## Data contract 0.1.0

The [schema](../schemas/host-reference-ips.json) defines a reference record. A known
record resembles this synthetic example:

```json
{
  "schema_version": "0.1.0",
  "host_id": "node",
  "status": "known",
  "ipv4_addresses": ["192.0.2.10"],
  "ipv6_addresses": ["2001:db8::10"],
  "observed_at": "2026-10-30T06:00:00+00:00",
  "source_id": "probe-2",
  "source_observation_id": "00000000-0000-4000-8000-000000000001",
  "source_record_id": "source-qualified-retained-record-id",
  "recipe": "system/inventory/overview"
}
```

- `status` is `known` or `unknown`, not an online/health verdict. A never-saved
  host returns `unknown`, empty arrays and null `observed_at`, without provenance.
- Arrays are deduplicated and sorted lexicographically. All successfully parsed
  observed addresses are included, including loopback/private/link-local
  addresses. MAC rows are excluded. IPv6 zone identifiers are preserved when
  reported. There is no invented primary IP or preferred address order.
- `observed_at` is the successful interface probe's original UTC time. Reading,
  failed attempts and unrelated queries never refresh it.
- Provenance identifies the successful live observation, retained record, probe
  and source-qualified recipe. It reflects the collector's visible environment;
  it does not establish physical host continuity or cross-profile identity.

The profile-local materialized metadata lives in
`.host-reference-ips/<sha256-of-host-id>.json`. Hashed filenames support arbitrary
configured IDs safely; they are not identity keys. Updates use a lock and atomic
replacement, and an older concurrent success cannot overwrite a newer success.
Different profile roots remain independent. Reads reject symlink paths and
malformed stored records. Do not edit these implementation files directly.

Historical raw/retained observations remain the evidence source; this small
reference projection is kept until a later successful live enumeration. Retention
deletion, replay, import and Vault rebuild do not update or erase references and
cannot masquerade as a new measurement. Observation/retention transfer packages
do not carry this separate profile-local metadata. No backfill, migration or
historical-data rewrite is performed; existing hosts initially return unknown.

## Coverage and verification limits

This feature uses the recipe's existing parsers and requires normalized interface
rows. Linux JSON-address and FreeBSD/macOS ifconfig rows can supply it. ESXi's
current opaque `entry` rows cannot; these preserve previous/unknown references.
Old Linux tools lacking `ip -j` still require a separate probe-compatibility fix.
This feature does not install tools or add fallback commands, resolved SSH peers,
route-based primary-address selection or OS summary fields.

Public synthetic tests cover successful replacement, retained failures, unrelated
and no-store queries, changed/empty address lists, both families, invalid rows,
older concurrent results, retention/update failures, API/CLI reads, unknown hosts,
terminal tables, help and symlink rejection. They do not establish native remote
Linux/FreeBSD/macOS/ESXi or SSH/su/sudo behavior. Run
`python -B -m unittest discover -s tests -p test_host_reference.py` and the complete
public suite before delivery.

*Last modified: 2026-10-30 16:02:12*
