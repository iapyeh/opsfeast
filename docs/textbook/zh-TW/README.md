# OpsFeast 教科書

**繁體中文**

[語言選擇](../README.md) · [英文版](../en/README.md) · [維護資訊](../MAINTAINING.md)

本書從「這是什麼、解決什麼問題」開始，帶你安裝與驗收，再用一台主機走過第一個 recipe、observation 與維運 Vault。先讓基本流程真正可理解，再學多環境、自製與分享。

讀者包括系統管理者、相關 PM（產品經理）與職務代理人。你可以用 Codex、Antigravity 或其他具備必要檔案與指令能力的 AI agent；OpsFeast 不綁定特定 agent 產品。目標是讓團隊累積可重用做法與證據，把 Token 用在新需求、判斷與例外。

## 認識、安裝與驗收

| 章節 | 要回答的問題 |
| --- | --- |
| [1. 認識 OpsFeast：讓維運成果持續發揮價值](01-overview.md) | 這是什麼？解決什麼問題？如何用 recipes 解決？ |
| [2. 建立可立即使用的維運環境](02-installation.md) | Agent 如何協助 clone、檢查、提出方案並執行已同意安裝？ |
| [3. 確認安裝成果，掌握目錄用途](03-verify-installation.md) | 看哪些版本、依賴、就緒狀態？得到的目錄有什麼用途？ |

## 基本篇

| 章節 | 要回答的問題 |
| --- | --- |
| [4. hosts.yaml：主機、帳號、群組與連線](04-hosts-and-access.md) | Host/user/group 是什麼？直接與 via 怎麼設定？如何 check、測連線、su、sudo？ |
| [5. Recipe 與第一個系統盤點](05-recipes-and-inventory.md) | Recipe/bundle 是什麼？如何 list、看 inventory 參數、執行第一個 recipe、設定與取消 cron？ |
| [6. Observation：我的第一份執行證據](06-observations.md) | 為何保存 observation？如何找第一次執行、列批次與看主機結果？ |
| [7. Consumer：如何在 Vault 看到結果](07-consumers-and-vault.md) | Consumer 為何存在？隨附 Vault 怎麼將資料變成頁面，在哪裡看那次結果？ |

建議第一次依序走完，不直接對全部主機執行。各章都先講概念，再給具體設定/指令、預期結果與界線。讀到需要連線或週期操作的步驟時，先確認實際目標與授權。

## 進階篇

| 章節 | 要回答的問題 |
| --- | --- |
| [8. Profile：管理多個環境](08-profiles.md) | 為什麼分環境？查看、變更、attach、detach、開新 profile 有何差別？ |
| [9. 製作自己的 recipe](09-authoring-recipes.md) | 如何從需求重用既有模組、產生完整可重跑交付？ |
| [10. 分享 recipe 給同事](10-sharing-recipes.md) | 分享哪些檔案？同事如何審查、安裝與綁定自己的私人資料？ |

## 速查表

- [指令參考](reference.md)：OpsFeast 版本/依賴與設定盤點、hosts.yaml、recipes、inventory cron、observation、consumer、profile 管理。
- [Prompt 參考](prompts.md)：初次安裝、驗收、第一次操作、OpsFeast release 更新、SSHScript release 更新，以及保存可重用成果。

速查表供已了解流程時查找；指令中的 `python`、profile、主機與 ID 必須換成實際值。實際執行時，依各章步驟確認操作結果。

## 各章的延伸閱讀

深入內容放在相關章節的基本流程之後。第一次閱讀可先完成各章的「完成後」檢核，再依需要往下讀；日後直接從下表前往相關段落。

| 想深入了解 | 章內位置 |
| --- | --- |
| 核心物件、身分與目錄 | [第 1 章：核心物件](01-overview.md#核心物件)、[第 3 章：完整目錄](03-verify-installation.md#延伸閱讀定位資料與排程設定)、[第 8 章：身分與時間](08-profiles.md#延伸閱讀身分時間與呈現) |
| Inventory 查詢、資料新舊、排程與 CVE 應變 | [第 5 章：Inventory 深入閱讀](05-recipes-and-inventory.md#延伸閱讀inventory資料新舊與排程)、[CVE 案例](05-recipes-and-inventory.md#延伸閱讀從-cve-事件到可重用盤點) |
| 權威資料、離線報表與故障復原 | [第 6 章：保留資料](06-observations.md#延伸閱讀查詢與修復保留資料)、[報表](06-observations.md#延伸閱讀報表與重複工作)、[排除故障](06-observations.md#延伸閱讀依證據排除故障) |
| Vault 導覽、人工筆記、通知與待辦 | [第 7 章：Vault](07-consumers-and-vault.md#延伸閱讀閱讀資料與使用維運-vault)、[服務](07-consumers-and-vault.md#延伸閱讀consumer通知與待辦) |
| 保存重跑呼叫、製作完整備份檢查 | [第 9 章：保存報表](09-authoring-recipes.md#延伸閱讀保存報表與例行呼叫)、[備份案例](09-authoring-recipes.md#延伸閱讀完整案例每日備份檢查) |
| 資料移轉、封存與復原 | [第 10 章：可攜與封存](10-sharing-recipes.md#延伸閱讀製作分享移轉與封存) |

## 閱讀方式與範圍

可在 Obsidian 將 `docs/textbook/zh-TW/` 開啟為獨立教學 Vault，或用一般編輯器閱讀。不需外掛、帳號或真實維運資料。正式參考連到同一 checkout 的其他文件，部分閱讀器不允許開 Vault 外連結時，可從 checkout 或[文件索引](../../README.md)開啟。正式參考多為英文，可請 agent 協助閱讀與說明。

管理根目錄的 `vault/` 是 consumer 的維運輸出，與本教科書分開。不要把私人憑證、實際 observation 或 consumer 輸出寫進本書。範例使用假想主機與路徑，指令參數與 schema 名稱保留原文。

本書依目前 checkout 契約說明，完整執行要求相符的 SSHScript 7.0.0。產品更新後，agent 仍需依當版指引重新閱讀 schema/資料契約。TUI 以獨立人類操作為目標，更完整流程待實作、驗證後補入。Inventory cron 已實作，通用 job 排程、即時 OpsBuffet 交流與 todo 自動執行等不應當成已提供功能。

## 關於本書

我們將完整流程放在各章，精確語法與資料契約則連到正式參考文件，方便你從理解用途一路查到操作細節。遇到問題時，可以請 agent 一起閱讀相關章節與保存的結果，再決定下一步。

雙語編寫、讀者註記與版本同步方式，整理在[維護指引](../MAINTAINING.md)，供參與修訂的人使用。

*Last modified: 2026-10-26 19:45:56*
