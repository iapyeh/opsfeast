# inventory-system

設備系統基礎盤點。版本 0.1.0 提供 Linux 採集程式與最小 runner，結果契約仍是第一版，尚無正式 JSON Schema。Linux 已實作、通過合成測試，**尚未在真正 Linux 或 SSH 目標驗證**。macOS 本機僅驗證不支援平台的停止流程。

## 採集範圍

| 欄位 | 定義與來源 |
| --- | --- |
| `hostname` | `uname -n` 回報名稱，不以管理 host ID 或連線位址代替 |
| `platform` | `uname -s` 為 `Linux` 時分類為 `linux` |
| `system_name` | os-release 的 `NAME` |
| `system_version` | os-release 的 `VERSION_ID`；未提供時為 unavailable，不推測版本 |
| `kernel_name` | `uname -s` |
| `kernel_release` | `uname -r` |
| `architecture` | `uname -m` 的原始架構字串，不推論實體 CPU 能力 |

先讀 `/etc/os-release`，確認不存在才改讀 `/usr/lib/os-release`；不合併兩者。讀取使用固定 `/bin/sh` 腳本與位置參數，44 表示路徑不存在、45 表示不可讀；其他非零退出碼保持 command_failed。不執行 os-release 的內容，不做 shell 插值。解析器接受單行 quoted assignments、空值與註解行；重複鍵、未閉合引號、多個未加引號的單字及格式錯誤均回報 parsing_failed。

非 Linux 僅執行 `uname -s`，保留 kernel_name，其餘欄位標為 unsupported。無法判斷 kernel 時，後續欄位保持 not_attempted。Linux 容器若回報 Linux kernel，採集的是容器可見的系統環境；不宣稱這是實體主機配置。

本 recipe 不採集 CPU／RAM、儲存、網路、軟體清單、服務或即時資源使用量。不 sudo、su、安裝工具或修改目標配置。登入帳號需要能執行 uname、/bin/sh、cat，以及讀取系統版本資訊。

## 執行

Controller 使用 Python 3.11+、PyYAML，以及 **SSHScript 5.0.0**。Runner 在連線前確認 import／distribution 皆為 5.0.0，不自動安裝或升級。執行時保留公開契約的預設 host-key 驗證；巢狀連線預設使用 calling parent 的 trust file，私鑰也依既有 Ops parent-host 規則處理。

管理目錄參數可省略：使用最近成功 `my_ops.py init [DIRECTORY]` 記住的位置；明確指定時仍優先使用 CLI 目錄。定位規則與定義檔詳見 [管理目錄指南](../../../docs/hosts-yaml.md)。

直接使用 SSHScript Ops checkout 內的 `recipes/inventory/system/`，更新 checkout 後即可使用新版，不必複製到 instance。可以用 CLI 指定本次 recipe，不必修改主機的 `recipes` 設定：

```sh
python -B tools/run_recipe.py example-host-01 \
  --recipe recipes/inventory/system --timeout 30
```

`--recipe` 接受單一 recipe 目錄路徑，不是 recipe ID、檔案或 glob。`recipes/...` 以工具所在 checkout 為基準，不受目前工作目錄影響。其他相對路徑（例如 `./recipes/inventory/system`）以管理根目錄為基準；絕對路徑可位於 checkout 的 recipes 或管理根目錄內。符號連結解析後不能離開所選來源的邊界。目錄必須包含相符的 recipe.yaml 與 main.py。

有指定 `--recipe` 時只使用該目錄，不展開或檢查該主機的 recipes 選取清單。指定無效路徑或不支援的 recipe 會在連線前失敗，不回退到主機設定；hosts.yaml 的主機與連線設定仍需存在且有效。

省略 `--recipe` 才使用該主機在 hosts.yaml 或 include YAML 中的 `recipes`：

```yaml
recipes:
  - recipe: recipes/inventory/system
```

`recipes/...` 直接指向 checkout，include YAML 中也相同。其他相對路徑以宣告它的 YAML 所在目錄為基準。真實設定和輸出留在使用者管理環境，不加入公開 repository。

從 Ops repository 執行（以下使用合成 host ID 與管理路徑）：

```sh
python -B tools/my_ops.py check /srv/my-ops
python -B tools/run_recipe.py example-host-01 /srv/my-ops --timeout 30
```

最小 runner 僅執行明確的 inventory-system，不執行該主機選取的其他 recipes。它檢查所選 recipe.yaml 與 main.py 是否與這份 runner bundle 完全相符，然後呼叫 repository 內的採集程式；不動態執行任意腳本。`recipes/...` 永遠使用 checkout，不回退到 instance 的同名舊副本；明確指定自訂副本時仍需與 runner bundle 相符。目前不是通用插件執行器。

