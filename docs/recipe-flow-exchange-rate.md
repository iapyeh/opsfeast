# Hybrid recipe case: monthly USD rate and domain query

Status: design case for recipe-flow-plan/0.1.0. This public case is a plan, not an
executable workflow, remote wrapper or permission to run the case. A private
instance can be registered through [definition authoring](recipe-definition-authoring.md), with
its target bindings retained in the selected Profile.
Read [architecture](recipe-flow-design.md), [language](recipe-flow-language.md)
and [conformance](recipe-flow-conformance.md).

## Purpose and boundaries

Use a normal browser to acquire the Bank of Taiwan USD history table at
https://rate.bot.com.tw/xrt/quote/ltm/USD after its JavaScript has rendered.
Select the same-month first available date on or after day 15, then use the
spot/bank-selling price as the sole varying argument to a privately bound
monthly-domain command.

Browser acquisition can require an agent. Table parsing and selection belong to
fixed reviewed utility routines, never per-agent interpretation or regeneration.
A routine may be ordinary Python even though the parent flow is a virtual plan.
Images, templates and schemas may be carried as explicit package resources.

A design-time browser inspection found a table with date, currency, cash buy,
cash sell, spot buy and spot sell columns. This observation is not a permanent
DOM guarantee, a routine implementation or a freshness promise. Reverify headers
and coverage at execution; preserve a failure when the page changes. The fixtures
below are synthetic and do not encode a live exchange rate.

## Readable numbered plan

~~~python
# Specification only. These names are bound by the package's step contracts.
target_month = inputs.target_month  # YYYY-MM, frozen in Asia/Taipei at run creation
rate_page = "https://rate.bot.com.tw/xrt/quote/ltm/USD"

# step 01 id: acquire_table
snapshot = agent.read_rendered_table(rate_page)

# step 02 id: parse_table
table = routines.parse_bot_usd_table(snapshot)

# step 03 id: select_quote
quote = routines.select_monthly_usd_quote(table, target_month)

# step 04 id: run_monthly
# The contract requires authority and a durable intent before dispatch.
result = script.monthly_query(usd_rate=quote.sell_rate)

if result.state == "outcome_unknown":
    stop("outcome_unknown", "Reconcile the original action; do not repeat it.")

if result.state == "failed":
    stop("action_failed", "Keep output and stop dependent work.")

# step 05 id: report_result
agent.explain_result(quote, result)
finish(execution="command_completed", business_outcome=result.business_outcome)
~~~

No quote, schema/coverage failure or ambiguous price is a typed terminal error
from steps 02/03, not a false condition, a previous-month fallback or an invented
rate. A missing grant/provider waits before its associated action.
A person can authorize the complete conditional policy up front; reaching
step 04 does not demand a duplicate approval when that grant already applies.

## Case step contracts

| Step | Contract | Input / output | Effects and failure |
| --- | --- | --- | --- |
| 01 acquire_table | browser.rendered-table/0.1.0 | Fixed URL -> immutable rendered-table snapshot | Normal browser read; challenge waits for human; no HTTP substitution or host access |
| 02 parse_table | bot-usd-table/0.1.0 | Snapshot -> normalized table | Local pure parser; changed headers, partial coverage or inconsistent rows stop |
| 03 select_quote | monthly-usd-quote/0.1.0 | Table + frozen month -> selected quote | Local pure routine; date/rate/ambiguity errors stop before SSH |
| 04 run_monthly | monthly-query-command/0.1.0 | Quote rate + private binding -> action receipt | Remote effects unknown until reviewed; login only unless separately authorized; no automatic retry |
| 05 report_result | result-explanation/0.1.0 | Saved quote/action receipts -> readable explanation | No new browser/host query or notification; prose cannot alter canonical outcome |

All names/versions above are proposed package contracts, not currently installed
functions. The candidate must include actual step contracts, exact utility code,
schemas and runtime pins before any execution-ready claim.

### Browser snapshot and parser

The snapshot includes requested/final URL, acquisition UTC time, provider/tool
identity and version, page language, query date bounds, full rendered table
HTML/DOM content and its SHA-256. Record claimed versus independently validated
properties separately. Screenshot evidence is optional supporting material;
an agent's manually transcribed price is not the routine's authoritative input.

The parser resolves merged headers and validates the semantic mapping of all
six columns. It can support a documented finite set of languages; unknown
labels/layouts are schema_changed, never "probably the sixth number".
Duplicate responsive/hidden representations may be normalized only by documented
identity rules. Different selected-day prices must remain an ambiguity.

Verify the required date interval is present in a completed table, all applicable
pages/rows were acquired, and there is no unresolved loading/pagination state.
Query-range text alone does not establish completeness. A cutoff row, missing
page or unverifiable coverage is coverage_incomplete; do not treat an absent
15th row as a holiday when acquisition itself is incomplete. The parser/coverage
verifier is future implementation work, with separate fixture/native tests.

### Normalized table and quote

Table contract bot-usd-table/0.1.0:

- schema_version is 0.1.0.
- as_of is a frozen ISO date derived from the acquisition time in Asia/Taipei.
- columns is exactly date, currency, cash_buy, cash_sell, spot_buy, spot_sell.
- coverage has from/to ISO dates and complete=true only after parser verification.
- rows have date, currency and all four price fields as normalized strings.
- Snapshot digest/provenance lives in the surrounding step receipt.

Quote contract monthly-usd-quote/0.1.0 has target_month, selected_date, currency
USD, rate_type spot, direction bank_sell and sell_rate as a positive finite
canonical decimal string. Its receipt binds the table/snapshot digest and rule
version. Decimal is never serialized as a JSON float. Prices are at most 32 ASCII characters with digits and an optional decimal
point, without sign, exponent, whitespace or locale separators. Do not round or truncate.
A date with a missing/bad price is an error, not a reason to skip to the next day.

