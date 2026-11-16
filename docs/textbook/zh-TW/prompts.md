# Prompt 參考

[全書首頁](README.md) · [指令速查](reference.md)

你可以直接複製本頁 prompt，交給自己的 agent。請從真實 OpsFeast 專案使用，agent 應確認工具 checkout 與管理資料的區別，提供實際路徑與選定環境，沿用已有授權。需要輸入機密時，在本機私人設定處理。

## 第一次安裝

使用[第 2 章的安裝 prompt](02-installation.md#步驟-2貼上安裝需求請-agent-檢查環境)。它先授權 clone、閱讀與唯讀前置檢查，再由 agent 提出可代為完成的本機方案。你同意方案後直接完成，無須再次授權相同工作。安裝不含主機操作。

## 安裝驗收與盤點

> 以目前選定 Python 唯讀盤點這份 OpsFeast。報告 checkout、VERSION/commit、interpreter、SSHScript import/distribution/受信任來源與其他依賴版本、完整 skill 狀態、profiles、實際管理根目錄及 hosts.yaml。執行本機環境與指定 profile 的 check，解釋實際存在目錄與尚未產生的正常目錄。不印憑證，不 init、不安裝、不連線或執行 recipe。

對照[安裝驗收章](03-verify-installation.md)，不要因為自己第一次看到這個目錄，就把接手環境重新初始化。

## 第一台主機與第一個 recipe

> 在 profile main，保留現有設定，幫我設定一台 server-01，包含我提供的 via 跳板。只詢問缺少的地址、登入帳號與認證來源，讓我在本機輸入憑證。先 check，不自行連線；給我下一步實際連線測試與 inventory 方案，說明各自效果與可能的權限。

> 我授權對已設定的 server-01 與必要跳板做 hostname/date 連線測試。請執行並說明每跳、目標及清理結果，不做 su/sudo 或 recipe。

> 我授權一次 system/inventory/overview，目標是 profile main 的 server-01，包含已說明的有限帳號政策、原始與 retention 儲存，以及已審查下游效果。完成後分別回報採集、身分/還原、retention 與內容更新，提供這次 observation ID、result ID 與 Vault 歷史入口。不要加入持續排程或新遞送設定。

使用執行 prompt 前，先和 agent 確認 recipe 的操作內容與下游效果；已有郵件路由時，也將是否遞送說清楚。

## OpsFeast release 有新版時

下面授權**這一次**適用更新，不建立自動追蹤或排程。若你只想查有沒有新版，將「我授權…」改成「先唯讀比較與提出方案，不套用更新」。完整正式來源在 [README 更新 prompt](../../../README.md#update-opsfeast-and-refresh-your-agents-skills)。

> 請檢查這個專案使用的既有 OpsFeast，並替我套用適用更新。我授權從官方 https://github.com/iapyeh/opsfeast.git fetch、對實際工具 checkout 的既有 upstream 執行 git pull --ff-only，以及依支援的既有整合方式更新未修改、來源可追溯的官方 agent skill 副本與完整 references/source records。例行步驟不必重問。
>
> 先區分管理資料與工具 checkout，閱讀現有 AGENTS.md、存在時的 AGENTS.local.md、README、skills 索引、能力地圖、docs/skill-updates.md 與 agent 指引，確認 repository 身分、實際分支與 upstream，記錄原 VERSION/commit。若只有資料目錄，使用已提供工具路徑，否則詢問；不要在資料目錄建立 Git。
>
> 核對官方最新穩定 release 的 notes、tag/目標 commit 與相容性，並比較 fetched upstream 的完整適用差異。沒有正式 release 時，明確區分 branch update；查詢失敗不是「沒有新版」。報告 upstream 是否包含超過 release 的提交，或無法取得該 release，不默默改更新管道。已包含適用版本且沒有新提交就略過 pull。
>
> 保留私人資料、憑證、人類筆記、自製 skills、設定與歷史。遇到 tracked/staged 修改、碰撞的未追蹤檔、detached HEAD、分歧或 checkout 限制，具體回報，不自行 stash/reset/clean、換分支、合併本機工作或覆寫。
>
> 更新後，重新閱讀安裝版本目前的所有必要 object schema 與資料契約，包括 hosts.yaml 指南，依 docs/skill-updates.md 的強制重讀清單執行。不要因為記得舊版就跳過。學習更新的技能、相容性與使用範例。支援時重新載入已更新官方 skill；有本機修改、來源/loader 衝突或需要新整合方式時，保留檔案，只詢問尚未解決的選擇。不能重新載入時可直接讀 Markdown，明說限制，不宣稱其他對話已更新。
>
> 使用既有選定 Python 做適用本機檢查。這次不授權安裝/升級套件、重建環境、資料 migration、連主機、測 sudo、執行維運 recipe、commit/push 或排程。以繁體中文回報 update/no-update/blocked、release 與 branch 證據、前後版號/commit、變更與必要動作、實際學到與載入的 skills、檢查結果和限制，不暴露機密。

這個 prompt 不授權繞過分支規則、擴大套件更新或自動執行主機驗證。若具體依賴修復另有既存授權，agent 應沿用；否則準備實際方案。

## SSHScript release 有新版時

OpsFeast 要求套件、來源核對、完整 skill 與 guard 一起相容，不能只因 PyPI 出現更高版號就升級。下面授權目前環境的**受支援**套件與 skill 更新，不改 OpsFeast guard 或其他環境。正式程序在 [SSHScript 更新指南](../../skill-updates.md#update-sshscript-with-one-prompt)。

> 請將這份 OpsFeast 環境更新到其受信任 checkout 支援的最新穩定 SSHScript，並學習相符的完整官方 skill。遵循 docs/skill-updates.md 的「Update SSHScript with one prompt」。我授權本次本機 package/skill 更新、候選下載、備份與不含憑證的本機檢查，不必再問相同例行授權。
>
> 先核對實際選定 interpreter、SSHScript import/distribution/來源、OpsFeast 精確需求與 runtime guard、官方 release、完整 skill 的版本與 provenance。若官方有更高但 OpsFeast 不支援的版本，具體說明缺少的相容性，保留現況，不繞過 guard、不自行 pull OpsFeast，也不改 library 原始碼。
>
> 保留私人設定、其他環境、既有使用者修改與 skill 副本；依程序準備完整候選、檢查 loader/來源衝突、保存備份，只在已核對的支援範圍內套用。學習版本相符的 Agent Guide、API、migration 與任務參考，檢查自製 recipe 是否使用已移除介面。不能證明來源或遇到實質衝突時，先回報缺口與待選擇項目。
>
> 完成後用同一 interpreter 驗證套件/skill 一致與適用的無憑證本機檢查。以繁體中文回報前後版本、來源、實際閱讀/更新/載入的內容、學到的能力、相容性動作、備份與證據位置、限制。不連線主機、不測 su/sudo、不執行遠端 recipe、不更改其他環境，也不新增排程或 commit/push。

套件與 skill 更新完成後，可依需要選一台主機做連線或採集驗證，並明確指定這次要做的操作。

## 保存成果與日後修改

> 將這次確認的做法保存成可重用 recipe/報表、私人設定、文件與測試。提供實際位置、rerun command、這次 observation/retention 與待補查項目。整理一份接手說明，讓我的同事能用自己的 agent 閱讀並重跑。只處理目前已確認的範圍，新的對外發布或持續操作請先列成具體方案。

保存完成後，先用實際 rerun command 確認流程，再請同事依文件閱讀與操作。接手者能找到設定、知道結果在哪裡，就能沿用這次成果。

*Last modified: 2026-10-26 18:12:37*
