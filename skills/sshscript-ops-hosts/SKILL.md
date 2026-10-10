---
name: sshscript-ops-hosts
description: 協助使用者建立、修改與審閱 SSHScript Ops 管理目錄中的 hosts.yaml 及 include YAML，處理主機連線、跳板引用、變數、recipe 選取與路徑邊界。適用主機設定維護；不代表授權連線或執行 recipes。
---

# SSHScript Ops 主機設定維護

使用者指南與設定規格位於 [docs/hosts-yaml.md](../../docs/hosts-yaml.md)。開始設定工作時閱讀它；不要自行建立另一套欄位語意。這是 repository 內的 skill，使用時保留 repository 結構。若要獨立安裝，需一併打包指南並調整此連結；目前未提供 skill 安裝工具。

Repository 提供 [tools/my_ops.py](../../tools/my_ops.py)：使用安裝 PyYAML 的 Python 執行 `init <管理根目錄>` 建立樣板，或 `check <管理根目錄>` 做唯讀檢查；`dump <設定路徑> <管理根目錄>` 可輸出 include 合併後的指定設定（JSON 縮排 4 格），例如 `dump hosts.host-01 <管理根目錄>`。Dump 只做載入檢查，不等同完整 check，並會原樣輸出選取值，包括密碼欄位。使用者要求實際測試連線時，可用 `test-connection <host-id> <管理根目錄>`，需要 SSHScript 4.0.1+，只在指定目標執行 hostname 與 date；先讀使用者指南中的工具範圍；完整 recipe 執行器尚未實作。先確認 repository 的實際狀態，使用已存在的驗證入口。只做人工審閱或 YAML 語法檢查時，明確區分它們與完整語意驗證，不虛構 CLI、schema 或成功執行結果。

## 工作入口與編輯範圍

連線診斷可加 `--verbose`（進度）、`--debug`（篩選後的有效設定）及 `--traceback`（不含原文、source 與 locals 的堆疊）。JSON 的 hops 與 error.hop 區分每跳；key_source 指出 identity_file 從哪一個 parent 主機讀取。這些是 Ops 自己的診斷，不等同啟用 SSHScript 原始 DEBUG log。診斷寫 stderr，stdout 保持 JSON；不要為了除錯回貼密碼、代理命令或 token，也不要只憑提示就聲稱已找到根因。

- 以使用者提供的管理根目錄為入口，讀取其中的 `hosts.yaml`。沒有根目錄時，先取得路徑；可以先提供合成範例。
- 確認要建立、修改或查詢的主機 ID 與目標。已提供的資料不重複詢問；只詢問會影響結果的缺漏。
- 先讀既有入口及相關 include，保留主機 ID、分檔方式、註解與不相關設定。修改主機定義所在的來源檔案，不在入口建立重複主機作為覆寫。
- 真實資料寫入使用者的管理環境；repository 文件和範例只使用合成資料。維護 SSHScript Ops 文件不代表可修改 SSHScript library；遵守當前目錄的 AGENTS.md。
- 設定維護請求不自動授權 SSH 連線、執行 recipes、修改遠端主機或發布資料。使用者已授權的操作依既有範圍進行，不重複要求授權。

## 不可改變的設定語意

