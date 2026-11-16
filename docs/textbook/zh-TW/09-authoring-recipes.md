# 9. 製作自己的 recipe

[全書首頁](README.md) · 上一章：[Profiles](08-profiles.md) · 下一章：[分享給同事](10-sharing-recipes.md)

## 先把需求寫成可以判定的問題

「幫我檢查備份」仍需補上目的地主機、目錄、檔名規則、日期與時區、截止時間、允許的權限，以及存在性是否已足夠。人類提供業務規則，agent 負責重用工具、完成實作與測試。

> 在 profile main，替 backup-example 建立每日檔案存在性檢查。依我提供的目錄、檔名與截止時間，只讀目錄中繼資料。先找 OpsFeast 現有模組與完整可攜範例，使用私人設定綁定主機。保存結果並說明未知/不完整狀態，不刪檔、不寄信、不排程。

這個需求可重用 `opsfeast.backup_check.portable_files(identity)`，不必再寫一套 scanner。詳見[完整備份案例](#延伸閱讀完整案例每日備份檢查)。如果現有 recipe 已能滿足，只調整私人設定即可，不需要為了「自製」重寫。

## 互動探索如何變成可重跑成果

互動式製作的目的，是把這次問清楚的需求與做過的確認保存下來，下一次由程式完成重複部分。使用者不必先學會框架再自己寫 recipe；agent 應完成必要工具重用、設定、文件、資料與驗證。

| 階段 | 人類與 agent 一起確認的事 | 留下的成果 |
| --- | --- | --- |
| 說明意圖 | 要回答什麼、哪些主機、允許的權限與效果 | 明確目標與範圍 |
| 探索現有能力 | 有沒有可直接使用的 recipe/模組、缺少哪些業務規則 | 工具選擇與必要問題 |
| 有限探索與審查 | 在授權內顯示並驗證實際操作，判斷輸入與邊界 | 可追溯證據與已審查規則 |
| 整理成 recipe | 將重複邏輯、輸入與結果契約標準化 | 程式、私人設定、retention、文件與測試 |
| 重跑與交付 | 新執行能否重現預期流程，部分/失敗如何顯示 | 精確 rerun command、observation 與驗證限制 |

之後例行採集、判讀或報表直接執行已審查程式，不必請模型重新產生每一條指令。新 CVE、新環境或新規則出現，再由 agent 判斷哪裡需要改。Token 用在理解新的差異、審查與解釋例外；必要驗證不能因節省 Token 而略過。

這個流程適用不同 agent。保存的 recipe、設定與證據是交付，不是某一產品的聊天紀錄。完整程序見[從互動探索到 recipe](../../../skills/opsfeast-recipes/references/exploration-to-recipe.md)。

## 客製化：先選對層次

OpsFeast 為不同公司的系統與管理需求保留擴充點。先找最小且可重用的變更，避免把私人環境差異變成產品框架的分叉。

- 地址、via、帳號與群組不同：修改私人 `hosts.yaml`，使用既有載入規則。
- 相同程式但門檻、檔名、路徑不同：使用該 recipe 支援的 vars；不要把機密塞進命令列。
- 管理資料需分環境：選擇 profile，保留各自來源與歷史。
- 需要新的採集、檢查或業務資料：補齊真正缺少的 recipe 與受支援資料定義，重用連線、儲存、服務等共用能力。
- 相同資料需要不同政策、報表或畫面：使用 consumer、離線報表與 adapter 擴充，不為了呈現再次採集。

選好層次後，再確認相應介面、版本與依賴。現有工具不適用時，讓 agent 補齊可重用程式、文件與測試，讓這次解決的需求也能交給下一位同事使用。以 PHP 事件為例，先讀既有 inventory，再補足供應商修補、runtime 與業務分級資料，詳見 [CVE 案例](05-recipes-and-inventory.md#延伸閱讀從-cve-事件到可重用盤點)。

## 放在哪裡，如何參照

使用選定 profile 的實際根目錄：

```text
<management-root>/recipes/
  backup/files/check/daily-backups/
    recipe.yaml
    main.py
    README.md
    LICENSE
    ...必要的 scanner、schema、helper、範例與測試
```

參照是 `:backup/files/check/daily-backups`。中間分類目錄不是 recipe，葉節點的 `recipe.yaml` 才定義它。共用 repository 可用登記的外部來源；不要為個人主機設定改隨附 bundle，也不要把私人密碼包進來源。

## 一份完整 recipe 要包含什麼

| 交付項目 | 用途 |
| --- | --- |
| Descriptor | ID、版本、目的、runner、平台、依賴、權限、副作用、輸入與輸出 |
| 程式與全部 helper | 在受支援介面執行任務，不另造連線/資料儲存框架 |
| 具型別與業務輸入檢查 | 無效路徑、日期政策等在執行前明確失敗 |
| Retention 定義 | 欄位含義、單位、來源時間、partial/unknown 與 schema |
| README 與範例 | 讓新的同事或 agent 能理解、設定、執行與恢復 |
| 作者與 LICENSE | 明確使用權，不使用保留的 Bundle 身分冒充隨附程式 |
| 公開可重現測試 | 成功、失敗、邊界與不完整情況；使用假想資料 |
| 私人綁定 | 主機、憑證、路徑留在管理環境，不列入公開套件 |

使用目前 descriptor 0.3.0 與合適 runner。`python-recipe` 取得平台提供的 `Recipe`，可使用既有 session、services 與帳號政策；舊 `python-session` 有自己的契約，不能直接混用。離線報表選 `python-report`，不建立假的目標主機。

執行工具開放選擇，適合命令執行與 session 協調時優先 SSHScript；其他工具更合適則記錄原因與依賴。使用版本相符公開 skill，不從私人 library checkout 猜 API。

## 讓結果能被判讀與重用

固定結果狀態仍是 success/partial/failed/skipped/unsupported，自訂 assessment 描述檢查發現，不遮蓋執行、還原、retention 或內容失敗。保留 null、零、false 與已觀察空集合的差別。

Retention 保存資料定義，不嵌呈現模板。新可攜結構化資料可以使用 recipe 自帶的受支援 schema；不要為每個業務資料集改產品 registry。呈現用 consumer 或離線 report，通知/待辦用既有服務，避免 recipe 自建私有狀態系統。

對需指定執行帳號的受支援 recipe，將 `execution` 放在 exact-reference 設定，由平台取得與驗證；不要每支 recipe 重寫帳號選擇與提權重試。權限取得失敗，不默默改用其他帳號。

## 從靜態檢查到第一次實際驗證

在完整 recipe 已建立且私人設定已合併後：

```sh
python -B tools/opsfeast.py recipes show :backup/files/check/daily-backups --profile main --json
python -B tools/opsfeast.py check --profile main --json
```

以上完成靜態檢查。接著請 agent 用假想資料與本機測試確認邏輯：

可直接複製給 agent：

```text
請檢視我們正在製作的 recipe 與現有測試，使用假想資料驗證成功、失敗、缺值與邊界情況。執行已審查的本機測試，回報結果與限制，整理第一次主機驗證所需的帳號、權限與預期證據。這次不連線、不執行真實主機操作，也不啟用 consumer、排程或遞送。
```

確認第一次主機驗證的目標與操作範圍後，執行：

```sh
python -B tools/opsfeast.py recipes run :backup/files/check/daily-backups --profile main --host backup-example --json
```

檢視 raw、retention、consumer 與業務判讀，提供實際 saved paths 與重跑指令。需要啟用 consumer、排程或寄信時，將其具體效果納入對應授權，不從「製作 recipe」自動推導。

## 向 agent 要完整交付

> 把已審查流程整理成可重用 recipe。先讀能力地圖與 recipe skill，優先重用既有模組。完成 descriptor、程式、資料定義、設定、文件、假想測試與精確 rerun command。回報工具選擇、平台證據與限制。已知私人綁定放回實際 profile，不留成我必須另寫程式的作業；不擴大連線、刪除或對外遞送範圍。

**這一章完成後：**你的 recipe 可以由另一個新 agent 發現、審查、設定與重跑，且不依賴這一次聊天的隱藏知識。

正式參考：[Recipe skill](../../../skills/opsfeast-recipes/SKILL.md)、[製作指南](../../recipe-authoring.md)、[分類與位置](../../recipe-taxonomy.md)、[執行契約](../../recipe-execution.md)、[可攜資料契約](../../portable-contracts.md)。

## 延伸閱讀：保存報表與例行呼叫

### 保存可重複的呼叫方式

審查 recipe 與參數後，可以在授權範圍內保存本機 job：

```sh
python -B tools/opsfeast.py recipes jobs save backup-review feast/report/retention-summary --profile main --vars-file /absolute/path/to/selection.json
python -B tools/opsfeast.py recipes jobs show backup-review --profile main --json
```

Save 只寫私人 job 定義，不執行。之後授權重跑時：

```sh
python -B tools/opsfeast.py recipes jobs run backup-review --profile main --json
```

Job 固定 recipe 來源與內容指紋，程式改變就拒絕執行。輸入資料與私人 vars 檔可能改變，仍要檢視目前綁定與新來源 digest。Recipe 改變後，使用新的已審查 job 名稱，不要繞過內容漂移檢查。Job 可能含私人路徑與參數，不能納入公開 recipe bundle。


### 讓例行重複不必依賴模型

保存 job 不會建立排程。若要週期執行，應定義頻率、目標或輸入、控制端環境、副作用與失敗處理。明確授權的外部排程器可以呼叫固定、已審查的 job 指令。OpsFeast 目前沒有通用 job 排程器、pipeline/DAG 引擎或所有 job 自動通知。Inventory 排程是獨立的已實作功能。

自訂報表時，請 agent 重用 `context.retention.query/show`、已驗證成品處理與既有 runner。保留單位、來源時間、origin、部分或未知狀態，並宣告 renderer 依賴。基本表格不應依賴特定視覺化產品才能理解。保存報表程式、模板與選擇政策，讓例行產生重跑已審查工作。

可以這樣對 agent 說：

> 準備可重用的離線報表，結合選定備份與 inventory 紀錄。使用現有 report reader 與 artifact 介面，清楚保留來源時間戳、身分與涵蓋警告、單位。私人選擇在執行時綁定，提供假想範例與測試，並給我一個精確重跑指令。不要採集新資料或發布報表。

**理解檢核：**找到報表結果及已驗證成品。說明產生時間、供應報表的 observation 時間，以及保存 job 為何不等於授權未來執行。

正式參考：[recipe 操作介面](../../recipe-experience.md)、[retention 內容介面](../../retention.md)、[報表製作](../../recipe-authoring.md#report-recipes-and-reusable-visualization)、[報表分享](../../recipe-sharing.md#share-report-recipes-across-feasts)。

## 延伸閱讀：完整案例：每日備份檢查

我們用每日備份檢查，帶你從一句需求走到可重跑的 recipe、保存結果與整理待辦。範例使用假想主機與路徑，你可以先閱讀流程，再換成自己的環境逐步操作。

### 定義問題

兩個應用程式將帶日期的資料庫 dump 送到備份主機。我們想知道：截止時間之後，今天必要的普通檔案是否存在；哪些可辨識備份超過依檔名日期計算的保留天數；有哪些非預期項目需要檢視。

SSH 目標是**備份目的地主機** `backup-example`。`database-a` 與 `database-b` 是該主機備份設定的 subject，不是額外連線目標。操作只讀目錄中繼資料，不讀 dump 內容、不驗 SQL、不算 checksum、不證明到達時間、不還原資料庫，也不刪檔。依目前政策，零長度普通檔案仍算存在。

你可以這樣提出需求：

> 在 profile main，為 backup-example 上的 database-a、database-b 準備可重複使用的存在性檢查。使用保存的檔名與 Asia/Taipei 截止時間，將超過 90 個日曆天的檔案列為整理發現，非預期項目另外列出。保存證據與易讀結果。需要時只啟用已審查的本機備份政策，不刪檔、不寄信、不加入排程。沿用現有授權，只詢問缺少的實際路徑或政策。

Agent 先確認實際路徑與前置條件，檢視既有 recipe、consumer、設定，再辨識已審查操作。即使案例要求不寄信，任何 dispatch 前也必須考慮其他地方已設定的郵件路由。


### 準備完整可重用程式

隨附 `opsfeast.backup_check` 提供 `portable_files(identity)`，可建立完整的 profile 本地可攜 recipe，包含 scanner、validator、schema、entrypoint、文件、授權與選用 consumer 來源。依[正式建立程序](../../backup-file-checks.md#create-a-complete-portable-recipe)，使用真實作者資訊與新的已審查目的地。保留既有 recipe，不默默覆寫。

預期位置與 selector：

```text
<actual-profile-root>/recipes/backup/files/check/daily-backups/
:backup/files/check/daily-backups
```

控制端需要目前 OpsFeast API 與支援的 SSHScript 7.0.0；目標需 POSIX Python 3.8+。Scanner 宣告 Linux、FreeBSD、macOS 支援；使用 FreeBSD 時，請先在一台主機核對掃描結果，目前的原生驗證紀錄仍待補齊。私人設定留在接收端。可攜 entrypoint 攜帶領域程式，不依賴只有薄薄包裝的產品領域模組。


### 綁定實際目的地與政策

以下片段合併到既有 `hosts.backup-example` mapping 下，保留連線、帳號、群組與其他 recipe：

```yaml
recipes:
  ':backup/files/check/daily-backups':
    enabled: true
    vars:
      timezone: Asia/Taipei
      retention_days: 90
      max_entries: 10000
      target_python: python3
      backups:
        - name: database-a
          directory: /srv/example-backups/database-a
          patterns: ['dump-{date}.sql']
          ready_after: '01:00'
          grace_minutes: 5
        - name: database-b
          directory: /srv/example-backups/database-b
          patterns: ['{date}.sql', '{date}.data.tar.gz']
          ready_after: '02:00'
```

這些路徑是範例，不是自動探索提示或實際目標。每個 pattern 的檔名部分恰有一個 `{date}`，換成有效 `YYYY-MM-DD` 日期；可以包含安全的相對上層目錄。Age 依指定時區的今天與檔名日期相減，不依 mtime。Expired 是嚴格大於門檻：門檻 90 時，90 天不過期，91 天才過期。

每日截止時間加寬限時間之前，缺少預期檔案屬 pending；之後才可由完整掃描判定 missing。限制或目錄不可讀，會讓尚未看見的預期檔案保持 unknown，即使已找到其他檔案也一樣。Symlink、放錯位置或無法辨識項目，不當作預期普通檔案。需要清理時，先用保存清單準備具體清理方案，再決定要移除哪些檔案。

預設用登入帳號執行。若實際路徑需要其他帳號，請依[第 4 章](04-hosts-and-access.md)與[結果及帳號](../../recipe-results-and-accounts.md)審查、設定精確 reference 執行政策。不要自行增加 sudo 重試迴圈，也不要假定一定需要 root。


### 檢視後執行一次

程式與設定準備好後：

```sh
python -B tools/opsfeast.py check --profile main --json
python -B tools/opsfeast.py recipes show :backup/files/check/daily-backups --profile main --json
python -B tools/opsfeast.py consumers list --recipe :backup/files/check/daily-backups --profile main --json
```

這些是本機檢視。先審查既有下游 consumer、服務路由與其效果。單次目標執行、儲存及下游範圍已授權後：

```sh
python -B tools/opsfeast.py recipes run :backup/files/check/daily-backups --profile main --host backup-example --timeout 30 --json
```

指令會連線到備份主機與必要跳板、掃描中繼資料、保存結果，再嘗試 retention 與已啟用下游處理。明確 `--host` 對此目標覆蓋主機、來源、recipe 啟用門檻，但不授予權限或停用驗證。

保存回傳的 batch、result、record ID 與實際路徑。檢查執行身分與還原、各組掃描完整度、預期檔案存在性、過期及非預期清單、retention 與內容/服務回執。若連線失敗，沒有合格 retained data，不會自動變成缺少備份的事件。


### 練習三種假想結果

| 證據 | 判讀 | 下一步 |
| --- | --- | --- |
| 預期檔案全部存在、完整掃描、有一個 91 天檔案 | `BACKUPS OK · CLEANUP NEEDED`；存在性健康，整理需檢視 | 讀保存的過期清單，考慮 todo，不刪檔 |
| 截止時間後缺少必要檔案、完整掃描 | `BACKUPS MISSING`；部分完成，發現當日缺檔 | 依另外的範圍調查來源或傳送，保留證據 |
| 達到 entry limit、部分預期檔案未看見 | `CHECK INCOMPLETE`；不存在與否未知，數量可能只是下界 | 檢視限制或權限，適當時授權有限重查 |

截止前也可能是 `BACKUPS PENDING`。執行成功但有整理警告，是刻意的設計。自訂標籤不能遮蓋儲存、身分、清理或發布失敗。Dump 看來存在，仍需要其他操作才能證明內容完整或可還原。


### 加入已審查的政策 consumer

審查完成、且在明確本機啟用授權內，合併到既有 `feast.yaml`：

```yaml
consumers:
  backup-check:
    source: builtin:backup-check
    enabled: true
```

每個 condition owner 使用單一政策實作。套件中的本機副本是另一個可選來源，不應與原政策同時競爭執行。啟用後可能處理先前累積事件；實際 dispatch 會執行程式，也可能嘗試已設定的服務遞送。特別是郵件不在範圍內時，先檢視服務設定。

政策依主機、精確 reference 與備份組別，協調最新合格證據：

- 當日缺檔產生 error 通知。
- 過期檔案或非預期項目產生 warning todo。
- 不完整掃描產生 error 通知，不能錯誤地驗證問題已清除。

重複發現沿用同一輪事件。驗證清除後解決，再次發生可建立新一輪。歷史 replay 不能製造新的即時事件。建立 todo 不會刪檔或安排清理排程。


### 閱讀結果並記錄人工工作

```sh
python -B tools/opsfeast.py observation latest --profile main --json
python -B tools/opsfeast.py observation result RESULT_ID --detail --profile main --json
python -B tools/opsfeast.py retention show RECORD_ID --profile main --json
python -B tools/opsfeast.py services list --kind todo --host backup-example --profile main --json
```

從主機產生的 records 索引開啟目前備份頁面，再跟到歷史來源報告。目前頁面提供簡短預覽，歷史紀錄保留完整已存清單與政策。說明該次 observation 時，不要拿今天重新計算舊檔案年齡。

處理整理 todo 時，先讀目前 revision，再用[revision 檢查更新流程](07-consumers-and-vault.md#延伸閱讀consumer通知與待辦)指派人員或記錄審閱。若提出清理方案，應另外列出精確候選檔案、證據新舊、排除項目、預期效果與復原。存在性檢查及其 todo 都不授權移除檔案。


### 復原與交付

掃描成功而發布失敗時，先看回執，修復內容階段，不必再掃描。Retention 失敗但有效 raw 存在時，先驗證 replay 再實際 ingest，仍須考慮下游效果。掃描本身不完整，重建無法補出缺少的目錄證據；新的有限採集仍需相應授權。

完成後，請 agent 提供實際 recipe 與設定位置、重跑指令、這次結果連結，以及需要補查的項目。

可直接複製給 agent：

```text
請整理剛完成工作的交付資訊：實際 recipe 與設定位置、精確重跑指令、已保存結果的連結，以及尚未驗證或需要補查的項目。只使用已有成果；沒有執行或證據的部分如實註明，不為整理回報而重新採集，也不對外傳送。
```

移植到其他 Feast 時，打包完整可攜來源，在接收端綁定私人路徑。若同事也需要這次資料，再選擇匯出 observation 或 retention，確認內容與接收者後傳送。

**理解檢核：**說明「預期檔案全在」、「掃描完整」、「需要清理」、「todo 完成」、「資料庫還原驗證通過」為什麼是五個不同主張。追蹤一個發現如何從 raw 結果走到 retention、政策與服務物件。

進一步閱讀：[備份流程與限制](../../backup-file-checks.md)、[模組](../../../opsfeast/backup_check.py)、[公開備份測試](../../../tests/test_backup_check.py)、[consumer](../../../consumers/backup-check/README.md)、[服務](../../services.md)、[可攜](../../portability.md)。準備用於新環境時，依[備份指南的驗證說明](../../backup-file-checks.md#verification)先做小範圍試跑；如果還要寄信，再依[adapter 指南](../../service-adapters.md)確認郵件設定與實際遞送。

*Last modified: 2026-10-26 23:35:09*
