# 速查表：指令參考

[全書首頁](README.md) · [Prompt 參考](prompts.md)

從實際 checkout 執行，`python` 代表該安裝選定的 interpreter。`main`、`server-01`、`appuser` 等是假想值；ID/hash 應取實際回傳。支援時用 `--json`；不支援的命令不要自行加 flag。查語法可用所選子命令 `--help`。

## 盤點 OpsFeast：版本、依賴與設定

```sh
cat VERSION
git rev-parse HEAD
python -B tools/check_environment.py --json
python -B tools/opsfeast.py instance inspect --json
python -B tools/opsfeast.py profiles
python -B tools/opsfeast.py check --profile main --json
```

這些是本機讀取。`VERSION` 與 commit 表示產品來源；環境檢查顯示實際 interpreter、Python、SSHScript 及其他依賴的 import/distribution、來源與 ready。Instance inspect 補充安裝身分、profile、設定與依賴摘要，不自動修復。Profiles 是登記可用性，check 才做指定環境完整設定檢查。尚未採集不代表安裝失敗。

選定設定的原始查詢例子：

```sh
python -B tools/opsfeast.py dump groups --profile main
python -B tools/opsfeast.py dump hosts.server-01.group --profile main
```

Dump 直接輸出 JSON，不另加 `--json`，也不遮罩欄位。不要以 `dump hosts`、users 或 connection 全量輸出來分享私人設定；憑證與任意私人文字可能外洩。需要盤點時，請 agent 摘要欄位是否存在與錯誤，不印機密。

可直接複製給 agent：

```text
請唯讀摘要目前選定 profile 的設定狀態，只回報必要欄位是否存在及驗證錯誤，不輸出完整 hosts.yaml 或 dump，不顯示密碼、私鑰、token 或其他憑證。若尚未選定 profile，先請我指定；不修改設定或連線。
```

完整驗收見[第 3 章](03-verify-installation.md)。

## hosts.yaml 管理

| 工作 | 指令 | 效果 |
| --- | --- | --- |
| 檢查設定 | `python -B tools/opsfeast.py check --profile main --json` | 本機讀取，不驗證連線 |
| 單台連線 | `python -B tools/opsfeast.py test-connection server-01 --profile main --json` | 真實連線含必要跳板、hostname/date |
| 測試 su | `python -B tools/opsfeast.py test-su server-01 appuser --profile main --json` | 目標帳號切換、身分與還原測試 |
| 測試 sudo | `python -B tools/opsfeast.py test-sudo server-01 --run-as root --profile main --json` | 實際登入 actor 的 sudo 測試 |
| 明確刷新平台資訊 | `python -B tools/opsfeast.py host-init server-01 --profile main --json` | 連線並更新平台快取 |
| 較廣的配置能力診斷 | `python -B tools/opsfeast.py test-host server-01 --profile main --json` | 可能包含 sudo 與其他帳號 su；查看 skipped |

Hosts.yaml 是人工/agent 維護的設定來源，沒有憑空新增的通用 hosts editor 指令。參照[主機章](04-hosts-and-access.md)合併欄位，保留註解、include 與其他主機。認證自動來源預設關閉，via 每跳各自設定。

## Recipes 管理

| 工作 | 指令 | 效果 |
| --- | --- | --- |
| 列隨附 bundle | `python -B tools/opsfeast.py recipes list --checkout-only --json` | 靜態，不需 profile |
| 列選定環境可用來源 | `python -B tools/opsfeast.py recipes list --profile main --json` | 靜態探索 |
| 看 recipe | `python -B tools/opsfeast.py recipes show system/inventory/overview --profile main --json` | 看輸入、依賴、限制 |
| 跑第一個 inventory | `python -B tools/opsfeast.py recipes run system/inventory/overview --profile main --host server-01 --json` | 實際採集、保存、嘗試下游處理 |
| 看屬性/job 定義 | `python -B tools/opsfeast.py inventory describe --json` | 只讀 catalog |
| 保存容量 job | `python -B tools/opsfeast.py inventory run --profile main --host server-01 --job storage-capacity --json` | 實際連線採集與儲存 |
| 只查容量、不儲存 | `python -B tools/opsfeast.py inventory query --profile main --host server-01 --property storage.filesystems.used_percent --json` | 實際探測與帳號政策；不持久化到 OpsFeast |
| 列保存的 recipe 呼叫 | `python -B tools/opsfeast.py recipes jobs list --profile main --json` | 讀私人 job；保存不等於排程 |

