# 初次使用 SSHScript Ops

本指南供系統管理者及不同 AI agent 使用，不要求特定產品或 skill loader。將 clone 後的 repository 路徑交給 agent，請它閱讀 README、AGENTS.md 與本指南。以下路徑以 repository 根目錄為基準；執行示例前先切換至該目錄。

## 先了解可以做什麼

目前提供管理目錄初始化、設定檢查、設定 JSON 查詢、指定主機連線測試，以及只支援 inventory-system 的最小 runner。Inventory 的 Linux 採集通過合成測試，真正 Linux／SSH 驗證仍有待執行；macOS 本機已驗證遇到不支援平台時停止。工具不是通用部署或修復執行器。各工具範圍見 [主機設定指南](hosts-yaml.md) 與 [inventory-system 指南](../recipes/inventory/system/README.md)。

README 是共同入口；AGENTS.md 是隨 Git 提供的專案工作規則。若 agent 沒有自動載入 AGENTS.md，請直接讀取它。不要將其他電腦的私人 checkout、絕對路徑或環境設定當成本專案的必備環境。

## 檢查環境，提出具體初始化方案

需要 Python 3.11+。選定之後所有檢查、安裝及工具執行都使用同一個 interpreter；可以沿用使用者提供的環境。唯讀檢查不需要預先安裝 PyYAML 或 SSHScript：

```sh
python3 -B tools/check_environment.py
# 只準備 init/check/dump，可先檢查精簡環境：
python3 -B tools/check_environment.py --scope init
```

工具輸出 interpreter、Python、套件 import／distribution 版本、模組位置與 skill 文件契約。ready 表示符合本專案列出的依賴及文件條件，不代表已驗證 SSH、su、sudo 或 recipe 採集。缺少或版本不符時回傳 1；只回報缺口，不自動安裝。

目前提供兩份依賴清單：

| 清單 | 用途 |
| --- | --- |
| `requirements-init.txt` | PyYAML 6.0.3，供 init/check/dump 及一般測試使用 |
| `requirements.txt` | 上述依賴加 SSHScript 5.0.0，供完整 Ops 工具使用 |

版本固定為本專案目前驗證的環境；這不是所有傳遞依賴的 lockfile。既有環境使用不同版本時先回報，不自行升級、降級或覆寫共用 venv。使用者只要求初始化時，可以只安裝精簡清單；要準備連線與 runner 時再選完整清單。

Agent 應先提出具體方案：選用哪個 Python、是否建立 `.venv/`、安裝哪份依賴、是否需下載 skill、管理目錄位置，以及將執行的本機初始化命令。確認這些操作在使用者授權範圍內後執行；若使用者已明確授權整套初次設定，不重複詢問同一授權。安裝或下載遇到網路／權限問題時回報，不擅自改全域環境或安裝系統套件。

新環境的典型方案（macOS／Linux shell；需要安裝與建立環境授權）：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -B tools/check_environment.py
```

若只初始化，將上面的清單換成 `requirements-init.txt`，環境檢查加 `--scope init`。Windows 使用 `.venv\Scripts\python.exe`。以下以 `python` 表示前面已選定的 interpreter，不要求一定建立新 venv。

## 閱讀 skill，完成本機初始化

Git clone 已包含完整 `.agents/skills/sshscript/` 公開快照，不必為初次使用重新下載。Agent 在使用 SSHScript 前依序閱讀其中的 SKILL.md、Agent Guide 與任務相關 API 章節；主機設定維護另讀 [Ops hosts skill](../skills/sshscript-ops-hosts/SKILL.md)。

可直接閱讀 Markdown，不需要 skill loader。若使用者要安裝到某個 agent 的 skill 搜尋位置，依該產品的機制與授權處理；不要假設所有 agent 都自動搜尋 `.agents/skills/`，也不要將「檔案隨附」或「已閱讀」回報成「已安裝／自動載入」。缺少快照或要檢查更新時，依 [下載與更新指南](skill-updates.md) 操作。

初始化不需要 SSHScript Session 或遠端連線：

```sh
python -B tools/ops.py init
python -B tools/ops.py check
```

預設建立 `my-ops/main/` 並登記 `main` profile；第一個成功登記的 profile 成為預設，後續登記不切換。`init inventory` 建立 `my-ops/inventory/`，`init /path/to/my-ops` 則使用指定路徑。兩個工具可省略目錄或用 `--profile NAME` 選擇本次環境；`use NAME` 切換預設。既有資料用 `add /existing/directory` 登記，不改寫原目錄。詳見 [管理環境指南](profiles.md)。重複初始化保留既有主機設定；定義檔與定位規則見 [主機設定指南](hosts-yaml.md)。

## Recipe next steps

To select, create or share recipes, start with the [recipe user guide](recipes.md) and repository [recipes skill](../skills/sshscript-ops-recipes/SKILL.md). The guides provide copyable prompts and a review/authorization workflow for third-party content. Only the dedicated inventory-system runner is currently implemented; placing a custom recipe in a directory does not make it executable by that runner.

## 告訴使用者下一步

回報實際使用的 Python、環境檢查結果、依賴安裝結果、skill 來源／文件版本與是否只閱讀、管理目錄及 `hosts.yaml` 的實際位置、init/check 的退出結果。

使用者接著需要：

1. 編輯 `hosts.yaml`，替換合成的 `host-01`／`host.example`，設定主機 ID、位址、登入帳號與認證方式；需要跳板時設定 via。不要把範例密碼當成實際憑證，也不要要求使用者在聊天重貼密碼。
2. 保留或依需求調整 localhost，選擇要使用的 recipes；初始 `recipes: []` 尚未選取任何 recipe。
3. 執行 `ops.py check` 確認設定；檢查成功只代表設定通過，不代表連線或採集成功。
4. 指定要測試的 host ID，授權 `test-connection`；要盤點時另指定或授權 runner 執行。首次設定本身不自動觸發 SSH、代理命令、su／sudo 或 recipe 採集。

`my-ops/` 與定位檔已被 Git 忽略；自訂管理目錄若放在 checkout 內，需另加忽略規則。真實憑證、主機設定與觀測不提交至公開 Git。

更新檢查是可選後續工作。若使用者希望定期檢查，先確定檢查範圍、週期及通知方式，使用其 agent 平台的排程能力；未建立排程不可回報「已定期檢查」。
