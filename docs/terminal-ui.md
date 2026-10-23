# Optional terminal display

Add `--tui` to an existing supported command to read its progress and results in a Textual terminal interface. The existing command still performs the operation and saves its usual results. The display does not select hosts, change privileges, add probes or authorize execution.

## Home, Hosts and Profiles

Run `python -B tools/opsfeast.py` without arguments to open Home. Main sections are **Home → Profiles → Recipes → Hosts → Help → Actions**. Explicit commands and --help remain CLI. Bare recipes still opens the recipes workbench directly.

Home displays the OpsFeast version/download time and **Defaults for New Recipes** with **Recipe Author**, **Author Contact Info** and **Default Recipe License** from `.opsfeast-author.yaml`. These three fields are Tab stops: Enter or mouse click opens an Input dialog. Name/license accept plain text; Contacts accepts a JSON list of strings. Enter or Save persists only that field and refreshes Home; Escape or Cancel discards changes. Validation/write errors stay in the dialog. The section explains that defaults apply when creating your own recipes and do not change existing recipes. Unset fields display **Not configured — click to set**, while stored placeholders remain `Unknown`; invalid settings show an explicit safe error and require file repair before editing. See [recipe attribution](recipe-attribution.md) for configuration and creation defaults. The product version comes from the tracked `VERSION` file (initial development version `0.1.0.dev0`). Download time comes from an optional local `.opsfeast-download.json` receipt; absent records display **Not recorded**, malformed/symlink records display **Invalid download record**. It is never inferred from file timestamps, Git commit dates, launch or activation time. The app does not create a receipt on opening. No download time is retroactively assigned to existing checkouts.

Download-receipt contract 1.0.0 contains `receipt_version`, timezone-aware ISO 8601 `downloaded_at` and the actual acquisition `source`. A user-authorized acquisition workflow may call `checkout_info.record_download(root, downloaded_at, source)` after a known download, or invoke `python -B tools/checkout_info.py --downloaded-at KNOWN_ISO_TIME --source ACTUAL_SOURCE`. This records supplied evidence and performs no download or verification of that claim. Do not use current time as a substitute for an unknown download time. The helper refuses existing receipts, uses exclusive creation and omits exception text on write errors. A failed write may leave an invalid receipt: preserve/review it before a separately authorized repair. The local receipt is ignored by Git and must not be shipped as someone else's acquisition evidence.

### Hosts

Hosts shows the persisted default profile's configuration after resolving `hosts.yaml` and includes through the existing loader. A Tree sidebar is docked to the left (`dock: left`), grouped by configured group membership, with host IDs as leaf options. Select/highlight a host ID to display its complete masked settings and source file on the right, including its enabled flag. A scalar group and a group list are both supported; duplicate memberships appear once, multi-group hosts appear under each group but share the same settings, and ungrouped hosts appear under **Ungrouped (no group)**. Group/host order follows first occurrence in merged configuration. Group branches can be collapsed/expanded using the Tree controls; highlighting a group shows a selection prompt rather than stale host settings. Refresh preserves the selected host when it still exists. Connection/users/group/vars/recipes and other stored host fields are preserved. These are merged configured values, not runtime-expanded connection settings, resolved recipe-input defaults or connectivity/privilege evidence. Loading errors show only exception type and expose no malformed YAML snippets. No hosts/default profile produces an explicit empty state; opening never initializes an environment.

Settings are recursively redacted before they enter UI state. Password/passwd/passphrase/secret/token fields and API/private-key values display fixed `********`, including nested connection, account, su/sudo and recipe variables. Masking does not reveal lengths and does not mutate original YAML. Identity-file paths remain visible; key files are not opened. Arbitrary text embedded in an innocently named field cannot be automatically recognized as a secret: keep credential values in appropriately named fields. Highlighting hosts remains read-only; there is no reveal-password or editor. Enter on a host leaf opens the explicit operation menu described below.

### Host action menu, progress and result dialog

