---
name: opsfeast-hosts
description: Maintain OpsFeast hosts.yaml and profiles, initialize host platform facts, and diagnose connections or configured su/sudo access when requested. Use for host configuration and diagnostics; recipe authoring belongs to opsfeast-recipes.
---

# OpsFeast 主機設定維護

Start with the [central skill index](../README.md). Keep newly authored Feast-specific skills in the selected management root's `skills/`; check task-relevant source/loaded copies and agree with the user on any naming, version, instruction or loader conflict before the affected action. Follow [storage and conflict resolution](../../docs/agent-guidance.md#skill-storage-and-conflict-resolution).

初次設定環境時先依 [初次使用指南](../../docs/getting-started.md) 檢查 Python、依賴與授權範圍，完成初始化後告知使用者應設定的主機、帳號與 recipes。需要準備或檢查公開 SSHScript skill 時依 [下載與更新指南](../../docs/skill-updates.md)；檢查不自動替換快照或升級套件。本 skill 與連結的 Markdown 可直接閱讀，不要求特定 agent loader。

使用者指南與設定規格位於 [docs/hosts-yaml.md](../../docs/hosts-yaml.md)。開始設定工作時閱讀它；不要自行建立另一套欄位語意。這是 repository 內的 skill，使用時保留 repository 結構。若要獨立安裝，需一併打包指南並調整此連結；目前未提供 skill 安裝工具。

Repository 提供 [tools/opsfeast.py](../../tools/opsfeast.py)：使用安裝 PyYAML 的 Python 執行 `init [名稱或路徑]` 建立樣板，或 `check [管理根目錄]` 做唯讀檢查；`dump <設定路徑> [管理根目錄]` 可輸出 include 合併後的指定設定（JSON 縮排 4 格），例如 `dump hosts.host-01 <管理根目錄>`。Dump 只做載入檢查，不等同完整 check，並會原樣輸出選取值，包括密碼欄位。使用者要求實際測試連線時，可用 `test-connection <host-id> [管理根目錄]`，需要 SSHScript 4.0.1+，只在指定目標執行 hostname 與 date；先讀使用者指南中的工具範圍；完整 recipe 執行器尚未實作。先確認 repository 的實際狀態，使用已存在的驗證入口。只做人工審閱或 YAML 語法檢查時，明確區分它們與完整語意驗證，不虛構 CLI、schema 或成功執行結果。

Use tools/opsfeast.py for new commands. Existing CLI/configuration names remain supported; see [rename compatibility](../../docs/migration.md). Profiles select private Feast instances; [ecosystem terminology](../../docs/ecosystem.md) distinguishes these from planned Buffet exchanges.

## Inventory access and result capability 0.1.0

Read [the complete inventory access/results guide](../../docs/inventory-access.md) before selecting accounts, testing access, running inventory, authoring collectors or interpreting/exporting new values. It documents exact interfaces, settings, source selection, dependencies, authorization, failure/skip/fallback states, units, scope and verification limits.

- Use check-access for selected hosts.yaml login/root validation; inventory --dryrun adds static recipe/input checks. Both make real connections and sudo attempts, but create no inventory or host-init data and never su to other users. Test-host is a broader diagnostic.
- Inventory 0.3.0 defaults to verified root/sudo; account sudo: "false" deliberately selects ordinary-account collection. Canonical sudo-password selects by presence: null/empty mean empty password; exact "false" means account-password fallback. Other disabling representations are invalid; no retry with another credential. Prefer these canonical fields; preserve legacy vars credentials and do not rewrite private configuration.
- The default batch gate rejects collection after any required access failure. Force allows connection skips and verified user fallback; uncertain identity/restoration/cleanup still stops that host. Dryrun/force are mutually exclusive and inventory-only, not saved-job flags. Check access.mode, batch counts and exit code separately from collected values.
- Pure results are inventory.system/hardware/storage/network/software/services with fixed nullable typed fields. Raw collection_process/observations/sources preserve execution evidence. Retention/exchange preserve inventory and minimal collection_scope, omit diagnostics, and keep original times/identity quality. Old records remain valid; update strict consumers before accepting new extension fields.
- For CSV use observation_store.py export --format csv with explicit filters; null becomes an empty cell, zero stays zero, empty lists remain []. JSON is the exchange contract. For SQL query the retained payload with json_extract; for reports reuse the updated offline report/summary or reviewed user recipes. A later run with another account is separate history, not automatic field merging.
- Extra queries have byte/item/command/shared time bounds and platform gaps. Root does not guarantee complete visibility. No new native SSH/sudo or all-platform collection evidence follows from synthetic tests. Do not install missing tools, probe arbitrary files or transmit exports without scope.

