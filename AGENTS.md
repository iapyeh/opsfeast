# SSHScript Ops：以外部使用者角度驗證 SSHScript 文件

使用者要求本專案作為 SSHScript 公開 AI agent 文件與 skill 的實際使用測試。
後續所有 SSHScript API 選擇、行為說明與使用技巧，必須重新從下列公開來源取得證據。

## 唯一的 SSHScript 學習來源

- 入口：<https://iapyeh.github.io/sshscript/v3a/ai-agents/>
- 可閱讀入口連結的 Agent Guide、canonical API guide、版本政策、API 參考、安全與操作文件，以及完整 SSHScript skill bundle。
- 公開 repository：<https://github.com/iapyeh/sshscript>。使用公開文件、範例、測試或原始碼時，記錄分支／tag／commit 與來源 URL，並優先依 AI agent 入口的閱讀順序進行。
- 不以本機 SSHScript 的 src、working_branch、git、gh-pages、其他私人 checkout、過往聊天／記憶或先前實測補足 SSHScript 知識；也不額外使用 Paramiko 等外部文件作為學習來源。若需要底層資訊，先查 SSHScript 公開 repository 是否提供。
- 可以閱讀及修改本 Ops 專案、使用者指定的管理設定，並沿用使用者提供的共用 Python 環境；這些是任務輸入與執行環境，不是 SSHScript API 的權威來源。

## 使用公開指南與 skill

- 已安裝完整公開 skill 快照於 `/Users/iap/Library/CloudStorage/OneDrive-財團法人台灣網路資訊中心/private/sshscript/ops/.agents/skills/sshscript/`，文件契約 5.0.0；來源、保存日期與 bundle SHA-256 記錄於該目錄的 `SOURCE.json`。
- 使用 SSHScript 前，優先讀上述本機 SKILL.md、Agent Guide 與任務相關 API 章節；同一任務已讀過且仍適用的內容不必重讀。這是公開資料快照，可以離線使用，不需要每次上網或重新學習。
- 只有使用者明確要求「更新 skill」或更新公開文件快照時，才取得新版 bundle 或補充公開資料；不得因經過時間、開始新任務或版本變動就自動更新。更新時保留完整 bundle 與來源紀錄，不只更新 SKILL.md。
- 本機快照資訊不足或與執行版本不符時，先說明具體缺口，等待使用者指示是否更新；不得自行改查私人 checkout 或以過往知識補足。
- 確認執行 interpreter、SSHScript import／distribution 版本，按公開版本政策核對文件契約；不要假設 /v3a/ 是套件版本，也不要自行升級既有環境。
- 區分下載、閱讀、安裝與環境自動載入 skill；未實際完成者不得聲稱完成。文件或 skill 的示範不擴大使用者的安裝、執行、遠端連線、權限切換或發布授權。
- 公開文件無法取得、內容缺漏或互相矛盾時，回報具體來源與缺口，不用先前知識猜測。網頁工具不可用時可直接讀取相同公開 URL，不能改讀私人 checkout。
- 後續實作與驗證須記錄使用的公開來源及版本，區分文件支持、推論、mock 測試、本機執行與真正 SSH／su／sudo 的證據。
- 發現公開指南不能支援需求或現有程式未遵守指南時，先將缺口明確呈現。修改 SSHScript library、公開文件或提交 GitHub 回饋，仍需符合使用者授權與既有修改限制。

本規則只限制本 Ops 專案取得 SSHScript 知識的方式，不取代使用者原有的 SSHScript 修改位置、分支或共用 venv 規則。
