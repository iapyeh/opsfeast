# 5. Recipe 與第一個系統盤點

[全書首頁](README.md) · 上一章：[主機設定](04-hosts-and-access.md) · 下一章：[第一個 observation](06-observations.md)

## Recipe 是什麼，為什麼需要它

Recipe 是有版本的工作配方：說明要解決的問題、輸入與適用環境，執行審查過的程式，並回傳可判讀結果。將調查整理成 recipe，下一次就能重跑相同邏輯，同事也能審查、移植，不必靠重述前一次聊天來復原做法。

Bundle recipe 是這份 OpsFeast checkout 隨附的 recipe。自己的 recipe 通常放在管理根目錄 `recipes/`，參照寫成 `:domain/action/name`；共用來源另行登記。完整 reference 指定來源與路徑，descriptor ID 可能跨來源重複。

## 列出與檢視 bundle recipes

```sh
python -B tools/opsfeast.py recipes list --checkout-only --json
python -B tools/opsfeast.py recipes show system/inventory/overview --checkout-only --json
```

這些只讀中繼資料，不需要已建立的 profile，也不執行候選程式。`--checkout-only` 只看隨附內容；要看 profile 本地與可用登記來源，改用 `--profile main`，不能兩者並用。

目前目錄有六個隨附 recipe：

| Reference | 用途 |
| --- | --- |
| `system/inventory/overview` | 系統、硬體、網路、儲存、軟體與服務盤點 |
| `system/account/check/identity` | 觀察執行帳號 |
| `system/network/check/port` | 從選定主機做有限 TCP 連線檢查 |
| `database/mysql/check/replication` | MySQL/MariaDB replica 狀態 |
| `feast/report/execution-summary` | 從既有結果產生離線摘要 |
| `feast/report/retention-summary` | 從 retention 產生離線 Markdown/HTML |

清單幫你找到候選 recipe；接著閱讀它的 README，確認目標平台、依賴與操作內容，再從一台主機開始使用。隨附內容也可在[recipe 目錄](../../../recipes/README.md)查找。

### 緊急 CVE 盤點時如何重用

