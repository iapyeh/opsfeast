# 3. 確認安裝成果，掌握目錄用途

[全書首頁](README.md) · 上一章：[安裝](02-installation.md) · 下一章：[hosts.yaml 與連線](04-hosts-and-access.md)

本章帶你確認上一章建立的本機環境是否就緒，並找出工具、設定與維運資料的實際位置。依序完成以下 6 步後，你會拿到版本與檢查結果、要使用的 profile，以及各目錄用途；接著再設定第一台主機。

使用 agent 時，將下列需求貼給它，讓它完成各步的檢查，你再依完成判準閱讀回報：

> 請只做本機安裝驗收。列出實際 checkout、產品版號/commit、選定 interpreter、SSHScript import/distribution 與依賴就緒狀態、skill 是否來源相符、目前管理根目錄與 hosts.yaml。執行 profiles 和指定 profile 的 check，盤點已存在的目錄及用途，說明哪些尚未產生是正常的。沿用已完成的安裝，不列出密碼，不連線、不初始化或修復。若有失敗，指出原因與下一步。

上方提示詞適合一次完成整章驗收；下方各步的提示詞適合只檢查其中一項。已完成的檢查直接閱讀回報，不必把所有提示詞再貼一次。

若選擇自行操作，依各步指令檢查，再請 agent 協助解讀需要確認的結果。TUI 尚未提供的檢查，改用 CLI 或 agent。以下指令以已啟用的選定 Python 和新建 `main` 為例，全部從實際 checkout 執行；使用 agent 代辦時，不必再手動重跑一次。

## 步驟 1：確認 Python、依賴與 skill 就緒

**你要做的事：**請 agent 檢查安裝時選定的 Python 環境。

可直接複製給 agent：

```text
請用安裝時已選定的 Python 執行本機環境檢查。回報 interpreter 路徑、Python 與依賴版本、ready、skill 來源是否相符，以及選用 Textual 的狀態。列出缺項與原因，保留現有環境；這次不安裝套件或連線到主機。
```

自行操作時，執行：

```sh
python -B tools/check_environment.py --json
```

**agent 會做的事：**說明實際 `interpreter`、`python`、各套件版本、`ready` 與 skill 來源是否相符；不足時指出個別缺口，保留正常環境。若安裝方案包含 TUI，還要在同一 interpreter 檢查 Textual，例如 `python -B -m pip show textual`，再確認可 import。環境檢查的 ready 本身不涵蓋選用 Textual；缺少時說明缺口，不因此自行安裝。

**完成判準：**你知道目前使用哪個 Python，環境檢查顯示 `ready: true`；若有缺項，已知道是哪一項及需要的處理。選用 TUI 時，也已另外確認 Textual 的狀態。

## 步驟 2：核對安裝身分與實際版本

**你要做的事：**請 agent 檢視安裝實例資訊。

可直接複製給 agent：

```text
請唯讀檢視這份 OpsFeast 的 instance 資訊、產品版本、可取得的 Git revision 與 SSHScript 版本，分別說明安裝身分、路徑與版本缺口。沒有 Git metadata 時如實回報，不初始化、不建立 repository，也不修改設定。
```

自行操作時，執行：

```sh
python -B tools/opsfeast.py instance inspect --json
```

產品版號與實際程式 revision 可另外唯讀查看：

```sh
cat VERSION
git rev-parse HEAD
```

**agent 會做的事：**解釋安裝身分、登記環境、設定摘要、依賴中繼資料與錯誤。對新安裝，instance 身分應已由成功 init 建立；既有或未初始化 checkout 的 inspect 可能顯示 placeholder，先說明狀況，不為了清掉警告改寫接手環境。

版號、Git commit、SSHScript 套件版號與 API 契約版本不同，回報時分別記錄。沒有 Git metadata 的已安裝副本，應說明查不到 commit，不自行建立 repository。

**完成判準：**你已取得可查到的版本與安裝身分，並知道有無身分、路徑或版本資訊缺口。

## 步驟 3：選定要驗收的管理環境

**你要做的事：**請 agent 列出已登記的 profiles。

可直接複製給 agent：

```text
請唯讀列出目前已登記的 OpsFeast profiles，說明預設 profile、各管理根目錄及可用狀態，讓我選擇這次要驗收的環境。不切換預設、不新增登記，也不初始化。
```

自行操作時，執行：

