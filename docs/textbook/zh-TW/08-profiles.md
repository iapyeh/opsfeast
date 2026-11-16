# 8. Profile：管理多個環境

[全書首頁](README.md) · 上一章：[Consumer 與 Vault](07-consumers-and-vault.md) · 下一章：[製作 recipe](09-authoring-recipes.md)

## Profile 是什麼，為什麼需要它

入門時我們一直用 `main`。Profile 是登記名稱，指向一份管理根目錄；那裡有自己的主機、設定、歷史、retention 與維運 Vault。你可以用不同 profile 分開測試環境、團隊或不同管理範圍。

整份工具 checkout 是 instance，一個 instance 可登記多個 profile。`feasts/` 通常只是容器；profile 也可以指向外部路徑，並不強迫使用固定父目錄。改 profile 名稱或移動管理根目錄，不等於改 retention namespace 或重寫主機身分。

## 查看與單次選擇

```sh
python -B tools/opsfeast.py profiles
python -B tools/opsfeast.py check --profile main --json
```

第一行唯讀列出可用性與預設。`--profile main` 只選這次，不改其他人的預設。管理根目錄缺少或不合法時應失敗，不自動找另一份。支援的命令也可用 `--root /absolute/path` 直接選既有資料；不能同時指定 root 與 profile。

## 變更預設 profile

```sh
python -B tools/opsfeast.py use lab
```

這會寫登記檔的預設選擇，不搬資料也不連線。之後省略 `--profile` 的命令將使用 lab。要回到 main：

```sh
python -B tools/opsfeast.py use main
```

共享操作或 agent 自動化優先明確 `--profile`，避免別人改預設後跑錯環境。

## 開新的 profile

以下是授權本機建立新環境的例子：

```sh
python -B tools/opsfeast.py init lab --json
python -B tools/opsfeast.py check --profile lab --json
```

通常建立 `feasts/lab/`、登記 lab、初始化自己的設定與資料儲存。已有登記名稱時重用其根目錄，不能靠同名 init 另建覆寫。第一個登記成為預設，後續新增保留既有預設。這不複製 main 的憑證，也不授權對 lab 主機連線。

## Attach 已有管理目錄

同事交付或先前已存在的管理目錄，應先盤點並驗證，再依授權登記：

```sh
python -B tools/opsfeast.py attach /absolute/path/to/existing-feast --profile team
python -B tools/opsfeast.py check --profile team --json
```

Attach 修改此安裝的登記，保留來源目錄；不重建骨架、不建立新副本、不把收到資料視為新觀察。重複根目錄、名稱衝突與無效環境會失敗。缺少工具或依賴時先說明，不用 init「修復」接手資料。

## Detach 只移除登記

```sh
python -B tools/opsfeast.py detach team
```

保留所有檔案，不刪管理目錄、retention、憑證或筆記。`main` 受保護不能 detach。移除目前預設的非 main profile 時，要求存在可用、已登記的 main 並切回；不符合條件就保持原狀。

Detach 不會自動移除原本已用絕對 root 安裝的 cron。封存、刪資料、搬移根目錄與停止排程是各自不同的操作；先檢視仍指向該根目錄的排程與工作，不能以登記已移除推論不會再採集。

## 交接時的身分問題

真正搬移 instance 時，依 Core relocate 流程保留 UUID；複製一份獨立 checkout 則需要新的 installation UUID。不要在不了解來源的情況下重新初始化或換 namespace。原始 observation 的來源與主機歷史也不因新登記名稱而自動合併。

> 請唯讀盤點這個既有 Feast，指出工具 checkout、管理根目錄、現有 profiles、身分與路徑缺口。不 init、不連線、不改預設。若只需讓這份資料可選用，準備 attach 方案，說明會修改哪一份登記檔以及哪些資料保留。

## 讓職務代理人或另一個 agent 接手

交接的重點，是讓接手者知道管理目標、真實資料位置、既有 recipe、最近 observation、資料涵蓋與尚待處理事項。Recipe 說明方法，observation/retention 說明既有證據，人工筆記補充業務背景。這些資料應足以讓新的 agent 開始了解環境，不依賴原操作者的私人聊天。

接手者可以使用 Codex、Antigravity 或其他有必要檔案/指令能力的 agent。請明確閱讀實際 checkout 的指引與完整任務文件；各產品的 skill 自動載入與權限機制不同，不能假定搬過來就已全部啟用。先唯讀確認設定與來源，再依新使用者自己的授權進行操作。

> 我是這個環境的職務代理人。請先閱讀已保存的文件、recipe、最近 observation、retention 與人工筆記，說明目前系統狀態、哪些證據過時、尚待確認或處理的項目，及下一個可重跑工作。不重新初始化、不直接繼承前一位同事的主機操作權限，不把缺資料當成正常。

如果只是共用做法或證據，可選擇分享 recipe、observation 或 retention；完整交接則要一併整理管理設定、資料身分、私人資料存取與一致備份。Vault 頁面適合快速了解現況，操作與歷史仍由管理根目錄中的設定和資料支援。

**這一章完成後：**你能區分 init、attach、use、detach，並知道單次 `--profile` 的作用。

正式參考：[Profiles](../../profiles.md)、[身分與 Core](../../core-api.md)、[接手環境](../../first-use.md#take-over-a-colleagues-existing-feast)。

## 延伸閱讀：身分、時間與呈現

### 區分身分、時間與呈現

穩定的邏輯主機可以在重裝系統或更換地址後延續。觀察到的硬體與帳號識別值提供證據，但不自動證明實體設備連續性。組合資料時，保留 namespace、主機 ID、來源 instance/profile、recipe 來源與實際採集身分。匯入的來源即使主機名稱相同，也仍保持獨立。

Observation 時間、各屬性採樣時間、匯入時間與報表產生時間，代表不同事件。剛產生的頁面仍可能包含舊樣本或新舊混合的樣本。重建檢視不會讓樣本變新。缺值、零、false 與確實觀察到的空集合，也各有不同含義。

**理解檢核：**找出選定 profile 的原始結果、權威保留資料、產生頁面與人工筆記。若資料存在但頁面不存在，說明你會修復哪個階段。

正式參考：[Core 與 instance 身分](../../core-api.md)、[profiles](../../profiles.md)、[retention](../../retention.md)、[observation runs](../../observation-runs.md)、[Vault 輸出歸屬](../../host-vault.md)、[服務](../../services.md)。

*Last modified: 2026-10-26 16:20:38*