遇到 PHP 等軟體漏洞事件，可以先讀既有 inventory 證據，確認新舊與涵蓋範圍，再依授權補採所需 job。先用套件與服務盤點找出相關系統，再補上該次漏洞需要的 runtime、供應商修補、暴露面與業務規則。把這次確認的篩選與報表規則保存下來，下次重用，流程見 [CVE 應變案例](#延伸閱讀從-cve-事件到可重用盤點)。

## system/inventory/overview 可以做什麼

目前 recipe 0.4.0 用一套採集程式提供 11 個獨立 job。每個 job 包含相關屬性，能單次執行或依不同間隔週期採集。

| Job ID | 主要內容 | 預設週期間隔 |
| --- | --- | --- |
| `hardware-baseline` | CPU、記憶體、型號、序號、架構、虛擬化 | 7 天 |
| `system-configuration` | 主機名、平台、系統/核心版本、時區 | 1 天 |
| `network-configuration` | 介面、MAC、IP、MTU、resolver 資訊 | 1 天 |
| `software-inventory` | 平台可見的套件或安裝項目 | 1 天 |
| `storage-layout` | 掛載、檔案系統與區塊裝置配置 | 1 天 |
| `storage-capacity` | 容量、使用率及支援的 inode/swap | 15 分鐘 |
| `service-state` | 平台可見的服務與監聽端點 | 5 分鐘 |
| `network-state` | 介面狀態與路由 | 5 分鐘 |
| `system-runtime` | Uptime 與開機時間脈絡 | 5 分鐘 |
| `resource-metrics` | 支援的 CPU、load、記憶體與計數器 | 1 分鐘 |
| `hardware-sensors` | 支援的溫度與風扇資料 | 1 分鐘，預設停用 |

這些間隔從你啟用排程後開始作用。Linux 的探測最廣；其他平台依可用工具回傳支援的欄位，缺少項目會顯示原因。選擇屬性時可查看[平台涵蓋說明](../../../recipes/system/inventory/overview/README.md)，計數器與速率的讀法則見[延伸篇](#如實解讀資料的新舊)。

## 設定參數放在哪裡

Recipe 的變數放在 `hosts.yaml` 的精確 reference 下，可分 default、group、host；逐欄位合併、主機優先、清單取代。排程的 job 間隔與主機 opt-in 則放 `inventory.yaml`，不是 recipe 的一般 vars。

| 參數或選項 | 意義與限制 |
| --- | --- |
| `command_timeout_seconds` | 正數，採集指令逾時；未指定時沿用呼叫的 timeout |
| `collection_budget_seconds` | 正數，共用採集指令預算；不是整個連線生命週期上限 |
| `attention.enabled` | 布林，是否評估目前 Attention 提示；與 recipe 啟用不同 |
| `attention.thresholds` | 檔案系統使用率、CPU、可用記憶體%、每 CPU load 的 warning/critical |
| `inventory query/run --job` | 選採集 job；query 也可改選 `--property`，不可混用 |
| `inventory query --save` | 保存立即查詢；未指定則不寫 OpsFeast observation/retention/Vault |
| `inventory configure --interval` | 排程間隔，至少 60 秒；改間隔不自動啟用主機 |

合併到既有設定的例子：

```yaml
default:
  recipes:
    system/inventory/overview:
      enabled: true
      vars:
        command_timeout_seconds: 30
        collection_budget_seconds: 90
        attention:
          enabled: true
          thresholds:
            filesystem_used_percent: {warning: 80, critical: 90}
```

Attention 其他內建預設為檔案系統 90/95、CPU 90/95、可用記憶體 10/5、5 分鐘 load/CPU 1/2。上例只把檔案系統改成 80/90。高使用率越高越嚴重，可用記憶體越低越嚴重；值必須有效、方向不能顛倒。詳見[完整門檻規則](../../inventory-jobs.md#attention-thresholds)。

## 執行第一個 recipe

先假設主機 `server-01` 已完成前章設定與連線測試。審查 inventory 的唯讀操作、可能的有限 su/sudo 取得 root 政策、儲存與 consumer 效果後，授權一次執行：

```sh
python -B tools/opsfeast.py recipes run system/inventory/overview --profile main --host server-01 --json
```

這會執行預設啟用的採集 job、保存證據、嘗試 retention 與已啟用 consumer。預設帳號政策可能取得 root，不能因為是唯讀就認定只用 login。前章登入帳號若 `sudo: false`，會依 inventory 有限政策與實際可用帳號保留可採集範圍，缺少欄位不應猜補。

明確 `--host` 對該目標覆蓋主機、來源、recipe 的 enabled 門檻；群組/全部批次仍需三者啟用。停用跳板、無效輸入與路徑仍會失敗。

第一次若只想保存容量 job，可以改用較小的立即操作：

```sh
python -B tools/opsfeast.py inventory describe --job storage-capacity --json
python -B tools/opsfeast.py inventory run --profile main --host server-01 --job storage-capacity --json
```

Describe 只讀定義，run 才連線、保存。兩個 run 範例是不同範圍的選擇，不必為了閱讀本章兩個都執行。

## Cron 設定與取消

這裡的 cron 是 **inventory 專用週期採集**。不是所有 recipe 的通用排程，保存的 recipe job 也不等於 cron。

先審查所有有效 job，再依授權設定間隔與主機 opt-in：

```sh
python -B tools/opsfeast.py inventory configure --profile main --host server-01 --job storage-capacity --interval 30m --json
python -B tools/opsfeast.py inventory configure --profile main --host server-01 --enable --json
python -B tools/opsfeast.py inventory status --profile main --json
python -B tools/opsfeast.py inventory dispatch --profile main --dry-run --json
```

前兩行寫設定，後兩行讀取。只設定容量間隔不會把範圍限制為容量；啟用主機也可能讓其他預設 job 到期。確認 `hosts.yaml` 的主機、來源、recipe 啟用門檻，並審查所有即將執行的 job。

未授權週期採集之前，不安裝或啟用。確認未來目標、權限、間隔、儲存與失敗觀察範圍後，才執行：

```sh
python -B tools/opsfeast.py inventory cron install --profile main --json
python -B tools/opsfeast.py inventory cron show --profile main --json
```

Install 修改目前使用者 crontab 的一個受標記項目，每分鐘呼叫到期 dispatcher，保留其他排程；它不啟用主機。Controller 必須開機、OS 允許存取 checkout 與資料。失敗進入下一個正常間隔，沒有自動採集重試、補跑或 AI 喚醒。Consumer 遞送重試是不同機制。

取消這個 profile 的 cron：

```sh
python -B tools/opsfeast.py inventory cron remove --profile main --json
```

只停用一台週期主機，則用：

```sh
python -B tools/opsfeast.py inventory configure --profile main --host server-01 --disable --json
```

Remove 不刪 observation 或主機設定；disable 不移除其他主機的 cron。已開始的採集是否完成，仍需查該次證據，不以刪除排程推論遠端已停止。

**這一章完成後：**你能列出隨附 recipe、解釋 inventory 參數，並在授權下執行一次採集。保存回傳 ID，下一章查看第一個 observation。

延伸：[Inventory 查詢、時間與排程](#延伸閱讀inventory資料新舊與排程)；正式參考：[recipe skill](../../../skills/opsfeast-recipes/SKILL.md)、[sources](../../recipe-sources.md)、[inventory jobs](../../inventory-jobs.md)、[採集表](../../../recipes/system/inventory/overview/collection-plan.md)。

## 延伸閱讀：Inventory、資料新舊與排程

Inventory 用測量結果回答主機相關問題。你可以立即查詢單一屬性、保存比較資料、執行包含相關屬性的 job，或明確讓指定主機加入週期採集。這些選擇的儲存與未來效果不同。

### 先了解測量項目

```sh
python -B tools/opsfeast.py inventory describe --json
python -B tools/opsfeast.py inventory describe --job storage-capacity --json
```

這些本機讀取不需要 profile，會列出屬性、型別、單位、實體 key 與來源模型對應。[採集表](../../../recipes/system/inventory/overview/collection-plan.md)列出 job 內容、起始間隔與涵蓋範圍。一個屬性可能回傳多個實體，例如以來源與掛載點區分的檔案系統。


### 只查需要的內容

選定目標與 inventory 權限政策已授權時：

```sh
python -B tools/opsfeast.py inventory query --profile main --host server-01 --property storage.filesystems.used_percent --json
```

未加 `--save` 時，仍會執行真實探測、帳號與平台檢查，但不寫入 OpsFeast 原始結果、retention、Vault、主機資訊快取或排程狀態。目標的 SSH/sudo 稽核仍可能記錄活動。探測會依 inventory 的有限帳號政策選擇執行身分；查詢前請確認這次允許使用的權限。

選擇屬性或 job 其中一種，不可混用。不支援欄位、探測失敗、未知值與輸出截斷都明確保留。共用探測可能供應數個屬性；執行預算約束採集指令，不能據此保證整個連線生命週期的期限。


### 保存立即查詢，供日後比較

```sh
python -B tools/opsfeast.py inventory query --profile main --host server-01 --property storage.filesystems.used_percent --save --note "Capacity review before application rollout" --json
python -B tools/opsfeast.py inventory run --profile main --host server-01 --job storage-capacity --json
```

兩個指令都會連線並保存證據。第一個保存選定屬性與人工註記，第二個執行選定 job。分別檢查原始儲存、retention 與下游回執。值即使重複，也仍是獨立樣本。註記是人提供的背景，不能證明相關修改真的發生。

手動更新不推進 inventory 排程，只更新最新檢視中實際測得的屬性。最新一次嘗試失敗時仍保留缺口，不會默默改用較舊的成功值。不同屬性有不同來源時間，是合理情況。


### 如實解讀資料的新舊

假設硬體資料是昨天採集，檔案系統容量是五分鐘前採集，目前頁面可以把兩者放在一起。頁面產生時間並不是兩者共同的採樣時間。比較數值時，應保留採樣時間、來源 ID、測量範圍與實際帳號警告。

速率需要測量區間或可比較的樣本。單一累計 byte 計數器不能直接當吞吐量。YANG 對應提供每個屬性的模型位置，方便不同程式理解資料。這裡採集的是選定屬性；需要 NETCONF、gNMI 或完整 datastore 整合時，應另行設計介面。欄位含義與單位可在所屬 recipe 定義查詢。

Inventory Attention 使用目前設定的門檻評估目前檢視；歷史批次 Attention 保留該次執行保存的發現與政策。修改今天的門檻再重建，不應重新解釋昨天的批次。


### 明確加入週期採集

Inventory 排程放在 profile 本地 `inventory.yaml`。沒有排程設定，就沒有啟用的主機。審閱方案應列出主機、job、間隔、權限範圍、儲存效果、控制端可用性，以及如何察覺失敗。

範圍已授權後，以下是本機設定修改的例子：

```sh
python -B tools/opsfeast.py inventory configure --profile main --host server-01 --job storage-capacity --interval 30m --json
```

這只寫設定，不連線或安裝 cron。啟用主機是另一個動作：

```sh
python -B tools/opsfeast.py inventory configure --profile main --host server-01 --enable --json
```

啟用主機也可能讓其他預設啟用的 job 取得執行資格。啟用前檢視所有有效 job；只覆寫 storage 的間隔，不會把採集範圍限制成只有 storage。`hosts.yaml` 的主機、來源、精確 recipe 啟用狀態，是另外的門檻。

執行前先檢視設定與預計工作：

```sh
python -B tools/opsfeast.py inventory status --profile main --json
python -B tools/opsfeast.py inventory dispatch --profile main --dry-run --json
python -B tools/opsfeast.py inventory cron show --profile main --json
```

這些是讀取。一般 `inventory dispatch` 會對到期、已啟用的工作連線一次。已授權的 `inventory cron install` 修改目前使用者的 crontab，每分鐘以固定絕對路徑與選定 profile 根目錄呼叫 dispatcher。它保留其他項目，不會啟用任何主機。控制端必須持續運作，而且能存取這些路徑。

失敗會推進到下一個正常間隔。沒有自動採集重試、補跑錯過區間、AI 喚醒或 inventory 自動通知。Consumer 重試是另一個機制。要證明 cron 真的執行，請確認之後保存的嘗試與時間，僅有排程項目不足以證明。

可以這樣對 agent 說：

> 替 server-01 準備週期容量採集方案。先檢視所有有效 job 與啟用狀態，說明哪些 job 會取得執行資格、間隔、權限、儲存與失敗可見性。在具體排程納入我的授權之前，不要啟用主機或安裝 cron。

**理解檢核：**區分未保存查詢、已保存手動更新、到期 dispatch 與 cron 安裝。說明為什麼剛重建的目前頁面，仍可能含有昨天的資料。

正式參考：[inventory jobs](../../inventory-jobs.md)、[recipe 目錄項目](../../../recipes/system/inventory/overview/README.md)、[採集表](../../../recipes/system/inventory/overview/collection-plan.md)、[inventory 存取](../../inventory-access.md)。

## 延伸閱讀：從 CVE 事件到可重用盤點

緊急漏洞事件最耗時間的部分，往往是重新找目標、準備查詢，再把零散結果整理成團隊能使用的資訊。我們用 2026 年 10 月的 PHP 事件，帶你把這些準備累積成可重用的流程。

### 先把來源與問題說清楚

PHP 在 2026 年 10 月 21 日發布 CVE-2026-109618、CVE-2026-109619 的安全更新。[官方公告](https://www.php.net/archive/2026.php)說明 Web 執行環境、修補與供應商資訊；[ENISA 聯合聲明](https://www.enisa.europa.eu/news/joint-statement-on-critical-php-vulnerabilities)也要求組織辨識相關應用並優先處理對外系統。開始處理事件時，先開啟官方與供應商公告，確認你目前使用的版本、套件與修補方式。

先問：「這次指定範圍中，哪些系統有需要進一步確認的 PHP 使用證據？哪些已確認受影響？哪些資料不夠？我們依什麼規則排序？」先分清楚這幾個問題，才能安排要讀哪些既有資料、補查什麼，以及誰來確認。


### 從已經累積的能力開始

1. **確認範圍與規則。**列出產品、profile、目標主機、允許操作與誰負責判讀；確認本次公告及供應商修補依據。
2. **查既有證據。**讀已保存 inventory、observation、retention，檢查採樣時間、實際帳號、平台與採集完整度。資料過時或缺欄位就列缺口。
3. **只補必要採集。**已授權時重用 `system/inventory/overview` 或選定 job；先取得系統、軟體與服務資料，再依部署情況補查 PHP-FPM pool、容器、內嵌 runtime 與供應商修補資訊。需要新增查詢時，整理成範圍明確、可重跑的補充 recipe。
4. **分開證據與判讀。**標出原始套件/服務證據、實際 runtime 是否確認、供應商修補狀態、暴露面與產品重要性；未知保持未知。
5. **產生團隊可用結果。**以已同意的分級規則，產生優先確認/處理清單與報表，附上來源時間、判斷依據與負責人需要補充的背景。把本次確認的報表與分級邏輯保存為 recipe，下一次就可以帶入新資料重跑。
6. **保存與交接。**Recipe 保存做法，observation 保存該次證據，retention 保存可再分析的資料。同事或 PM 可以用自己的 agent，在獲准範圍內繼續提問，不必重新探索整套流程。

一般套件盤點可能看不到自編譯、容器或產品內嵌的 PHP；CLI 的 PHP 也未必是服務請求使用的版本。供應商回補修補時，顯示的上游版號也不能單獨判定是否受影響。因此，在清單加上實際 runtime、供應商修補狀態與待確認欄位，讓同事知道下一步要查哪裡。反覆需要的查詢則補成可重用模組或 recipe，下次就有現成工具。


### 每個角色如何參與

| 角色 | 這次要解決的問題 | 可留下的成果 |
| --- | --- | --- |
| 系統管理者 | 如何得到可信測量？哪些需修補與驗證？ | 已審查採集、來源證據、修復後驗證；修補本身需要對應授權 |
| PM（產品經理） | 影響哪些產品、哪裡要優先確認、還缺什麼？ | 有來源的問題清單、產品對照與可重用報表 |
| 職務代理人 | 前一位做過什麼，現在從哪一步接手？ | Recipe、該次 observation、retention、人工背景與未解決事項 |

請先由團隊整理主機與產品的對照、處理責任與優先序規則，再讓 agent 依這些背景產生報表。確認結果後，就能分別安排補查、修補與修復後驗證。


### 一個可交給 agent 的需求

> 我們需要回應這次 PHP CVE。請先核對官方與供應商公告，只讀現有資料，提出我們能回答與不能回答的問題清單。保留採樣時間、平台/帳號範圍與未知狀態。重用現有 inventory，列出需要補查的實際 runtime、供應商修補與暴露面；主機操作未在既有授權內時，先準備具體採集方案。將確認的篩選與報表流程保存成 recipe/設定，方便 PM 與職務代理人使用各自的 agent 接續。不自行修補、寄送或排程。


### 把這次的準備留給下一次

事件結束前，花一點時間整理這次用過的查詢、篩選、業務對照與報表。哪些已有 recipe 可以繼續使用？哪些是臨時補查、值得保存的新能力？哪些背景應留在設定或人工筆記？

把這些成果留下來，下一個 CVE 出現時，就能先讀現有資料、重跑既有採集，再把注意力放在新的影響條件與需要處理的主機。這也是我們設計 OpsFeast 的出發點：每次工作都增加團隊的能力，而不是結束後只留下聊天紀錄。

延伸：[Recipe 與 inventory](#systeminventoryoverview-可以做什麼)、[互動製作與客製化](09-authoring-recipes.md)、[分享三種成果](10-sharing-recipes.md)、[PM 報表](06-observations.md#讓-pm-探索答案並產生報表)。

*Last modified: 2026-10-26 16:26:48*
