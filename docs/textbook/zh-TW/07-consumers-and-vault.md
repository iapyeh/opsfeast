# 7. Consumer：如何在 Vault 看到結果

[全書首頁](README.md) · 上一章：[Observation](06-observations.md) · 下一章：[進階 profile](08-profiles.md)

## Consumer 是什麼，為什麼需要它

一次採集得到資料之後，你可能要產生 Markdown、建立檢查待辦，或讓其他內容應用處理它。Consumer 是經審查的下游程式，依 retention 事件讀取權威資料，完成自己宣告的工作。

這讓採集程式專心產生可判讀資料，呈現或政策可以獨立更新。不必因為想換表格格式就再連線採集；也不必把每種通知政策塞進每個 recipe。Consumer 的輸出與回執獨立，因此你可以在保留已存資料的情況下，單獨處理內容更新問題。

## 隨附 Vault consumer

新的環境預設有 `builtin:vault`，本機名稱通常是 `vault`。它將保留資料整理到管理根目錄的 `vault/`，包含主機目前紀錄、歷史報告、批次導覽等。它消費已存資料，不會為了重建頁面重新連線。

```text
recipe 執行 → raw observation → retention
                                  ↓
                          builtin:vault consumer
                                  ↓
                       <management-root>/vault/
```

檢視 consumer 狀態，不啟動程式或寄送：

```sh
python -B tools/opsfeast.py consumers list --recipe system/inventory/overview --profile main --json
python -B tools/opsfeast.py consumers inspect --profile main --json
python -B tools/opsfeast.py vault inspect --profile main --json
```

實際是否啟用，以 `feast.yaml` 與回執為準。`vault.auto_refresh: false` 可關閉自動發布，同時繼續保存 retention。其他 consumer 需要審查與明確登記；安裝 recipe 不會自動啟用附帶程式。

## 在 Vault 看第一個 observation

1. 使用安裝驗收或 `profiles` 找到實際管理根目錄。
2. 在 Obsidian 或 Markdown 閱讀器開啟它的 `vault/`，例如實際根目錄若是 `feasts/main/`，就開 `feasts/main/vault/`。
3. 從 `HOSTS.md` 進主機列表，或從 `Observations/SUMMARY.md` 進批次歷史。
4. 找到剛才保存的 observation 批次，核對主機與時間，跟到該次來源報告。
5. 需要看目前彙整時，從主機 `SUMMARY.md` 進 `records/SUMMARY.md`，再開 current 頁面。

| 想回答的問題 | 看哪裡 |
| --- | --- |
| 這次第一個 recipe 對哪些主機做了什麼 | Observation 批次頁與其歷史來源報告 |
| 這台主機目前可用的最新資料 | 主機 records 的 current 頁面 |
| 完整採樣、來源、部分或未知證據 | 歷史報告末端 metadata、retention 或 raw result |
| 自己補充的維運背景 | 主機人工 README 或非受管理筆記 |

Current 頁面之後可能來自更新觀察；要指認「第一次執行」，請用保存的 ID 與歷史報告。主機依第一個群組放置，其他群組連回同一位置。使用產生索引，不自行猜經編碼的路徑。

這個維運 Vault 與 `docs/textbook/zh-TW/` 教學 Vault 不同，不要讓 consumer 發布到教科書裡。Mermaid 圖表可由 Obsidian 內建功能顯示，不需要另外安裝圖表外掛；其他閱讀器不支援時仍可讀表格。

## 找不到結果時，先查哪一層

| 情況 | 下一步 |
| --- | --- |
| 採集或連線失敗 | 先查 observation/raw，可能沒有 eligible retention |
| Raw 成功，retention 失敗 | 保留 raw，依 replay 指引先 dry-run，不必立即重採 |
| Retention 成功，Vault 回執失敗 | 查 ownership/路徑/consumer 錯誤，修復內容 |
| Consumer 停用或 auto_refresh 關閉 | 說明現有設定與授權，再決定本機重建或啟用 |
| 頁面存在但數值很舊 | 看原始採樣時間，重建不能更新量測 |

若只有隨附頁面需修復，已授權的本機重建：

```sh
python -B tools/opsfeast.py vault rebuild --profile main --json
```

它改寫受管理內容，不改 retention/批次，也不確認 pending consumer 回執。若要重試 consumer，則是不同操作：

```sh
python -B tools/opsfeast.py consumers dispatch vault --profile main --json
```

Dispatch 執行設定中的程式，還可能嘗試服務 dispatch；已有郵件路由時可能寄送。重試前確認真實下游設定與授權，不因為名稱叫 vault 就假設沒有外部效果。

