export default {
 title:'主機與群組', intro:'管理目前環境的主機設定。新增、儲存與刪除只修改本機設定，不會連線主機。',
 profile:'管理環境（Profile）', add:'新增主機', empty:'目前沒有符合條件的主機。', search:'篩選 Host ID', allGroups:'全部群組', groupFilter:'依群組篩選',
 columns:['Host ID','登入帳號','群組','IP Address','備註'], disabled:'已停用', noIp:'尚無已保存的 IP 資料',
 loginRequired:'請先登入管理帳號，才能查看或修改實際主機設定。', login:'登入並管理主機', noProfile:'尚未建立管理環境，請先建立或附加 Profile。', profiles:'前往 Profiles 設定',
 loading:'正在讀取主機設定…', unavailable:'無法讀取這個 Profile 的設定，請檢查設定後再重新載入。', reload:'重新載入',
 missing:'找不到這台主機；它可能已被其他人移除。', summary:'Summary', settings:'設定', console:'互動 Console', recipes:'Recipes',
 hostId:'Host ID', immutable:'Host ID 用於對應既有紀錄，建立後在此保持唯讀。', label:'顯示名稱（可留白）', description:'備註', enabled:'啟用此主機',
 connection:'連線設定', mode:'連線方式', ssh:'SSH 連線', local:'本機', alias:'SSH Config Alias', hostname:'SSH 主機名稱／位址', user:'登入帳號', port:'Port', identityFile:'金鑰檔路徑（可留白）', sshAlias:'SSH Config Alias',
 connectionNote:'登入密碼、代理命令與進階連線設定會保留在原有檔案，此表單不會讀出或覆蓋它們。新增主機可使用現有金鑰、SSH agent 或 SSH config；密碼欄位尚未接入。',
 via:'跳板主機（可留白）', direct:'直接連線', groups:'所屬群組', groupInput:'輸入或選擇群組', groupAdd:'加入群組', groupRemove:'移除群組', groupHint:'輸入時會列出目前群組；也可輸入新群組名稱。群組順序影響設定繼承。', parentGroup:'這台主機在群組 {group} 內宣告，該群組會保留為第一個群組。',
 save:'儲存主機設定', create:'建立主機', cancel:'取消', saving:'正在驗證並儲存…', source:'設定來源', inventory:'已保存的 IP 資料', sampledAt:'資料時間', unknown:'尚無資料',
 summaryNote:'IP 來自已保存的 system inventory，僅供參考，不會用來替換 SSH 連線目標。完整 inventory 呈現尚待接入。',
 users:'已宣告帳號', usersNote:'以下顯示設定中的帳號與 sudo 設定，並不代表已驗證權限。帳密與帳號編輯將另行接入。', sudo:'sudo 設定', on:'啟用', off:'停用',
 recipesNote:'保留原有 recipe 設定。執行紀錄與 recipe 參數編輯尚待接入。', consoleNote:'此主機的互動 Console 歷程尚待接入。新增與編輯主機不會啟動 Console。',
 deleteTitle:'刪除主機設定', deleteIntro:'只移除此 Profile 中的主機定義。既有 observation、retention、工作紀錄與人類筆記會保留，也不會連線或刪除遠端主機，或停止已啟動的工作。',
 deletePrompt:'請輸入 Host ID「{host}」以確認刪除：', deleteConfirm:'確定刪除主機設定', deleteBusy:'正在驗證並刪除…', backupNote:'每次成功寫入前會在該 Profile 留下私人原檔備份，含原有敏感設定，請勿分享。',
 errors:{revision_conflict:'設定已被其他人更新，請重新載入後再修改。',host_already_exists:'Host ID 已存在，請使用不同識別。',host_is_jump_dependency:'其他主機仍使用它作為跳板，請先調整那些連線設定。',host_confirmation_required:'確認文字必須與這台主機的 Host ID 完全相同。',candidate_configuration_invalid:'設定未通過完整驗證，請檢查連線、群組與既有 recipe 設定。原檔未套用這次變更。',yaml_alias_edit_unsupported:'這份來源含 YAML 錨點／別名，目前表單尚不支援編輯。請保留原檔，透過設定檔維護。',unsupported_connection_fields:'連線包含此表單尚未支援的欄位。',connection_mode_change_unsupported:'目前不支援直接改變既有主機的連線方式。',host_writer_dependency_missing:'Server 缺少主機設定寫入依賴，請安裝 requirements-host-settings.txt。',default:'無法確認操作結果。請重新載入核對目前設定，再決定是否重試。'}
};
