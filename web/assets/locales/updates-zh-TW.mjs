export default {
  title:'版本與更新', current:'目前版本', latest:'來源版本', commit:'提交版本', check:'檢查目前版本與新版', checking:'正在查詢官方來源…', source:'版本來源', checked:'檢查時間',
  hint:'檢查只讀取官方版本資訊。是否更新由你決定，確認後交給你的 Agent 執行。',
  failed:'無法確認官方版本，請稍後重試。', unknown:'未知', missing:'未安裝',
  comparisons:{up_to_date:'目前已與來源版本一致。',local_newer:'本機版本較新或包含來源的後續開發，沒有可直接套用的新版本。',update_available:'有新版本。要交給 Agent 協助更新嗎？',comparison_unknown:'無法確認版本先後，需由 Agent 檢閱差異。',diverged:'本機與官方來源已分歧，需由 Agent 檢閱差異。'},
  localChanges:'此目錄有本機修改；更新前須保留並檢閱。', unsupported:'此 SSHScript 版本尚未列入目前 OpsFeast 的支援契約，須先評估產品支援及相符的 Skills。',
  ask:'請 Agent 協助更新', review:'請 Agent 檢閱差異', confirmTitle:'確認交給 Agent 更新', confirmText:'會產生含有目前版本、目標版本與來源的更新指示。請將指示送給你的 Agent；網站不會自行安裝或取代檔案。',
  confirm:'確認並產生更新指示', cancel:'取消', instruction:'給 Agent 的更新指示', copy:'複製更新指示', copied:'已複製，請貼到與 Agent 的對話。', copyFailed:'無法自動複製，請選取下方文字複製。',
  prompt:(data)=>`請檢查這個 OpsFeast 環境的 ${data.product==='opsfeast'?'OpsFeast':'SSHScript'} 更新，並依目前檢閱結果執行可適用的更新。\n${data.origin?'網站：'+data.origin+'\n':''}目前版本：${data.current.version||'未知'}${data.current.commit?'，commit '+data.current.commit:''}\n檢查時的目標版本：${data.latest.version}${data.latest.commit?'，commit '+data.latest.commit:''}\n官方來源：${data.source}\n檢查時間：${data.checked_at}\n以指示中的目標版本／commit 為本次範圍；若來源已變更，先說明差異並確認新目標。請先重新確認版本、來源及相容性，遵守 AGENTS.md、AGENTS.local.md 與 docs/skill-updates.md 的更新流程。先依 docs/update-preservation.md 記錄並核對原本的 installation-data、網址／port、管理者帳密、Profile 實際目錄、自訂分類／套餐、recipe 預設值與資料。沿用既有設定，不重新初始化或重設帳號；若本次 OpsFeast 更新需要把舊 registry port 移到外部資料，僅依文件執行有備份的 migrate-port，維持原值。保留未提交修改、私有資料、安裝識別、站台設定、Profile 登記及既有管理環境。不得覆寫或自行 stash/reset 本機修改；若無法安全套用，請說明差異與需要的決定。SSHScript 必須使用此 OpsFeast 支援的版本及完整相符 Skill，不能只因較新就繞過支援限制。使用既有 interpreter，保留備份，執行必要的本機驗證。OpsFeast 更新後請重新閱讀新版本的物件 schema、資料契約及相關 Skills。若需要重啟，請保留啟動設定並恢復網站。此指示不授權 commit/push、主機連線或遠端操作。\n請回報實際更新、保留未變更、受阻及驗證結果。`,
};