## Reference selector for review and offline vectors

This pure reference implementation is executable documentation for the selector
only. It is not the browser parser, runner, script wrapper or a live recipe.
It assumes the acquisition/parser contract above was independently satisfied;
accepting a caller's complete=true flag is not proof that a browser did so.
The [offline vectors](examples/recipe-flow/quote-cases.json) exercise its boundary.

~~~python
from calendar import monthrange
from datetime import date
from decimal import Decimal
import re


class QuoteError(ValueError):
    pass


def iso_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise QuoteError("invalid_date")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise QuoteError("invalid_date") from None


def select_monthly_usd_quote(table, target_month):
    if not isinstance(target_month, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", target_month):
        raise QuoteError("invalid_month")
    try:
        year, month = map(int, target_month.split("-"))
        start = date(year, month, 15)
        last = date(year, month, monthrange(year, month)[1])
    except ValueError:
        raise QuoteError("invalid_month") from None
    columns = ["date", "currency", "cash_buy", "cash_sell", "spot_buy", "spot_sell"]
    if table.get("schema_version") != "0.1.0" or table.get("columns") != columns:
        raise QuoteError("schema_changed")
    as_of = iso_date(table["as_of"])
    if as_of < start:
        raise QuoteError("not_yet_available")
    coverage = table["coverage"]
    if (coverage.get("complete") is not True
            or iso_date(coverage["from"]) > start
            or iso_date(coverage["to"]) < min(as_of, last)):
        raise QuoteError("coverage_incomplete")
    candidates = []
    for row in table["rows"]:
        day = iso_date(row["date"])
        if day > as_of:
            raise QuoteError("future_row")
        if row["currency"] == "USD" and (day.year, day.month) == (year, month) and day >= start:
            candidates.append((day, row))
    if not candidates:
        raise QuoteError("no_available_date")
    selected = min(day for day, row in candidates)
    prices = set()
    for day, row in candidates:
        if day != selected:
            continue
        value = row["spot_sell"]
        if not isinstance(value, str) or len(value) > 32 or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
            raise QuoteError("invalid_rate")
        amount = Decimal(value)
        if not amount.is_finite() or amount <= 0:
            raise QuoteError("invalid_rate")
        prices.add(amount)
    if len(prices) != 1:
        raise QuoteError("ambiguous_rate")
    text = format(next(iter(prices)), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return {"target_month": target_month, "selected_date": selected.isoformat(),
            "currency": "USD", "rate_type": "spot", "direction": "bank_sell",
            "sell_rate": text}
~~~

A production implementation additionally validates the full bounded input schema
before this function, locks the Python/Decimal environment and associates exact
code/input/output digests. KeyError/TypeError from an invalid envelope is a schema
failure, never successful selection. The specification is the policy plus schema
plus exact routine; another agent must not replace this function with its own
interpretation during execution.

## Remote binding and authorization

Public examples use synthetic bindings, such as a host named monthly-job-host
and reviewed /opt/monthly-job paths. Do not publish the operator's real host,
private paths or configuration contents in a portable example.

The actual local candidate must reproduce the user's approved invocation via
private bindings, with this argv structure:

~~~text
[bindings.python,
 bindings.script,
 bindings.config,
 "--usd-rate",
 quote.sell_rate]
~~~

The target host is bindings.target_host, resolved from the intended Profile.
Use SSHScript through the reviewed action implementation when suitable; this
document does not invent an SSHScript argv API or privilege behavior.
Quote arguments through the implementation's reviewed command facility; never
string-eval a price or accept a URL/table cell as a command fragment.

Before enabling step 04, inspect the script under separately authorized scope
and declare actual writes, notifications, success evidence and repeatability.
The command name/path does not establish read-only behavior. Reuse grants that
cover the exact fixed action and rate-selection policy; otherwise show selected
month/date/rate, target/identity/argv and effects, then wait for confirmation.
No passwords or config file contents belong in the plan or river.

The business key is Profile identity + recipe purpose ID + target host identity +
target month. A code-version change must not bypass duplicate detection.
Reserve it atomically before dispatch. An existing running/unknown/completed
attempt must be shown for reconciliation or explicit repeat authorization.
An unstarted failed preflight can be retried within scope, without pretending an
uncertain remote action was unstarted.

## Result interpretation and evidence

Preserve selected date/rate, table snapshot, routine/input digests, authority,
actual argv/identity and real command output. Exit 0 establishes command
completion only. Until the script's business postcondition is defined and
verified, business_outcome remains unverified. A timeout/lost connection after
dispatch is outcome_unknown and never triggers automatic rerun.

The example neither stores a live quote nor rewrites old reports. Future quote
retention is Profile/external-source scoped and linked to the action receipt.
The conformance vectors are sufficient to review deterministic selection;
browser extraction, native SSH, idempotency and end-to-end business outcomes
remain unverified.

## Executable implementation

[Python workflows 0.1.0](python-workflows.md) now provides
`opsfeast.bot_usd.parse_bot_usd_table/select_monthly_usd_quote` and a reviewed
browser-to-command execution service. The virtual plan above remains a review
artifact; its routine policy is retained verbatim in the product selector.
Browser completion is an explicit active-agent attestation with strict request
binding and schema checks. Current bank DOM, real SSH and mail delivery have not
been tested. The executable private recipe uses its own reviewed target/paths;
public bindings and tests remain synthetic. This implementation does not add a
general virtual-flow interpreter or closed flow importer.

*Last modified: 2026-11-17 17:19:19*
