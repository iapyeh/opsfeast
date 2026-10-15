# 管理 hosts.yaml 與主機設定

User agents must reread this guide after every OpsFeast release update, even if unchanged or previously read, to learn the installed release's current host schema and semantics before resuming work. See the [mandatory release schema reading rule](skill-updates.md#required-schema-reread-after-a-release-update). Reading completion is not verified.

這份文件定義 OpsFeast 初版的主機設定規則，供使用者與 AI agent 建立及維護管理環境。**目前提供管理目錄初始化、設定檢查與指定主機連線測試工具；另有支援 inventory-system 跨平台實作的 runner，詳見 [recipe 指南](../recipes/inventory/system/README.md)。通用 recipe 執行器與獨立 hostname recipe 尚未實作。** 下列 YAML 定義初版設定格式，不代表可以執行遠端操作。

New to this configuration? Start with [Connect your first host](first-host.md) for a minimal example and practical cases. This document remains the complete reference.

## 從管理目錄開始

使用者提供自己的管理根目錄，例如 `/srv/feasts/`，以及要操作的主機 ID 與目標：

> 我的管理目錄是 `/srv/feasts/`。請取得 `web-01` 目前作業系統回報的 hostname，並把結果存入這個管理目錄。

Agent 從根目錄的 `hosts.yaml` 讀取設定，不要求使用者每次重貼 SSH 指令。`init` 不給目錄時，預設在工具所在 OpsFeast checkout 下建立 `feasts/main/`；`feasts/` 是各管理環境的容器，與 `recipes/` 同層。可用具名環境或自訂路徑，詳見 [管理環境指南](profiles.md)。

```text
feasts/main/
├── feast.yaml
├── hosts.yaml
├── hosts/
│   ├── bastions.yaml
│   └── production.yaml
├── observations/
├── records/
└── runs/
```

`hosts.yaml` 與其他 YAML 保存設定；可執行 recipes 直接使用 OpsFeast checkout 內的 `recipes/`；`observations/` 保存觀測；`records/` 保存整理後的主機紀錄與人工筆記；`runs/` 保存執行狀態。後三者的詳細格式待定，不是本文件新增的資料契約。

公開的 OpsFeast repository 保存工具與合成範例。真實主機設定、憑證與結果留在使用者的管理環境。使用公開 recipes 時，直接更新 OpsFeast checkout 即可，不必複製到管理根目錄。`recipes/...` 固定指向執行工具所在 checkout，不依目前工作目錄或 YAML 所在位置，也不回退到 instance 內的同名副本。自訂 recipe 可另存於管理目錄，用 `./recipes/...` 明確選取；既有副本不會被刪除。

## Read host configuration from Python

For new standalone Python tools, use the bundled [Core API](core-api.md) and [Core skill](../skills/opsfeast-core/SKILL.md):

```python
from opsfeast import Instance

instance = Instance.open(installation="/srv/opsfeast")
profile = instance.profile("main")
hosts = profile.hosts.list()  # Masked, independent snapshot.
host = profile.hosts.get("host-01")
# profile.reload() explicitly refreshes the configuration snapshot.
```

Core reuses Validator include/path/duplicate/connection validation. Keep installation/profile and host ID as invocation inputs; do not generate another YAML parser or freeze private connection settings into code. Raw values require explicit reveal_secrets=True and must not be logged. Loading requires Python 3.11+/PyYAML and makes no connections. See the canonical guide for package installation, errors and snapshot semantics.

The existing `opsfeast.Validator(root).load(root / "hosts.yaml")` and check_connections() remain compatibility interfaces. Runner-managed python-recipe entrypoints use execute(recipe), recipe.session and Recipe vars; legacy python-session recipes retain execute(session, *, context, timeout), with context.host_id/vars only. Neither should reload credentials or reconnect independently.

## 建立與重複檢查管理目錄

Repository 提供 [tools/opsfeast.py](../tools/opsfeast.py)，需要 Python 3.11 以上與 PyYAML。使用已安裝 PyYAML 的 Python 執行；以下假設目前工作目錄是 OpsFeast repository：

```sh
python tools/opsfeast.py init
python tools/opsfeast.py init inventory
python tools/opsfeast.py profiles
python tools/opsfeast.py use inventory
python tools/opsfeast.py check
python tools/opsfeast.py dump hosts.localhost
# 自訂位置或登記既有環境：
python tools/opsfeast.py init /srv/feasts/main
python tools/opsfeast.py attach /srv/existing-ops
```

`init` 在所選管理目錄內建立 `feast.yaml` 定義檔：

```yaml
schema_version: 1
kind: opsfeast
```

