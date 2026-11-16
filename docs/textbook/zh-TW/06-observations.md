# 6. Observation：我的第一份執行證據

[全書首頁](README.md) · 上一章：[第一個 recipe](05-recipes-and-inventory.md) · 下一章：[Consumer 與 Vault](07-consumers-and-vault.md)

## Observation 是什麼，為什麼需要它

Observation 是一次操作或測量留下的觀察證據，保留來源、時間、目標、狀態與可用結果。它讓你能回頭回答「哪一台、哪個 recipe、什麼時候、用誰的身分做了什麼、哪些完成、哪些未知」，不必為了看結果再連線一次。

OpsFeast 有兩種相關入口：一個 **observation run** 記錄整批選擇與各主機結果；個別主機的 **raw result** 保存該次詳細執行資料。單台執行也可以有一個批次。`observation` 瀏覽批次，`observation result` 瀏覽個別主機結果。它們的 ID 不應混用。

另外，retention 是從合格 observation 取得的結構化資料。Raw、批次與 retention 彼此連結，但不是每個失敗都一定有完整 raw 或 retained record。連線或前置階段失敗，可能只有批次目標證據。

## 找到我的第一個 observation

上一章的採集輸出通常包含 `observation_run_id`、各主機結果位置與相關回執。先保留這次實際回傳的 ID，不要只記住「latest」，因為之後另一個人或排程可能產生新批次。

```sh
python -B tools/opsfeast.py observation latest --profile main --json
```

這是讀既有最新批次，不重新連線、重跑、修復或 dispatch。剛跑完第一個 recipe 且沒有其他新執行時，應可找到那次 batch；如果 latest 已變，使用保存的批次 ID：

```sh
python -B tools/opsfeast.py observation OBSERVATION_ID --profile main --json
```

將 `OBSERVATION_ID` 換成實際 observation run ID。確認目標、recipe、來源時間、完整目標數、採集狀態與指令結果。歷史資料沒有記錄的欄位應是未記錄，不能自行猜補。

## 查看有哪些 observation

```sh
python -B tools/opsfeast.py observation --profile main --json
python -B tools/opsfeast.py observation latest --status failed partial --profile main --json
```

第一行列批次歷史，第二行顯示最新批次符合條件的主機；篩選包含 retention/content 等呈現結果，採集狀態仍另行保存。篩選後沒有主機，不等於所有歷史都沒有失敗。

查看某台主機的已存結果：

```sh
python -B tools/opsfeast.py observation result --host server-01 --profile main --json
python -B tools/opsfeast.py observation result RESULT_ID --profile main --json
python -B tools/opsfeast.py observation result RESULT_ID --detail --profile main --json
python -B tools/opsfeast.py observation result RESULT_ID --raw --profile main
```

先從清單取得 `RESULT_ID`，再看聚焦診斷、完整 detail 或原始 JSON。短 ID 方便在同一管理根目錄查找，長期自動化宜保存完整 ID。離線報表歷史使用 `recipes results`，不與主機 observation 混用。

## 如何閱讀這次結果

| 證據 | 問題 |
| --- | --- |
| 執行狀態 | 是 success、partial、failed、skipped 還是 unsupported？ |
| 身分與還原 | 實際採集帳號/UID 是什麼？SSH 登入與執行者是否不同？清理是否確認？ |
| Recipe 判讀 | 掃描發現什麼？成功執行仍可能有 warning 或不健康狀態 |
| Retention 回執 | 結構化資料是否成功保存？ |
| Content/consumer 回執 | Vault 或其他 consumer 是否完成？ |
| 來源與採樣時間 | 這些值是哪次、何時量到？不是頁面重建時間 |

先看操作是否完成，再讀 recipe 的檢查發現。例如掃描順利完成，仍可能找到需要處理的檔案。讀取歷史指令的 exit 0 表示讀取成功，該次執行狀態要看保存的結果。最新 inventory 可組合不同採樣時間的屬性；最新測量失敗時，該欄位會保留缺口，方便你決定是否重查。

## 檔案在哪裡

原始主機結果在該 profile 的 `observations/`，結構化資料在 `retention/`，易讀歷史頁在維運 `vault/` 下。檔名與歸屬以回傳路徑、索引與 publisher 為準，不自己用時間拼檔案。

