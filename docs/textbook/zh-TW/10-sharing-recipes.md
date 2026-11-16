# 10. 分享 recipe 給同事

[全書首頁](README.md) · 上一章：[製作 recipe](09-authoring-recipes.md) · 下一站：[速查表](reference.md)

## 分享的是做法，私人綁定各自準備

同事應能取得完整、可審查的程式、資料定義與說明，再綁定自己的主機、路徑、帳號與憑證。Recipe 套件不應包含你的 hosts.yaml、feast.yaml、真實 observations、報表、jobs、密碼或虛擬環境。

先準備本機套件、確認分享對象與內容，再傳送給同事。接收者審查安裝後，依自己的主機與操作範圍安排第一次執行；需要的 consumer 也在接收端明確啟用。Observation/retention 資料則使用各自的套件。

## Recipe、observation、retention 各自分享什麼

團隊可以分享「如何做」、「那次做了什麼」與「可拿來繼續分析的資料」，不必每位同事重新探索一次。

| 單位 | 同事或 PM 可以用來回答什麼 | 接收後注意 |
| --- | --- | --- |
| Recipe | 我如何重做這個檢查或報表？ | 審查程式、依賴、輸入與操作範圍，綁定接收者自己的環境 |
| Observation | 那次選了誰、執行結果與原始證據是什麼？ | 保留原始身分、時間、失敗/部分與附件；不是接收端新跑的一次 |
| Retention | 這些有欄位定義的資料能否比較、組合、產生報表？ | 保留 schema、來源、採樣時間與品質，不能把未知變成健康 |