登記與預設 profile 記錄於 checkout 的 `.opsfeast.yaml`（schema 2）。Checkout 內的目錄保存相對路徑，外部保存絕對路徑。兩個工具省略目錄時使用預設 profile；--profile NAME 只影響本次執行，明確目錄與 --profile 不可同時指定。不存在或無效的登記不自動回退到其他目錄。

第一個成功登記的環境成為預設，後續新增不切換。重複初始化保留原 profile 名稱與設定，失敗不更新登記。`attach` 唯讀檢查既有環境後登記，不建立或改寫其內容；舊環境只有 hosts.yaml 也可加入，若有定義檔則須有效。舊 schema 1 定位檔視為 default，唯讀操作不改寫它；後續登記或切換時寫成 schema 2，不搬移資料。

完整命名、互動選擇、遷移與路徑規則見 [管理環境指南](profiles.md)。管理入口使用 `tools/opsfeast.py`；舊命令中的單一名稱參數如今代表 `feasts/<name>`，若要指定目前目錄下的路徑需使用 `./name`。

`init` 建立 `hosts/`、`observations/`、`records/`、`runs/` 與 `hosts.yaml` 樣板，接著檢查設定。重複執行只補缺少的目錄或入口檔案，保留既有內容；既有 scaffold 項目是符號連結或型別不符時拒絕初始化。它不建立未實作的 hostname recipe，也不產生 include 子檔案。

新建的樣板自動包含 `localhost`（本機執行）與一個 `host-01` 遠端範例；可設定欄位集中在註解區。遠端 hostname 使用非空的合成值 `host.example`，`recipes: []` 保持空清單，方便尚未選取 recipes 時檢查通過。使用前替換連線值，再加入 checkout 內已有的 recipe 選取。空清單表示沒有選取；非空選取沒有匹配結果仍是錯誤。

`check` 唯讀載入入口與 include，檢查 YAML 語法、重複鍵、欄位與型別、重複主機 ID、缺少引用、跳板與 include 循環、recipe 路徑邊界及選取。錯誤輸出來源和引用鏈，不輸出 YAML 原文或變數值。成功退出碼為 0，錯誤為 1。`init` 保留既有設定後若檢查失敗，也回傳 1，讓使用者修正；不覆寫有問題的檔案。

Check validates descriptor mappings and per-source ID conflicts. The inventory runner additionally checks implementation/version contracts and effective inputs.variables before creating the selected host Session; configuration check is not execution or host compatibility evidence.SSH config alias 會顯示尚需執行時檢查的提示，不讀取 SSH config 或驗證金鑰。`init`、`check`、`dump` 不連線、不執行 recipes、不產生觀測；只有明確呼叫 `test-connection` 才會執行以下連線測試。

目錄遞迴及 `**` 不跟隨符號連結向下遍歷；直接選取根目錄內的連結目標可以接受，指向根目錄外則拒絕。工具拒絕 YAML `<<` 合併鍵及循環 alias；日期等非基本變數型別請以引號寫成字串。設定中的 `${...}` 仍原樣保存。

## Host groups

Each host may declare an optional `group` string or list of strings beside `connection`, `users`, `vars` and `recipes`. A host may belong to multiple groups; omitted group or `group: []` means no membership. Group names must be non-empty strings and match exactly, including case. Duplicate membership is accepted and never causes duplicate execution. Groups are derived from host memberships across the complete include tree; there is no top-level group definition, nesting, inheritance or group variable mapping.

```yaml
hosts:
  web-01:
    connection: {hostname: web-01.example}
    group: [web, production]
  web-02:
    connection: {hostname: web-02.example}
    group: web
  db-01:
    connection: {hostname: db-01.example}
    group: [database, production]
```

