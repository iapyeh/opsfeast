# Check a TCP port from a host

## Declared retention and bundled content

In a namespace-enabled profile this read recipe retains declared safe scalar result fields through host-values 0.2.0 with dataset/field semantics. The separate bundled vault author can render a per-host state page. Failed/mock results are excluded; missing values remain unavailable. Read [vault setup and output rules](../../../../../docs/host-vault.md). Profiles without namespace retain raw-only behavior. Read [retention query/content interfaces](../../../../../docs/retention.md); Markdown templates are not part of the recipe contract.

This recipe makes one TCP connection attempt **from the selected host** to an explicit IP address and port. By default it checks 127.0.0.1 on that host. It does not test accessibility from the controller, UDP, listener configuration or application/HTTP health. Selecting a different address expands the target network operation and must remain within the user's scope.

## Run

Use the selected Python interpreter from the OpsFeast checkout:

```sh
python -B tools/run_recipe.py system/network/check/port --host rms3 --root ~/Download/testops --var port=8888
python -B tools/run_recipe.py system/network/check/port --host rms3 --var port=443 --var address=::1
python -B tools/run_recipe.py system/network/check/port --group web --vars-file /path/to/port-inputs.json
```

An example JSON input file is `{"port":8888,"address":"127.0.0.1","connect_timeout_seconds":3}`. The Feast must already have the selected hosts configured. Reading/configuration checks do not authorize connection or execution. Use `run_recipe.py`; main.py defines execute and has no standalone --host/--port CLI. See the [execution contract](../../../../../docs/recipe-execution.md) and [recipe skill](../../../../../skills/opsfeast-recipes/SKILL.md).

## Dependencies, inputs and operations

Controller: Python 3.11+, PyYAML 6.0.3 and SSHScript 5.0.0. Target: python3 on PATH with the standard library. Declared Linux/FreeBSD/macOS coverage is implementation intent, with synthetic tests only; targets without python3 are unsupported by this implementation and report command/execution failure. No installation, sudo or su is attempted.

port is a required integer from 1 to 65535. address is an IPv4/IPv6 literal string, default 127.0.0.1; hostnames are rejected by recipe code to avoid unbounded DNS lookup. connect_timeout_seconds is positive, at most 60, default 3; the actual socket budget is min(input, runner timeout). The SSHScript total command budget is the runner timeout, including Python startup. Invalid IP text fails execution before a probe command, but after the runner establishes its Session.

Operations: use the borrowed Session to execute a fixed `python3 -c` socket probe with argv inputs, open and close one TCP connection, then parse a small JSON response. The runner saves raw result JSON in the selected Feast. No files are written on the target. A TCP handshake can produce network/service logs; no application payload is sent.

## Results

| reason_code | status | data.reachable | Meaning |
| --- | --- | --- | --- |
| port_open | success | true | TCP handshake completed from the selected host |
| port_refused | success | false | TCP connection was refused; the check itself completed |
| port_timeout | failed | null | TCP reachability is unknown; timeout is not proof that no listener exists |
| port_network_error | failed | null | Network operation failed; reachability is unknown |
| command_failed / parsing_failed | failed | null | Probe command failed, output was truncated or its response was invalid |
| execution_failed / cleanup_failed | failed | See saved data | Runner exception or Session cleanup failure; inspect execution_errors |

Schema 0.1.0 data includes probe_from (host ID), address, port, protocol tcp, state and reachable. UTC observation time is represented by the surrounding run's started_at/completed_at interval. A successful exit does not necessarily mean the port is open: read reachable and reason_code. See [synthetic output](examples/result.synthetic.json). This recipe uses the declared scalar retention adapter, independently of inventory exchange and identity probes.

## Implementation choice and verification

SSHScript supplies local/SSH command execution through the runner's borrowed Session, argv handling, finite command budgets and retained CommandResult. Python's socket standard library handles the probe without depending on platform-specific nc flags. See [implementation](main.py), the bundled [public SSHScript skill](../../../../../skills/sshscript/SKILL.md) and its [API contract](../../../../../skills/sshscript/references/api-guide.md). Documentation contract and runtime requirement are 5.0.0; [SOURCE.json](../../../../../skills/sshscript/SOURCE.json) preserves provenance.

[Public tests](../../../../../tests/test_general_recipes.py) cover open/refused/timeout/network error with synthetic sockets, invalid/truncated command output, runner inputs and failure states. No real target, SSH or local TCP probe has been performed. Review target prerequisites and the complete recipe before authorized use. No distribution license is currently declared by the repository.

_Last modified: 2026-10-19 15:24:36_
