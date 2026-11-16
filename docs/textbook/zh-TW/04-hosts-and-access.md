# 4. hosts.yaml：主機、帳號、群組與連線

[全書首頁](README.md) · 上一章：[安裝驗收](03-verify-installation.md) · 下一章：[第一個 recipe](05-recipes-and-inventory.md)

本章的目標是設定一台真實主機，先通過本機 check，再依需要測試連線、su 與 sudo。範例的 profile 是 `main`；實際設定檔位置以安裝驗收結果為準。

## 主機、user 與 group 的概念

| 概念 | 例子 | 意義 |
| --- | --- | --- |
| 主機 ID | `server-01` | 你為邏輯主機取的穩定名稱，CLI 使用這個 ID |
| 連線地址 | `server.example` | DNS 或 IP，與主機 ID 分開；改地址不必改 ID |
| SSH 登入 user | `operator` | `connection.user` 指定的登入帳號 |
| Users | `operator`、`appuser` | 這台主機已宣告的帳號、憑證與政策；列出不會建立帳號或授權切換 |
| Group | `production` | 便於選擇、分類與顯示的主機群組；可多重成員 |

`group` 是主機分類，不是遠端 Unix 群組，不會新增系統帳號或授予權限。`group: [production, web]` 的第一個群組是主要群組，也影響 Vault 的呈現路徑。群組 ID 用於 CLI 選擇；label 只是顯示名稱。不要將一台主機重複定義成數個 ID 只為分類。

## 先設定一台直接連線的主機

以下是新的可拋棄示範檔，使用已存在的 SSH agent 金鑰：

```yaml
groups:
  production:
    label: Production
hosts:
  server-01:
    group: production
    connection:
      hostname: server.example
      user: operator
      allow_agent: true
    users:
      operator:
        sudo: false
```

將地址、帳號與 ID 換成實際值。`sudo: false` 表示此帳號不使用 sudo，適合先測最小登入；未來若需要提權，應依實際政策修改。既有環境請合併到原定義，保留其他主機、includes 與註解，不能追加第二個頂層 `hosts:` 或重複 ID。

目前 OpsFeast 的 `allow_agent`、`look_for_keys` 預設都是布林 false。要用 SSH agent，明確設 `allow_agent: true`；要搜尋預設金鑰，明確設 `look_for_keys: true`。這兩種自動來源取決於本機 Python 程序環境，即使是多層 SSH 亦然。明確 `identity_file` 或 SSH config 的 IdentityFile 仍有自己的選擇規則。沒有認證來源時應補齊實際設定，不猜測自動金鑰一定可用。

## 密碼、指定金鑰與 SSH config

密碼認證的替代完整範例：

```yaml
hosts:
  server-01:
    connection:
      hostname: server.example
      user: operator
    users:
      operator:
        password: "REPLACE_LOCALLY_WITH_LOGIN_PASSWORD"
        sudo: false
```

占位密碼不可直接使用。請在本機私人檔輸入，不能貼到對話或公開 Git。目前密碼以明文保存，`dump` 會原樣顯示選定資料，避免用它分享帳號設定。沒有登入密碼時，不會借用別人的密碼。

