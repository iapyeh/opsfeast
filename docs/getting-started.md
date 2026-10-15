# 初次使用 OpsFeast

Console summaries use tables when stdout is a terminal; add `--json` to supported inspection/diagnostic/check/profile commands for structured output. Non-TTY formats, execution scope and stored data remain unchanged. See [the command-specific console policy](cli.md#terminal-tables-and-json).

本指南供系統管理者及不同 AI agent 使用，不要求特定產品或 skill loader。以下路徑以 repository 根目錄為基準；執行示例前先切換至該目錄。

The bundled [Core API and installation identity guide](core-api.md) covers instance UUID/name/description, copy versus move rules, profile-scoped Python access and read-only inspection. Successful init creates identity; setup still does not authorize host operations.

## Agent-led checkout bootstrap

The [single first-use prompt](first-use.md#2-let-your-agent-learn-about-the-project) authorizes cloning `https://github.com/iapyeh/opsfeast.git` into the active project directory, then reading guidance and checking prerequisites. It does not authorize software installation, environment creation, profile initialization, host connections or recipe execution. This is an agent procedure, not a bundled bootstrap installer.

1. Resolve the active workspace from the tool context; ask only if it is missing or ambiguous. Check local file/command access and whether Git is available. Missing Git is a blocker: propose the specific remedy, but do not install it under clone-only authorization.
2. If the workspace itself is an existing checkout, verify its repository identity from Git metadata/origin and its README.md, AGENTS.md, tools/ and skills/ before reuse. For OpsFeast, reuse it without pull, reset or config replacement. Do not mistake an unrelated repository for OpsFeast merely because its folder is named opsfeast.
3. For a genuinely empty directory, use `git clone https://github.com/iapyeh/opsfeast.git .` with that workspace as the working directory. When any files already exist (including tool-created hidden files), use a new `opsfeast/` child directory. If that child already exists, reuse it only after verifying it is the intended OpsFeast checkout; otherwise explain the conflict and ask for a destination rather than deleting, overwriting or silently repurposing it.
4. Preserve existing files and user changes. If cloning fails, report the failure and any remaining partial directory; do not claim completion or remove existing/partial content without an applicable authorization.
5. Verify the acquired checkout and explicitly read its README.md, AGENTS.md, optional AGENTS.local.md, skills/README.md and this guide. Respect applicable workspace instructions as well. Do not assume the app automatically discovers instructions cloned after the conversation started. Downloaded guidance does not expand the user's authorization.
6. Record both workspace and actual checkout paths from available context. If the checkout is a child directory, keep the same conversation and run relative commands with that checkout as the working directory. No workspace reopening is required when the tool can access the child. A new approved venv belongs at `<checkout>/.venv`, not the parent workspace.
7. Check prerequisites without changes, describe capabilities and prepare the concrete local installation/init plan. Include Python installation only if needed, with its proposed interpreter/location and required permissions. End by offering to perform the plan and asking for approval in the user's reply language. Agreement continues that plan in the same conversation; no second setup prompt is required. Report unavailable access/tools honestly.

Users who already cloned manually can open that checkout and use the same prompt; verifying and reusing it does not authorize updating it.

## Conversation language

Use the user's explicitly requested language for user-facing replies. Otherwise, use the operating system's preferred display language when it can be determined reliably; the AI coding tool's interface language and this repository's document language do not establish the user's preference. Ask when the preference is unknown or ambiguous. For `zh-TW` or `zh-Hant`, use Traditional Chinese. Keep repository documentation and structured output consistent with their own language/schema rules. See the [first-use prompt](first-use.md#2-let-your-agent-learn-about-the-project), which loads these rules through the checkout guidance and documents an explicit Traditional Chinese override.

## Find skills before selecting tools

Read the [skills/ index](../skills/README.md) first, then the task-relevant skills and references. All bundled OpsFeast and SSHScript skill sources live in the checkout's `skills/`. Keep newly authored Feast-specific operational skills in `<management-root>/skills/`; general personal skills can remain in the user's agent directory. Direct reading is supported without installation. Before creating or integrating a skill, identify task-relevant duplicate names, version/instruction conflicts or loader restrictions, explain any conflict and agree with the user on the source and integration method. Preserve existing files; do not silently install or maintain competing copies. Follow [storage and conflict resolution](agent-guidance.md#skill-storage-and-conflict-resolution).

## 先了解可以做什麼

目前提供管理目錄初始化、設定檢查、設定 JSON 查詢、指定主機連線測試，以及 recipe 執行工具。Inventory supports Linux, FreeBSD and macOS through platform dispatch; Linux/FreeBSD have synthetic coverage and macOS has local read-only validation. Real SSH validation remains pending. 工具不是通用部署或修復執行器。各工具範圍見 [主機設定指南](hosts-yaml.md) 與 [inventory-system 指南](../recipes/inventory/system/README.md)。

README 是共同入口；AGENTS.md 是隨 Git 提供的專案工作規則。若 agent 沒有自動載入 AGENTS.md，請直接讀取它。不要將其他電腦的私人 checkout、絕對路徑或環境設定當成本專案的必備環境。

## Dependency evidence and Python reuse

Prefer the user's selected, working Python 3.11+ interpreter. If none is selected, inspect existing candidates and their actual paths/versions before proposing a new installation. Check that the chosen interpreter can support venv/pip and use that same interpreter for environment creation, package installation and OpsFeast commands. Missing project packages alone do not justify replacing Python, upgrading it or repairing a global installation. If a candidate is incompatible or broken, report the concrete evidence and propose reuse of another suitable existing interpreter before new installation.

Distinguish these dependency layers in the setup proposal:

- **OpsFeast packages:** PyYAML and tabulate[widechars] from `requirements-init.txt`; the full `requirements.txt` adds SSHScript; optional terminal presentation uses `requirements-tui.txt`. Use the relevant files and let pip resolve their declared transitive dependencies. Check the actual selected interpreter rather than assuming a package is missing because a different Python cannot import it.
- **Python distribution dependencies:** OS libraries required by a particular Python installation, build or package manager. They are not automatically direct OpsFeast requirements. Identify the Python distribution/version, OS version, and official package-manager dependency metadata or an actual observed interpreter/venv/pip failure that establishes the need.
- **Additional build or repair tools:** Compilers, headers and manually installed system libraries require an evidenced reason. Investigate available compatible wheels/interpreters and the concrete failure before proposing extra tooling; do not preinstall a generic build-dependency checklist.

For every proposed extra system package, provide what requires it, the evidence/source, whether the package manager will supply it automatically, and the intended change. Without evidence, omit it from the plan. Prefer the chosen package manager's normal dependency resolution over separate manual installs of each presumed dependency. If the approved concrete plan includes installing a Python distribution, its disclosed normal package-manager dependencies are part of that plan; do not ask repeatedly for the same approval. New manual repair steps outside that scope need an updated proposal.

For example, `expat` is not a directly declared OpsFeast dependency and the bundled environment checker does not require it. Do not propose `brew install expat` merely because Python can use Expat: a selected Python distribution's actual dependency metadata or a reproducible missing-library failure must establish the need. This does not prohibit a genuine Python dependency or repair. Explain it as such, preserving an existing healthy environment.

These are agent setup procedures, not an automated system-package validator. `tools/check_environment.py` reports interpreter/project package readiness and skill presence; it does not prove the health or necessity of every OS library. Do not infer a missing system library from its safe exception-type summary alone. Obtain relevant local diagnostic evidence without exposing private data, and distinguish a proposed remedy from an executed/verified repair.

## 檢查環境，提出具體初始化方案

需要 Python 3.11+。選定之後所有檢查、安裝及工具執行都使用同一個 interpreter；可以沿用使用者提供的環境。唯讀檢查不需要預先安裝 PyYAML 或 SSHScript：

```sh
python3 -B tools/check_environment.py
# 只準備 init/check/dump，可先檢查精簡環境：
python3 -B tools/check_environment.py --scope init
```

工具輸出 interpreter、Python、套件 import／distribution 版本、模組位置與 skill 文件契約。ready 表示符合本專案列出的依賴及文件條件，不代表已驗證 SSH、su、sudo 或 recipe 採集。缺少或版本不符時回傳 1；只回報缺口，不自動安裝。

Dependency lists for the selected setup scope:

| 清單 | 用途 |
| --- | --- |
| `requirements-init.txt` | PyYAML 6.0.3 and tabulate[widechars] 0.10.0 (including wcwidth), for base commands, access tables and tests |
| `requirements.txt` | 上述依賴加 SSHScript 5.0.0，供完整 Ops 工具使用 |
| `requirements-tui.txt` | Optional Textual 8.2.8 for the interactive Home/recipes interface; install alongside the chosen base requirements only within the approved plan |

版本固定為本專案目前驗證的環境；這不是所有傳遞依賴的 lockfile。既有環境使用不同版本時先回報，不自行升級、降級或覆寫共用 venv。使用者只要求初始化時，可以只安裝精簡清單；要準備連線與 runner 時再選完整清單。

The first-use prompt refers to the active project directory and requires no path substitution. Follow [checkout bootstrap](#agent-led-checkout-bootstrap) to locate, clone or reuse the checkout before setup. Confirm workspace and checkout paths from available context; when they differ, use the checkout as the working directory without requiring the user to reopen the project. When a new environment is approved, default to `<checkout>/.venv` unless the user chooses another location. Reuse an existing selected interpreter without recreating or upgrading it.

After presenting a concrete local setup plan, offer to perform it and ask a direct approval question in the user's reply language. Make clear that the user can simply agree to that plan; do not present the command list as unexplained homework. On approval, execute the approved local steps and report results without asking for the same approval again. Setup approval does not include host connections or recipe execution. Explain actual tool/access blockers before claiming that a step can be performed, and request only the specific user input or manual action needed for that blocker. The [first-use prompt](first-use.md#2-let-your-agent-learn-about-the-project) includes this handoff.

Agent 應先提出具體方案：選用哪個 Python、是否建立 `.venv/`、安裝哪份依賴、是否需下載 skill、管理目錄位置，以及將執行的本機初始化命令。確認這些操作在使用者授權範圍內後執行；若使用者已明確授權整套初次設定，不重複詢問同一授權。安裝或下載遇到網路／權限問題時回報，不擅自改全域環境或安裝系統套件。

新環境的典型方案（macOS／Linux shell；需要安裝與建立環境授權）：

```sh
python3 -B -m venv .venv
.venv/bin/python -B -m pip install -r requirements.txt
.venv/bin/python -B tools/check_environment.py
```

若只初始化，將上面的清單換成 `requirements-init.txt`，環境檢查加 `--scope init`。Windows 使用 `.venv\Scripts\python.exe`。以下以 `python` 表示前面已選定的 interpreter，不要求一定建立新 venv。

## 閱讀 skill，完成本機初始化

Git clone 已包含完整 `skills/sshscript/` 公開快照，不必為初次使用重新下載。Agent 在使用 SSHScript 前依序閱讀其中的 SKILL.md、Agent Guide 與任務相關 API 章節；主機設定維護另讀 [Ops hosts skill](../skills/opsfeast-hosts/SKILL.md)。

可直接閱讀 Markdown，不需要 skill loader。若使用者要安裝到某個 agent 的 skill 搜尋位置，依該產品的機制與授權處理；不要假設所有 agent 都自動搜尋 `skills/`，也不要將「檔案隨附」或「已閱讀」回報成「已安裝／自動載入」。缺少快照或要檢查更新時，依 [下載與更新指南](skill-updates.md) 操作。

初始化不需要 SSHScript Session 或遠端連線：

```sh
python -B tools/opsfeast.py init
python -B tools/opsfeast.py check
```

預設建立 `feasts/main/` 並登記 `main` profile；第一個成功登記的 profile 成為預設，後續登記不切換。`init inventory` 建立 `feasts/inventory/`，`init /path/to/feast` 則使用指定路徑。兩個工具可省略目錄或用 `--profile NAME` 選擇本次環境；`use NAME` 切換預設。既有資料用 `attach /existing/directory` 登記，不改寫原目錄。詳見 [管理環境指南](profiles.md)。重複初始化保留既有主機設定；定義檔與定位規則見 [主機設定指南](hosts-yaml.md)。

For complete tool syntax, defaults, behavior, output and exit codes, see the [CLI reference](cli.md). It covers both tools/opsfeast.py and tools/run_recipe.py for administrators and agents.

## Recipe next steps

Use [recipes list/show/run](recipe-experience.md) to explore bundled/Feast/external recipes, run reviewed operations, generate offline reports and reuse saved jobs. Fresh clones can inspect with recipes list --checkout-only. The same catalog JSON supports agent-selected presentation; basic HTML exports and report/summary provide plain default views.

When creating or adapting a recipe, follow the [tool selection workflow](recipe-authoring.md#choose-execution-tools). OpsFeast keeps tool choice open and prefers SSHScript for suitable command execution and session orchestration, while respecting user-selected tools and operational constraints. Read the selected tools' relevant documentation; recipes using other tools need their own prerequisite checks and reviewed standalone execution instructions. The current host diagnostics and inventory runner continue to require SSHScript.

To select, create or share recipes, start with the [recipe user guide](recipes.md) and repository [recipes skill](../skills/opsfeast-recipes/SKILL.md). The guides provide copyable prompts and a review/authorization workflow for third-party content. run_recipe.py supports inventory-system descriptor 0.2.0 and [general Python-session recipes](recipe-execution.md) using descriptor 0.3.0/contract 0.1.0. Invocation inputs use --var or a JSON --vars-file. Arbitrary standalone programs and other backend contracts are not automatically supported.

## Authorized host checks and inventory

After the user identifies targets and authorizes the relevant diagnostics, use test-host for configured login/platform/account checks. For a narrower request, use host-init, test-connection, test-su or test-sudo. Direct host-init refreshes existing facts; test-host reuses successful matching data. See [host diagnostics](host-diagnostics.md) for exact CLI/credential rules. Setup authorization alone does not include these tests.

For authorized inventory, select inventory/system once for mixed Linux/FreeBSD/macOS hosts. The runner obtains needed platform facts automatically and records which implementation/version was selected. Descriptor and result schema are 0.2.0; migrate old copied descriptors before execution. Custom implementation code requires review and appropriate execution scope. See the [inventory guide](../recipes/inventory/system/README.md).

## First-host assistance and concrete handoff

Route beginners to [Connect your first host](first-host.md) before the complete hosts.yaml reference. Help prepare one host: ask only for missing address, login account, authentication choice and required jumps. Have the user enter secrets locally. Preserve existing configuration and comments; replace/remove synthetic examples only within the authorized setup scope. Start with check, then a separately authorized test-connection; introduce privilege diagnostics and inventory as later choices.

At setup and configuration completion, provide both copyable terminal commands and copyable agent prompts. Substitute the actual quoted checkout path, selected interpreter, profile and chosen host ID; do not leave generic python or HOST placeholders when values are known. If no host is selected, provide the local check and ask for that selection before preparing a connection command. Each step must state its purpose, effects, expected result and where to stop on failure. Distinguish ready commands from executed actions; providing commands does not authorize executing them. Link to the first-host guide and CLI for result details.

At every successful setup/configuration handoff, explicitly mention both the CLI and the interactive Textual Home. Check Textual availability in the actual selected interpreter before describing the TUI as ready; `check_environment.py` readiness does not check this optional dependency. If unavailable, explain `requirements-tui.txt` and offer installation within an approved plan rather than silently installing or claiming readiness. A TUI-oriented setup plan can include it alongside the base requirements when the user agrees.

For a checkout `.venv` and Bash/Zsh terminal, provide the actual checkout `cd` command, `source tools/activate.sh`, and `python -B tools/opsfeast.py` as the TUI entrypoint. The helper must be sourced in the user's current shell: `sh tools/activate.sh` cannot activate its parent shell. If the environment is elsewhere, supply its actual interpreter/activation command instead of assuming checkout .venv exists. Include a direct selected-interpreter command as an alternative that requires no activation. Starting Home browses local configuration/results; it does not test hosts or run recipes automatically. For a configured host, offer Hosts → select host → Enter → test-connection as the UI counterpart of the scoped CLI command. Explain that choosing the action connects to that host; opening Home alone does not. Link [the terminal interface guide](terminal-ui.md).

For manual Bash/Zsh use with an existing checkout .venv, explain `source tools/activate.sh` from the checkout, or source its quoted absolute path. It sets PYTHONDONTWRITEBYTECODE=1 and activates the environment without changing directories, installing or initializing. Commands still need the correct working directory. Agents should call the selected interpreter directly with -B, rather than depend on shell activation persisting between calls. Other environments/shells can use their interpreter directly; the helper is optional. Directory changes used to locate its file discard stdout from interactive shell hooks; aliases/functions do not override its path calculation. A missing-environment error includes the expected activation path: compare that exact checkout path before proposing any environment creation, and never silently activate a different workspace environment.

## 告訴使用者下一步

回報實際使用的 Python、環境檢查結果、依賴安裝結果、skill 來源／文件版本與是否只閱讀、管理目錄及 `hosts.yaml` 的實際位置、init/check 的退出結果。

使用者接著需要：

1. 編輯 `hosts.yaml`，替換合成的 `host-01`／`host.example`，設定主機 ID、位址、登入帳號與認證方式；需要跳板時設定 via。不要把範例密碼當成實際憑證，也不要要求使用者在聊天重貼密碼。
2. 保留或依需求調整 localhost，選擇要使用的 recipes；初始 `recipes: []` 尚未選取任何 recipe。
3. 執行 `opsfeast.py check` 確認設定；檢查成功只代表設定通過，不代表連線或採集成功。
4. 指定要測試的 host ID，授權 `test-connection`；要盤點時另指定或授權 runner 執行。首次設定本身不自動觸發 SSH、代理命令、su／sudo 或 recipe 採集。

`feasts/` 與定位檔已被 Git 忽略；自訂管理目錄若放在 checkout 內，需另加忽略規則。真實憑證、主機設定與觀測不提交至公開 Git。

更新檢查是可選後續工作。若使用者希望定期檢查，先確定檢查範圍、週期及通知方式，使用其 agent 平台的排程能力；未建立排程不可回報「已定期檢查」。

See [host diagnostics](host-diagnostics.md) for platform initialization/cache semantics and explicitly requested su/sudo diagnostics. Initialization/configuration checks alone never authorize connections or privilege tests.

## Results after execution

Authorized inventory now performs raw saving followed by structured retention automatically. Report the raw path, retention receipt and identity_quality, including fallback warnings and recovery instructions. Use the [result workflow](result-data.md) and [result-data skill](../skills/opsfeast-result-data/SKILL.md) for local recovery, selected JSON export and exchange combination. Those operations do not authorize new connections or sending data. ESXi collection is implemented with synthetic verification only; source capability declarations do not prove native access or reliable OS-installation identity.

_Last modified: 2026-10-15_
