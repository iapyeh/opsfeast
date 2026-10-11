# SSHScript skill 下載與更新檢查

Git 隨附 `.agents/skills/sshscript/` 完整公開文件快照。`SOURCE.json` 記錄下載 URL、保存時間、文件契約與原始 ZIP 的 SHA-256；目前快照為 5.0.0。初次使用可離線閱讀，不必重新下載。

公開入口：https://iapyeh.github.io/sshscript/v3a/ai-agents/

完整 bundle：https://iapyeh.github.io/sshscript/v3a/ai-agents/downloads/sshscript-skill.zip

網址可能提供新版，`/v3a/` 不是套件版號。下載資料須核對其版本；檔案或示範不增加安裝、連線或遠端操作授權。

## 檢查更新

使用者明確要求檢查，或已授權定期檢查時，執行：

```sh
python -B tools/skill_bundle.py check
```

此工具僅使用 Python 標準庫，從固定公開 URL 下載 ZIP 到記憶體，檢查完整 bundle、路徑、大小與一致的文件契約，與 `SOURCE.json` 的 ZIP SHA-256 及目前本機內容比較；不寫入或替換 skill。它也指出候選文件契約是否與目前 runner 的 5.0.0 相符。

- `status: unchanged`：ZIP 摘要與本機內容都一致。
- `status: review_required`：ZIP 摘要或內容有差異，需要閱讀並核對；不代表已知存在較新版本。ZIP 包裝變動也可能改變摘要，本機改動也可能使內容不同。
- `contract_matches_runner: false`：候選文件與目前 runner 契約不符，不直接替換。
- 正常完成比較回傳 0；網路、ZIP、來源紀錄或契約解析失敗回傳 1，寫 stderr，不能當成「沒有更新」。

來源 ZIP 摘要用於辨識內容，不是獨立的簽章／發布者認證。工具不查 PyPI 最新版本、不安裝套件，也不承諾候選內容適用本專案。

## 下載完整候選快照

若快照缺少，或使用者授權下載以準備更新：

```sh
python -B tools/skill_bundle.py download /path/to/new-candidate
```

指定目錄須不存在；下載檔經驗證後保存完整 ZIP、`sshscript/` 所有 bundle 檔案及新 `SOURCE.json`。不執行下載內容，不改既有快照，也不安裝到 agent。可將候選放在本機暫存目錄，或 Git 忽略的 `.skill-downloads/<自行選定名稱>/` 下。工具只支援官方 bundle 的單一 `sshscript/` 根目錄與已知契約標示；新版格式若變動，會明確失敗，需人工確認後更新工具。

## 審閱與套用

1. 讀候選的 SKILL.md、Agent Guide、版本政策及相關 API 差異；核對實際使用的 Python、SSHScript import／distribution 版本與 Ops runner 要求。
2. 明確呈現文件契約或依賴差異。需要改 Ops runner 或升級套件時另外規劃與驗證，不只因 bundle 改變就升級環境。
3. 在使用者授權套用更新後，備份既有快照，將候選完整 `sshscript/` 目錄替換到 repository 的 `.agents/skills/sshscript/`，包括 SOURCE.json；不要只換 SKILL.md，也不要把新舊版本 references 混在一起。若目的地有本機修改，先保留並處理差異。
4. 執行 `check_environment.py`、Ops 一般測試、skill 格式驗證與本次操作所需的驗證；回報版本、摘要、實際替換範圍與驗證限制。套用不包含 Git 提交／push；依使用者要求處理。

本工具只做檢查及準備候選，實際套用仍由 agent 按上述步驟處理；它沒有自動更新命令。若目前 snapshot 不足以支援任務，先說明缺口，不從私人 SSHScript checkout 或過往記憶補足。

## Ops skills and accompanying guides

Official Ops repository: <https://github.com/iapyeh/sshscript-ops>. `skills/sshscript-ops-hosts/`, `skills/sshscript-ops-recipes/`, docs/ and AGENTS.md are published with Ops, not in the official SSHScript ZIP. Start with the [recipe user guide](recipes.md) or [recipes skill](../skills/sshscript-ops-recipes/SKILL.md). There is currently no separate Ops skill bundle or download/update CLI.

Initially acquire a full Ops snapshot at a fixed commit, or a trusted clone. Preserve the relative directory structure and record source URL and actual commit. Skill links depend on accompanying guides; downloading SKILL.md alone is incomplete. Standalone installation into an agent requires the relevant documents, adjusted links, platform-specific handling and user authorization. Direct Markdown reading remains the cross-agent baseline.

When the user requests an update check or authorizes a schedule, acquire a new candidate in isolation. Compare skills, related docs, AGENTS.md, dependencies and tool changes. Follow the [acquisition guide](recipe-acquisition.md) to verify source and content; report commit, differences, compatibility and trust gaps. Checks do not pull over the active checkout or replace installed skills. Apply updates only within authorization, preserving local changes and complete accompanying documents. Code changes require their appropriate CI and are not merely skill updates. A fixed commit does not authenticate a publisher by itself; do not assume this project supplies signed releases.

Review skills bundled with third-party recipes through the acquisition guide; they are not authoritative SSHScript API references. Check recipe updates against their fixed sources and installation records. Checking and applying updates remain separate scopes.

## Update check scopes

Checking the SSHScript public bundle, Ops skills and recipes are different scopes. Schedules must specify sources; permission to check the SSHScript bundle does not authorize updates to third-party recipes. For authorized scheduled checks, use the above `check` command for the SSHScript bundle and the candidate comparison workflow for Ops skills. Preserve scope, frequency, environment and notification preferences. No schedule is established merely by documenting it.

## 定期檢查

文件不會啟動排程。使用者授權後，由其 agent 平台排程執行相同 `check` 命令，保留 scope、週期、環境與通知約定。預設未變更時保持安靜；有差異、檢查失敗或需使用者決定時通知。定期檢查授權不等於套用、套件升級或遠端執行授權；若另外授權特定更新流程，按其明確範圍執行。