- `hosts` 的鍵是穩定主機 ID；`connection.hostname` 是 DNS 或 IP。
- 新建的 init 樣板包含 `localhost: {connection: {local: true}, users: {}, vars: {}, recipes: []}`。本機 connection 只接受 `local: true`，不建立 SSH 連線，不能作為跳板或混用 SSH 欄位；既有設定仍保留，不自行覆寫。
- 明確 SSH 連線可使用 `connection.proxy_command` 非空字串，不能與同一層的 `via` 或 `ssh_config_alias` 混用。命令原樣保存，不展開 `%h`、`%p` 或 shell 變數；使用具體目標值。check 只驗證設定；明確要求 test-connection 時可啟動代理並測試連線。
- proxy_command 建立資料通道；目標 SSH 驗證仍使用 connection.user 與該 host 對應 users 帳號的 password。提供密碼且未設定 identity_file 時，test-connection 停用 agent 與自動搜尋金鑰。沒有對應帳號或 password 時，不借用其他帳號密碼、不自動新增帳號，使用私鑰或 agent／預設金鑰，驗證失敗則回報失敗。代理程式自己的憑證不自動取用 users 中的 SSH 密碼。
- `via: {host: bastion}` 引用載入後的 `hosts.bastion.connection`。也接受巢狀明確連線；不能把主機引用與覆寫欄位混用。
- `ssh_config_alias` 引用 SSH config 的 `Host`，不是 YAML 主機 ID。每層 alias 與明確連線欄位互斥；YAML 與 SSH config 的跳板衝突不得默默忽略。建議使用 YAML 主機引用以保留可搬移拓樸。
- `connection.user` 保持單一 SSH 登入帳號名稱；host 層 `users` 是以實際帳號名稱為鍵的 mapping，每個帳號只接受可選的字串 `password` 與 mapping `vars`。帳號變數不與 host vars 合併；users 可省略，connection.user 不強制有 users 項目。su 目標必須明確指定，不從帳號順序推定、不自動切換。可用 `dump hosts.<主機>.users.<帳號>` 取得資料，現有 `vars.sudo` 語意不變。
- `vars` 是各主機原樣、保留型別的輸入 mapping，不從跳板繼承，不插值、不深層合併、不自動轉成 shell 或環境變數。
- `vars.sudo.user` 是 sudo 的目標帳號；`vars.sudo.password` 是驗證密碼，通常屬於登入帳號。初版可保存明文；不自動輸出這些值到日誌、觀測或紀錄。
- 根層 `include` 是明確的本機 YAML 路徑清單，可遞迴，不接受 glob、URL 或 `!include`。同一實際檔案只載入一次；載入中的循環必須報錯。
- 重複 mapping 鍵或跨檔案主機 ID 都報錯，沒有載入優先級或覆寫。一般 YAML parser 可能默默採最後一個鍵；驗證時需確認使用的 parser 能拒絕重複鍵，否則揭露檢查限制。
- `recipes` 是選取 mapping 的清單：`recipe` 指完整 recipe 目錄；`directory` 選直接子目錄，只有 `recursive: true` 時遞迴；`glob` 比對 recipe 目錄，`*`、`?` 不跨 `/`，`**` 可跨層級。
- 每個 recipe 目錄含 `recipe.yaml`，不直接把任意檔案當 recipe。依選取清單順序及組內路徑排序展開；同一實際目錄保留第一次，不同目錄同 ID 報錯；空匹配報錯。
- `${...}` 目前是原樣字串；不加入未定案的版本、全域 vars、exclude 或變數存取 API。

## 路徑與引用檢查

Include 的相對路徑以**宣告它的 YAML 所在目錄**為基準。Recipe 的 `recipes/...` 固定以工具所在 checkout 為基準，無需複製到 instance；其餘相對路徑（例如 `./recipes/...`）才以宣告 YAML 的目錄為基準。維持來源檔案資訊，不能合併後一律改用入口 YAML 的目錄。

Include 與自訂 recipe 以管理根目錄為邊界；repository recipe 以工具所在 checkout 的 recipes 目錄為邊界。解析相對路徑、`..` 與符號連結後，實際路徑必須仍在各自邊界內；recipe 的絕對路徑可位於這兩個邊界內。不可因此放寬 include 或結果輸出的邊界。用路徑元件而非字串前綴檢查。Glob 或遞迴選取不能先搜尋外部再過濾，每個結果也需檢查邊界。新設定優先用相對路徑。

這個邊界不適用於目標主機的變數值。`identity_file` 是連線層設定，test-connection 將 identity_file 原樣傳給 SSHScript pkey_path，從呼叫 connect 的 parent Session 所在主機讀取 RSA 私鑰：直連讀 localhost，經由跳板時讀前一跳主機（SFTP 原始登入帳號）。不以 YAML 目錄解析相對路徑、不展開 ~，建議 parent 主機上的絕對路徑；不能將它替換成始終在 localhost 讀取的 key_filename。

全部設定載入後，檢查 `via.host` 是否存在、跳板圖是否循環，以及選取的 recipes 是否存在。錯誤指出來源檔案、主機 ID 或欄位與引用鏈；不要為修正錯誤自行編造主機、密碼或 recipe。

## 完成設定維護

使用 `tools/my_ops.py check` 檢查本次修改，若缺少 Python 或 PyYAML 明確回報，不虛構成功結果。檢查涵蓋 YAML 語法、重複鍵、跨檔案引用、路徑邊界與 recipe 選取規則。使用安全的 YAML 載入方式，不執行自訂標籤。若所選 recipes 不存在，明確回報選取尚無法驗證，不把草案稱為可執行環境。

回報修改檔案、主機 ID、解析後的連線拓樸與檢查結果；不要為說明變更而重貼真實密碼。需要示範完整設定時使用合成值。

若使用者也要求執行，先展開確定的 recipe 清單，檢查支援平台、變數、權限與副作用，並確認操作在該次授權範圍內。記錄實際 recipe ID 與版本；觀測與人工資料分開，保留人工筆記。查詢失敗不得寫成零值、空值或成功，也不得把舊觀測改成新時間。