指定 `identity_file` 時必須符合目前支援的格式與路徑規則，不能假設支援所有金鑰或加密格式，也不會展開 `~`。使用 `ssh_config_alias` 時，依 alias 規則管理 hostname/user/key，不能再混入衝突的明確欄位。完整替代範例見[第一台主機指南](../../first-host.md)，認證預設則以目前 [hosts 契約](../../hosts-yaml.md#ssh-authentication-sources)為準。

## Via：透過跳板主機

優先引用同一份已載入主機清單的 ID：

```yaml
hosts:
  bastion:
    connection:
      hostname: jump.example
      user: jumpoperator
      allow_agent: true
    users:
      jumpoperator:
        sudo: false
  server-01:
    connection:
      hostname: internal.example
      user: operator
      allow_agent: true
      via:
        host: bastion
    users:
      operator:
        sudo: false
```

這裡 `via.host: bastion` 引用主機 ID，不是地址。每跳各自選帳號與認證來源，自動認證開關不從目標繼承。引用不可形成循環，停用的跳板不能使用。多層跳板可繼續引用；引用形式只接受 `host`，不能同時填 hostname/user 覆寫。

明確 `identity_file` 仍保留「從前一跳讀取」的語意；它與使用本機程序環境的 agent/預設金鑰搜尋不同。不要假定目標金鑰會自動從控制端送到跳板。使用 SSH config 跳板時，也不能重複設定衝突的 YAML via。

## 基本指令一：檢查設定

```sh
python -B tools/opsfeast.py check --profile main --json
```

Check 在本機驗證 YAML、重複定義、主機引用、路徑與 recipe 設定，不連線或啟動 proxy。若有錯誤，依回報的來源檔與欄位修正；通過後，再用下一個步驟確認網路與認證。

## 基本指令二：測試連線

選定主機及必要跳板已授權後：

```sh
python -B tools/opsfeast.py test-connection server-01 --profile main --json
```

實際連線，執行 `hostname`、`date`，不執行 recipe 或 su/sudo。查看 `connected`、每跳、指令、`success` 與清理結果，確認 hostname 是預期設備。已連線但指令或清理失敗，不算通過。

> 請先 check profile main。對 server-01，我授權既有 SSH 連線、必要 via 跳板，以及 hostname/date 測試。回報各跳與清理證據，不暴露憑證，不執行 su、sudo 或 recipe。

## 基本指令三：測試 su 與 sudo

假設既有主機已宣告 `appuser`，且你已準備該目標帳號 su 憑證，可以明確授權測試：

```sh
python -B tools/opsfeast.py test-su server-01 appuser --profile main --json
```

Su 使用目標帳號的憑證；`users.appuser.vars.su.password` 可指定 su 密碼，依目前診斷規則處理 fallback。先確認 appuser 已存在、憑證備妥，而且這次測試包含切換到該帳號。重複指定使用者預設各自獨立測試；有明確鏈需求才使用 `--chain`。

Sudo 測試預設由實際登入帳號當 actor、root 當目標：

```sh
python -B tools/opsfeast.py test-sudo server-01 --run-as root --profile main --json
```

先確認登入帳號的 sudo 政策已允許；前面的 `sudo: false` 範例需依真實授權修改，不能直接期待通過。Sudo 通常使用 actor 的憑證，不是 root 密碼。`sudo-password`、欄位是否存在、null、空字串與 `"false"` 各有精確含義，請依[存取政策](../../inventory-access.md)設定，不自行重試其他密碼。

查看身分匹配、UID、進入與還原結果。若狀態是略過或不完整，依原因處理後再測；身分流程通過後，實際 recipe 所需的指令權限仍依目標主機政策確認。`test-host` 是更廣的能力診斷，可能測試 sudo 與其他帳號 su，不應拿來代替最小登入測試。

**這一章完成後：**一台主機設定已通過 check；你知道是否測過連線、su、sudo，以及各自的帳號與範圍。下一章才執行第一個 recipe。

正式參考：[hosts skill](../../../skills/opsfeast-hosts/SKILL.md)、[hosts.yaml](../../hosts-yaml.md)、[主機診斷](../../host-diagnostics.md)、[recipe 執行帳號](../../recipe-results-and-accounts.md)。

## 延伸閱讀：測試結果能回答什麼

### 從結果決定下一步

| 看到的結果 | 已完成的步驟 | 接著要確認的事 |
| --- | --- | --- |
| 設定檢查通過 | 本機驗證接受設定 | SSH 登入成功 |
| Hostname/date 與清理通過 | 那些連線指令已完成 | 資料庫存取或 sudo 可用 |
| Sudo 身分探測 UID 符合 | 被測 shell 與身分路徑有效 | 所有特權指令都被允許 |
| 備份普通檔案存在 | 存在性政策找到普通檔案 | Dump 完整、準時到達或可還原 |
| Retention 已儲存 | 結構化證據已保存到該路徑 | 所有 consumer 與對外遞送完成 |
| 頁面剛重建 | 保存證據剛被重新呈現 | 測量也剛更新 |
| SMTP mock 測試通過 | 被測協定路徑在 mock 中有效 | 真實收件人收到這封信 |

歷史缺少的輸出仍是「未記錄」。逾時可能讓遠端終止狀態未知。本機取消已確認、遠端程序已終止、身分已還原、操作成果已驗證，都是不同主張。安心的 recipe 判讀也不能覆蓋這些缺口。

*Last modified: 2026-10-26 16:20:38*