With a host leaf focused, press Enter to open a modal **SelectionList** containing `test-connection`, `run recipe` and `cancel`. Only one chosen action is applied: Enter/Space toggles the highlighted option and immediately proceeds. Group nodes keep their ordinary Tree behavior. Merely highlighting a host, refreshing or switching profiles never opens the menu or executes an operation. Escape/cancel before starting performs nothing.

`test-connection` immediately invokes the existing `opsfeast.py test-connection HOST ROOT --verbose`. It uses the normal connection/hostname/date/cleanup contract, without host-init or privilege probes. `run recipe` opens an **Input** for a reviewed operational recipe path; submit with Enter or Run on this host. Empty paths remain in the form with an error. The runner uses `--recipe`, exactly one `--host`, the captured Feast directory and verbose progress. Existing recipe/source/path/compatibility/default-input checks still apply; no fallback to all hosts occurs. Use the full Actions form for typed invocation overrides or report inputs. Offline report recipes do not run through this host-bound action.

The menu and recipe form display the selected host and Feast directory before execution. These are explicit operational actions and require the user's authorization for that host and recipe behavior; opening the Hosts tab is not authorization. Targets/root are captured when the menu opens, and later default-profile changes do not rebind that operation. User-provided recipes must be reviewed before choosing Run.

Execution displays a **ProgressBar** with unknown total, stage messages and safe stderr. It deliberately does not estimate a percentage or completion time. A **ModalScreen** dialog retains the final stdout/result, CLI exit code and warnings. Completion fills the bar to indicate command completion, including on failure; the exit/result states determine outcome. Partial/failed/skipped/unsupported, cleanup evidence, result paths and retention remain visible in original JSON. Scrollback is limited to 3,000 rendered lines; use normal recipe result files for durable evidence. Connection-test output is not automatically stored by this dialog.

Close/Escape is enabled only after execution finishes; active-run cancellation is not implemented. Other operations/profile switches are blocked while this host dialog is active. The UI uses the same interpreter and existing CLI via argv (no shell), with stdin closed. If the display/transport fails it attempts to terminate/reap the local subprocess; this does not prove remote termination or cleanup. Errors show exception type, not arbitrary exception text. Close returns focus to the host sidebar. No real SSH or privileged operations are exercised by the synthetic dialog tests.

### User nodes and privilege diagnostics

Each host has user children: the configured connection account (if known) plus the declared `users` mapping, deduplicated in configured order. The login child is marked `(login)`. For direct SSH without `connection.user`, the UI uses the existing connection-plan local-account fallback; local hosts use the controller's effective OS account. SSH config aliases with no confirmed account remain unknown: the UI does not parse external SSH configuration, contact a host or enumerate remote accounts to build the tree. These labels describe local selection evidence, not a verified remote identity.

Highlighting a user shows its masked account settings and host/source. Account vars are not merged with host vars. Enter opens the same SelectionList dialog: **test-sudo**, **cancel**, and **test-su** only when a known login account differs from the selected user. Unknown login hides test-su rather than guessing. A host's own Enter menu remains test-connection/run recipe/cancel; group nodes keep Tree navigation behavior.

`test-su HOST USER --root ROOT --verbose` independently switches from the actual login account to the selected target; no chain is constructed. `test-sudo HOST USER --root ROOT --run-as root --verbose` uses the selected user as the sudo actor and root as the target. A different sudo actor may require prerequisite su, which is part of this selected diagnostic scope. Existing runtime identity checks, credential precedence, skipped/failure states and cleanup contracts remain authoritative; UI login labels never override them. Missing credentials may produce skipped results. Select these diagnostics only within the user's actual privilege-testing authorization.

Host/user/root are captured when the menu opens. The existing progress/result modal is reused, with user shown in its header, preserved per-step identity/error/cleanup evidence and no credential values added to argv or logs. This feature neither edits account settings nor connects merely to display users. Tests use mocked privilege execution; no actual SSH/su/sudo validation is claimed.

### Profiles