```sh
python -B tools/opsfeast.py profiles
```

從結果確認這次要驗收的 profile 名稱與根目錄。以下步驟使用 `main` 作為範例；若你選擇其他 profile，將 `--profile main` 改成實際名稱即可，不需要為了本次驗收變更預設環境。

**agent 會做的事：**說明目前選擇、各根目錄與 available/missing 等狀態。指定環境無法使用時指出原因，不默默改用另一個 profile，也不重新初始化來掩蓋問題。

**完成判準：**你已選定一個明確的 profile，知道它的實際管理根目錄與可用狀態。

## 步驟 4：驗證指定 profile 的設定

**你要做的事：**請 agent 檢查步驟 3 選定的 profile。

可直接複製給 agent：

```text
請對前一步已選定的 profile 執行本機設定檢查，回報 profile 名稱、實際管理根目錄、檢查結果，以及錯誤對應的檔案與欄位。若對話中還沒有選定名稱，先請我指定。這次不修改設定、不初始化，也不連線到主機。
```

自行操作時，執行：

```sh
python -B tools/opsfeast.py check --profile main --json
```

**agent 會做的事：**說明設定驗證是否通過，以及錯誤對應的檔案與欄位。需要補裝、修復或更改設定時，先指出原因與具體方案，保留已完成的安裝。

**完成判準：**指定 profile 的本機設定驗證通過，或已列出需要處理的明確錯誤。這個結果用來確認設定是否可接受；主機連線與帳號能力在後續章節另行測試。

## 步驟 5：找出安裝檔案與工具的位置

**你要做的事：**依步驟 2、3 的回報找到實際 checkout，對照下方目錄盤點工具與設定入口。

可直接複製給 agent：

```text
請依前面確認的安裝資訊，唯讀盤點這份 OpsFeast 的實際 checkout、選定 Python、CLI 入口、profile 登記與安裝身分檔案位置。列出實際存在的路徑與用途，指出不適用或尚未建立的項目，不建立目錄或修改檔案。
```

```text
<checkout>/
  VERSION                      產品版號
  tools/opsfeast.py             CLI 入口
  opsfeast/                    可重用 Python 模組
  recipes/                     隨附 bundle recipes
  consumers/                   隨附 consumers
  skills/                      agent 知識與完整 skill 來源
  docs/                        正式參考文件
    textbook/zh-TW/            你正在閱讀的繁中教科書
  .venv/                       若本次選用新建的 Python 環境
  .opsfeast.yaml               私人 profile 登記與預設選擇
  .opsfeast-instance.json      私人安裝實例身分
  feasts/main/                 新入門範例的管理根目錄
```

`.venv/` 只在選用它時存在。管理根目錄也可能在 checkout 外，實際位置以 `profiles` 與 init 回傳值為準。既有環境可能使用舊名稱登記檔；遇到命名衝突依指引處理，不自行選一份或覆寫。

**agent 會做的事：**列出實際存在的路徑，說明產品工具、Python 環境、profile 登記與安裝身分各放在哪裡，並保留不適用或尚未建立的項目。

**完成判準：**你能指出 checkout、選定 Python、CLI 入口與 profile 登記位置，不必依賴範例目錄名稱猜測。

## 步驟 6：找出管理資料並確認各目錄用途

**你要做的事：**開啟步驟 3 選定的管理根目錄，對照下表辨認主機設定、原始結果、保留資料與維運 Vault。

可直接複製給 agent：

```text
請唯讀盤點前面已選定 profile 的實際管理根目錄，指出 hosts.yaml、原始結果、retention、維運 Vault 與其他現有目錄的位置及用途。說明哪些目錄會在使用功能後才出現。只摘要必要資訊，不輸出密碼、不修改 SQLite、不初始化或產生新資料。若尚未選定 profile，先請我指定。
```

