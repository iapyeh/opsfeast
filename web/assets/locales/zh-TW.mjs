// Authoring locale. Add other languages only after explicit translation approval.
import firstUse from "./first-use-zh-TW.mjs";
import hostManagement from "./host-management-zh-TW.mjs";
export default {
  firstUse, hostManagement,
  locale: "zh-TW",
  languageName: "繁體中文",
  shell: {
    title: "OpsFeast · 工作台", skip: "跳至主要內容", navigation: "主要導覽",
    brand: "維運工作空間", workspace: "本機工作台", noProfile: "尚未選擇 profile",
    area: "工作空間", reference: "教科書與文件", home: "總覽", operations: "操作工作台",
    hosts: "主機與群組", recipes: "Recipes", retention: "資料與成果", apps: "應用與呈現",
    learn: "教材與案例", docs: "文件與契約", preview: "設計預覽", previewTag: "預覽",
    user: "登入後畫面示意", guest: "尚未登入", local: "本機介面原型",
    server: "FastAPI + Uvicorn · 預設連接埠 8740", language: "介面語言",
    languageHint: "目前僅有繁體中文；英文版將於內容確認後翻譯。",
    notice: "站台、Profiles 與主機設定已接入實際資料；其他管理版面仍有規劃預覽。",
    previewNumber: "原型 02", back: "回到總覽", planned: "設計方向 · 尚未接入",
    plannedShort: "規劃中", footer: "看得見、停得下來、查得到發生過什麼事。",
    localPreview: "本機原型", modified: "最後修改：{time}", guestLink: "查看未登入畫面",
    workspaceLink: "預覽工作台", loginLink: "登入", entry: "入口"
  },
  home: {
    kicker: "掌握操作，理解環境", title: "每一步，都看得見。",
    intro: "從理解環境到採取行動，在同一個工作台掌握過程與證據。",
    action: "探索操作工作台", metricsLabel: "資料連接狀態",
    metrics: [["管理主機", "—", "尚未載入主機設定", "▤"], ["進行中操作", "—", "尚未接入執行服務", "⌘"], ["待核准事項", "—", "核准機制尚未實作", "◇"], ["資料更新時間", "未載入", "畫面即時，不代表採集即時", "◷"]],
    start: "從這裡開始", startHint: "一個入口，連起操作與知識",
    entries: [
      {path: "/operations", icon: "⌘", color: "teal", kicker: "操作", title: "透明地操作", text: "看清計畫、命令與輸出，依約定核准，隨時提出停止。", action: "進入操作工作台"},
      {path: "/retention", icon: "▥", color: "sand", kicker: "理解", title: "以證據理解環境", text: "查閱保留資料、結果與來源，辨識新鮮度、不完整與未知。", action: "探索資料與成果"},
      {path: "/learn", icon: "▱", color: "blue", kicker: "學習與建立", title: "學習，也累積自己的方法", text: "從教材到 recipes，再到自己的資料契約與 Web 呈現。", action: "開啟教材與案例"}
    ],
    flowTitle: "操作的每個階段，都有交代", flowLabel: "互動流程示意",
    steps: [["檢視計畫", "目標、權限與影響"], ["依約定核准", "沿用已授權範圍"], ["觀看執行", "直接輸出與停止"], ["核對成果", "結果、清理與證據"]],
    flowNote: "停止已受理、遠端程序結束與清理完成，會分別呈現。",
    own: "建立自己的方法", ownTitle: "也為你的應用，留一個位置。",
    ownText: "使用者 recipes、retention 與自訂 presentation，共用資料與介面契約。",
    ownAction: "查看擴充方向"
  },
  auth: {
    welcomeTitle: "讓每一次維運，都有脈絡。", welcomeIntro: "在同一個工作空間，連起環境、操作與知識。看清楚正在發生的事，再決定下一步。",
    welcomeKicker: "歡迎來到 OpsFeast", loginAction: "登入工作台", learnAction: "先認識 OpsFeast",
    publicNote: "這是未登入入口的設計示意。主機、操作與私有資料不在這個入口呈現。",
    features: [["看得見", "計畫、輸出與證據，在同一個情境裡。"], ["停得下來", "依約定核准，也能清楚提出停止。"], ["累積得起來", "把經驗留下，成為可重複的 recipe 與呈現。"]],
    illustrationTitle: "一個入口，掌握整個工作流程", illustrationLabel: "工作空間示意",
    illustrationSteps: ["理解環境", "檢視計畫", "觀看執行", "核對成果"],
    illustrationNote: "來源有依據 · 資料有時間 · 未知有標示",
    loginTitle: "登入你的工作台", loginIntro: "登入後，依你的身分與授權範圍開啟工作空間。",
    loginKicker: "歡迎回來", formLabel: "登入版面示意", account: "帳號", password: "密碼",
    accountPlaceholder: "帳號欄位示意", passwordPlaceholder: "此原型不接收密碼",
    formNote: "驗證服務尚未接入，帳密欄位停用，不會收集或傳送憑證。",
    previewAction: "預覽登入後工作台", previewHint: "僅切換到工作台版面，不會建立登入狀態或授予權限。",
    back: "回到入口", help: "需要使用說明？", docsAction: "查看文件",
    accountNote: "管理帳號已提供本機登入；多使用者與個別 agent 憑證仍待實作。"
  },
  demo: {
    start: "播放流程示意", stop: "停止示意", label: "純前端模擬 · 合成內容",
    terminal: "本機模擬 / 沒有主機連線", idle: "等待播放。沒有實際操作。",
    state: "操作狀態：{state}", notStarted: "未開始",
    frames: [
      ["[示意] 計畫：檢視 demo-host 的已保存資料\n[示意] 授權：僅限示範流程，沒有實際請求", "計畫已展示"],
      ["[示意] 讀取已保存的結果…\n[示意] 資料距今 2 小時 · 涵蓋情形：部分完成", "執行中（合成內容）"],
      ["[示意] 收尾：分別確認結果、retention 與 consumer 狀態", "收尾中"],
      ["[示意] 流程結束。沒有連線、執行或寫入資料。", "示意結束"]
    ],
    stoppedOutput: "[示意] 已停止播放。沒有遠端程序需要終止。",
    stopped: "示意已停止（不是遠端終止驗證）"
  },
  settings: {
    title: "設定", kicker: "依你的方式，管理工作空間", intro: "從工作空間的樣貌，到主機、recipes 與資料政策，都在這裡設定。",
    principle: "Web、CLI 與 agent API 共用設定服務、驗證與授權規則。變更設定不等於連線、執行或重新採集。",
    available: "可使用", planned: "規劃中", open: "開啟設定", explore: "查看規劃", back: "回到設定專區",
    installation: "整個 installation", profile: "依 profile 管理", boundaries: "作用範圍與變更邊界",
    service: "共用介面", implemented: "已提供 Web、CLI 與 Python／HTTP API。", pending: "目前提供規劃說明，尚無此類設定的 Web 寫入介面。",
    catalogError: "設定能力目錄讀取失敗，請重新載入；目前無法確認可用功能。", catalogLabel: "以目前 server 的能力目錄為準",
    categories: {
      profiles: {title: "Profiles", text: "查看目前預設 profile、環境狀態，建立或切換管理環境。", detail: "沿用 Core 的 profile 管理，現有管理目錄保持原處。", rules: ["不連線、不採集、不執行 recipe。"]},
      site: {title: "站台設定", text: "網站名稱、標語、Logo、代表角色與管理帳號。", detail: "屬於整個 installation，保存在產品目錄外。公開內容會出現在未登入頁。", rules: ["保留原有 UUID、name 與 namespace。", "可換上自己的圖片，也能恢復預設圖案。"]},
      hosts: {title: "主機與連線設定", text: "管理 hosts.yaml、主機、群組、連線方式與帳號。", detail: "依選定 profile 的實際 hosts.yaml 與 include 結構編輯，保留人類註記與私有憑證。", rules: ["區分設定驗證與連線測試；儲存不觸發連線。", "敏感值需遮蔽並個別授權修改，不用空白覆蓋既有密碼。", "先檢視差異，再以版本檢查保存，避免覆蓋他人修改。"]},
      recipes: {title: "Recipes 管理", text: "來源註冊、可用範圍、啟用設定與內容檢視。", detail: "重用既有 recipe catalog、sources 與安裝契約。下載、安裝、啟用及執行是不同動作。", rules: ["安裝或啟用不自動授權主機操作。", "保留精確來源、版本與完整性證據。", "使用者程式保存在管理環境或外部來源，不寫進 bundled recipes。"]},
      parameters: {title: "預設參數與執行政策", text: "設定 recipe 的預設值、群組覆寫與主機覆寫。", detail: "遵守既有參數 schema、精確 recipe reference 與繼承規則，讓人類與 agent 看到相同的有效值。", rules: ["顯示值從哪一層而來，以及最終會套用的值。", "更新預設值不改寫既有結果，也不自動重跑工作。", "不另建一份只供 Web 使用的參數設定。"]},
      retention: {title: "Retention 政策與資料管理", text: "設定保存行為、檢視資料定義與管理已保存內容。", detail: "區分 recipe 定義的資料契約、平台保存政策及使用者的內容管理。consumer 只管理自己的衍生成果。", rules: ["政策修改、重建、重播、匯入與刪除分開授權。", "破壞性動作必須先預覽範圍，保留受保護的操作證據。", "透過既有 retention API，不直接修改 SQLite 或人類筆記。"]}
    }
  },
  admin: {
    title: "管理帳號", configured: "已設定", unconfigured: "尚未設定", username: "管理員 username",
    usernameHint: "3–64 個英文字母、數字、點、連字號或底線。", currentPassword: "目前的密碼",
    newPassword: "新的密碼", confirm: "再次輸入新的密碼", passwordHint: "密碼須為 12–256 個 Unicode 字元，可含中文與 emoji；不會以明文保存。",
    bootstrapHint: "請自行設定管理帳號。首次設定使用本機編輯憑證，沒有預設帳號或密碼。",
    changeHint: "變更 username 與密碼需要目前密碼；儲存後所有登入工作階段都會失效。",
    setupRequired: "管理帳號尚未保存。請先解鎖本機編輯，在此填寫帳密，再按「建立管理帳號」。儲存站台外觀不會建立帳號。", changeLoginHint: "管理帳號已建立。登入後，可在這裡輸入目前密碼，修改 username 與密碼。", recoveryTitle: "如何修改帳密／忘記時怎麼辦？", recoveryHint: "修改帳密：登入後到「站台設定 → 管理帳號」，輸入目前密碼與新帳密。忘記 username 可由本機帳號狀態查詢；忘記密碼目前尚未提供重設功能。本機外觀編輯憑證不能重設既有帳號，請保留原有資料。",
    setup: "建立管理帳號", change: "更新管理帳號", login: "前往登入", logout: "登出",
    locked: "管理帳號設定需要管理員登入；尚未建立帳號時，請先解鎖本機編輯。",
    mismatch: "兩次輸入的新密碼不同。", saved: "管理帳號已保存，請重新登入。",
    invalid: "目前密碼不正確或登入已過期。", conflict: "帳號已被其他人更新，請重新載入。", failed: "帳號設定失敗，請檢查格式與登入狀態。",
    notReady: "尚未建立管理帳號，請先到站台設定完成首次設定。", signIn: "登入工作台", loginFailed: "帳號或密碼不正確。",
    limited: "登入嘗試過於頻繁，請稍後再試。", unavailable: "無法確認登入狀態，請檢查本機服務。", authenticated: "管理員：{username}",
    loginHint: "使用這個 installation 的管理帳號登入。", configuredNote: "登入後可以管理站台與 profiles；主機操作服務尚未啟用。"
  },
  profiles: {
    title: "Profiles", kicker: "管理環境", intro: "查看與切換目前環境，或建立獨立的管理空間。",
    current: "目前預設 profile", none: "尚未選擇", name: "Profile 名稱", namespace: "Namespace", root: "既有管理目錄的絕對路徑",
    create: "建立新的 profile", attach: "附加既有環境", use: "切換為預設", active: "目前預設", available: "設定可用", unavailable: "設定不可用",
    namespaceHint: "留白沿用 profile 名稱；新的管理目錄建立於持久資料目錄的 profiles/ 下。",
    attachHint: "只驗證並註冊既有環境，不重建或覆寫其資料。", statusHint: "此狀態只代表本機設定可用性，不代表已驗證主機連線。",
    boundary: "建立、附加與切換不會連線、採集或執行 recipe。現有 profile 與 namespace 保持原處；目前未提供更名或刪除。",
    saving: "正在保存 profile 設定…", saved: "Profile 設定已保存。", conflict: "Profile 設定已被更新，請重新載入後再操作。",
    failed: "Profile 操作失敗，請檢查名稱、namespace 與目錄。若建立途中失敗，可能保留新目錄，請先檢查再重試。",
    loginRequired: "請先設定管理帳號並登入，才能查看或變更 profiles。", empty: "尚未註冊任何 profile。", unknown: "未知"
  },
  site: {
    defaultName: "我的維運基地", defaultSlogan: "你的系統，你的節奏。",
    title: "站台設定", kicker: "打造自己的地方", intro: "名字、圖案與一句話，讓這裡成為你的維運基地。",
    poweredBy: "技術支援：OpsFeast", configure: "設定", logoAlt: "工作空間標誌", avatarAlt: "工作空間代表角色",
    avatarTitle: "這裡，可以住著你的守護角色。", avatarNote: "喜歡的角色、一包乖乖，或只是讓你安心的圖案。",
    avatarEmpty: "目前使用預設圖案，可以換上你喜歡的角色或乖乖。", avatarAction: "放上我的代表圖案", guardian: "基地守護者",
    loadError: "網站設定讀取失敗。請檢查設定檔；目前顯示中性預設版面。",
    publicWarning: "這裡設定的名稱、標語與圖片會出現在未登入頁面，請選擇適合公開的內容。",
    name: "網站名稱", inheritName: "留白時沿用 installation name；未設定名稱時顯示中性預設標題。",
    slogan: "網站標語", sloganHint: "一句屬於這個地方的話，最多 160 個字。",
    logo: "網站 Logo", logoHint: "導覽與識別用，適合方形圖案。", avatar: "代表角色／守護圖案",
    avatarHint: "首頁的陪伴圖案；可以是角色、乖乖或自己的插畫。",
    imageRules: "PNG 或 JPEG，最多 2 MiB、4096 × 4096 像素；保存為不超過 1024 × 1024 的 PNG，移除中繼資料。",
    chooseImage: "選擇圖片", removeImage: "恢復預設圖案", noImage: "目前使用 OpsFeast 預設圖案",
    imagePending: "目前僅預覽，尚未上傳。請按「儲存站台外觀」套用。", imageRemoved: "尚未儲存。按「儲存站台外觀」後使用預設圖案；保留原有圖片檔案。",
    identity: "Installation 識別（唯讀）", identityHint: "這些設定不會修改 UUID、既有 name 或各 profile 的 namespace。",
    namespaceHint: "Namespace 屬於各 profile，這裡不修改。", inherited: "既有名稱", unknownIdentity: "尚未初始化識別",
    unlockTitle: "本機編輯權限（30 分鐘）", token: "本機編輯憑證", tokenPlaceholder: "貼上本次 server 的編輯憑證",
    tokenHint: "在 installation 持久資料目錄讀取 .opsfeast-web-edit-8740.token（使用其他 port 時依 port 命名）。解鎖後同一瀏覽器可維持編輯 30 分鐘，換頁與重新整理不需重貼憑證；結束編輯、逾時或 Server 重啟會失效。不授予 profile 管理權限。",
    unlock: "解鎖設定", lock: "結束編輯", unlocked: "本機編輯已解鎖；30 分鐘內換頁或重新整理可恢復。管理帳號表單位於下方。", locked: "本頁尚未解鎖，或先前編輯權限已逾時／因 Server 重啟失效。已保存的站台外觀不受影響。",
    appearance: "站台外觀", appearanceUnlocked: "本機權限已驗證，可以設定外觀。", saveScope: "名稱、標語、Logo 與代表圖案一起儲存", saveHint: "選擇圖片只會預覽；按下儲存後才會上傳並套用。管理帳號在下方另外儲存。", unsaved: "有尚未儲存的外觀變更，請按「儲存站台外觀」。",
    save: "儲存站台外觀", saving: "正在驗證圖片並儲存…", saved: "設定已儲存，頁面已套用。", failed: "儲存失敗，未完成的變更仍保留在表單。",
    conflict: "設定已被其他人更新，請重新載入後再編輯。", unauthorized: "編輯憑證無效或 server 已重啟，請取得本次憑證。",
    invalid: "設定或圖片無效，請檢查字數、格式與尺寸。", uploadLimit: "圖片超過 2 MiB，請選擇較小的檔案。",
    network: "無法連線到本機 server，請確認服務仍在執行。", preview: "目前設定", remaining: "站台外觀與管理帳號分開保存；這些設定不會授權主機操作。",
    settingsNote: "可使用管理員登入身分編輯；首次設定也可使用本機編輯憑證。"
  },
  pages: {
  operations: {title: "操作工作台", kicker: "操作流程", intro: "把計畫、核准、即時輸出與停止，放在同一個情境。", cards: [["先看清楚，再開始", "每項操作呈現目標、版本、參數、權限與效果。既有授權範圍沿用。"], ["輸出直接到畫面", "執行程序直接傳送進度與輸出；人類與 agent 共用同一操作契約。"], ["停止也有可核對的結果", "停止受理、遠端終止、清理及操作成果分開呈現，保留未知。"]], note: "下面只演示畫面變化；按鈕只改變瀏覽器內的文字，不會建立連線或執行任何命令。"},
  hosts: {title: "主機與群組", kicker: "環境概況", intro: "把設定、最後已知狀態與原始證據連在一起。", cards: [["主機", "查看連線設定、已保存事實與相關操作。此原型未讀取 hosts.yaml。"], ["群組", "依既有群組呈現成員與涵蓋情形，不把資料缺口視為正常。"], ["Inventory", "區分歷史查詢、明確採集與排程；開啟頁面不會觸發採集。"]], note: "目前為版面預覽。實際資料將透過 Core 與既有公開介面接入。"},
  recipes: {title: "Recipes", kicker: "可重複的操作", intro: "累積經過檢視的操作，讓下一次可以重複使用。", cards: [["發現與檢視", "呈現來源、支援平台、輸入、版本、依賴與驗證限制。"], ["準備執行", "選擇目標與參數，產生可供核對的操作計畫。此原型未提供執行能力。"], ["自己的 recipe", "保留在管理環境或外部來源，私有 bindings 不進入產品原始碼。"]], note: "Recipe、retention 與 presentation 可組合，但各自有獨立契約及授權範圍。"},
  retention: {title: "資料與成果", kicker: "資料與證據", intro: "資料有時間、有來源，也有不完整與未知。", cards: [["Observations 與結果", "查閱批次與主機結果，分開呈現執行、清理、保存與內容更新狀態。"], ["Retention", "沿用權威儲存與查詢契約，不另外建立 Web 資料庫。"], ["報告與 Vault", "連結產物、來源時間、consumer 處理結果與閱讀輸出。"]], note: "畫面更新不會改變採樣時間。此原型未讀取 observations、retention 或 Vault。"},
  apps: {title: "應用與呈現", kicker: "自己的應用", intro: "讓你的資料，有自己的閱讀與操作方式。", cards: [["Presentation", "不必附屬 consumer；可以直接查詢 retention，呈現特定領域的視圖。"], ["共用 utilities 與 libraries", "規劃提供公開元件、資料讀取與事件介面；此原型尚無擴充 SDK。"], ["明確註冊與權限", "自訂 route、依賴、資料來源與副作用需宣告。啟用 consumer 不等於啟用任意 Web 程式。"]], note: "未來 profile 內的應用路徑規劃為 /p/:profile/apps/:presentationId/*view；目前尚未註冊任何使用者程式。"},
  learn: {title: "教材與案例", kicker: "與 OpsFeast 一起學習", intro: "從理解概念，到與自己的 AI agent 一起完成工作。", cards: [["理解 OpsFeast", "學習 profiles、主機、recipes、retention 與 consumer 的關係。"], ["從意圖到成果", "練習表達目標、界定範圍、檢視授權及判讀結果。"], ["建立可重複的方法", "從案例累積 recipe、資料契約與自己的 presentation。"]], note: "這是教材入口的版面預覽；章節內容尚未接入。既有 docs/textbook/ 保持原有權威來源。"},
  docs: {title: "文件與契約", kicker: "參考依據", intro: "人類與 agent，都能找到同一份準確的使用依據。", cards: [["使用指南與 CLI", "沿用既有功能命名與契約；Web 與 CLI 共用服務邏輯。"], ["資料與服務契約", "查閱版本、輸入輸出、時間、失敗狀態與驗證限制。"], ["Agent 能力目錄", "發現 bundled utilities、libraries 與規則，優先使用已提供的功能。"]], note: "這是文件入口的版面預覽；文件閱讀與搜尋尚未接入。沒有把 repository 根目錄掛載為靜態網站。"}
}
};