## 保護人工筆記

產生頁面的 manifest 記錄輸出歸屬，手動編輯仍會被重建覆蓋，拿掉 generated 提示也不改歸屬。人工筆記放在保留的 host README、獨立檔案，或支援的 todo note 欄位。不要直接改 SQLite 或抓 Markdown 表格重建產品資料介面。

> 請依這次已保存的 observation ID 找出 Vault 入口，說明批次歷史頁、主機 current 頁與原始結果的差別。如果缺頁，先診斷 retention 和 consumer 回執，不重新連線。不在未核對遞送設定前 dispatch。

**基本篇完成：**你已走過主機設定 → recipe → observation → retention → consumer → Vault。接下來才擴展多個管理環境、自己的 recipe 與同事共用。

延伸：[retention 與內容](#延伸閱讀閱讀資料與使用維運-vault)、[通知與待辦](#延伸閱讀consumer通知與待辦)；正式參考：[consumer 契約](../../retention-consumers.md)、[Vault](../../host-vault.md)。

## 延伸閱讀：閱讀資料與使用維運 Vault

一般閱讀與導覽使用維運 Vault，結構化分析使用 retention 介面，需要原始執行證據時則查看保存的 raw 結果。這些介面回答不同問題，也保留不同細節。

### 瀏覽維運 Vault

在 Obsidian 或其他 Markdown 工具開啟選定 profile 的實際 `vault/` 目錄。它與你現在閱讀的教科書目錄分開。

| 入口 | 適合閱讀的內容 |
| --- | --- |
| `HOSTS.md` | 主機導覽與 Observations 入口 |
| `Observations/SUMMARY.md` | 已記錄的執行批次與結果 |
| `hosts/<primary-group>/<host>/SUMMARY.md` | 單一主機的內容與筆記 |
| 主機下的 `records/SUMMARY.md` | 目前資料集與操作歷史 |
| 主機下的 `records/current-*.md` | 保留原始來源時間的易讀最新狀態 |
| 主機下各年度 `reports/` | 完整歷史 observation 與來源脈絡 |
| `Services/SUMMARY.md` | 通知與待辦呈現 |
| `Transfers/SUMMARY.md` | 匯入證據導覽 |

實際路徑片段由發布程式編碼。使用回傳連結與產生的索引，不要自己拼檔名。主機放在第一個解析出的群組下，其他群組連到相同位置。呈現位置換群組，不會改變主機歷史身分。

目前 inventory 頁面省略不適合閱讀的 null 或空值欄位，但保留涵蓋範圍警告。零、false、確實觀察到的空集合仍分開呈現。某些長清單只顯示預覽並提供歷史來源連結。歷史報告保留完整已儲存 observation，最後有 Collection metadata 區段。目前頁面省略某欄位，不是「已確認不存在且健康」的證據。

檔案系統使用率長條圖與介面／IP 關係圖採用 Mermaid，Obsidian 內建支援。沒有另外安裝圖表外掛或 MCP server 的需求；表格保留原始資料，介面關係也不代表已驗證網路連通。既有產生頁面的 DGMO 圖，可在選定 profile 執行本機 `vault rebuild` 時更新為 Mermaid；自己的非管理筆記不會被轉換。目錄連結遵循 Obsidian 標題規則，其他閱讀器可能不同。本書使用一般相對 Markdown 連結切換章節。


### 保護自己的筆記

產生頁面由 manifest 記錄輸出歸屬，即使有人手動修改，仍可被覆寫。移除產生提示不會移除歸屬。人工背景請放在保留的主機 `README.md`、獨立非管理筆記或支援的服務 note 欄位。

群組變更後，完整重建可能搬移受管理內容。非管理筆記留在原位置，需明確搬移或更新連結。發布是逐檔原子替換，不是整個 Vault 的單一交易。

## 延伸閱讀：Consumer、通知與待辦

Retention consumer 將保存證據轉成有用的下游工作。服務管理發現與待辦的生命週期，遞送 adapter 負責呈現及對外傳送。採集、consumer 完成、訊息送達可以各自成功或失敗。

### 先探索，不立即啟用

```sh
python -B tools/opsfeast.py consumers list --recipe system/inventory/overview --profile main --json
python -B tools/opsfeast.py consumers inspect --profile main --json
python -B tools/opsfeast.py services inspect --profile main --json
```

這些指令檢視可用或已設定的程式、回執與服務可用性，不會寄信。靜態檢視不執行候選程式，也不能證明 provider 憑證有效。在 `feast.yaml` 啟用之前，先審查實作、支援資料契約、依賴、輸出歸屬與副作用。

隨附 Vault consumer 預設啟用。其他 consumer 需要明確審查並登記。把 consumer 放進 recipe 套件不會啟用它。備份政策是獨立 consumer，採集備份中繼資料不會隱含啟用政策。


### 理解 consumer 復原

Consumer 處理持久化事件，每個事件有自己的回執與重試歷史。程式必須容忍重複遞送與過時提示；收到事件時，應讀取權威資料確認目前狀態，而不是直接把提示中的紀錄當成最新值。Vault consumer 可以批次發布，同時保留逐事件回執。

確認失敗 consumer 並審查效果後，已授權的重試例如：

```sh
python -B tools/opsfeast.py consumers dispatch vault --profile main --json
```

Dispatch 會執行已設定程式。Retention-consumer dispatch 也會嘗試設定中的服務 dispatch，有遞送路由時可能寄信。因此，即使重試內容 consumer，也要了解目前服務設定與授權遞送範圍。若只有隨附內容需要修復，可用指定的 `vault rebuild`，但它不會確認待處理事件。


### 區分檢查發現、訊息與工作

政策使用主機、精確 recipe reference、subject 與 rule 識別一個 condition。持續不利證據更新同一輪事件；驗證清除後解決，之後再次發生則建立新一輪。未知或不完整證據不能錯誤地解除既有問題。

通知有 active/resolved condition 狀態，另有獨立的已讀與確認狀態。Todo 的狀態是 `open`、`in_progress`、`blocked`、`done`、`cancelled`。Todo 記錄預計工作；指派人員或填入日期，不會執行指令、刪檔、安裝排程或喚醒 agent。

透過 consumer services，只有合格的即時採集證據才能建立事件。歷史 replay/import 不會變成新的目前事件。不要改時間戳或繞過 consumer facade 來製造即時效果。


### 檢視並更新待辦

```sh
python -B tools/opsfeast.py services list --kind todo --profile main --json
python -B tools/opsfeast.py services show OBJECT_ID --kind todo --profile main --json
python -B tools/opsfeast.py services history OBJECT_ID --profile main --json
```

這些都是讀取。指派工作或加註記之前，先讀目前 revision。以下是已授權修改的例子，請把 `3` 換成實際回傳的 revision：

```sh
python -B tools/opsfeast.py services update OBJECT_ID --kind todo --revision 3 --actor operator --changes '{"status":"in_progress","assignee":"operator","note":"Review the saved file list before proposing cleanup."}' --profile main --json
```

Revision 過時會失敗，避免覆蓋別人的修改。重新載入並檢視中間變更後，再決定重試。到期、開始與靜音時間需要時區偏移，並正確解讀 timezone。政策協調會保留人工指派與註記。問題仍持續時手動標成 done，下一次檢查仍可重開待辦；問題確實消失時，政策會依新證據確認清除。修改產生的 Markdown 不會更新服務物件。


### 在授權範圍內發布與遞送

```sh
python -B tools/opsfeast.py services deliveries --profile main --json
```

這會讀取 outbox 狀態。已授權的 `services dispatch` 執行設定中的呈現與遞送 adapter。直接更新物件不自動重新發布。預設有 Vault 呈現、沒有遞送路由；認定 dispatch 只在本機作用之前，仍應讀取實際設定。

遞送狀態包含 pending、sending、delivered、failed、unknown、cancelled。Unknown 可能代表訊息已送出，只是確認遺失。`--retry-unknown` 是明確決策，可能重複遞送。已讀或已確認不證明 provider 實際送達，穩定 ID 也不保證 SMTP 恰好遞送一次。

可以這樣對 agent 說：

> 不做 dispatch，檢視 profile main 尚未處理的備份待辦與通知遞送狀態。說明各 condition 的證據、目前 revision、最新 observation 時間與不確定性。需要更新生命週期時，以目前 revision 準備修改。不要把 todo 當成刪檔授權。

**理解檢核：**說明問題是檢查發現、尚未完成的 consumer、過時呈現，還是遞送不明。決定復原前，先找到原始證據。

正式參考：[consumer 契約](../../retention-consumers.md)、[consumer 目錄](../../../consumers/README.md)、[服務](../../services.md)、[adapters](../../service-adapters.md)、[備份政策](../../../consumers/backup-check/README.md)。

*Last modified: 2026-10-26 16:22:18*