## Beginner setup and handoff

For user-facing setup explanations, follow the [conversation-language guidance](../../docs/getting-started.md#conversation-language): explicit user language first, then reliably known OS display language, otherwise ask; an English tool interface does not imply English replies. Keep repository documents and structured output under their own rules.

After a concrete local setup proposal, explicitly offer to execute it and ask whether to proceed in the user's reply language. Agreement authorizes that exact local setup; carry it out rather than assigning the commands to the user or repeating an already granted approval. Explain any actual tool/access blocker and the specific help needed. Setup agreement does not authorize connections or recipes. See [the first-use handoff](../../docs/first-use.md#3-review-the-plan-and-authorize-local-initialization).

For a fresh workspace, follow [agent-led checkout bootstrap](../../docs/getting-started.md#agent-led-checkout-bootstrap): clone only within the prompt's scope, preserve existing workspace files, verify and reuse an existing clone without updating it, and explicitly read newly acquired guidance. Clone authorization does not authorize software installation or initialization. Confirm workspace and actual checkout paths from context; use the checkout as the working directory and place a newly approved environment at `<checkout>/.venv`, without requiring project reopening. Ask only for genuinely missing/ambiguous context or a destination conflict. Reuse user-selected environments and call the selected interpreter directly with -B. Follow [getting started](../../docs/getting-started.md) for the approval handoff and optional Bash/Zsh activation.

Prefer an existing compatible, working Python and follow [dependency evidence and Python reuse](../../docs/getting-started.md#dependency-evidence-and-python-reuse). Separate requirements-file packages from Python distribution/system dependencies. For each proposed extra system package, identify its actual consumer and failure evidence or official distribution/OS dependency metadata; state whether the package manager handles it automatically. Do not independently preinstall presumed libraries such as expat or build tools. Missing PyYAML in another interpreter does not justify replacing the selected environment. Genuine repairs remain within the user's concrete scope, without repeating an already granted approval.

For a first host, read [Connect your first host](../../docs/first-host.md) before the complete reference. Ask only for missing address, login account, authentication method and required jumps. Help prepare one host and tell the user where to fill secrets locally. Preserve unrelated hosts/includes/comments; identify host.example as synthetic. Run configuration check within scope. Start authorized connection testing with test-connection; introduce su/sudo, test-host and inventory only when needed and authorized.

Always include the optional interactive Home in a successful setup/host-configuration handoff, alongside CLI commands. Check Textual in the selected interpreter; if missing, explain `requirements-tui.txt` and propose its authorized installation. For a checkout .venv and Bash/Zsh user, give the actual checkout `cd` command, `source tools/activate.sh`, then `python -B tools/opsfeast.py`; otherwise give the actual selected interpreter command. Explain source versus direct execution and that activation only changes the user's current shell. Home browses local data; Hosts → host → Enter → test-connection is a connecting action within that host's scope. Do not claim the user's shell was activated by an agent subprocess. On a missing-environment error, compare its expected path rather than recreating or selecting a different environment silently. See [the interface handoff](../../docs/first-use.md#use-the-cli-or-try-the-interactive-home).

At setup/configuration completion, supply exact copyable terminal commands and agent prompts with the actual quoted checkout path, interpreter, profile and selected host ID. Provide a local check first, then applicable connection/inventory steps with purpose, side effects, success evidence and failure stopping points. If selection is missing, provide the check and ask for the host. Do not claim proposed commands were run or execute beyond existing authorization. The first-host guide contains canonical beginner examples; CLI remains the argument/result reference.

## Command reference

The current host connection, platform and account diagnostics use SSHScript; they do not offer backend selection. For new recipes or operational workflows, follow the [tool selection workflow](../../docs/recipe-authoring.md#choose-execution-tools): prefer SSHScript when suitable, respecting user-selected tools and environment constraints. Configuration-only maintenance does not require an SSHScript Session or justify adding one for demonstration.

Read the [CLI reference](../../docs/cli.md) when choosing, explaining or running opsfeast.py commands. It is the shared administrator/agent manual for all subcommands, root/profile argument forms, output and exit codes. Use the detailed guides below only for the configuration/diagnostic mode needed.

## Host initialization and account diagnostics

For connection/platform/account checks, read [host diagnostics](../../docs/host-diagnostics.md). New diagnostics require matching SSHScript import/distribution 5.0.0. Read the bundled public SSHScript skill, Agent Guide and authenticated-console API sections before privilege tests; reuse already-read applicable material. Setup/configuration requests alone do not authorize connections, proxies, su/sudo or recipe execution. Apply the user's existing authorization without asking again.

Choose the narrowest command that satisfies the request:

| Request | Command from repository root |
| --- | --- |
| Check login and hostname/date | `python -B tools/opsfeast.py test-connection HOST [ROOT]` |
| Refresh platform facts | `python -B tools/opsfeast.py host-init HOST --root ROOT` |
| Check login and refresh facts | `python -B tools/opsfeast.py test-connection HOST ROOT --host-init` |
| Check configured host capabilities | `python -B tools/opsfeast.py test-host HOST --root ROOT` |
| Independent su targets | `python -B tools/opsfeast.py test-su HOST user2 user3 --root ROOT` |
| Two independent su chains | `python -B tools/opsfeast.py test-su HOST --chain user2 user3 --chain user3 user2 --root ROOT` |
| Login-account sudo | `python -B tools/opsfeast.py test-sudo HOST --root ROOT` |
| Other sudo actors | `python -B tools/opsfeast.py test-sudo HOST user2 user3 --run-as root --root ROOT` |

Use the selected interpreter instead of assuming `python`. New commands accept `--root` or `--profile`, not a positional management root; omit both for the default profile. Existing test-connection retains its positional root. `--timeout` is per stage/command, not a whole-run deadline.

- Direct host-init and test-connection --host-init refresh facts. Test-host reuses successful target-matching facts, otherwise probes; failed latest refresh never becomes a reused success. Show cache/probe provenance and original observation time. Endpoint reinstallation or external SSH-config changes require explicit refresh; the cache has no age expiry.
- Test-host includes login checks, platform initialization, enabled connection-account sudo using the selected password or passwordless policy, and independent su to other declared accounts. It does not enumerate accounts or test chains. This is the explicit exception to ordinary configuration work never selecting su targets automatically.
- Test-sudo usernames are actors; omitted means the actual connection identity, and --run-as selects the sudo target (default root). Another actor requires verified su entry first. Distinguish failed su prerequisites from an attempted sudo failure.
- For sudo use the canonical account field-presence rules in the access guide. For su select the first non-null credential: users.<target>.vars.su.password, host vars.su.password only for the actual connection account, then users.<target>.password. Test-su excludes the connection account, so host su overrides do not apply to its targets. Apply this rule to independent tests, chain steps and su prerequisites for other sudo actors. Preserve empty strings; reject invalid selected values; never retry lower-priority credentials after an entry failure. Report the source without the value. See [credential precedence](../../docs/host-diagnostics.md#credential-precedence). Diagnostics select the target with --run-as; they do not read vars.sudo.user. Standalone test-sudo and test-host can test enabled passwordless sudo.
- Test-su requires targets excluding the actual connection account. Space-separated targets are independent; each repeated --chain is an independent ordered chain. Do not mix forms. Missing required credentials are skipped; failed/skipped predecessors prevent remaining chain steps. Other groups use fresh sessions and continue.
- Report verified identities, entry/command/cleanup failures and skipped reasons separately. Shell sudo success does not establish command-specific privileges or prove password consumption. Test-host partial/skipped can return exit code zero; inspect JSON statuses rather than treating zero as all tests verified. Native SSH/su/sudo support has not been established by synthetic tests.

## Profile lifecycle

Use attach PATH [--profile NAME] for existing directories (the former add command is removed), init [NAME] to create/reuse a Feast, and use NAME to choose the default. Init without a name means main. Detach NAME removes only a registration and preserves all directory contents; never detach main, auto-delete missing registrations or auto-attach a directory just because it exists. Detaching the current default requires a registered usable main and changes the fallback/removal in one atomic registry write. If main is absent/invalid, fail without modifications; explicitly repair it or use another profile before detaching. Profiles basic available/missing/invalid/unavailable status is not full configuration or connection evidence. Read the [profile guide](../../docs/profiles.md#detach-a-registration) and [CLI reference](../../docs/cli.md); registry operations do not authorize host execution.

## 工作入口與編輯範圍

連線診斷可加 `--verbose`（進度）、`--debug`（篩選後的有效設定）及 `--traceback`（不含原文、source 與 locals 的堆疊）。JSON 的 hops 與 error.hop 區分每跳；key_source 指出 identity_file 從哪一個 parent 主機讀取。這些是 Ops 自己的診斷，不等同啟用 SSHScript 原始 DEBUG log。診斷寫 stderr，stdout 保持 JSON；不要為了除錯回貼密碼、代理命令或 token，也不要只憑提示就聲稱已找到根因。

- 以使用者提供的管理根目錄為入口，讀取其中的 `hosts.yaml`。沒有明確根目錄時，依工具所在 checkout 的 `.opsfeast.yaml` 使用預設 profile，或使用 --profile NAME 選取；缺少登記或位置無效時明確回報，不自行改查其他目錄。無參數 init 新建 feasts/main，具名 init 新建 feasts/<name>；帶路徑分隔符的參數是自訂路徑。既有目錄用 attach <directory> 驗證登記，不能為了登記執行 init 改動它。新增不切換預設；use NAME 才切換。名稱衝突須詢問使用者，非互動時以 --profile 指定選定名稱。細節見 [管理環境指南](../../docs/profiles.md)。
- 確認要建立、修改或查詢的主機 ID 與目標。已提供的資料不重複詢問；只詢問會影響結果的缺漏。
- 先讀既有入口及相關 include，保留主機 ID、分檔方式、註解與不相關設定。修改主機定義所在的來源檔案，不在入口建立重複主機作為覆寫。
- 真實資料寫入使用者的管理環境；repository 文件和範例只使用合成資料。維護 OpsFeast 文件不代表可修改 SSHScript library；遵守當前目錄的 AGENTS.md。
- 設定維護請求不自動授權 SSH 連線、執行 recipes、修改遠端主機或發布資料。使用者已授權的操作依既有範圍進行，不重複要求授權。

## 不可改變的設定語意

- Host-level `group` is an optional non-empty string or list of non-empty group names; one host may belong to multiple groups, including memberships declared in included files. Omitted/empty lists mean no membership; a scalar is treated as a one-element list for selection without rewriting stored configuration. Reject the former groups field with a migration hint, including when both names are present. Groups only select runner targets and do not inherit connection settings, variables or recipes. Read [host groups](../../docs/hosts-yaml.md#host-groups) and the [runner reference](../../docs/cli.md#toolsrun_recipepy-inventory-execution) for mixed host/group unions, explicit --host/--group options, required recipe selection, exclusive --all and deduplication. Diagnostic commands still require individual host IDs. Group/all selection does not authorize execution.
- `hosts` 的鍵是穩定主機 ID；`connection.hostname` 是 DNS 或 IP。
- 新建的 init 樣板包含 `localhost: {connection: {local: true}, users: {}, vars: {}, recipes: []}`。本機 connection 只接受 `local: true`，不建立 SSH 連線，不能作為跳板或混用 SSH 欄位；既有設定仍保留，不自行覆寫。
- 明確 SSH 連線可使用 `connection.proxy_command` 非空字串，不能與同一層的 `via` 或 `ssh_config_alias` 混用。命令原樣保存，不展開 `%h`、`%p` 或 shell 變數；使用具體目標值。check 只驗證設定；明確要求 test-connection 時可啟動代理並測試連線。
- proxy_command 建立資料通道；目標 SSH 驗證仍使用 connection.user 與該 host 對應 users 帳號的 password。提供密碼且未設定 identity_file 時，test-connection 停用 agent 與自動搜尋金鑰。沒有對應帳號或 password 時，不借用其他帳號密碼、不自動新增帳號，使用私鑰或 agent／預設金鑰，驗證失敗則回報失敗。代理程式自己的憑證不自動取用 users 中的 SSH 密碼。
- `via: {host: bastion}` 引用載入後的 `hosts.bastion.connection`。也接受巢狀明確連線；不能把主機引用與覆寫欄位混用。
- `ssh_config_alias` 引用 SSH config 的 `Host`，不是 YAML 主機 ID。每層 alias 與明確連線欄位互斥；YAML 與 SSH config 的跳板衝突不得默默忽略。建議使用 YAML 主機引用以保留可搬移拓樸。
- `connection.user` 保持單一 SSH 登入帳號名稱；host 層 `users` 是以實際帳號名稱為鍵的 mapping，Account fields now include password, vars, sudo and sudo-password; read the canonical access policy before editing them. 帳號變數不與 host vars 合併；users 可省略，connection.user 不強制有 users 項目。su 目標必須明確指定，不從帳號順序推定、不自動切換。可用 `dump hosts.<主機>.users.<帳號>` 取得資料，現有 `vars.sudo` 語意不變。
- `vars` 是各主機原樣、保留型別的輸入 mapping，不從跳板繼承，不插值、不深層合併、不自動轉成 shell 或環境變數。
- `vars.sudo.user` 是 sudo 的目標帳號；`vars.sudo.password` 是驗證密碼，通常屬於登入帳號。初版可保存明文；不自動輸出這些值到日誌、觀測或紀錄。
- 根層 `include` 是明確的本機 YAML 路徑清單，可遞迴，不接受 glob、URL 或 `!include`。同一實際檔案只載入一次；載入中的循環必須報錯。
- 重複 mapping 鍵或跨檔案主機 ID 都報錯，沒有載入優先級或覆寫。一般 YAML parser 可能默默採最後一個鍵；驗證時需確認使用的 parser 能拒絕重複鍵，否則揭露檢查限制。
- Recipe items accept shorthand strings or selector mappings with optional vars. Read [recipe sources and controls](../../docs/recipe-sources.md) for entry-only recipe_sources, checkout/profile/named references, shallow default/source/host input overlays and typed runner validation. Predefined recipe_sources.bundle/profile accept enabled/vars without path; optional path assertions must resolve to their fixed defaults from entry hosts.yaml. They do not create bundle:/profile: aliases. Host/source enabled flags default true; disabled hosts cannot be jump hosts. Source disable is an explicit skip, not a fallback or unknown-source exemption. --all --exclude is one-invocation target filtering only.
- `recipes` 是選取 mapping 的清單：`recipe` 指完整 recipe 目錄；`directory` 選直接子目錄，只有 `recursive: true` 時遞迴；`glob` 比對 recipe 目錄，`*`、`?` 不跨 `/`，`**` 可跨層級。
- 每個 recipe 目錄含 `recipe.yaml`，不直接把任意檔案當 recipe。依選取清單順序及組內路徑排序展開；同一實際目錄保留第一次，同一來源內不同目錄同 ID 報錯，不同來源可有相同 ID；空匹配報錯。
- `${...}` 目前是原樣字串；不加入未定案的版本、全域 vars、exclude 或變數存取 API。

## 路徑與引用檢查

Include 的相對路徑以**宣告它的 YAML 所在目錄**為基準。Recipe 的 `recipes/...` 固定以工具所在 checkout 為基準，無需複製到 instance；其餘相對路徑（例如 `./recipes/...`）才以宣告 YAML 的目錄為基準。維持來源檔案資訊，不能合併後一律改用入口 YAML 的目錄。

Include 與自訂 recipe 以管理根目錄為邊界；repository recipe 以工具所在 checkout 的 recipes 目錄為邊界。 Registered named sources permit external recipe roots, but never widen include/output boundaries; profile :paths remain inside profile recipes/.解析相對路徑、`..` 與符號連結後，實際路徑必須仍在各自邊界內；recipe 的絕對路徑可位於這兩個邊界內。不可因此放寬 include 或結果輸出的邊界。用路徑元件而非字串前綴檢查。Glob 或遞迴選取不能先搜尋外部再過濾，每個結果也需檢查邊界。新設定優先用相對路徑。

這個邊界不適用於目標主機的變數值。`identity_file` 是連線層設定，test-connection 將 identity_file 原樣傳給 SSHScript pkey_path，從呼叫 connect 的 parent Session 所在主機讀取 RSA 私鑰：直連讀 localhost，經由跳板時讀前一跳主機（SFTP 原始登入帳號）。不以 YAML 目錄解析相對路徑、不展開 ~，建議 parent 主機上的絕對路徑；不能將它替換成始終在 localhost 讀取的 key_filename。

全部設定載入後，檢查 `via.host` 是否存在、跳板圖是否循環，以及選取的 recipes 是否存在。錯誤指出來源檔案、主機 ID 或欄位與引用鏈；不要為修正錯誤自行編造主機、密碼或 recipe。

## 完成設定維護

For su/sudo result interpretation, read [identity evidence](../../docs/host-diagnostics.md#read-the-identity-evidence). Report each step's expected/actual username and effective UID, matched/status, and the group's parent identity restoration. Keep prerequisite su evidence separate from final sudo evidence. Entry/skipped checks marked not_run and incomplete checks with matched null are not verified success; environment variables do not prove identity. --verbose/--debug explain successful verification on stderr while stdout remains JSON.

使用 `tools/opsfeast.py check` 檢查本次修改，若缺少 Python 或 PyYAML 明確回報，不虛構成功結果。檢查涵蓋 YAML 語法、重複鍵、跨檔案引用、路徑邊界與 recipe 選取規則。使用安全的 YAML 載入方式，不執行自訂標籤。若所選 recipes 不存在，明確回報選取尚無法驗證，不把草案稱為可執行環境。

回報修改檔案、主機 ID、解析後的連線拓樸與檢查結果；不要為說明變更而重貼真實密碼。需要示範完整設定時使用合成值。

若使用者也要求執行，先展開確定的 recipe 清單，檢查支援平台、變數、權限與副作用，並確認操作在該次授權範圍內。記錄實際 recipe ID 與版本；觀測與人工資料分開，保留人工筆記。Failed result values are null while process evidence preserves failure; never substitute zero or claim success. 也不得把舊觀測改成新時間。

Host identity_key, label and description are now supported. An explicit identity_key takes precedence and is shared across Feasts as user-assigned identity; change it after OS reinstall/replacement and coordinate its namespace. label/description are captured human text, never identity keys, and are preserved through retention/exchange. See [the canonical host configuration](../../docs/hosts-yaml.md#explicit-host-identity-and-human-readable-metadata) and [identity/metadata rules](../../docs/result-data.md#explicit-identity-and-display-metadata). MAC is not an automatic key.

The bare OpsFeast TUI includes a read-only Hosts view of default-profile configuration with includes/source paths and recursive credential masking. A left docked Tree groups host IDs by scalar/list memberships; multi-group hosts share settings, and ungrouped hosts have a separate branch. Highlight a leaf for masked details. Enter opens the explicit test-connection/run-recipe/cancel menu; execution needs the actual host/recipe scope. Recipe input captures exactly one host and Feast root, while ProgressBar and ModalScreen expose completion/exit/result evidence. See the canonical [host action workflow](../../docs/terminal-ui.md#host-action-menu-progress-and-result-dialog) for prerequisites, cancellation limits and verification. User children show the connection account when locally known plus declared users. Enter offers test-sudo as the selected actor to root, and independent test-su only for a known non-login target; aliases with unknown login hide su. Prerequisite su for a different sudo actor belongs to that explicit diagnostic. Runtime identity/credential/cleanup checks remain authoritative. See [user diagnostic menus](../../docs/terminal-ui.md#user-nodes-and-privilege-diagnostics). Profiles can update the persistent default using the existing use contract, refreshing Hosts; explicit recipe root/profile inputs remain unchanged. Opening and selecting host rows do not authorize connections or diagnostics. See the [Home/Hosts/Profiles guide](../../docs/terminal-ui.md#home-hosts-and-profiles) for availability, masking limits and failure behavior.

For an explicitly requested human terminal display, supported diagnostics accept `--tui`. Read the [display guide](../../docs/terminal-ui.md) for optional Textual installation, terminal checks, shortcuts and limits. The diagnostic starts immediately within its existing authorization scope; the UI does not grant connections or privilege tests. Preserve skipped/failed states and inspect per-step details. Agents and pipelines should use ordinary JSON output.

_Last modified: 2026-10-14_