完整自製與分享流程見[第 9 章](09-authoring-recipes.md)、[第 10 章](10-sharing-recipes.md)。離線報表使用相同 recipes run 入口，但不採集主機；歷史在 `recipes results`，成品由 `recipes artifact` 驗證取得，見[報表延伸](06-observations.md#延伸閱讀報表與重複工作)。

### Inventory cron

| 工作 | 指令 | 效果 |
| --- | --- | --- |
| 看排程設定 | `python -B tools/opsfeast.py inventory status --profile main --json` | 讀取 |
| 看待執行項目 | `python -B tools/opsfeast.py inventory dispatch --profile main --dry-run --json` | 讀取，不連線 |
| 啟用已審查主機排程 | `python -B tools/opsfeast.py inventory configure --profile main --host server-01 --enable --json` | 寫 inventory.yaml；先看全部 job |
| 安裝 cron | `python -B tools/opsfeast.py inventory cron install --profile main --json` | 修改目前使用者受標記 crontab |
| 看 cron | `python -B tools/opsfeast.py inventory cron show --profile main --json` | 讀排程，不證明已執行 |
| 取消 cron | `python -B tools/opsfeast.py inventory cron remove --profile main --json` | 移除本 profile 項目，保留其他項目與資料 |
| 停用單台週期採集 | `python -B tools/opsfeast.py inventory configure --profile main --host server-01 --disable --json` | 寫設定，不刪歷史 |

Cron 是 inventory 專用，不是通用 recipe scheduler，也不是 consumer dispatch。間隔、有效 job、三個 enabled 門檻與失敗行為見[第 5 章](05-recipes-and-inventory.md#cron-設定與取消)。

## Observation 管理

| 工作 | 指令 | 效果 |
| --- | --- | --- |
| 列 observation 批次 | `python -B tools/opsfeast.py observation --profile main --json` | 讀明確保存的批次 |
| 看最新批次 | `python -B tools/opsfeast.py observation latest --profile main --json` | 讀取，可能已非你剛才那次 |
| 看特定批次 | `python -B tools/opsfeast.py observation OBSERVATION_ID --profile main --json` | 用實際批次 ID |
| 看最新批次失敗/部分結果 | `python -B tools/opsfeast.py observation latest --status failed partial --profile main --json` | 篩選該批次 |
| 列主機結果 | `python -B tools/opsfeast.py observation result --host server-01 --profile main --json` | 讀個別結果清單 |
| 聚焦診斷 | `python -B tools/opsfeast.py observation result RESULT_ID --profile main --json` | 讀保存失敗證據，不重跑 |
| 完整細節 | `python -B tools/opsfeast.py observation result RESULT_ID --detail --profile main --json` | 完整結構 |
| 原始 JSON | `python -B tools/opsfeast.py observation result RESULT_ID --raw --profile main` | 原始結果 |
| 列 retained record | `python -B tools/opsfeast.py retention list --profile main --json` | 讀結構化資料 |
| 看 retained record | `python -B tools/opsfeast.py retention show RECORD_ID --profile main --json` | 讀完整資料與來源 |

這些讀取不改寫或收集。`OBSERVATION_ID`、`RESULT_ID`、`RECORD_ID` 各有用途，不能互換。資料刪除、移轉與封存有獨立保護與復原流程，見[延伸篇](10-sharing-recipes.md#延伸閱讀製作分享移轉與封存)，不可用手動刪 SQLite/raw 模擬管理工具。

## Consumer 管理

| 工作 | 指令 | 效果 |
| --- | --- | --- |
| 列 recipe 相關 consumer | `python -B tools/opsfeast.py consumers list --recipe system/inventory/overview --profile main --json` | 靜態探索，不啟用 |
| 看處理回執 | `python -B tools/opsfeast.py consumers inspect --profile main --json` | 讀取 |
| 看 Vault 狀態 | `python -B tools/opsfeast.py vault inspect --profile main --json` | 讀取 |
| 重建隨附 Vault | `python -B tools/opsfeast.py vault rebuild --profile main --json` | 寫受管理內容，不採集 |
| 重試 Vault consumer | `python -B tools/opsfeast.py consumers dispatch vault --profile main --json` | 執行設定程式，可能連動服務遞送 |
| 看服務設定/可用性 | `python -B tools/opsfeast.py services inspect --profile main --json` | 靜態，不寄送 |
| 看遞送回執 | `python -B tools/opsfeast.py services deliveries --profile main --json` | 讀取，不重試 |

Consumer 在 `feast.yaml` 明確登記，沒有自動安裝/啟用候選的通用命令。Dispatch 不等同靜態 inspect；已有路由時可能寄信，先確認對應授權。通知與待辦進階操作見[服務延伸](07-consumers-and-vault.md#延伸閱讀consumer通知與待辦)。

## Profile 管理

| 工作 | 指令 | 效果 |
| --- | --- | --- |
| 查看 | `python -B tools/opsfeast.py profiles` | 讀登記與可用性 |
| 變更預設 | `python -B tools/opsfeast.py use lab` | 寫預設選擇 |
| 開新的 | `python -B tools/opsfeast.py init lab --json` | 建立/重用管理目錄並登記 |
| 掛接既有 | `python -B tools/opsfeast.py attach /absolute/path/to/existing-feast --profile team` | 寫登記，保留目錄 |
| 解除登記 | `python -B tools/opsfeast.py detach team` | 保留資料，main 受保護 |

參照[進階 profile 章](08-profiles.md)了解 detach 預設切換、身份與排程邊界。

## 正式參考索引

| 問題 | 正式來源 |
| --- | --- |
| 產品目標與人類/agent 分工 | [設計原則](../../vision.md) |
| 精確 CLI 參數、輸出與 exit code | [CLI 參考](../../cli.md) |
| 現有可重用工具與模組 | [能力地圖](../../agent-capabilities.md) |
| Agent 任務路由 | [Skill 索引](../../../skills/README.md) |
| 安裝與初次使用 | [開始使用](../../getting-started.md)、[初次使用流程](../../first-use.md) |
| Profile 儲存與登記 | [Profiles](../../profiles.md) |
| 主機欄位、include、路徑與憑證 | [hosts.yaml](../../hosts-yaml.md)、[第一台主機](../../first-host.md) |
| 權限診斷與採集範圍 | [診斷](../../host-diagnostics.md)、[inventory 存取](../../inventory-access.md) |
| Recipe reference、繼承與啟用 | [來源與政策](../../recipe-sources.md) |
| Recipe 探索、報表、成品、保存 job | [Recipe 操作介面](../../recipe-experience.md) |
| 維運入口、輸入與輸出 | [執行](../../recipe-execution.md) |
| 判讀摘要與執行帳號、狀態的差別 | [結果與帳號](../../recipe-results-and-accounts.md) |
| 屬性/job 選擇、資料新舊與 cron | [Inventory jobs](../../inventory-jobs.md)、[採集表](../../../recipes/system/inventory/overview/collection-plan.md) |
| 結構化歷史與可重用 reader | [Retention](../../retention.md)、[Core API](../../core-api.md)、[結果資料](../../result-data.md) |
| 內容路徑、筆記與輸出歸屬 | [維運 Vault](../../host-vault.md) |
| 離線 raw 復原 | [Retention replay](../../retention-replay.md) |
| 事件、啟用與重試 | [Consumers](../../retention-consumers.md)、[consumer 目錄](../../../consumers/README.md) |
| 通知/待辦狀態、呈現與遞送 | [服務](../../services.md)、[adapters](../../service-adapters.md) |
| 備份存在性、日期政策與完整可攜程式 | [備份檢查](../../backup-file-checks.md) |
| Recipe 製作、取得與分享 | [製作](../../recipe-authoring.md)、[取得](../../recipe-acquisition.md)、[分享](../../recipe-sharing.md) |
| 保留來源的移轉、安裝與封存 | [可攜與封存](../../portability.md)、[可攜契約](../../portable-contracts.md) |
| Release、schema 與 skill 更新程序 | [Skill 更新](../../skill-updates.md) |
| 目前已實作的 TUI | [終端介面](../../terminal-ui.md) |

## 如何核對操作結果

先確認指令選中了正確的 profile 與主機，再看它完成了哪一步：

- 設定檢查通過後，進行選定主機的連線測試。
- Recipe 完成後，閱讀 observation 中的執行、身分、採集與各階段結果。
- 資料已保存而頁面缺少時，查看 retention 與 consumer 回執，選擇本機內容修復。
- 報表已產生時，使用結果與 artifact 介面取得實際檔案，並保留來源時間。
- 要處理失敗時，先讀保存的證據，再決定是否重試、補查或復原。

詳細判讀見[Observation 章](06-observations.md)與[故障排除](06-observations.md#延伸閱讀依證據排除故障)。本書的編寫與檢查紀錄由[維護指引](../MAINTAINING.md)集中管理。

*Last modified: 2026-10-26 23:35:09*
