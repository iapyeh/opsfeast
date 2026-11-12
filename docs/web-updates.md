# Version checks and Agent update handoff 0.1.0

Settings shows installed OpsFeast/SSHScript versions and a separate explicit check
button for each product. Loading Settings reads local evidence only. Checking a
source does not install packages, change Git refs, replace Skills or grant update
authorization. The feature requires the optional Web environment, including
`packaging==26.3` for PEP 440 comparisons.

## Human workflow

1. Open Settings and choose **檢查目前版本與新版** for one product.
2. Read the checked source, version/commit, check time and comparison result.
   Local changes, a diverged checkout and an unsupported SSHScript target remain
   explicit. A lookup error is never treated as "already current."
3. When a newer version is established, a confirmation dialog asks whether to
   prepare an Agent update instruction. Cancel leaves everything unchanged.
   Unknown/diverged comparisons offer an explicit review action instead of
   automatically claiming that an update is available.
4. Confirm, then copy the resulting instruction into the conversation with the
   Agent managing this installation. The text identifies current/target versions,
   source and check time, and routes the Agent to the existing update procedure.
   The website does not dispatch messages, wake an Agent or run an installer.
5. The Agent rechecks the actual environment, applicability and authorization,
   preserves edits and private data, follows [update preservation](update-preservation.md) and [the skill update guide](skill-updates.md),
   applies only an applicable update, learns matching contracts/Skills and reports
   verification. An unsupported target requires product support; it is not
   permission to bypass the execution guard. Any required service restart must
   restore the same Web workspace and report availability.

The generated instruction is a handoff, not an installation receipt. Confirmation
and copying do not mean the instruction has been sent or the software updated.
The instruction is kept in that page's memory, not saved to a new task store.
No repository publication, managed-host connection or remote execution is implied.

## Official sources and interpretation

- **OpsFeast:** the official `iapyeh/opsfeast` GitHub `main` commit, with `VERSION`
  read at that exact SHA. The development version string may remain unchanged
  across commits, so comparison uses commit ancestry. Local read-only Git ancestry
  checks are preferred; the public GitHub comparison endpoint is used when needed.
  A checkout containing the source commit is `local_newer`; divergence and missing
  comparison evidence remain distinct. Untracked/tracked local changes are reported
  as a Boolean, without returning filenames or private paths.
- **SSHScript:** official PyPI release metadata. The newest non-yanked stable
  PEP 440 release is compared with installed distribution metadata. Prereleases and
  development releases are excluded; post-releases are supported. A target's match
  to `schemas/sshscript-runtime.json` is reported separately. Version ordering is
  not proof of complete package integrity, runtime readiness or matching Skill
  availability; the applying Agent must verify those under the canonical guide.

No configurable remote URL, private repository credential or arbitrary subprocess
command is accepted from browser input. Requests use HTTPS, reject redirects,
bound response reads to 4 MiB and use a ten-second timeout per remote request.
Source failures, rate limits, invalid metadata, missing stable releases and missing
version dependencies return failure evidence rather than fabricated versions.

## Shared interfaces

`opsfeast.updates.current(INSTALLATION)` reads installed evidence; it does not
contact release servers. `opsfeast.updates.check(INSTALLATION, PRODUCT)` checks
`opsfeast` or `sshscript` and returns JSON-serializable evidence. These are
checkout-level interfaces, independent of recipe execution. Prefer direct module
calls or the CLI for agent programs; do not recreate version scraping.

```sh
.venv/bin/python -B -m opsfeast.updates show
.venv/bin/python -B -m opsfeast.updates check --product opsfeast
.venv/bin/python -B -m opsfeast.updates check --product sshscript
```

Use `--installation PATH` for an explicit product checkout. Both CLI actions emit
JSON; failed checks exit 1. No files are installed or updated by either action.

`GET /api/v1/updates` returns `opsfeast` (version, commit, branch, local_changes) and
`sshscript` (version, supported_version). `POST /api/v1/updates/check` accepts
exactly `{"product":"opsfeast"}` or `{"product":"sshscript"}`. Both require an
administrator session or the independent launching-agent capability and use the
existing same-origin checks. Unknown products/extra fields return 422; missing
authority returns 401; foreign origins return 403.

Check evidence has `schema_version: 0.1.0`, product, current, checked_at, source,
status, nullable update_available and `update_method: agent_review`. Successful
reads include latest and comparison (`up_to_date`, `local_newer`,
`update_available`, `diverged` or `comparison_unknown`). SSHScript also reports
nullable compatible. Failures have `status: failed` and a safe reason_code.
HTTP 200 means a check receipt was returned; inspect status before interpreting it.
The earlier `/api/v1/workspace/version` view is replaced by `/api/v1/updates`.

Tests cover stable/yanked/prerelease selection, commit relationships, missing and
invalid evidence, source failures, authorization/origin boundaries, escaped UI
results and exact handoff content. Remote responses in public tests are synthetic;
real-source checks do not prove that an update can be safely applied.



Update instructions must retain the existing installation-data UUID, Web port, administrator credentials and resolved Profile roots. Saved categories/assignments/meals and recipe defaults are not regenerated. Apply the one-time registry-port transfer only when required by Web endpoint 0.2.0; no general private-data migration or new initialization is implied. Compare before/after state and restore the same Web origin before reporting success. See [the canonical procedure](update-preservation.md), including browser draft limits.

*Last modified: 2026-11-11 22:35:58*