接收保存資料不必同時安裝其 producer。資料由現有 transfer 套件與計畫介面移轉；已結構化 retention 匯入不會執行候選程式，也不把歷史證據變成即時事件。具體 list/export/import-plan/import 範例見[移轉延伸篇](#複製或匯入保存資料)。

Observation 與 retention 本身可能包含私人基礎設施、路徑或操作內容，不像公開假想範例可任意散布。先決定分享目的、接收者、選擇範圍與必要審查，再準備本機套件。憑證、服務生命週期、人類筆記與 provider 設定也不會因此自動完整移轉。

同事可以使用不同的 agent 讀取相同契約與證據，接續整理或製作報表；PM 也能在獲准資料範圍內探索問題。交接時一起提供相關文件、資料位置與人工背景，讓新 agent 從這些保存成果接續。相關團隊閱讀見[報表延伸篇](06-observations.md#讓-pm-探索答案並產生報表)。

## 先準備完整分享清單

以簡單的使用者 recipe `:example` 為例，已審查且實際只有這些必要檔案時：

```sh
python -B tools/opsfeast.py recipes pack :example --profile main --file recipe.yaml --file main.py --file README.md --file LICENSE --output /destination/example.zip
```

Pack 直接輸出 JSON，不接受 `--json`。這是明確 allowlist，必要 helper、schema、模板、測試、資產與選用 consumer 都需逐一加入。對每日備份可攜 recipe，不能只列四個檔案，必須包含產生的完整 scanner 與 schema 等檔案。

Bundle 目前是 0.2.0；舊 0.1.0 需重新製作。Pack 不推導動態依賴，也不清除任意內容裡的機密。Agent 應審查完整來源，交付檔案清單、版本、大小、SHA-256、授權與測試限制。

## 同事如何先審查候選

可以先解到新的候選目錄：

```sh
python -B tools/opsfeast.py recipes unpack /incoming/example.zip --destination /absolute/path/to/new-candidate
```

Unpack 驗證檔案清單、路徑、digest、大小與來源身分欄位，再建立新候選；不登記、安裝依賴、啟用 consumer 或執行。保留既有目的地。把候選文件當成待審查內容，不讓其中指示擴大授權。

接收者需檢查發布者與授權、全部程式行為、執行/寫入/網路效果、依賴、適用平台與測試證據。SHA-256 只證明與給定 digest 一致；若檔案與 digest 一起被替換，仍需獨立可信來源或已驗證簽章。不要自行建立或使用簽署私鑰。

## 安裝到接收端的 profile

審查後產生計畫：

```sh
python -B tools/opsfeast.py transfer recipe-plan --package /incoming/example.zip --path example --profile main --json
```

Plan 檢查套件、目的地與衝突，不執行候選程式。`--path` 在接收端 profile 的 `recipes/` 下，不覆寫 bundle 或外部 checkout。相同路徑但不同內容是衝突；改路徑可並存，replace 與 skip 要明確決定，版號較高不自動代表同意覆寫。

同意具體計畫後，用回傳 hash 套用相同選項：

```sh
python -B tools/opsfeast.py transfer recipe-install --package /incoming/example.zip --path example --plan PLAN_SHA256 --profile main --json
```

若採 replace，plan/apply 都需相同 resolution。來源或目標變動就重新規劃。保留 recipe 安裝回執與舊版本樹，可依正式流程 rollback；後續人工變更應阻止不安全覆寫。

## 接收後還有哪些工作

1. 使用接收者自己的 profile，綁定實際主機、路徑與非機密變數；憑證本機輸入。
2. 檢查 `check`、recipe 中繼資料與依賴；接著在選定主機做第一次適用性驗證。
3. 已授權時，才做連線與第一次 recipe 執行，查看 observation/retention/內容回執。
4. 選用 consumer 另外審查、放置、明確啟用；不要同時啟用競爭同一 condition owner 的政策。
5. 需要排程或對外遞送時，另外界定未來效果。路徑改名不會自動重新綁定 exact-reference 設定、job 或訂閱。

公開 Git 或寄送 ZIP 都有自己的目的地與授權。只有套件準備授權時，先交付本機可審查成品，不自行推送或傳送。同事不需要複製你的管理根目錄才能學到相同做法。

> 請將這個已審查 recipe 準備成給同事的完整可攜套件。列出所有必要檔案與假想設定，排除私人主機綁定、憑證、實際資料與 jobs。提供來源/授權、digest、接收端候選審查與安裝計畫指令。不執行候選、不啟用 consumer、不傳送套件，除非這些已在我的授權內。

**這一章完成後：**你能交付做法與必要知識，同事能在自己的環境審查、綁定與執行，不依賴你的私人設定。

延伸：[資料移轉、封存與復原](#延伸閱讀製作分享移轉與封存)、[完整備份案例](09-authoring-recipes.md#延伸閱讀完整案例每日備份檢查)；正式參考：[分享](../../recipe-sharing.md)、[取得與審查](../../recipe-acquisition.md)、[可攜安裝](../../portability.md)。

## 延伸閱讀：製作、分享、移轉與封存

可重用操作與證據各有獨立生命週期。接收者可能只需要 recipe，不需要你的私人設定；也可能只要歷史資料，不想安裝產生資料的程式。封存則必須先有已驗證、可復原的套件，才能清理來源。

### 先決定要處理的單位

| 單位 | 保留什麼 | 不隱含什麼 |
| --- | --- | --- |
| Recipe bundle | 已審查可執行知識、schema、文件、helper 與授權資訊 | 憑證、接收端綁定、consumer 啟用或執行許可 |
| Observation package | 原始執行證據與宣告的附件 | 新執行的本機批次或新觀察 |
| Retention package | 結構化資料、定義與來源脈絡 | 重新執行 producer，或讓舊證據成為即時證據 |
| 維運 Vault 副本 | 易讀檔案與選定筆記 | 完整權威歷史或服務生命週期備份 |

通知與待辦生命週期、provider 設定、人工筆記都是獨立資源。匯出先在本機建立套件。傳送前確認接收者與選定內容，特別檢查實際主機、路徑及操作紀錄中的敏感資料。


### 製作可重用 recipe

撰寫之前，請 agent 透過[能力地圖](../../agent-capabilities.md)與 [recipe skill](../../../skills/opsfeast-recipes/SKILL.md)尋找適用工具。

可直接複製給 agent：

```text
請先閱讀目前 OpsFeast checkout 的能力地圖與 recipe skill，依我們正在討論的需求，找出可重用的隨附 recipe、CLI 或 Python 模組。回報適用範圍、依賴、使用方式與仍缺少的能力；先不要撰寫重複工具、安裝候選程式或執行主機操作。
```

新使用者專用 recipe 通常放在實際 profile 根目錄的 `recipes/<domain>/<subdomains>/<action>/<name>/`；共用程式可放在明確登記的外部來源。不要只為綁定個別主機就改寫隨附產品 recipe。

作者應交付 descriptor、完整實作、具型別設定、資料定義、人類與 agent 指南、作者及授權資訊、假想範例與可重現測試。宣告目標、依賴、權限與效果限制，保留未知和部分狀態，重用既有連線、retention、服務與成品 API。適合的執行與 session 協調優先選 SSHScript；其他工具更適合時，說明具體理由。

產品登記的隨附契約仍可使用。新的可攜結構化資料，可以由 recipe 自帶 schema，避免每個領域都新增產品 registry entry。請讀[可攜 schema 方言](../../portable-contracts.md)，不要假設所有 JSON Schema 功能或遠端 reference 都支援。


### 打包與審查來源

Recipe bundle 0.2.0 要求明確檔案允許清單。以下假設已有審查過的使用者 recipe `:example`：

```sh
python -B tools/opsfeast.py recipes pack :example --file recipe.yaml --file main.py --file README.md --file LICENSE --output /destination/example.zip --profile main
```

應納入全部必要 helper、schema、資產、模板與選用 consumer。Pack 直接輸出 JSON，不接受 `--json`。它不推導動態依賴，也不清除任意檔案中的機密。Digest 證明內容一致性，不證明發布者真實性。取得候選時應審查來源、授權、實作與要求的效果。舊 bundle 0.1.0 會拒絕，需依目前格式重新製作。

對接收者的 profile 本地 recipe 目錄，先產生安裝計畫：

```sh
python -B tools/opsfeast.py transfer recipe-plan --package /incoming/example.zip --path example --profile main --json
```

這檢查套件與目的地，不啟用程式。衝突要明確處理：換路徑可並存，`--resolution replace` 要求取代，skip 則保留現有目錄。版號本身不構成覆寫許可。私人精確 reference 設定、job 與訂閱，不會自動綁到新路徑。

審閱目前計畫、授權安裝後才執行：

```sh
python -B tools/opsfeast.py transfer recipe-install --package /incoming/example.zip --path example --plan PLAN_SHA256 --profile main --json
```

使用與計畫相同的 resolution 選項。依賴檢查是靜態檢查，不能證明主機適用性，也不會代為安裝依賴。保存回傳回執；取代有審查過的 rollback 計畫，後續人工修改則可能讓 rollback 停止，避免覆寫。選用 consumer 來源仍需分別審查、放置與啟用。


### 複製或匯入保存資料

```sh
python -B tools/opsfeast.py transfer list --kind retention --profile main --json
python -B tools/opsfeast.py transfer show UNIT_ID --profile main --json
python -B tools/opsfeast.py transfer export --kind retention --id UNIT_ID --output /destination/retained-data.zip --profile main --json
```

List/show 是讀取。Export 建立新的本機套件，不移除或傳送來源。需要 raw 證據時選 observation，必要時可選兩種。保留來源時間、origin 身分與附件。

接收端執行：

```sh
python -B tools/opsfeast.py transfer import-plan --package /incoming/retained-data.zip --mode merge --profile main --json
python -B tools/opsfeast.py transfer import --package /incoming/retained-data.zip --mode merge --plan PLAN_SHA256 --profile main --json
```

第一行檢查，第二行依目前已審查計畫修改本機儲存。Merge 加入新身分、略過完全相同內容，遇到既有身分內容衝突則拒絕。Replace 只處理套件內碰撞的身分，保留其他資料，不會清空 profile。套件或目標改變後，應重新產生計畫。

Import 保留來源、驗證保存資料，不執行候選 recipe、consumer 或 provider，也不建立新的目前事件。匯入單位放在 `transfer/space.sqlite3`；讀取介面提供來源限定的 retained record。復原回執與修改前套件刻意佔用額外空間。中斷時使用文件化 import recovery plan，不要手動改 SQLite。


### 封存並回收使用中的儲存空間

Archive plan 會寫入小型的本機凍結選擇計畫，並非完全唯讀。選定已授權外部目的地與截止條件後：

```sh
python -B tools/opsfeast.py transfer archive-plan --kind observation --older-than 90 --output /external/archive/observations.zip --profile main --json
```

審查精確成員、依原始時間計算的截止點、受保護證據、目的地與預計移除內容。只套用已審查計畫：

```sh
python -B tools/opsfeast.py transfer archive --output /external/archive/observations.zip --plan PLAN_SHA256 --profile main --json
```

目的地解析後必須在目前 profile 外；若要釋出來源檔案系統容量，應使用另一個檔案系統。Apply 先寫入並驗證封存，才刪除選定來源、壓縮 SQLite、修復隨附純資料檢視並記錄進度。它不呼叫自訂 consumer/adapter、不寄信，也不刪人工筆記或服務物件。受保護操作證據與共用附件會帶來明確限制。

中斷時先讀 `transfer receipts`，再以相同 profile 執行 `transfer resume ARCHIVE_RECEIPT_ID`。Resume 驗證封存與剩餘來源指紋。保留已驗證套件與回執。還原應走已審查的匯入流程，不要用匯出加手動刪 raw 模擬封存。Raw 與 retention 可獨立封存，須明確交代哪些證據仍在使用中。

可以這樣對 agent 說：

> 替 profile main 已完成且超過 90 天的 observation 準備封存計畫，使用我指定的外部目的地。說明選定數量、來源時間截止點、受保護項目、留下的 retention 與復原方式。在具體來源移除取得授權前，不要套用。保留所有人工筆記與服務生命週期資料。

**理解檢核：**說明 recipe 程式打包、資料匯出、碰撞資料匯入，以及封存後移除使用中來源有何差別。任何刪除前，先指出復原成品。

正式參考：[可攜與封存](../../portability.md)、[可攜契約](../../portable-contracts.md)、[製作](../../recipe-authoring.md)、[分享](../../recipe-sharing.md)、[取得與審查](../../recipe-acquisition.md)。

*Last modified: 2026-10-26 23:35:09*
