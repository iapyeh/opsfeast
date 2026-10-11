# 人類使用者的第一次體驗

你可以先下載 SSHScript Ops，再把專案目錄交給 AI agent，請它說明環境需求、提出設定方案，完成授權後的初始化。你不需要先研究每個 Python 工具的參數。以下以 Codex、Hermes 等能讀取本機檔案與執行命令的 agent 為使用情境；若 agent 在另一台機器執行，專案必須位於它能存取的位置。

這次體驗的目標是建立管理環境、知道主機資料應該填在哪裡。初始化完成後，再選擇要測試的主機與採集工作。

## 1. 下載專案

在有 Git 的電腦上執行：

```sh
git clone https://github.com/iapyeh/sshscript-ops.git
cd sshscript-ops
```

記下這個目錄的絕對路徑。macOS／Linux 可以執行 `pwd`，PowerShell 可以執行 `Get-Location`。之後提示詞裡的 `/absolute/path/to/sshscript-ops` 都要替換成實際路徑；Windows 可直接使用其完整路徑。

## 2. 讓 agent 先認識專案

開一個新對話，貼上：

> 我是第一次使用 SSHScript Ops，專案位於 `/absolute/path/to/sshscript-ops`。請查看 README.md、AGENTS.md 與入門指南，告訴我它可以做什麼、需要哪些環境，並提出初次設定方案。先不要安裝或執行初始化。

Agent 應該能從專案找到說明，告訴你需要 Python 3.11+，哪些套件用於初始化或完整工具，並說明：

- Skill 的完整公開快照已隨 Git 提供，可以直接閱讀；初次使用通常不需要重新下載。
- 專案可以初始化與檢查設定、查詢設定、測試指定主機連線，以及執行目前支援的 inventory-system recipe。
- 它將選用哪個 Python、在哪裡建立環境、安裝哪些依賴，以及管理資料放在哪裡。

如果 agent 找不到檔案，先確認它實際能存取你提供的目錄。若 Python 尚未安裝，讓它回報缺口與安裝方案，再依你的電腦環境處理。

## 3. 看過方案後，授權本機初始化

若你同意在專案內建立獨立 Python 環境，可以貼上：

> 請在這個專案內建立獨立 `.venv`、安裝完整依賴，使用隨附 skill，執行預設 init 和 check。不連線到遠端、不執行 recipes。完成後告訴我下一步應設定哪些資料。

若你已有要使用的 Python 環境，改為告訴 agent 該 interpreter 的位置，要求沿用並先回報缺少的依賴。具體安裝步驟由 [入門指南](getting-started.md) 定義。

完成後，目錄中應包含：

```text
sshscript-ops/
├── .venv/
├── .my-ops.yaml
├── recipes/
└── my-ops/
    └── main/
        ├── my-ops.yaml
        ├── hosts.yaml
        ├── hosts/
        ├── observations/
        ├── records/
        └── runs/
```

`.venv/` 只在你選擇建立新環境時出現。`my-ops/` 與 `recipes/` 同層；`.my-ops.yaml` 記錄 profile 清單與預設環境，後續命令可以省略該目錄參數。Agent 應回報實際 Python、套件及文件版本、初始化與檢查結果、`hosts.yaml` 的完整路徑。

## 4. 設定自己的主機

打開 agent 回報的 `my-ops/main/hosts.yaml`。預設有 localhost 與使用合成位址 `host.example` 的遠端範例。替換範例主機 ID 與位址，設定登入帳號、認證方式；需要跳板時設定 via。Recipe 清單初始為空，可按需求加入。

可以請 agent 協助整理格式，但不要在聊天裡重貼密碼或私鑰。完整欄位與認證規則見 [主機設定指南](hosts-yaml.md)。預設管理目錄已被 Git 忽略；真實設定與觀測留在你的管理環境。

修改後貼上：

> 請檢查目前預設管理目錄的設定，不連線、不執行 recipes。若有錯誤，指出來源檔案與需要修正的地方。

這也能確認 agent 使用同一個 Python，並能省略目錄執行 `ops.py check`。設定檢查通過不代表主機已可連線。準備好後，再指定要測試的 host ID；盤點則另行指定 recipe 與執行範圍。

## 5. 體驗 skill 更新檢查

貼上：

> 請檢查公開 SSHScript skill 是否有變更，只比較並回報，不套用更新、不升級套件、不建立排程。

Agent 應依 [下載與更新指南](skill-updates.md) 比較公開 bundle，回報是否一致、候選文件版本與相容性。沒有變更是正常結果；檢查失敗應回報原因，不能當成沒有更新。若你之後希望定期檢查，再與 agent 約定週期及通知方式，使用其平台的排程功能。

## 使用不同管理環境，或接手既有資料

想另外分類管理時，請 agent 建立具名環境，例如 `ops.py init inventory`，資料會放在 `my-ops/inventory/`。`ops.py profiles` 列出所有環境，`ops.py use inventory` 切換預設；互動終端可只輸入 `ops.py use` 後選擇。

換電腦、交接或收到同事的管理目錄時，請 agent 使用 `ops.py add /path/to/existing-profile` 檢查並登記；它不建立 scaffold、不改寫該目錄的檔案。名稱衝突時由你選擇新名稱。詳細路徑與命名規則見 [管理環境指南](profiles.md)。

## 想先試用、不沿用既有管理資料

可以 clone 到另一個全新目錄，例如：

```sh
git clone https://github.com/iapyeh/sshscript-ops.git sshscript-ops-trial
```

把這個 trial 目錄的絕對路徑交給 agent，再依上面步驟操作。新 clone 不包含被忽略的既有管理設定、Python 環境或定位檔。

維護者要試用尚未 push 的本機已提交版本，可以從本機 repository clone 到新目錄；將以下路徑替換成自己的位置：

```sh
git clone "/absolute/path/to/sshscript-ops" "/absolute/path/to/sshscript-ops-trial"
```

本機 clone 只包含已提交內容。使用另一個 agent 重複此流程時，仍從新對話與新 trial 目錄開始，讓它只靠 repository 文件完成設定；可以比較它是否自行找到入門指南、正確使用隨附 skill，並清楚回報下一步。