無儲存的 `inventory query` 不建立 observation；離線報表、replay、頁面重建也不是新的主機採集批次。舊檔案時間接近不能當成同一批次證據。

> 請只讀 profile main 中我剛執行的 observation，使用我提供的批次 ID。說明執行、採集身分與還原、retention、Vault 發布各自結果，列出原始結果與可讀入口。不要重跑主機或用後來的 latest 代替這一次。

**這一章完成後：**你能列出批次，找到第一個 observation 與主機 result，並說明哪些成功、哪些仍是部分或未知。

正式參考：[觀察批次](../../observation-runs.md)、[CLI 歷史與診斷](../../cli.md)、[資料與 Vault 延伸](07-consumers-and-vault.md#延伸閱讀閱讀資料與使用維運-vault)。

## 延伸閱讀：查詢與修復保留資料

### 查詢權威保留資料

以下讀取保存資料，不連線或更新測量：

```sh
python -B tools/opsfeast.py retention list --profile main --json
python -B tools/opsfeast.py retention show RECORD_ID --profile main --json
```

選用 list 回傳的真實 record ID。組合資料前，先讀資料集定義、單位、原始來源時間、origin、實際帳號、品質與涵蓋證據。可重用 Python 組合使用 Core `profile.retention.query/show`；報表 recipe 使用 `context.retention.query/show`。不要把 Markdown 表格當資料庫解析，也不要直接讀 SQLite 重建現有公開介面。

匯入 retention 保留來源限定的身分，與本機主機資料獨立。比較或組合時，請以保存的來源身分區分同名主機。保留資料即使沒有明確憑證欄位，也可能敏感；選取匯出分享前應先審查內容。


### 修復真正失敗的階段

如果 retention 已存在，只需更新 Markdown，可以在授權範圍內執行本機重建：

```sh
python -B tools/opsfeast.py vault inspect --profile main --json
python -B tools/opsfeast.py vault rebuild --profile main --json
```

Inspect 讀取歸屬與狀態；rebuild 從保存資料重寫受管理內容，不重新採集，也不修改 retention 或 run 證據。它無法還原從未擷取的輸出，不會確認 consumer 事件回執，也不執行任意自訂 consumer。服務呈現有自己的 dispatch 流程，移轉檢視則使用 `transfer rebuild`。

若 raw 證據存在而 retention 失敗，先離線驗證指定 raw：

```sh
python -B tools/opsfeast.py retention ingest /absolute/path/to/selected-raw.json --profile main --dry-run --json
```

Dry-run 只驗證，不寫入或 dispatch。實際 ingest 寫入 retention，之後可能執行已啟用 consumer 與設定中的服務效果。移除 `--dry-run` 前，先確認下游範圍。Replay 不重新連線、不執行候選 recipe 程式，並保留歷史分類；它不更新測量，也不能把舊證據當成建立目前事件的授權。

`retention rebuild` 修復 retention 衍生檢視，不重新採集。受保護的 write/unknown 操作證據，不能靠修改目前 descriptor 變成可刪資料。破壞性移除與空間回收應走已審查的[移轉與封存流程](10-sharing-recipes.md#延伸閱讀製作分享移轉與封存)。

可以這樣對 agent 說：

> 閱讀這台主機保存的紀錄，說明新舊、單位、涵蓋與身分警告。如果只有受管理 Vault 頁面過時，依既有授權在本機重建。不要重新連線、改寫歷史或覆寫人工筆記。

**理解檢核：**找到一個易讀目前頁面，以及供應它的歷史紀錄。辨認測得的零、已觀察空集合與未知值，並將自己的筆記保存在受管理輸出之外。

正式參考：[result-data skill](../../../skills/opsfeast-result-data/SKILL.md)、[retention](../../retention.md)、[結果資料](../../result-data.md)、[Vault](../../host-vault.md)、[replay](../../retention-replay.md)。

## 延伸閱讀：報表與重複工作

離線報表讀取選定的既有證據，產生本機成品。它讓你不必重新連線，也能組合資料、解釋發現並建立可重複使用的呈現。報表的來源時間，仍是輸入資料原本的時間。

### 讓 PM 探索答案並產生報表

OpsFeast 的使用者包含系統管理者與相關 PM（產品經理）。PM 不必每次先請維運人員重新查一輪，才能開始理解系統狀況；在已獲准的資料範圍內，可以請自己的 agent 讀取既有證據、追問原因、整理報表，把真正缺少的測量交回維運確認。

例如在 CVE 應變中，PM 可以問：

> 請只用已保存的資料，整理本次事件的受檢主機、可能關聯產品、需優先確認的原因、原始採樣時間與資料缺口。業務/產品對照若未提供，明說未知並請我補充，不猜測。先產生本機報表，不連線、不修補、不寄送。

Agent 應分開呈現已知事實、根據指定規則的判讀與尚待補證據。已存資料只能回答其涵蓋的問題；系統有 PHP 套件，不等於已確認實際 Web runtime 或修補狀態。報表生成時間不能冒充採樣時間。

若這份報表會反覆使用，將確認的資料選擇、業務對照、判讀規則與呈現保存成 recipe/設定/模板，下次直接重跑，讓 Token 用於新問題與例外。隨附 retention-summary 提供資料閱讀與基本輸出；需要 CVE 規則或產品分類時，讓 agent 補成已審查的報表程式，私人對照資料在執行時綁定。

PM、管理者與職務代理人可以選用不同 agent，但需有實際資料存取與執行能力。團隊用現有檔案與帳號管理資料存取，交接時提供共同的設定、契約與工作成果。交接與分享分別見 [profile 章](08-profiles.md#讓職務代理人或另一個-agent-接手)與[分享章](10-sharing-recipes.md#recipeobservationretention-各自分享什麼)。


### 從 retained observation 產生報表

先閱讀隨附的 [retention-summary recipe](../../../recipes/feast/report/retention-summary/README.md)。在本機報表授權範圍內：

```sh
python -B tools/opsfeast.py recipes show feast/report/retention-summary --profile main --json
python -B tools/opsfeast.py recipes run feast/report/retention-summary --profile main --json
```

第一行讀取中繼資料，第二行執行已審查的控制端 Python，寫入新的報表結果與成品。這個隨附 recipe 不使用連線、Session、網路服務或模型。任意第三方報表 Python 沒有通用沙箱，需要另外審查。

具型別的選擇變數包含標題、recipe reference 與主機 ID。空選擇陣列會選取範圍內全部 retention 資料；若只需部分資料，應明確指定。私人 JSON vars 檔可以保存選擇：

```json
{
  "title": "Backup evidence review",
  "recipes": [":backup/files/check/daily-backups"],
  "hosts": ["backup-example"]
}
```

將選擇保存在本機後，使用它的實際路徑：

```sh
python -B tools/opsfeast.py recipes run feast/report/retention-summary --profile main --vars-file /absolute/path/to/selection.json --json
```

Recipe 在這次 run 的 artifacts 目錄寫入 `retention.md` 與 `retention.html`。輸出保留來源 envelope、欄位狀態與警告。若報表成功但沒有紀錄，先查看選定 profile、recipe、主機與既有 retention，確認你選到了需要的資料。


### 取得驗證過的成品

```sh
python -B tools/opsfeast.py recipes results list --profile main --json
python -B tools/opsfeast.py recipes results show RESULT_ID --profile main --json
python -B tools/opsfeast.py recipes artifact RESULT_ID retention.html --profile main
```

使用執行或清單回傳的報表 result ID。Artifact 查詢先驗證宣告路徑、大小與 digest，再回傳本機路徑；不發布、傳送或啟動檢視器。報表成功代表產生成功，內容仍可能正確描述失敗或過時的來源觀察。

若要整理原始結果，隨附 `feast/report/execution-summary` 可用 `--input` 接收明確選定的 JSON。這與 retention-summary 的 retained-data reader 不同。混合輸入前先讀所選 recipe 契約。主機或群組選擇參數屬於維運 recipe，不適用離線報表。

## 延伸閱讀：依證據排除故障

從原本 profile 與保存的執行 ID 開始，先找出第一個失敗階段，再決定是否重跑。資料或內容失敗通常有本機復原方法；反覆採集可能模糊原問題，也造成不必要操作。

### 找出階段

| 現象 | 先檢查 | 適當處理 |
| --- | --- | --- |
| 環境錯誤或不存在 | `profiles`、選定 `--profile`、實際根目錄與 locator | 修正選擇或登記，保留資料 |
| 設定遭拒 | `check` 錯誤與定義 YAML | 修正特定欄位或 reference，重做本機驗證 |
| SSH 失敗 | 保存的 hop、認證、指令證據與實際目標 | 在範圍內診斷地址、信任與選定認證 |
| 登入成功但執行身分失敗 | 要求的帳號政策、actor/UID、還原證據 | 檢視允許方法，不默默更換帳號或傳輸方式 |
| Recipe 不支援或前置檢查失敗 | Descriptor、精確來源、目標平台、依賴與具型別輸入 | 選支援實作或修復具體前置條件 |
| 部分測量 | 個別 query/probe 狀態、原因、擷取限制、實際範圍 | 保留未知，必要且已授權才重新採集 |
| Raw 存在但 retention 失敗 | 保存 raw、snapshot/schema、retention 回執 | Dry-run 指定 replay，不重連就修復資料流程 |
| 資料存在但頁面缺少或過時 | Retained record、發布歸屬、consumer 回執 | 重建適當內容，或重試已審查 consumer |
| 有通知但沒收到信 | 路由、遞送回執、靜音/解決狀態、adapter 結果 | 將遞送與 condition、採集分開診斷 |
| 匯入或封存中斷 | 計畫、已驗證套件、持久化回執 | 用文件化 recovery/resume，保留復原成品 |


### 先讀保存證據

```sh
python -B tools/opsfeast.py observation latest --status failed partial --profile main --json
python -B tools/opsfeast.py observation result RESULT_ID --profile main --json
python -B tools/opsfeast.py observation result RESULT_ID --detail --profile main --json
python -B tools/opsfeast.py consumers inspect --profile main --json
python -B tools/opsfeast.py services deliveries --profile main --json
```

這些讀取不重試或重新連線。若最近批次篩選後清單為空，先確認你要找的是不是更早的一次執行。舊批次請用 `observation` 與 CLI 明確選擇。目標在 raw 儲存前失敗時，讀批次證據，並明說主機細節沒有保存。

讀歷史的指令不等於重跑；exit code 零可能只表示成功讀出失敗歷史。採集狀態、指令執行結果與 retention、內容、服務結果都應分開。


### 三個本機復原例子

**案例 A：備份 retention 完整，Vault 發布失敗。**先確認 record 與內容錯誤。授權的 `vault rebuild` 從資料重發隨附受管理檢視，不重新掃描。Consumer 重試可以更新其回執，但也可能 dispatch 服務。選擇符合失敗階段與授權效果的復原方法。

**案例 B：Raw 有效，但保存的 retention 定義不相容。**使用 `retention ingest ... --dry-run`，查看精確相容性錯誤。文件所列 snapshot/digest 情況可使用已審查 `--recipe-dir` 覆寫，但不能把舊 write/unknown 操作重標成 read。實際 ingest 可能執行已啟用下游程式。保留原始 raw，不編輯證據強迫通過。

**案例 C：封存套件驗證後中斷。**檢查 `transfer receipts` 與相符封存套件。`transfer resume ARCHIVE_RECEIPT_ID` 驗證剩餘來源指紋，再接續紀錄中的清理。套件遺失或變動時，停止後續清理並先解決復原問題，不能刪掉唯一已驗證套件。


### 要求最小的下一步

> 只從保存證據診斷 profile main 的 RESULT_ID。指出第一個失敗階段、已成功部分與未知之處。準備最小具體復原方案，說明效果與預期證據。沿用既有授權；只有需要新目標存取、權限、刪除、對外遞送或重要決策時才補問。

如果對外遞送在範圍內、狀態卻是 unknown，選 `--retry-unknown` 前應說明可能重複。如果 todo 被手動標完成，但不利 condition 仍持續，應查證據與政策，不能刪物件或虛構已清除 observation。如果失敗源於缺少產品介面，記錄缺口並優先做可重用修正，避免另造私人平行實作。

**理解檢核：**選一個歷史失敗，找出最早失敗階段、最具體已保存原因、缺少證據，以及不牽涉其他無關操作的復原方式。

正式參考：[CLI 診斷](../../cli.md#diagnose-a-saved-failure)、[主機診斷](../../host-diagnostics.md)、[replay](../../retention-replay.md)、[consumers](../../retention-consumers.md)、[服務遞送](../../service-adapters.md)、[移轉復原](../../portability.md)。

*Last modified: 2026-10-26 16:26:48*
