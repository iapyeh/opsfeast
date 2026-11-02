import hostCopy from './host-draft-zh-TW.mjs';
// Design-review content only. These records never represent the owner's environment.
export default {
  back: "回上頁", backOverview: "回到總覽", workspace: "工作空間", newWindow: "另開視窗", timezone: "時間：Asia/Taipei（UTC+08:00）", notFound: "找不到這筆示範紀錄。",
  history: {title:"觀測歷史",note:"此 Recipe 的合成觀測紀錄；時間、狀態與筆數均為示範。",columns:["觀測時間","結果","涵蓋主機","保存狀態"],states:["部分完成","完成","失敗"],saved:"已保存（示範）",notSaved:"未產生資料（示範）"},
  preview: "互動版面預覽 · 下列清單均為合成示範資料，不代表你的環境。",
  pending: "待接入", empty: "沒有符合的示範項目。", filter: "篩選", all: "全部", active: "處理中", archived: "已封存",
  archive: "封存", restore: "還原", remove: "刪除", export: "匯出", import: "匯入", complete: "完成", read: "標為已讀",
  actionsNote: "此處僅呈現操作位置；封存、還原、匯入、匯出與刪除尚未接入，不會改動資料。",
  home: {title:"今天，先關心這些事", intro:"掌握需要注意的訊息，與你的 AI agent 一起安排下一步。", notifications:"優先通知", todos:"待辦工作", issues:"追蹤中的問題", more:"查看全部", badge:"示範", priority:"需要你的注意", context:"每則訊息都能追到來源、相關工作與處理紀錄。", links:[["/hosts","主機與群組","找到主機，理解最後已知狀態。"],["/recipes","Recipes","使用自己的方法，也重用內建工具。"],["/logs","活動與紀錄","回看人類與 agent 做過的事情。"]]},
  notices: [["高","demo-db-01 備份資料缺失","示範規則發現缺口；仍需確認目前情況。","備份檢查 · DEMO-ISSUE-01"],["中","demo-web-02 採集未完整完成","部分資料未知，不能視為正常。","盤點 · DEMO-RUN-02"]],
  todos: [["高","確認備份缺失原因","待處理","你與 AI agent · DEMO-ISSUE-01"],["中","檢視同事提供的 recipe","進行中","先檢閱內容，再決定是否安裝與執行。"]],
  work: {title:"工作與問題",intro:"把提醒變成工作，讓問題從發現、調查到驗證都有脈絡。", tabs:["待辦","問題","通知"], issueTitle:"DEMO-ISSUE-01 · 備份缺失",issueText:"調查中 · 關聯 demo-db-01、備份檢查 recipe 與待辦。", timeline:["發現：備份檢查產生通知","調查：人類與 agent 補充證據","處理：安排工作與經過檢閱的操作","驗證：確認恢復，再結案或重新追蹤"], lifecycle:"完成、結案、封存與刪除各有不同用途；資料由使用者管理。"},
  hosts: {...hostCopy,title:"主機與群組",intro:"找到主機、檢閱設定，並準備互動操作。",search:"Host ID 包含…",group:"群組"},
  recipes: {title:"Recipes",intro:"自己的方法放在前面，執行過程與產物也在同一個脈絡裡。",mine:"我的 Recipes",bundle:"內建 Recipes",search:"搜尋名稱或用途…",columns:["Recipe","用途","來源","檢視"],open:"開啟",back:"回到清單",tabs:["說明與參數","執行與紀錄","Observations","Retention 與成果"],selected:"示範 Recipe",description:"檢閱來源、版本、程式、依賴與參數，再選擇目標。私有主機與憑證不隨 recipe 分享。",run:"準備執行",dataNote:"觀測資料、保留資料與 recipe 是獨立的交換單位。跨 recipe 的資料仍可組合查詢。",cross:"跨 Recipe 資料",transfer:"交換與封存",transferNote:"先選擇 recipe 或 retention、資料範圍及附件，再預覽套件與衝突。匯入不會自動執行 recipe，也不會觸發歷史通知。",scope:"套件內容、來源、時間範圍、完整性與名稱衝突將在這裡確認。",rows:[["my-backup-check","每日備份檢查","使用者提供"],["my-service-report","服務狀態週報","使用者提供"],["system/inventory/overview","系統盤點","內建示範"],["feast/report/retention-summary","保留資料摘要","內建示範"]]},
  logs:{title:"活動與紀錄",intro:"按時間查閱操作與對話，展開內容，也能另開視窗比較。",search:"搜尋時間或摘要…",source:"來源",columns:["日期時間","來源","摘要"],
    rows:[["2026-11-01 10:32:08","互動式 SSHScript","互動式檢視服務狀態（示範）"],["2026-11-01 09:15:42","Recipe","備份檢查部分完成，仍有資料未知（示範）"],["2026-10-31 18:04:03","IRC（未來）","討論備份問題的處理方向（示範）"]],
    entries:[{id:"demo-session-01",lines:["[10:32:08] 示範互動 session 開始。","[10:32:09] 顯示服務狀態的合成輸出。","[10:32:12] 示範 session 結束；未連線或執行命令。"]},{id:"demo-run-02",lines:["[09:15:42] 示範備份檢查開始。","[09:15:44] 部分資料缺失，結果保留為未知。","[09:15:47] 示範檢查結束；未採集或寫入資料。"]},{id:"demo-chat-03",lines:["[18:04:03] 人類（示範）：先確認資料缺失的原因。","[18:04:15] Agent（示範）：先安排檢查，再決定後續操作。","[18:04:16] 此為合成對話，IRC 尚未接入。"]}],
    detail:"紀錄詳情",back:"回到活動與紀錄",content:"紀錄內容（合成示範）",note:"一般紀錄服務與 IRC 串接尚待實作；這不是已存在的操作紀錄。秘密資訊應在保存前處理。",play:"查看執行流程示意"},
  skills:{title:"Skills 檢閱",intro:"隨時檢視 AI agent 可參考的規則，理解工具如何被使用。",mine:"我的 Skills",bundle:"內建 Skills",open:"檢閱示範內容",source:"來源",availability:"可供參考 ≠ 本次確實使用；實際使用情形需要執行證據。",example:"示範內容；並非讀取真實 SKILL.md。",rows:[["my-operations","使用者設定","描述自己的維運慣例，指定目標與授權範圍。"],["opsfeast-recipes","內建","探索、檢閱與重用 recipe；安裝不代表授權執行。"],["sshscript","內建","依版本相符的公開契約使用互動式命令與 session。"]],metadata:"來源路徑、版本與完整原文會在接入後提供；目前不宣稱 agent 已載入。"},
  versions:{title:"版本與更新",intro:"查看目前的 OpsFeast 與 SSHScript，檢查相容版本，再決定是否升級。",current:"目前版本",unavailable:"版本讀取待接入",check:"檢查新版",upgrade:"開始升級",note:"更新功能待接入。檢查後將顯示版本差異、相容性與升級範圍；升級過程、重新啟動與結果會清楚呈現。"},
  reference:{title:"教科書與文件",intro:"學習、查閱契約，也能檢閱 agent 的 Skills。",links:[["/learn","教科書與案例"],["/docs","使用指南與資料契約"],["/skills","內建與我的 Skills"]]},
  nav:{work:"工作與問題",logs:"活動與紀錄",skills:"Skills 檢閱",reference:"教科書與文件"}
};