Runner 沿用現有 connection／users／via 設定，僅連至指定主機與必要跳板。`--timeout` 是每跳連線、banner、驗證以及每項查詢的正有限秒數，預設 30 秒，**不是整次執行的總期限**。Session 在 finally 中以 `close(strict=True)` 清理，清理失敗使整體 failed。期限到達或 channel 關閉不證明遠端程序已結束。

## 輸出與狀態

每次保存一個 `observations/inventory-system-<uuid>.json`，不覆寫舊觀測，不更新人工 records。檔名不使用主機名稱或 host ID。結果包含執行狀態，初版不另寫 runs 檔案。stdout 僅印 status 與完整結果路徑。完整成功退出碼為 0；partial、unsupported、failed、設定／保存失敗為 1。無法保存時不回報成功。

- `schema_version` 與 recipe version 分開；recipe 另保留 implementation SHA-256、`installed_path`（相對 checkout 或 instance 的路徑）、`location_source`（repository／instance）與 `resolved_path`（實際絕對路徑）。
- recipe 的 `selection_source` 記錄 `cli` 或 `hosts`，表示本次使用哪一種選取來源。
- `runtime` 保留 interpreter、Python 與 SSHScript import／distribution 版本。
- `host_id` 是穩定管理 ID；hostname 是本次觀測值。
- 時間是含 UTC 時區的 ISO 8601 字串。各觀測有自己的時間，不代表原子快照。
- `evidence_kind` 區分 synthetic、mock、local、ssh。合成與 mock 不是目標實際觀測。
- 每個欄位都有 value、status、observed_at、source_ids、error。非成功值是 null；not_attempted 的時間也是 null。
- sources 保留固定 argv、開始／完成時間、stdout、stderr、exitcode 或安全錯誤類別。Timeout 例外提供 partial result 時保留輸出、termination_status 與截斷旗標，不把 partial output 當成功值。即使退出碼是 0，stdout 或 stderr 被截斷也標為 parsing_failed。
- execution_errors 保存連線、transport／框架或清理失敗的階段與安全類別，不保存憑證或第三方例外原文。主機來源 stdout／stderr 原樣保存，結果應留在使用者管理環境。

觀測狀態包含 success、unavailable、unsupported、permission_denied、timeout、command_failed、parsing_failed、not_attempted。Permission_denied 只依上述明確不可讀檢查分類，不從任意非零退出碼猜測。必要工具在本機不存在可辨識為 unavailable；SSH shell 回報的工具缺失非零退出碼則保持 command_failed。

整體狀態優先順序：execution_errors 非空為 failed；不支援平台為 unsupported；全部七欄成功為 success；部分成功為 partial；無任何成功為 failed。舊觀測不補進新結果。

[合成結果範例](examples/result.synthetic.json) 示範缺少 system_version 的 partial 情境。它不是實測證據；合成 sources 使用 payload，實際執行使用上述 command 證據欄位。

## 公開來源與驗證

SSHScript API 的依據僅為安裝的公開 skill bundle：

- URL：https://iapyeh.github.io/sshscript/v3a/ai-agents/downloads/sshscript-skill.zip
- 保存日期：2026-10-10；文件契約：5.0.0。
- SHA-256：`e065bec4e7bd48791563412c5ca3bdaac5f46c5e09456ba5d24665a01ba79b4b`。
- 閱讀 SKILL.md、Agent Guide、canonical API guide 的 command result／connections／lifetime 章節與版本政策。此來源是公開文件快照，不是私人原始碼 checkout。

Linux 資料來源語意參考 [GNU uname manual](https://www.gnu.org/s/coreutils/manual/html_node/uname-invocation.html) 與 [systemd os-release 定義](https://github.com/systemd/systemd/blob/main/man/os-release.xml)（2026-10-10 查閱）。這些不是 SSHScript API 學習來源。

執行 `python -B -m unittest discover -s tests -p 'test_*.py'` 驗證合成解析、缺值、缺檔 fallback、拒絕權限、unsupported、期限／partial output、transport／cleanup 失敗、設定選取、checkout 選取與自訂副本一致性、輸出路徑與重複保存。SSHScript 5.0.0 credential-free quickstart 和 macOS unsupported 本機流程已驗證；Linux 完整採集、真正 SSH 與跳板仍待使用者指定目標後驗證。