| 位置 | 用途 | 何時需要注意 |
| --- | --- | --- |
| `hosts.yaml` 與 include 檔 | 主機、帳號、群組、recipe 設定與來源 | 真實資料、密碼留在私人環境 |
| `feast.yaml` | Namespace、consumer、服務等環境設定 | 保留既有值，不能為了通過檢查隨意換 namespace |
| `hosts/` | 個別主機的初始化資訊等輔助檔案 | Init 先建立目錄；平台事實需由後續已授權操作取得，空目錄正常 |
| `observations/` | 原始維運結果 | 執行前可為空；有些前置失敗沒有 raw |
| `records/` | 初始化骨架及歷史 observation-store 資料位置 | 舊 snapshot 介面可能使用；目前 inventory job 權威資料在 `retention/`，不可與 Vault 裡的 records 混為一談 |
| `runs/` | 初始化骨架保留的執行資料目錄 | 批次歷史請用 observation 指令查詢，目前證據依 retention 批次契約保存 |
| `retention/` | 權威結構化歷史與衍生資料 | 不直接改 SQLite 來修資料 |
| `vault/` | 產生的維運頁面與人工筆記 | 與本教科書 Vault 分開 |
| `vault/.obsidian/` 與 `vault/.reader-assets.json` | Obsidian 樣式、外觀設定與 CSS 歸屬 | 預設 Vault 發布會準備；保留其他設定，個人樣式另放一份 |
| `recipes/` | 你自己的 profile 本地 recipe | 建立自己的 recipe 時再使用此目錄 |
| `reports/`、`jobs/` | 離線報表結果與保存呼叫 | 使用對應功能後才出現 |
| `services/`、`transfer/` | 通知待辦狀態、移轉資料與回執 | 使用功能後才需要，不是初始化必備全部空目錄 |
| `inventory.yaml` 與 `.inventory-state.json` | 週期採集設定與嘗試狀態 | 沒有啟用主機時不會自動採集 |

Init 會建立 `hosts/`、`observations/`、`records/`、`runs/` 等起始骨架，以及 retention/Vault 起始內容。其他選用目錄不必立刻出現，工作資料會由後續功能產生。先認識目前已有的目錄，開始使用各功能時再觀察新增的資料。

**agent 會做的事：**盤點目前存在的目錄，指出 `hosts.yaml` 與維運 Vault 的實際位置，說明哪些目錄會在使用功能後才出現。只讀取必要資訊，不列出密碼、不直接修改 SQLite，也不替你初始化或產生新資料。

**完成判準：**你知道應編輯哪一份 `hosts.yaml`、去哪裡閱讀維運結果，以及原始結果與 retention 的差別。驗收有缺項時，也已知道原因與下一步。

**完成本章時：**你應拿到這 6 步的實際路徑與檢查結果。若有失敗，先確認需要補足的項目；本機就緒與遠端驗證仍是不同階段。

## 延伸閱讀：定位資料與排程設定

### 沿目錄樹找到工具與維運資料

```text
opsfeast-checkout/
  tools/                    CLI entrypoints
  opsfeast/                 reusable Python modules
  recipes/                  bundled recipe sources
  consumers/                bundled consumers
  skills/                   complete agent guidance sources
  docs/                     canonical human/agent references
    textbook/               textbook language entrypoint
      en/                   English teaching vault
      zh-TW/                繁中教學 Vault，含基本、進階與章內延伸閱讀
  .opsfeast.yaml            private profile registry
  feasts/main/              one possible registered management root
    hosts.yaml              private hosts, accounts, settings and sources
    feast.yaml              namespace, consumers and service configuration
    recipes/                optional profile-local recipes
    observations/           raw operational results
    retention/              authoritative retained history and projections
    vault/                  generated operational content and human notes
    reports/                offline report results and artifacts
    jobs/                   saved recipe invocations
    services/               notification/todo state and delivery history
    transfer/               imported data, transfer plans and recovery receipts
```

上面的目錄樹沿用英文版名稱與註解，方便對照實際檔案；本繁中教學 Vault 位於 `docs/textbook/zh-TW/`。選用功能的目錄會在需要時出現。Profile 可以指到 checkout 外面；找資料前先解析實際登記的根目錄，指定環境無法使用時，不得默默改用另一個 profile。

Inventory 另外使用 profile 本地的 `inventory.yaml`、`.inventory-state.json` 與錯誤紀錄。這些排程設定，與 `hosts.yaml` 的 recipe 啟用設定、保存的 recipe job 各自不同。

正式參考：[CLI](../../cli.md)、[Core inspect](../../core-api.md)、[profiles](../../profiles.md)、[保留資料](../../retention.md)。

## 下一步

完成本機驗收後，前往[第 4 章設定第一台主機](04-hosts-and-access.md)，再依實際範圍進行連線與帳號測試。

*Last modified: 2026-10-26 23:35:09*