`run_recipe.py inventory/system --group web` selects web-01 and web-02. `run_recipe.py inventory/system --group web production` selects their union (web-01, web-02 and db-01), running each host once. `--all` selects every configured host, including localhost and jump hosts regardless of membership. All examples require an authorized environment and recipe; see the [runner reference](cli.md#toolsrun_recipepy-inventory-execution) for complete commands, ordering, root/profile options and output.

Use `--host NAME` for host IDs and `--group NAME` for group names, including when both share the same name. Unknown names fail before any host executes; the runner never guesses a target kind. Recipe and targets are required, and --all cannot be combined with --host/--group. `check` validates membership types without connecting. Groups only select targets in run_recipe.py; they do not change connection topology, authorize execution or add group support to diagnostic commands. Existing configurations without group remain valid. The former groups field is rejected with a migration hint; rename it to group, preserving its list values. If both names appear, validation fails. Scalar membership is treated as a one-element list for selection, while dump preserves the original string/list representation. Null, blank strings, numbers and non-string list members are rejected.

## 測試指定主機的連線

此命令需要在執行它的 Python 環境安裝 SSHScript 4.0.1 以上與 PyYAML：

```sh
python tools/opsfeast.py test-connection host-01
python tools/opsfeast.py test-connection localhost /srv/feasts/main
python tools/opsfeast.py test-connection host-01 /srv/feasts/main --timeout 10
python tools/opsfeast.py test-connection rms4 /srv/feasts/main --debug --traceback
```

載入入口與 include，檢查連線、帳號與跳板循環後，只連線至指定 host 及其所需跳板，再於目標主機各執行一次 `hostname`、`date`。不要求 recipes 已選取、不執行 recipes、不切換 users 中的其他帳號，也不修改管理檔案。`localhost` 的 `local: true` 使用本機 Session 執行相同指令。

- 明確 hostname 模式使用 YAML 連線資料，不自動混入 SSH config；省略的 user 使用目前本機帳號，省略 port 使用 22。
- 使用 `users.<登入帳號>.password` 作為該主機的登入密碼。未指定私鑰且提供密碼時，停用 agent 與自動找金鑰，讓測試實際使用該密碼。未提供密碼或私鑰時使用 SSH agent／預設金鑰。
- `identity_file` 對應 SSHScript 的 `pkey_path`，讀取呼叫 connect 的 parent Session 所在主機上的 RSA 私鑰。直連時從 localhost 讀取；經由跳板連線時從前一跳主機透過 SFTP 讀取。路徑原樣傳入，不以 YAML 目錄為基準、不在 localhost 展開 `~`；建議使用該 parent 主機上的絕對路徑。它不受 include／recipe 的管理目錄邊界限制。
- `via.host` 使用所引用主機自己的 connection 與 users 密碼；inline via 可用私鑰或 agent，不借用目標主機 users 的密碼。多層 via 依序建立巢狀 Session。
- `proxy_command` 在本機啟動；SSH config alias 先解析為有效連線與帳號，再查 users。若 alias 解析出代理且同時使用 YAML via，於連線前拒絕衝突，不默默忽略。
- 保持 SSHScript 預設的主機金鑰驗證，未知或變更的主機金鑰會失敗；使用者需先以可信方式確認並加入標準 known_hosts。

`--timeout` 預設 30 秒，必須是正的有限數字，分別用於每跳 TCP 連線、banner、驗證及每個指令的總期限；不是整條跳板鏈的總期限。

輸出為 JSON，包含 `host`、`connected`、`hops`、`commands` 與 `success`。`hops` 依實際嘗試順序記錄每跳 host ID、hostname、user、port、parent 與 connected；設定 identity_file 時也記錄 `key_source`（私鑰讀取所在主機）。每個完成的指令包含 `command`、`stdout`、`stderr`、`exitcode`；逾時或執行異常包含 `error`。連線成功後會嘗試兩個指令，即使其中一個失敗。只有兩個指令退出碼皆為 0 且 Session 清理成功，才回傳 0；連線、指令或清理失敗回傳 1。失敗保留已取得結果，不把部分成功當完整成功。

連線與第三方例外回報發生階段及例外類別；能辨識時附上安全的 reason：`host_key_mismatch`（已記錄金鑰不符）、`unknown_host_key`（未知金鑰）、`ssh_banner_unavailable`（收不到 SSH banner）或 `authentication_failed`（登入驗證失敗）。不回貼可能包含密碼或代理命令的例外原文。設定或必要依賴缺失的錯誤寫入 stderr。指令 stdout／stderr 原樣回報。

### 跳板連線診斷

- `-v`／`--verbose`：在 stderr 即時顯示每跳開始、成功或失敗，以及目標指令執行進度。
- `--debug`：包含 verbose，另外顯示有效 hostname、user、port、parent、timeout、私鑰來源，以及是否提供 password、proxy_command、identity_file、local key_filename 和是否允許 agent／自動找金鑰。不輸出密碼、代理命令、token 或私鑰內容。
- `--traceback`：在 stderr 顯示執行例外的堆疊檔名、行號與函式名稱。省略例外原文、原始碼行與 locals，避免將憑證帶入診斷。這是 frames-only traceback。

以上是 Ops 工具的診斷選項，不直接啟用 SSHScript 的原始 verbose／DEBUG log；原始日誌可能包含代理命令或敏感輸出。stdout 仍為單一 JSON，可另存結果，診斷則使用 `2>diagnostics.log` 保存。診斷不增加任何遠端指令，仍只執行 hostname、date。

例如 localhost → iapdev → rms4，若 iapdev 成功、rms4 失敗，`hops` 保留 iapdev 的 `connected: true`，而 `error.hop` 指向 rms4，`parent: iapdev`。若 rms4 設定 identity_file，`key_source: iapdev` 提醒使用者檢查該路徑能否由 iapdev 的原始 SSH 登入帳號透過 SFTP 讀取，而不是只檢查 localhost 上的檔案。`FileNotFoundError`、`PermissionError` 也可能由連線其他部分造成，這項提示不代表已證實根因。第一跳失敗時，只記錄實際嘗試的 iapdev，不將未嘗試的 rms4 標為失敗。

另可辨識 `timeout`、`name_resolution_failed` 與 `connection_refused`。每跳的 connection 階段包含 SSHScript 的私鑰載入、通道建立、主機金鑰及登入驗證；堆疊可協助縮小位置，但工具不宣稱所有第三方錯誤都能自動分類。

## 輸出指定設定

```sh
python tools/opsfeast.py dump hosts /srv/feasts/main
python tools/opsfeast.py dump hosts.host-01 /srv/feasts/main
python tools/opsfeast.py dump hosts.host-01.connection /srv/feasts/main
```

`dump <設定路徑> <管理根目錄>` 以 `.` 分隔 mapping 鍵，輸出指定設定的 JSON（縮排 4 格，中文原樣保留，結尾換行）。`hosts` 包含入口與所有 include 合併後的主機；主機內的引用、recipe 選取與變數值仍原樣保留，不展開成執行結果。其他入口欄位如 `include` 也可查詢。路徑只能逐層選取 mapping 鍵，不支援 list 索引或含 `.` 的鍵名。

成功時 stdout 只有 JSON，退出碼為 0，可直接重新導向到檔案。指定路徑不存在或載入失敗時，錯誤寫入 stderr，退出碼為 1，不輸出部分 JSON。被選取的值必須可表示為 JSON，不接受日期型別、循環 alias 或 NaN／Infinity。

此命令唯讀，沿用 include、重複定義與路徑邊界的載入檢查；不執行完整 connection 或 recipe 語意驗證，也不要求 recipe 已安裝。完整設定檢查請另外執行 `check`。`dump` 原樣輸出選取設定，包含其中的密碼等欄位。

## 最小設定

```yaml
hosts:
  web-01:
    connection:
      hostname: web-01.example
      port: 22
      user: operator
    recipes:
      - recipe: recipes/inventory/hostname
```

`web-01` 是穩定的主機 ID，不是 DNS 位址，也不必等於主機實際設定的 hostname。IP 或連線方式改變時，維持相同 ID 可延續紀錄。

此初版格式的根層欄位為 `include` 與 `hosts`，主機欄位為 `connection`、`users`、`vars` 與 `recipes`。`connection` 必須存在；不需要帳號資料、變數或 recipe 選取時可以省略其餘欄位。跳板主機不必列出 recipes。

## ProxyCommand 連線

在明確連線的 `connection` 下設定 `proxy_command`：

```yaml
hosts:
  proxied-host:
    connection:
      hostname: target.internal
      port: 22
      user: operator
      proxy_command: "ssh -W target.internal:22 jump-user@jump.example"
    users:
      operator:
        password: "example-target-password"
    vars: {}
    recipes: []
```

命令提供通往目標 SSH server 的標準輸入／輸出資料流。YAML 使用 snake_case 的 `proxy_command`；將來 runner 對應 SSHScript `Session.connect(..., proxyCommand=...)`。`check` 只檢查字串和欄位衝突，不啟動命令；`test-connection` 才會啟動代理並驗證連線與兩個固定指令。

`proxy_command` 與 SSH 登入帳密各自處理不同階段，可以同時設定：代理命令建立通往目標主機的資料通道，`connection.user` 與同一 host 的 `users.<帳號>.password` 用於目標主機的 SSH 驗證。上例使用代理通道後，以 `operator` 和 `users.operator.password` 登入 `target.internal`，不會因設定了 proxy_command 而忽略 SSH 密碼。

若提供登入密碼且未設定 `identity_file`，`test-connection` 停用 SSH agent 與自動搜尋金鑰，讓目標 SSH 登入使用提供的密碼。若也提供 `identity_file`，仍將私鑰與密碼交給連線層處理，不宣稱一定以密碼登入。代理命令本身需要的帳號、密碼或 token 由代理命令自己的設定處理，不會自動使用或注入 `users` 中的 SSH 密碼。

`proxy_command` 與同一層的 `via` 不能同時設定，也不能與 `ssh_config_alias` 混用。若由 SSH config 管理 ProxyCommand，使用 `ssh_config_alias` 並把命令留在 SSH config。

明確提供的命令是原樣字串：請填入實際目的 hostname 與 port，不會展開 `%h`、`%p`、`${...}` 或 shell 變數，也不保證 shell 管線等語法可用。SSH config 內的 ProxyCommand token 展開由 SSHScript 的 SSH config 解析處理。命令在管理工具所在的本機執行；經由 `via` 的第一個跳板可使用 proxy_command，但同一層不能同時使用兩種代理方式。

## 本機執行

新建管理目錄時，`init` 自動產生以下資料：

```yaml
hosts:
  localhost:
    connection:
      local: true
    vars: {}
    recipes: []
```

`local: true` 表示執行工具的本機，將來 runner 使用 SSHScript 的本機 session，不建立 SSH 連線，也不需要本機啟用 SSH server。這個 connection 只接受 `local: true`，不能混用 hostname、port、user、identity_file、ssh_config_alias、proxy_command 或 via，也不能作為跳板。`hostname: localhost` 則仍代表透過 SSH 連線到 loopback，與本機執行不同。

既有 `hosts.yaml`（包括 include）仍完整保留，重複 `init` 不會自動插入或覆寫 localhost；既有管理環境可手動加入上述項目。此設定不會在初始化或檢查時執行本機 recipe。

## 連線、跳板與主機引用

明確連線設定使用：

| 欄位 | 意義 |
| --- | --- |
| `hostname` | 必填的 DNS 名稱或 IP，與主機 ID 分開 |
| `port` | SSH 連線埠；省略時為 22 |
| `user` | SSH 登入帳號；建議明確指定以便搬移，省略時依執行環境的連線預設 |
| `identity_file` | 可選的金鑰檔案路徑，由連線層處理，不是 include 或 recipe 路徑 |
| `via` | 可選的跳板設定，使用主機引用或巢狀連線 |
| `proxy_command` | 可選的非空代理命令字串；與同一層的 `via` 互斥 |

建議用 `via.host` 引用同一份載入後主機清單的 ID，多台主機可共用一個跳板定義：

```yaml
hosts:
  bastion:
    connection:
      hostname: bastion.example
      port: 2222
      user: jump-user

  web-01:
    connection:
      hostname: web-01.internal
      user: operator
      via:
        host: bastion
    recipes:
      - recipe: recipes/inventory/hostname
```

`via.host: bastion` 引用的是 `hosts.bastion.connection`。跳板本身可以再經由其他主機，形成多層跳板；引用必須存在，而且不能形成循環。引用不帶入該主機的 `users`、`vars` 或 `recipes`。

也可直接巢狀描述跳板：

```yaml
connection:
  hostname: web-01.internal
  user: operator
  via:
    hostname: bastion.example
    port: 2222
    user: jump-user
```

每一層 `via` 可以繼續包含 `via`。引用形式 `{host: bastion}` 不得混入 `hostname`、`user` 等覆寫欄位；需要不同設定時，建立另一個主機定義或使用巢狀連線。

既有 SSH config 仍可透過 `ssh_config_alias` 使用：

```yaml
connection:
  ssh_config_alias: production-web
```

它指的是 SSH config 的 `Host production-web`，不是 YAML 的主機 ID。每層選用 alias 或明確連線欄位，不能混用。Alias 可以搭配 YAML 的 `via`；若 SSH config 已指定跳板，應省略 YAML 的 `via`，兩邊同時指定時必須檢查並拒絕衝突。Alias、金鑰與省略的登入預設可能依賴本機環境；完整描述 YAML 拓樸不代表複製設定後就具備網路與驗證條件。

### identity_file：私鑰位於前一跳主機

`identity_file` 用來登入它所屬的目標 host，但檔案必須存在於呼叫 connect 的 parent Session 所在主機。例如 localhost → iapdev → rms4：

```yaml
hosts:
  iapdev:
    connection:
      hostname: iapdev
      user: iap
      identity_file: /Users/iap/.ssh/iapdev_rsa
  rms4:
    connection:
      hostname: rms4
      user: iap
      identity_file: /home/iap/.ssh/rms4_rsa
      via:
        host: iapdev
```

`iapdev.connection.identity_file` 在 localhost 讀取，用來登入 iapdev；`rms4.connection.identity_file` 在 iapdev 讀取，用來登入 rms4。多層跳板遵循相同規則。ProxyCommand 只提供資料通道，不把呼叫 Session 變成代理主機；沒有 YAML via 的 proxy 連線仍從 localhost 讀取 identity_file。

工具將路徑原文交給 `pkey_path`。`iap/.ssh/id_rsa` 是相對路徑，不代表 `~iap/`：本機 pkey 使用 Python 檔案開啟的工作目錄，遠端 pkey 使用 SFTP 相對路徑的基準目錄；不能套用 YAML 或 recipe 路徑規則。工具與公開 pkey 實作都不替這個欄位展開 `~`／`~iap`，請使用明確絕對路徑。

SSHScript 的 pkey_path 載入 RSA 私鑰，與 Paramiko 的 key_filename 始終從 localhost 讀取且支援其他格式的行為不同。本工具的 identity_file 採 pkey_path 語意，不提供 key_filename 的隱式替代。pkey_path 不將 users.password 當作私鑰解密 passphrase；加密 RSA key 的明確解密流程目前未納入此 YAML 格式。

遠端 pkey 透過 SFTP，以前一跳的原始 SSH 登入帳號讀取。su／sudo 不改變 SFTP 身分，因此登入帳號必須有讀取權限；工具不自動提權讀取私鑰。

## 多個帳號、密碼與帳號專屬變數

`connection.user` 仍是一個 SSH 登入帳號名稱。`users` 與 `connection` 並列，以實際帳號名稱為鍵，可同時保存登入帳號與後續 su 帳號的資料；本機 host 也可設定 `users`。以下全為合成資料：

```yaml
hosts:
  host-01:
    connection:
      hostname: host.example
      user: operator
    users:
      operator:
        password: "example-login-password"
        vars:
          workspace: /home/operator
      appuser:
        password: "example-su-password"
        vars:
          app_root: /srv/app
      root: {}
    vars:
      environment: staging
    recipes: []
```

Accounts accept optional password, vars, sudo and sudo-password. Read the [inventory access policy](inventory-access.md#configure-the-actual-connection-account) for the exact control-string and field-presence rules. `password` 必須是字串，數字或布林形狀的密碼應加引號；空字串與未提供密碼是不同資料，工具保留此差異。使用金鑰或不需要保存密碼時省略 `password`，不自行推定驗證方式。`vars` 必須是 mapping，保留各值的型別，與 host 層的 `vars` 分開保存，不自動繼承或合併。

`users` 可省略或為 `{}`；`connection.user` 不必有對應的 users 項目，維持既有金鑰及 SSH config 設定可用。有項目時，可用帳號名稱取得登入密碼或明確指定的 su 帳號密碼和變數；su 的目標帳號必須由使用者或 recipe 指定，不從 users 順序推定，也不把列出帳號當成切換授權。

若 `connection.user` 不在該 host 的 `users` 中，或該帳號沒有 `password`，不提供 SSH 密碼，也不借用其他帳號的密碼或自動建立 users 項目。使用已設定的 `identity_file`；未設定私鑰時使用 SSH agent／預設金鑰。若這些方式都無法驗證，連線回報失敗。這個帳密選取規則同樣適用於透過 `proxy_command` 的連線。

```sh
python tools/opsfeast.py dump hosts.host-01.users /srv/feasts/main
python tools/opsfeast.py dump hosts.host-01.users.appuser /srv/feasts/main
python tools/opsfeast.py dump hosts.host-01.users.appuser.vars /srv/feasts/main
```

`check` 驗證 users 的欄位、帳號名稱、密碼與變數型別，不驗證帳號存在或密碼正確。`dump` 可取得原樣設定；General Python-session execution is implemented; inventory uses the connection account and verified root when its sudo policy is enabled. `init`、`check`、`dump` 不會登入；`test-connection` 僅使用登入帳號，不執行 su。Legacy vars.sudo credentials remain supported subject to the documented presence/null migration; Host diagnostics select su/sudo credentials using the precedence rules in [host diagnostics](host-diagnostics.md#credential-precedence), including account-password fallback.

## 每台主機的變數

`vars` 與 `connection` 並列，可以保存字串、數字、布林、清單與巢狀 mapping。以下全為合成值：

```yaml
hosts:
  web-01:
    connection:
      hostname: web-01.example
      user: operator
    vars:
      sudo:
        user: root
        password: example-password
      application:
        service_name: nginx
        config_path: /etc/nginx/nginx.conf
      maintenance_enabled: false
    recipes:
      - recipe: recipes/inventory/hostname
```

`connection.user` 是 SSH 登入帳號；`vars.sudo.user` 是 sudo 切換到的目標帳號；`vars.sudo.password` 是 sudo 驗證所需的密碼，通常屬於登入帳號，而不是目標帳號。

初版接受明文值。變數是 recipe 輸入，不自動加入觀測、主機紀錄或執行日誌。每個 recipe 應宣告必需變數及型別，執行前檢查；Inventory now explicitly tests enabled sudo and uses verified root for the complete collection; set account sudo: "false" for intentional ordinary-account collection.

目標主機與跳板各自使用自己的變數，不自動繼承。也不自動把變數轉成環境變數或插入 shell 命令。Recipe 讀取變數的程式介面尚未定案。

## include：把主機清單分檔

YAML 本身沒有標準 include；這是 OpsFeast 設定載入層定義的根層欄位，使用一般 YAML，不使用自訂 `!include` 標籤。

```yaml
# feasts/hosts.yaml
include:
  - hosts/bastions.yaml
  - hosts/production.yaml
hosts: {}
```

```yaml
# feasts/hosts/bastions.yaml
hosts:
  bastion:
    connection:
      hostname: bastion.example
      user: jump-user
```

```yaml
# feasts/hosts/production.yaml
hosts:
  web-01:
    connection:
      hostname: web-01.internal
      user: operator
      via:
        host: bastion
    recipes:
      - recipe: recipes/inventory/hostname
```

各檔案使用相同格式，也可以再 include 其他檔案。只負責 include 的檔案可以省略 `hosts`。全部載入後組成一份主機清單，才檢查跨檔案引用。

載入規則：

- `include` 是明確本機檔案路徑的清單，不接受 glob 或遠端 URL。
- 相對路徑以**宣告 include 的檔案所在目錄**為基準。
- 檔案不存在、格式錯誤或循環 include 時報錯，指出來源及引用鏈。
- 同一實際檔案重複引用時只載入一次；仍在載入鏈上的檔案再次出現屬於循環，必須報錯。
- 同一 YAML mapping 的重複鍵，以及不同檔案的重複主機 ID 都報錯，不能靜默覆寫。重複主機 ID 的錯誤應指出兩個來源。
- 沒有檔案優先級、深層合併或主機覆寫規則。

## Recipe sources and selectors

Read [recipe sources, inputs and execution controls](recipe-sources.md) for the canonical source/variable/disable/exclude contract. Root hosts.yaml may register recipe_sources with local path, enabled and vars; included files reference those registrations without defining new sources.

```yaml
recipe_sources:
  community:
    path: ~/Download/recipes
    vars: {command_timeout_seconds: 15}

hosts:
  host1:
    enabled: true
    connection: {hostname: host1.example}
    recipes:
      - inventory/system
      - ":inventory/system"
      - recipe: community:inventory/system
        vars: {command_timeout_seconds: 10}
```

Bare inventory/system selects checkout recipes; :inventory/system selects the profile's recipes/; community:inventory/system selects the registered community root. Legacy recipes/... still selects the checkout, while ./ paths retain declaring-YAML semantics. String items select one recipe; mappings use exactly one of recipe/directory/glob, with optional vars and directory-only recursive. Same-directory duplicates retain their first selection/vars; duplicate IDs within one source fail, while separate sources have independent identities.

Include and output paths remain inside the management root. Recipe paths remain inside their chosen checkout/profile/registered source after symlink resolution; inventory entrypoints/helpers remain inside their recipe directory. Registration does not authorize installation or execution, and path validation is not a sandbox.

Source enabled: false yields explicit source_disabled skips, even when files are absent. Host enabled: false removes --all/group targets and disallows its use as a jump host; an explicit host request reports host_disabled. Fields/references remain validated. --all --exclude HOST ... excludes targets for one run and does not disable their use as jump hosts. See the [CLI reference](cli.md#toolsrun_recipepy-inventory-execution) for output and exit codes.

## include 與變數插值不同

`include` 載入檔案；插值是在值中引用另一個值，例如未來可能把 `${vars.app_root}/config.yaml` 展開成實際路徑。**初版不支援 `${...}` 插值**，字串原樣保留，Recipe vars use the explicit overlay rules in the [source guide](recipe-sources.md); there is no host/account-variable inheritance or interpolation. --exclude filters host targets only.

將來可在載入完成後加入插值解析步驟，但必須透過格式版本或明確啟用機制引入，避免把既有密碼或字串中的 `${...}` 意外當成引用。目前不新增未定義的版本欄位。

## 執行前與結果保存

預期流程為：確認管理根目錄 → 載入 YAML 並保留來源 → 合併主機清單 → 檢查跳板引用 → 展開 recipes → 驗證輸入及執行條件 → 執行已授權操作 → 保存結果。

Agent 可以使用上述工具編寫及檢查設定，但必須說明檢查範圍，不把設定檢查宣稱為實際連線或 recipe 執行驗證。建立設定本身不會觸發 SSH 連線或執行 recipes。

觀測應保留主機 ID、時間、來源、recipe 版本及狀態。連線失敗、權限不足、逾時或解析失敗都不能變成空字串、零值或成功。更新主機紀錄時保留人工筆記；舊的成功值應保留原時間並標明過期，不能冒充本次觀測。

## 尚待實作與定案

Host configuration/path rules and inventory-system descriptor/result schema 0.2.0 are implemented, alongside platform initialization and requested account diagnostics. The [Python-session contract](recipe-execution.md) supports other reviewed Python recipe IDs and typed invocation inputs; arbitrary backend execution and other retained record schemas remain planned. Linux/FreeBSD have synthetic inventory coverage; macOS has local read-only validation. Real SSH and native su/sudo verification remain pending. Future changes must preserve existing configuration semantics or introduce an explicit version/option.

## Diagnostic credential interpretation

New host diagnostics are described in [host-diagnostics.md](host-diagnostics.md). They use the existing users/vars mappings without adding connection fields. Su retains the diagnostic precedence; sudo follows [account field-presence rules](inventory-access.md#configure-the-actual-connection-account), with canonical sudo-password first and exact "false" controls. Su selects the target account; sudo selects the actor. Su overrides use vars.su.password, while sudo overrides use vars.sudo.password; --run-as selects the diagnostic sudo target (default root), rather than vars.sudo.user.

Test-host is an explicit account-diagnostic request: it tests independent su to other declared users and tests enabled connection-account sudo, including passwordless policy when no password is selected. Configuring users alone does not trigger these actions. New commands take --root or --profile; existing test-connection retains its optional positional root. Test-connection --host-init explicitly refreshes saved platform facts.

## Host icon

Each host accepts optional `icon` beside connection/label/description:

```yaml
hosts:
  mac-01:
    icon: 🍎
    connection: {hostname: mac-01.example.org}
  linux-01:
    icon: 🐧
    connection: {hostname: linux-01.example.org}
  other-01:
    connection: {hostname: other-01.example.org}  # Effective icon defaults to 🍎.
```

The loader requires a string containing **exactly one Unicode code point** (`len(icon) == 1`) whose Unicode General Category is Symbol (`Sm`, `Sc`, `Sk` or `So`). It uses the selected Python runtime's Unicode database. Examples accepted across supported runtimes include 🍎, 🐧, ★, ☀, $, + and ©. Letters, digits, whitespace, controls, empty strings, null and non-string values are invalid. Multi-code-point presentations are invalid even when displayed as one glyph: ☀️ (variation selector), 👍🏽 (skin tone), 🇹🇼 (flag) and 👩‍💻 (ZWJ sequence). No trimming, normalization or grapheme-cluster interpretation is performed; write the intended symbol directly in UTF-8 YAML.

When icon is omitted, every loaded effective host gets 🍎, including hosts from include files. The default is added in memory, without rewriting hosts.yaml, comments or the loader's raw source documents. Invalid explicit icons fail during configuration loading, including for disabled hosts; they do not silently fall back to 🍎. CLI dump of hosts, Core host list/get and inspection, UI read models and runner configuration receive the same effective value through the common loader. Icon is display metadata only and does not affect host/instance identity, target selection or connection settings. This configuration field does not extend retained/exchange observation schemas.

## Explicit host identity and human-readable metadata

Hosts accept optional identity_key, label and description beside connection. label is a display label, not a unique ID; description is free-form explanatory text. Both accept strings, including empty strings, Unicode and multiline text; null/numeric/container values and NUL are rejected. Their original content is preserved. No caption alias is implemented. Command selectors continue to use the local host ID.

```yaml
hosts:
  mail-01:
    identity_key: example.org:mail:os-install-2026-10
    label: Corporate mail service
    description: |
      Production mail service.
      Maintained by the operations team.
    connection:
      hostname: mail.example.org
      user: operator
```

identity_key is an exact, case-sensitive nonempty string without leading/trailing whitespace or control characters. Use a shared organization namespace and OS-installation-specific suffix. Duplicate keys anywhere in the resolved include tree fail before connecting. A and B may use the same key in independent Feasts to assert the same installation. This explicit assignment takes priority over native candidates; it does not verify machine identity. Change it after OS reinstall or target replacement. Labels/descriptions are copied into each raw/retained observation and JSON exchange; differing source labels are preserved rather than overwritten. See [identity precedence and sharing](result-data.md#explicit-identity-and-display-metadata).

_Last modified: 2026-10-15_