Profiles lists registered name, root, available/missing/invalid/unavailable state and the persisted default mark. Availability uses the existing CLI's directory/definition/entry-file checks, not full YAML/recipe or connection validation. Missing registrations remain visible and are never removed automatically.

Move the table cursor to select a profile, then press Enter or **Switch selected profile** to update the persistent default. Moving the cursor alone does not write. The update shares `set_default_profile` with `opsfeast.py use`; failed validation or registry replacement preserves the prior saved default. Unavailable rows cannot be switched. On success both tables refresh and Hosts follows the new profile immediately. No connections or recipes run. The switch is blocked while a recipe action/profile update is active.

Recipe Actions using **Default Feast** resolve the new default on their next invocation. Explicit root/profile selections and already filled recipe/target inputs are preserved; switching does not silently rebind those forms. Checkout-only discovery remains checkout-only. Refresh reloads both management views without changing the default. There are no init/attach/detach/edit controls in this version; use their documented CLI workflows.

### Navigation and Help

The main tab strip receives initial focus. Left/Right selects adjacent sections without first clicking them. Ctrl+Tab / Ctrl+Shift+Tab cycles main sections; F1 opens Help; click tab headings to select them. Tab moves into a section's controls, and table Up/Down selects rows. In Hosts/Profiles, Up/Down from the main tab strip or a section button directly focuses the host Tree or profile table and moves its selection; no mouse click or preliminary Tab is required. When the host-details view has focus, Up/Down keeps scrolling that view. Shortcut-driven entry to Help/Actions focuses the tab strip; Recipes retains sidebar navigation, and delayed tab-activation callbacks preserve focus already moved into its sidebar/content; starting an Actions command focuses its Output result table. Shortcuts do not dismiss an execution review dialog. Escape moves focus back one tier: Recipes/Hosts right content → its left Tree sidebar → the main tab strip. It preserves the selected item and active section; on the main strip, Left/Right switches sections (for example Recipes → Profiles with Left). Other section controls return directly to the main strip. Escape on the main strip does nothing. Open Select dropdowns consume Escape locally, and modal dialogs retain their own cancel/close/active-run protection. Text already entered in a form is preserved.

Help renders allowlisted bundled README, first-use, first-host, terminal UI and CLI documents without launching external links. The original environment overview has been removed from Home; author defaults are shown instead. Initial background work reads the profile registry/configuration and the checkout recipe catalog once. It performs no installation, profile write, host probe or recipe execution. Opening/closing an idle UI returns 0; missing Textual returns 1, nonterminal stdin/stdout returns 2 with a CLI hint, and other display failures return 1. Active-run/profile-update close protection applies.

## Recipes workbench entrypoint

`python -B tools/opsfeast.py recipes` opens the interactive recipes workbench. Any explicit subcommand, including `recipes list`, `recipes run ...` and `recipes --help`, uses the ordinary CLI. Unknown subcommands and extra arguments are CLI errors; they never fall back to the workbench. Existing `--tui` commands still provide a single-invocation display.

Opening the workbench reads local catalog/result metadata, without connections, initialization or recipe execution. The **Recipes** section replaces Results / progress. Its left docked Tree labels checkout recipes **OpsFeast Bundle** and profile recipes with the actual default profile name (for example **testops**). Registered external sources retain their registered names. Internal source identifiers and recipe references remain unchanged. A profile source with no catalog recipes is hidden, including absent/disabled profile roots; other source nodes retain their available/unavailable/disabled states. Source status remains in parentheses and describes discovery, not execution readiness. Recipe directories form the hierarchy below each source, preserving identical paths as distinct nodes across sources. Select a recipe directory to update the right-side **Info** and **Executions** tabs. Info is initially selected and displays title/description, ID/version/source/reference, runner/static inspection status, inputs, dependencies, platforms, permissions, side effects, output contract, verification and inspection errors. Undeclared fields remain explicit. This is literal catalog metadata, not proof of installed dependencies or successful execution. Executions contains timestamp/status/host/result history. Highlight, click or press Enter on an execution row to read its saved result into the Details and Original output subtabs below the table. Details formats a display copy of the JSON, with local whole-second timestamps; Original output preserves the saved file text. These views contain only the selected execution of the selected recipe, never the most recent global action output. Changing recipe clears the previous execution output. Missing/deleted/changed-provenance/invalid results show an unavailable notice rather than stale data; local storage path/symlink guards apply. Switching recipe nodes updates both views without changing the chosen right-side tab; selecting a source/directory without a recipe clears stale information.

