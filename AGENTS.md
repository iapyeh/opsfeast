# SSHScript Ops：以外部使用者角度驗證 SSHScript 文件

## 所有 AI agent 的工作入口

- 本檔隨 Git 追蹤，使用 repository 相對路徑；不要求特定 AI 產品自動載入。
- 初次接手先讀 [README](README.md) 與 [初次使用指南](docs/getting-started.md)，了解已實作範圍、依賴、skill、初始化與使用者下一步。
- 唯讀環境檢查用 `python -B tools/check_environment.py`；初始化精簡需求用 `--scope init`。缺少依賴時依 requirements 清單提出安裝方案，使用者已提供的 Python 環境優先，不自行重建或升級共用環境。
- 初次設定須在授權範圍內建立環境、安裝套件、下載缺少的 skill 及執行 init/check。只交付 repository 路徑供查看不等於授權安裝或執行；已明確授權的初始化流程不重複詢問。
- 使用 [管理環境指南](docs/profiles.md) 的 profile 規則：init 建立、add 唯讀驗證登記、use 切換；兩個工具支援 --profile，本次選擇不改預設。名稱衝突不能覆寫既有登記，非互動執行不等待輸入。
- 完成後回報實際環境、skill 狀態、管理目錄、hosts.yaml 位置及檢查結果，請使用者設定主機帳號、認證及 recipes。初始化不自動授權連線、代理命令、權限切換或 recipe 採集。

使用者要求本專案作為 SSHScript 公開 AI agent 文件與 skill 的實際使用測試。
後續所有 SSHScript API 選擇、行為說明與使用技巧，必須重新從下列公開來源取得證據。

## Documentation language

At this stage, write new documentation and skills in English. Chinese editions will be created later; do not add new Chinese documentation unless the user requests it. Existing Chinese guides may remain until translation is requested.

## Recipe workflow entrypoint

For recipe discovery, authoring, sharing, acquisition or installation, read the [recipes skill](skills/sshscript-ops-recipes/SKILL.md) and its task-specific guides. The human entrypoint is [Use, create and share recipes](docs/recipes.md); available content is listed in the [recipe catalog](recipes/README.md). Complete source verification, safety review and a concrete installation report before installing third-party candidates within user authorization. Installation does not authorize execution. Documented workflows do not imply that a general runner or installer exists.

## 唯一的 SSHScript 學習來源

- 入口：<https://iapyeh.github.io/sshscript/v3a/ai-agents/>
- 可閱讀入口連結的 Agent Guide、canonical API guide、版本政策、API 參考、安全與操作文件，以及完整 SSHScript skill bundle。
- 公開 repository：<https://github.com/iapyeh/sshscript>。使用公開文件、範例、測試或原始碼時，記錄分支／tag／commit 與來源 URL，並優先依 AI agent 入口的閱讀順序進行。
- 不以本機 SSHScript 的 src、working_branch、git、gh-pages、其他私人 checkout、過往聊天／記憶或先前實測補足 SSHScript 知識；也不額外使用 Paramiko 等外部文件作為學習來源。若需要底層資訊，先查 SSHScript 公開 repository 是否提供。
- 可以閱讀及修改本 Ops 專案、使用者指定的管理設定，並沿用使用者提供的共用 Python 環境；這些是任務輸入與執行環境，不是 SSHScript API 的權威來源。

## 使用公開指南與 skill

- Repository 隨附完整公開 skill 快照於 `.agents/skills/sshscript/`（相對於本 repository 根目錄），文件契約 5.0.0；來源、保存日期與 bundle SHA-256 記錄於該目錄的 `SOURCE.json`。快照隨附不代表 agent 已安裝或自動載入此 skill。
- 使用 SSHScript 前，優先讀上述本機 SKILL.md、Agent Guide 與任務相關 API 章節；同一任務已讀過且仍適用的內容不必重讀。這是公開資料快照，可以離線使用，不需要每次上網或重新學習。
- Skill 下載與更新依 [下載與更新指南](docs/skill-updates.md)。使用者要求檢查或授權定期檢查時，可用 `tools/skill_bundle.py check` 取得公開 bundle 並比較；沒有此授權時不因經過時間或開始新任務自動抓取新版。檢查不替換目前快照，也不升級套件。
- 缺少快照或使用者授權準備候選時，用 `tools/skill_bundle.py download <新目錄>` 下載完整 bundle 與來源紀錄；在授權套用後才替換完整快照，不只更新 SKILL.md。文件契約與執行版本不符先呈現缺口。定期執行須使用 agent 平台排程，沒有實際建立者不得聲稱已排程。
- 本機快照資訊不足或與執行版本不符時，先說明具體缺口，等待使用者指示是否更新；不得自行改查私人 checkout 或以過往知識補足。
- 確認執行 interpreter、SSHScript import／distribution 版本，按公開版本政策核對文件契約；不要假設 /v3a/ 是套件版本，也不要自行升級既有環境。
- 區分下載、閱讀、安裝與環境自動載入 skill；未實際完成者不得聲稱完成。文件或 skill 的示範不擴大使用者的安裝、執行、遠端連線、權限切換或發布授權。
- 公開文件無法取得、內容缺漏或互相矛盾時，回報具體來源與缺口，不用先前知識猜測。網頁工具不可用時可直接讀取相同公開 URL，不能改讀私人 checkout。
- 後續實作與驗證須記錄使用的公開來源及版本，區分文件支持、推論、mock 測試、本機執行與真正 SSH／su／sudo 的證據。
- 發現公開指南不能支援需求或現有程式未遵守指南時，先將缺口明確呈現。修改 SSHScript library、公開文件或提交 GitHub 回饋，仍需符合使用者授權與既有修改限制。

本規則只限制本 Ops 專案取得 SSHScript 知識的方式，不取代使用者原有的 SSHScript 修改位置、分支或共用 venv 規則。
