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
    user: "尚未登入", guest: "尚未登入", local: "本機工作空間",
    server: "每套安裝獨立連接埠", language: "介面語言",
    languageHint: "目前僅有繁體中文；英文版將於內容確認後翻譯。",
    notice: "資料依目前選定的 Profile 顯示；開啟頁面不會連線主機或執行工作。",
    previewNumber: "本機工作空間", back: "回到總覽", planned: "設計方向 · 尚未接入",
    plannedShort: "規劃中", footer: "看得見、停得下來、查得到發生過什麼事。",
    localPreview: "本機工作空間", modified: "最後修改：{time}", guestLink: "查看未登入畫面",
    workspaceLink: "開啟工作台", loginLink: "登入", entry: "入口"
  },
  auth: {
    welcomeTitle: "讓每一次維運，都有脈絡。", welcomeIntro: "在同一個工作空間，連起環境、操作與知識。看清楚正在發生的事，再決定下一步。",
    welcomeKicker: "歡迎來到 OpsFeast", loginAction: "登入工作台", learnAction: "先認識 OpsFeast",
    publicNote: "登入後可查看管理環境、已保存資料與工作紀錄。",
    features: [["看得見", "計畫、輸出與證據，在同一個情境裡。"], ["停得下來", "依約定核准，也能清楚提出停止。"], ["累積得起來", "把經驗留下，成為可重複的 recipe 與呈現。"]],
    loginTitle: "登入你的工作台", loginIntro: "登入後，依你的身分與授權範圍開啟工作空間。",
    loginKicker: "歡迎回來", formLabel: "管理帳號登入", account: "帳號", password: "密碼",



    back: "回到入口", help: "需要使用說明？", docsAction: "查看文件",
    accountNote: "你以管理帳號登入；agent 使用獨立的網站最高權限，依你的指示操作。"
  },
  settings: {
    title: "設定", kicker: "依你的方式，管理工作空間", intro: "從工作空間的樣貌，到主機、recipes 與資料政策，都在這裡設定。",
    principle: "Web、CLI 與 agent API 共用設定服務、驗證與授權規則。變更設定不等於連線、執行或重新採集。",
    available: "可使用", planned: "規劃中", open: "開啟設定", explore: "查看規劃", back: "回到設定專區",
    installation: "整個 installation", profile: "依 profile 管理", boundaries: "作用範圍與變更邊界",
    service: "共用介面", implemented: "已提供 Web、CLI 與 Python／HTTP API。", pending: "目前提供規劃說明，尚無此類設定的 Web 寫入介面。",
    catalogError: "設定能力目錄讀取失敗，請重新載入；目前無法確認可用功能。", catalogLabel: "以目前 server 的能力目錄為準",
    parametersHelpLabel: "設定方式（尚無 Web 編輯器）",
    parametersWhere: "Bundle Recipe 的參數設定位置", parametersOwnership: "Bundle 程式由各 Profile 共用；參數、啟用狀態及執行政策分別由各 Profile 管理，使用者 Recipes 也使用相同規則。",
    parametersFile: "設定檔：", parametersGenericPath: "所選 Profile 的管理目錄/hosts.yaml", parametersNoEditor: "目前 Web 尚未提供參數編輯器。可在對話中請 Agent 協助設定，或直接修改這個 Profile 的 hosts.yaml。此頁不會變更任何設定。",
    parametersSteps: ["Profile 共用值：default.recipes.<完整 Recipe 參照>.vars。", "只套用到特定群組或主機：在該群組或主機的 recipes.<同一參照>.vars 覆寫。", "Bundle 使用 system/network/check/port 這類完整路徑；使用者 Recipe 使用 :分類/路徑。不要修改產品內建 Recipe 的程式或描述檔來設定自己的參數。"],
    parametersExample: "範例：設定 Bundle Recipe 的 Profile 預設參數（不會啟用或執行 Recipe）", parametersYaml: "default:\n  recipes:\n    system/network/check/port:\n      vars:\n        port: 443", parametersPrecedence: "同一 Recipe 的值依主機覆寫、群組覆寫、Profile 預設及 Recipe 預設值套用；單次執行的 --var／--vars-file 只影響該次執行。完整合併規則請見指南。", parametersGuide: "閱讀參數與繼承規則", parametersChooseProfile: "選擇或管理 Profiles",
    readOnly: "唯讀檢閱", profileHierarchy: "每個 Profile 擁有自己的主機、使用者 Recipes、預設參數與資料政策。", ownedBy: "隸屬於 Profile：{profile}",
    categories: {
      execution: {title:"執行設定",text:"設定 Recipes 的預設同時執行數；每次執行也能臨時調整。",detail:"預設 8 threads，主機台數不限；同一主機內依序執行。",rules:["儲存設定不會執行工作。"]},
      "bundle-recipes": {title: "Bundle Recipes", text: "獨立檢閱隨 OpsFeast 提供的內建 Recipes、版本及契約。", detail: "內建程式隨產品更新；各 Profile 的執行啟用與參數仍在該 Profile 管理。", rules: []},
      profiles: {title: "Profiles", text: "查看目前預設 profile、環境狀態，建立或切換管理環境。", detail: "沿用 Core 的 profile 管理，現有管理目錄保持原處。", rules: ["不連線、不採集、不執行 recipe。"]},
      site: {title: "站台設定", text: "網站名稱、標語、Logo、代表角色與管理帳號。", detail: "屬於整個 installation，保存在產品目錄外。公開內容會出現在未登入頁。", rules: ["保留原有 UUID、name 與 namespace。", "可換上自己的圖片，也能恢復預設圖案。"]},
      hosts: {title: "主機與連線設定", text: "管理 hosts.yaml、主機、群組、連線方式與帳號。", detail: "依選定 profile 的實際 hosts.yaml 與 include 結構編輯，保留人類註記與私有憑證。", rules: ["區分設定驗證與連線測試；儲存不觸發連線。", "敏感值需遮蔽並個別授權修改，不用空白覆蓋既有密碼。", "先檢視差異，再以版本檢查保存，避免覆蓋他人修改。"]},
      recipes: {title: "使用者 Recipes", text: "這個 Profile 的自訂 Recipes 與已註冊外部來源。", detail: "重用既有 recipe catalog、sources 與安裝契約。下載、安裝、啟用及執行是不同動作。", rules: ["安裝或啟用不自動授權主機操作。", "保留精確來源、版本與完整性證據。", "使用者程式保存在管理環境或外部來源，不寫進 bundled recipes。"]},
      parameters: {title: "預設參數與執行政策", text: "Bundle 與使用者 Recipes 的 Profile 預設值、群組與主機覆寫。", detail: "遵守既有參數 schema、精確 recipe reference 與繼承規則，讓人類與 agent 看到相同的有效值。", rules: ["顯示值從哪一層而來，以及最終會套用的值。", "更新預設值不改寫既有結果，也不自動重跑工作。", "不另建一份只供 Web 使用的參數設定。"]},
      retention: {title: "Retention 政策與資料管理", text: "設定保存行為、檢視資料定義與管理已保存內容。", detail: "區分 recipe 定義的資料契約、平台保存政策及使用者的內容管理。consumer 只管理自己的衍生成果。", rules: ["政策修改、重建、重播、匯入與刪除分開授權。", "破壞性動作必須先預覽範圍，保留受保護的操作證據。", "透過既有 retention API，不直接修改 SQLite 或人類筆記。"]}
    }
  },
  admin: {
    title: "管理帳號", configured: "已設定", unconfigured: "尚未設定", username: "管理員 username",
    usernameHint: "3–64 個英文字母、數字、點、連字號或底線。", currentPassword: "目前的密碼",
    newPassword: "新的密碼", confirm: "再次輸入新的密碼", passwordHint: "密碼不可為空字串，可使用任意非空字串，沒有長度下限或大小寫、數字與符號組合要求；不會以明文保存。",
    bootstrapHint: "請在對話中請 agent 設定管理帳號與密碼，沒有預設帳號或密碼。",
    changeHint: "變更 username 與密碼需要目前密碼；儲存後所有登入工作階段都會失效。",
    setupRequired: "管理帳號尚未保存。請在對話中請你的 agent 建立帳號與密碼，完成後再登入。", changeLoginHint: "管理帳號已建立。登入後，可在這裡輸入目前密碼，修改 username 與密碼。", recoveryTitle: "如何修改帳密／忘記時怎麼辦？", recoveryHint: "修改帳密：登入後到「站台設定 → 管理帳號」，輸入目前密碼與新帳密。忘記 username 可由本機帳號狀態查詢；忘記密碼時，可在對話中請你的 agent 設定新密碼，也可以請 agent 產生。Agent 使用獨立的網站最高權限，不需要你的舊密碼。",
    setup: "建立管理帳號", change: "更新管理帳號", login: "前往登入", logout: "登出",
    locked: "管理帳號設定需要管理員登入；尚未建立帳號或忘記密碼時，請在對話中請 agent 設定。",
    mismatch: "兩次輸入的新密碼不同。", saved: "管理帳號已保存，請重新登入。",
    invalid: "目前密碼不正確或登入已過期。", conflict: "帳號已被其他人更新，請重新載入。", failed: "帳號設定失敗，請檢查格式與登入狀態。",
    notReady: "尚未建立管理帳號，請先到站台設定完成首次設定。", signIn: "登入工作台", loginFailed: "帳號或密碼不正確。",
    limited: "登入嘗試過於頻繁，請稍後再試。", unavailable: "無法確認登入狀態，請檢查本機服務。", authenticated: "管理員：{username}",
    loginHint: "使用這個 installation 的管理帳號登入。", configuredNote: "登入後可以管理站台與 profiles；主機操作服務尚未啟用。"
  },
  profiles: {
    description: "說明（Description）", noDescription: "尚未設定說明。", editDescription: "編輯說明", saveDescription: "儲存說明", cancelDescription: "取消", descriptionHint: "最多 1000 個字；留白可清除。這是 Profile 登記的用途說明，不會改變名稱、目錄、Namespace、主機或預設選擇。",
    title: "Profiles", kicker: "管理環境", intro: "查看與切換目前環境，或建立獨立的管理空間。",
    current: "目前預設 profile", none: "尚未選擇", name: "Profile 名稱", namespace: "Namespace", root: "既有管理目錄的絕對路徑",
    create: "建立新的 profile", attach: "附加既有環境", use: "切換為預設", active: "目前預設", available: "設定可用", unavailable: "設定不可用",
    namespaceHint: "留白沿用 profile 名稱；新的管理目錄建立於持久資料目錄的 profiles/ 下。",
    manageEnvironments: "建立或登記管理環境", manageHint: "這些操作會增加 Profile 登記，不屬於上面任何一個既有 Profile。",
    attachExplanation: "將磁碟上已存在的 Feast 管理目錄登記成 Profile，沿用其中的主機設定、Recipes、保存資料與 Vault。適合登記既有環境，或重新接回原有資料；目前已列出的 Profiles 不需要再附加。",
    attachHint: "請指定含 hosts.yaml 的既有管理目錄。只驗證並登記，不複製、搬移、重建或覆寫其資料。", statusHint: "此狀態只代表本機設定可用性，不代表已驗證主機連線。",
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
    unlockTitle: "網站設定權限", token: "本機編輯憑證", tokenPlaceholder: "由 agent 協助，或先登入管理員帳號",
    tokenHint: "請在對話中請 agent 協助設定網站，或登入管理員帳號。Agent 的最高權限憑證只留在執行環境記憶體，不提供給此頁貼上；服務重啟即失效。",
    unlock: "解鎖設定", lock: "結束編輯", unlocked: "本機編輯已解鎖；30 分鐘內換頁或重新整理可恢復。管理帳號表單位於下方。", locked: "本頁尚未解鎖，或先前編輯權限已逾時／因 Server 重啟失效。已保存的站台外觀不受影響。",
    appearance: "站台外觀", appearanceUnlocked: "本機權限已驗證，可以設定外觀。", saveScope: "名稱、標語、Logo 與代表圖案一起儲存", saveHint: "選擇圖片只會預覽；按下儲存後才會上傳並套用。管理帳號在下方另外儲存。", unsaved: "有尚未儲存的外觀變更，請按「儲存站台外觀」。",
    save: "儲存站台外觀", saving: "正在驗證圖片並儲存…", saved: "設定已儲存，頁面已套用。", failed: "儲存失敗，未完成的變更仍保留在表單。",
    conflict: "設定已被其他人更新，請重新載入後再編輯。", unauthorized: "請先登入管理員帳號，或在對話中請 agent 協助設定。",
    invalid: "設定或圖片無效，請檢查字數、格式與尺寸。", uploadLimit: "圖片超過 2 MiB，請選擇較小的檔案。",
    network: "無法連線到本機 server，請確認服務仍在執行。", preview: "目前設定", remaining: "站台外觀與管理帳號分開保存；這些設定不會授權主機操作。",
    settingsNote: "可登入管理員帳號編輯，或在對話中請 agent 協助設定。"
  }
};