History converts timezone-aware start times to the running system's local timezone and displays `YYYY-MM-DD HH:MM:SS`, without fractional seconds or a per-cell timezone suffix. The column heading carries the offset, for example **Time (started, GMT+8)**; the offset is not hardcoded. Historical daylight-saving rules are applied per timestamp; a table spanning multiple local offsets lists them in the heading, for example GMT-5/GMT-4. Missing values stay unknown; malformed or timezone-less values show `(invalid or unzoned time)` rather than assuming UTC. Saved JSON and Original output retain the original timezone and full precision. It shows exact status, executed host ID and result ID. It indexes the selected default Feast's existing observations/reports files. The host column is the runner's resolved host_id (the selected --host value for direct host runs); offline reports have no host and are labelled accordingly. Partial/failed/skipped/unsupported states remain distinct, and missing host/time stays unknown. No raw file means no retained execution-history row; the UI does not fabricate records for preflight failures or commands that do not save results.

Rows match both recipe_source and recipe_reference, not recipe ID alone. Different versions at the same source/reference remain visible. Records without these provenance fields are counted as unattributed and are not assigned to any source by guesswork. Invalid result files remain visible as an error count. Source status and browser errors do not imply operational success. This is the raw execution index, not identity-aware retained observation analysis.

Refresh recipes / history re-reads metadata. Switching the persisted profile refreshes the browser and Hosts; completing an action or closing a completed host-operation dialog refreshes history. No profile means checkout catalog with empty execution history. Invalid selected Feast configuration is reported rather than silently falling back. Browsing does not import or execute recipe entrypoints.

**Actions** now contains **Configure** and **Output** subtabs. Running an Actions form switches to Actions → Output, which contains the global action summary table, Details, Progress / errors and Original output. Recipes has only Info and Executions. Execution Original output is the saved observation/report JSON, not an archived process stdout/stderr stream; the runner does not persist those streams as execution history. Live command stdout/stderr remains in Actions → Output for the current action. Main-tab shortcuts remain available; Up/Down from the Recipes tab heading focuses its Tree. Group/directory nodes prompt for a recipe; selecting a recipe updates only its history. Bare recipes has Recipes/Actions sections; the full Home entrypoint uses the six-section order above.

The action menu supports all current recipes command families:

| Action | Shared CLI |
| --- | --- |
| Browse / inspect recipes | list / show, query/kind filters and optional HTML export |
| Run recipe / report | run, exact host/group/all selection, exclusions, variables, inputs and concurrency |
| Browse / inspect results | results list/show, filters and optional HTML export |
| Verify artifact | artifact, result ID and declared artifact name |
| Saved jobs | jobs list/show/save/run |
| Recipe candidates | pack with explicit file allowlist; unpack into a new directory |

Select checkout-only for catalog/show/pack, or default Feast, named profile or Feast directory for operations and private records. The workbench does not switch the persisted default. Unpack uses its explicit archive/destination and needs no Feast. Empty environment paths/names and missing required fields are rejected in the form. Existing configuration, recipe, source, path, input, job drift and artifact/bundle checks remain in the CLI.

List fields use JSON arrays, for example hosts `["host-01", "host-02"]`, groups `["web"]`, inputs `["/path/to/input.json"]` and bundle files `["recipe.yaml", "main.py", "README.md"]`. Variables use a JSON object such as `{"port": 8888, "label": "example"}`; string values stay literal and non-string values become JSON for the existing typed `--var` interface. All-host selection is `true` or `false`. Unused fields are hidden and ignored, so values from another action do not become extra options. Report inputs and operational host selectors remain distinct; the shared CLI validates compatibility with the selected recipe. There is no implicit all-host selection.

