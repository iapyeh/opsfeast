# 管理環境與 profiles

`tools/ops.py` 管理主機設定與 profile 清單。每個 profile 指向一個管理根目錄，有自己的 hosts.yaml、recipe 選取、observations、records 與 runs；公開 recipes 共用 checkout 的 recipes/。初始化及登記不連線、不執行 recipes。

以下以 `python` 表示已選定且安裝 PyYAML 的 Python，命令從 checkout 執行。省略目錄或 profile 的設定／執行命令使用目前預設；排程建議明確指定 --profile，避免日常切換預設影響排程。

For complete tool syntax, defaults, behavior, output and exit codes, see the [CLI reference](cli.md). It covers both tools/ops.py and tools/run_recipe.py for administrators and agents.

## 建立環境

| 命令 | 目錄 | 自動 profile 名稱 |
| --- | --- | --- |
| `python tools/ops.py init` | `<checkout>/my-ops/main` | main |
| `python tools/ops.py init inventory` | `<checkout>/my-ops/inventory` | inventory |
| `python tools/ops.py init ~/my_ops/inventory` | `$HOME/my_ops/inventory` | inventory |
| `python tools/ops.py init ./inventory` | `<目前工作目錄>/inventory` | inventory |

無參數或單一名稱以工具所在 checkout 為基準，不依目前 shell 位置。含 `/`（Windows 也可用 `\`）或絕對路徑的參數視為路徑；相對路徑依目前工作目錄解析。工具會展開 ~，也處理被引號包住的 ~ 路徑。

初始化成功並通過設定檢查後才登記。第一個成功登記的 profile 成為預設；後續新增不切換。重複執行保留既有設定與相同實際目錄的原 profile 名稱。名稱預設取解析後目錄的最後一個元件；名稱可含中文或中間的空白（CLI 使用引號），不可包含路徑分隔符、控制字元、頭尾空白，或只為 .／..；可用 --profile 明確指定名稱。

同名但不同實際目錄是衝突，不能覆寫。互動終端要求輸入新名稱，建議 `<parent-foldername>.<foldername>`；建議名稱若也已登記，仍需使用者選擇。Enter、Ctrl+C 或 EOF 取消登記。非互動執行回報衝突及建議名稱後退出 1，不等待輸入。Agent 先詢問使用者，再用選定名稱重新執行：

```sh
python tools/ops.py init ~/my_ops/inventory --profile my_ops.inventory
```

衝突在建立 scaffold 前處理；失敗不更新 profile 清單。初始化若在後續檢查或保存登記時失敗，已建立的 scaffold 可能仍存在，保留供修正，不刪除使用者檔案。

## 登記既有環境

換電腦、交接或同事分享既有管理目錄時使用：

```sh
python tools/ops.py add /path/to/existing-profile
python tools/ops.py add ./inventory --profile team.inventory
```

`add` 的參數一律是既有目錄路徑，單一名稱也以目前工作目錄為基準，與 init 的名稱模式不同。它驗證 hosts.yaml、include、連線設定與 recipe 選取；有 my-ops.yaml 時也驗證定義檔。舊目錄只有 hosts.yaml 可以加入。驗證不建立 scaffold、不補定義檔、不改寫目錄內任何檔案，不啟動 Session。

驗證通過才更新 checkout 的 .my-ops.yaml。既有預設保持不變；若這是第一個登記的環境，才成為預設。名稱與衝突規則與 init 相同。相同解析後的目錄（含符號連結別名）保留原登記名稱；用 --profile 要求另一名稱則報錯，不替原登記改名。

搬移資料後，新的路徑可用 add 登記為另一個 profile，再 use 切換；目前沒有刪除或重命名 profile 的 CLI，舊位置的登記可在備份定位檔後手動整理。Ops 不會自動掃描其他目錄找遺失資料，也不會複製 repository recipes 到管理目錄。

## 查看與選擇

```sh
python tools/ops.py profiles
python tools/ops.py use inventory
python tools/ops.py use
```

`profiles` 唯讀列出所有名稱、解析後的完整路徑與目前預設（*）。沒有登記時提示先 init 或 add，退出 0。

`use <profile>` 確認登記、目錄與入口／定義檔有效後切換預設；這不是完整設定 check，不驗證 SSH。`use` 無參數且 stdin/stdout 都是互動終端時，列出編號、以 [current default] 標記目前預設，並接受名稱或編號；無效輸入重新提示，Enter、Ctrl+C 或 EOF 取消並退出 0，不改設定。沒有 profile 或非互動環境則提示並退出 1，不等待輸入。Agent 可呈現清單，取得選擇後執行明確 use 命令。

單次指定環境：

```sh
python tools/ops.py check --profile inventory
python tools/ops.py dump hosts.localhost --profile inventory
python tools/ops.py test-connection host-01 --profile inventory
python tools/run_recipe.py host-01 --profile inventory --recipe inventory/system
```

--profile 不改預設，不能與執行命令的明確目錄參數同時使用。明確目錄仍可直接使用未登記的既有管理資料。未知 profile、無效定位檔或遺失目錄報錯，不改查其他環境。設定、連線測試及 recipe 執行的範圍與授權依 [主機設定指南](hosts-yaml.md) 和 [recipe 指南](../recipes/inventory/system/README.md)。

## 定位檔與舊版相容

Checkout 根目錄的 `.my-ops.yaml` 保存清單，原子替換寫入：

```yaml
schema_version: 2
default_profile: main
profiles:
  main:
    root: my-ops/main
  inventory:
    root: my-ops/inventory
  team.inventory:
    root: /srv/team/inventory
```

Checkout 內位置保存相對路徑，外部保存絕對路徑。`.my-ops.yaml`、`my-ops/` 與定位暫存檔被 Git 忽略；其他位於 checkout 內的自訂目錄需自行加忽略規則。各管理根目錄是 include／自訂 recipe／結果的邊界，不能越過到相鄰 profile。對已登記的舊環境，沒有 my-ops.yaml 時仍可使用 hosts.yaml；已有定義檔但無效則報錯。

舊 schema 1 的 `root` 視為名叫 default 的 profile，原位置不搬移；唯讀命令不改寫定位檔。成功登記或 use 時將清單寫為 schema 2。為新環境引入的 my-ops/main 結構不會自動套用到既有資料。

原入口 `tools/my_ops.py` 已移除，命令與 Python imports 請改用 ops.py／ops。明確路徑與既有設定可繼續使用；`init inventory` 如今是具名初始化，若舊命令要指定目前 shell 下的同名路徑，請改成 `init ./inventory`。之後的文件及新命令使用 ops.py。

無參數 init 的初始名稱是 main；default 只作為「目前預設」的角色概念，不是新建環境的固定名稱。已登記的 default profile 仍可使用，不自動改名或搬移；在這種環境執行無參數 init 會新增 main，並保留原本預設。

_Last modified: 2026-10-11_
