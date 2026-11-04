# Ephemeral Console secret delivery 0.1.0

Use this checkout-level Web/worker service for a signed-in human to supply a
single-line password to the exact entered program currently waiting for it.
It extends the [worker 0.3.0](console-agent.md); ordinary record/form schemas stay
at 0.2.0. No recipe service, saved credential store, SSH credential editor or
secret-manager adapter is introduced. Loopback Web and matching SSHScript 7.0.1
are required. Use one Web process: requests live only in that process's memory.

## Human workflow and data boundary

The agent opens the exact host's river, connects, enters the approved program and
observes its password prompt. The agent issues `secret` with a descriptive label
and a 1–300 second timeout. The live river displays a password field with submit
and cancel controls. Enter the existing password there; empty passwords are valid.
The browser clears the field on submission/cancellation/page departure, never
stores a draft, and never retries a password POST automatically. A network error
requires checking the request's current state; do not assume failed transport
means the input was not delivered. Refreshing the page clears the unsent field.
Historical readers do not enumerate requests or provide private-input controls.
The agent's chat receives public progress only, never the password.

The Web service does not send the value to Records, SQLite, snapshots, SSE,
ordinary form responses or logs. It retains at most one request per session and
64 installation-wide; a request is removed on one successful take, worker cancel,
expiry or shutdown. Human cancellation erases the value and leaves only a cancelled
marker until worker cleanup or expiry. A daemon expiry timer clears the request
without relying on browser/worker polling. Restart loses every pending value.
Values have a 4096 UTF-8 byte limit; NUL and line breaks are rejected.

The consuming worker uses SSHScript's `password_func` and `input(secret=True)`;
it never constructs a command or Python expression containing the value.
The configured program must disable password echo (as MySQL's password prompt
does). Additionally, the worker redacts the delivered value from subsequent stdout
and stderr, including split writes; redaction strings remain only in worker memory
until close. This is exact-value protection, not general secret detection: transformed,
encoded or unrelated secrets and arbitrary program output are not automatically
safe. Python, HTTP and browser runtimes hold temporary copies; no forensic memory
zeroization, encrypted RAM or isolation from the same OS administrator is claimed.
Access logging must remain disabled as in the bundled launcher. Do not enable body
logging/tracing or use this HTTP loopback channel across a network.

## HTTP contract

All paths start `/api/v1/console-sessions/{sid}/secret-requests` and responses use
`Cache-Control: no-store`. UUIDs bind to an existing exact record session. The
existing same-origin policy applies to every route. The record service itself
never executes a browser command.

| Method and suffix | Authority | Input and result |
| --- | --- | --- |
| POST base | Writer bearer only | `{request_id,label,timeout}` → public metadata plus private `claim` |
| GET base | Signed-in administrator only | `{requests:[{request_id,label,state,expires_at}]}`; no claim/value |
| POST `/{rid}/submit` | Signed-in administrator only | `{value}` → `{state:"submitted"}` |
| POST `/{rid}/take` | Writer bearer and matching claim | `{claim}` → `{state:"waiting"}` or one `{state:"consumed",value}` |
| POST `/{rid}/cancel` | Administrator with `{}`, or writer with `{claim}` | `{state:"cancelled"}` |

Reader/site tokens cannot create, submit, enumerate or consume requests. A writer
cannot impersonate the authenticated human submission. A second worker/writer
without the per-request random claim cannot take or cancel the value. The same
OS user can read the writer token; this is not an OS isolation boundary.
No generic secret-take CLI is provided: the worker consumes the response internally.
Never fetch this route through a model-visible tool or display its raw response.

Unknown/cross-session/expired/consumed requests, claim mismatch, duplicate submit,
capacity conflict and invalid schemas fail with sanitized 409 errors. Authentication
fails with 401 and cross-origin access with 403. Oversized bodies fail with 413.
A value is accepted only once, even across simultaneous browser submissions.
No submission, request restart, expiry or cancellation causes an execution retry.
The existing standalone agent client cannot submit as the human.

## Verification

`tests/test_console_secrets.py` exercises scope/claim enforcement, duplicate and
concurrent submission, expiry without polling, cancellation, shutdown, empty and
invalid values, HTTP roles/origin/cache policy and absence from persistent files.
A real local getpass program exercises prompt detection, hidden delivery, split
output redaction, subsequent ordinary input and leaving the program. Browser
handler tests verify password masking, immediate clearing, no retry and page cleanup.
These tests are synthetic/local evidence; real database authentication requires
an explicitly authorized host and the human's actual password.

*Last modified: 2026-11-04 17:05:04*