Press **Apply / review action**. Read-only actions run immediately. Recipe/job execution, job saves, pack/unpack and HTML exports first display their exact CLI argument list and require **Confirm and execute**; **Cancel** performs nothing. The preview shows requested selectors and supplied values, not an expanded target inventory or resolved variable defaults. Inspect the recipe and review its dependencies, permissions and behavior before executing. This local confirmation does not create a durable approval record or authorize operations outside the user's scope.

Only one action runs at a time. After completion the workbench stays open; select Actions to continue. Each action's exit code and stderr remain visible until the next action replaces the display. Closing an idle workbench returns 0; launch/display errors return 1 or 2 as above. Active-run close shortcuts remain disabled. This is a persistent interface over the shared CLI, not a shell, installer, publisher, scheduler or execution sandbox. Artifact verification returns metadata/path and does not launch a viewer.

## Installation and availability

Use Python 3.11+ in your selected OpsFeast environment. Textual is optional and pinned separately from the base dependencies:

```sh
python -B -m pip install -r requirements.txt -r requirements-tui.txt
python -B tools/check_environment.py
python -B -c "from importlib.metadata import version; print(version('textual'))"
```

Install only within the user's authorized environment; do not replace or upgrade an existing environment automatically. This integration is tested with Textual 8.2.8. `check_environment.py` checks the base environment and SSHScript bundle, not optional Textual availability. Initialization/configuration-only users can install `requirements-init.txt` plus `requirements-tui.txt`; host operations still require SSHScript 6.0.0.

The UI requires terminal stdin and stdout. Missing Textual returns 1 before starting the command. A pipe, redirected stdout, unsupported command or repeated `--tui` returns 2 before execution. There is no silent fallback that could execute an operation after a UI prerequisite failure. Omit `--tui` for AI agents, scripts, JSON pipelines and noninteractive use. Ordinary commands do not import or require Textual.

## Supported commands

The flag may be placed after the existing command and arguments:

```sh
python -B tools/opsfeast.py inspect-recipe --tui
python -B tools/opsfeast.py check --profile main --tui
python -B tools/opsfeast.py test-host host-01 --profile main --tui
python -B tools/opsfeast.py test-su host-01 alice --tui
python -B tools/opsfeast.py test-sudo host-01 --run-as root --tui
python -B tools/opsfeast.py recipes run system/inventory/overview --group web --threads 4 --tui
python -B tools/opsfeast.py recipes list --checkout-only --tui
python -B tools/opsfeast.py observation result --profile main --tui
python -B tools/opsfeast.py observation result RESULT_ID --profile main --tui
python -B tools/opsfeast.py recipes results list --profile main --tui
```

Supported `opsfeast.py` commands are `check`, `inspect-recipe`, `test-connection`, `host-init`, `test-host`, `test-su`, `test-sudo`, `recipes list/show/results/run`, and `observation result [RESULT_ID]` (host history/diagnosis/detail). Batch observation views do not support --tui. Recipes results and the workbench result actions are offline-report-only. All existing `opsfeast.py recipes run` selections and typed inputs remain available. Profile registration/switching and initialization are outside the recipes workbench. Bundles, artifacts and saved jobs are available through the workbench forms or their ordinary CLI; the single-invocation `--tui` flag supports only the commands listed above.

Examples involving diagnostics or recipes are executions and require the user's actual target/operation scope. Opening a UI is not an execution preview: the supplied command starts immediately after UI prerequisites pass, and the ordinary command's configuration/selection checks still run before connections. The single-invocation display has no selection menu; use the bare recipes workbench for its action forms.

## Reading the display

- The table shows host/test/recipe, reported status, current stage or final reason, elapsed time, retention status and result path where supplied.
- Select a row with the arrow keys to inspect its complete CLI result entry in **Details**. Diagnostic reports show their tests or account chains, with steps and identity evidence in the details. Missing status stays `unknown`; connected alone is not success.
- **Progress / errors** shows existing stderr, including safe diagnostic messages, warnings and errors. This scrollback keeps the latest 2,000 lines; it is not persistent logging.
- **Original output** preserves the child's stdout for inspection. Catalog/inspection commands request their existing `--json` representation. Plain-text commands and usage errors remain readable even without valid JSON.
- The final summary shows status counts and the command's exit code. Partial, skipped, unsupported and failed remain distinct. Excluded hosts are counted separately and remain in original output. A successful collection with failed retention keeps both states visible and retains the command's failure exit code.

Press Tab to move focus between the table and tabs; use arrow keys and scrolling to inspect data. Press `q`, Ctrl+C or Ctrl+Q after completion to close. The UI returns the child's exit code, including usage error 2. It consumes stdout for display rather than printing final JSON after closing. Saved result paths and storage behavior follow the [CLI reference](cli.md).

Elapsed time is local wall time from first display of a row, including queue waiting for selected hosts; it is not a remote command duration. Final diagnostic rows without individual timing use the invocation duration. There is no percentage estimate for unknown-duration operations.

## Execution and extension limits

The display runs the existing CLI in a subprocess using the same interpreter, working directory and arguments, with stdin closed. It requests verbose progress unless the caller explicitly selects quiet. `--quiet` suppresses live recipe stage messages; final results still appear. The runner sends structured host selection/stage/completion events through a private presentation transport, so the UI does not infer statuses by parsing human progress lines. The final JSON remains authoritative. Host diagnostics expose current stage; individual test/group rows appear when their final report is available. Offline reports and catalog operations may show only the final result and existing stderr.

There is no recipe-author API, persistent logging service, automatic cancellation or public event subscription contract. Recipes keep their existing execution/result contracts. Keep new renderers as presentation adapters over those contracts; do not use UI events to make execution decisions or claim remote completion/cleanup. Custom recipes that require interactive stdin are not supported in this display mode.

Close shortcuts are disabled while the command is active. If the display fails, the adapter attempts to terminate and reap its local child process. A crashed or forcibly closed terminal can interrupt execution; this does not prove remote-process termination or cleanup. Review saved reports and existing cleanup evidence before retrying. Starting the UI again starts a new invocation; it does not resume a previous run. The UI does not expand credential access or sanitize arbitrary custom recipe output: only expose data appropriate for the terminal user.

Public synthetic tests cover argument forwarding, dependency/TTY failures before execution, structured events, status interpretation, child streams/exit codes, literal Unicode/markup text, active-run close shortcuts and narrow terminal layouts. Base CLI suites cover existing selection/execution/storage behavior. These tests do not establish real SSH/su/sudo behavior or every terminal emulator.

## Group catalog in the Hosts tree

The Hosts pane uses the shared effective group catalog. A group label differing from
its ID displays as LABEL (ID); unchanged/default labels display the ID. Labels and
descriptions are literal text, including markup-like characters. Highlight a group
to inspect its ID, label, description, configured icon defaults and member IDs.
Declared empty groups remain visible. Group nodes do not open host/account action
menus. Host/account leaves retain existing explicit action scopes and masked details.

The same host can appear in multiple branches with the same effective settings and
icons; the primary group is the first effective membership, regardless of the branch
currently displaying it. Group host/user icons supply defaults with the shared
precedence, rather than changing when a host is viewed in another branch. See
[bulk configuration and metadata](hosts-yaml.md#host-groups).

## Consistent local time in human views

Home download time and live/saved-result Details now use OS local time at whole-second
precision, matching history. The displayed Details object is a copy; stored item data,
Original output and JSON exports retain the original timezone/precision. The history
heading still names its offset(s). See [the shared time policy](cli.md#human-time-display-policy)
for DST, invalid/unzoned timestamps, HTML generation and machine-data exceptions.

_Last modified: 2026-10-23 08:11:44_
