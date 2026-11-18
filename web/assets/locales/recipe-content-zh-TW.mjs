export const roles={
 plan:{title:'計畫',description:'操作步驟、判斷分支與停止條件。'},
 step_contracts:{title:'步驟契約',description:'各步驟的輸入、輸出、工具需求與失敗處理。'},
 utilities:{title:'工具 routines',description:'日期選取、資料解析等可重複使用的固定處理程式。'},
 execution:{title:'執行程式與入口',description:'執行方式、實際入口檔案與對應程式。文字資源本身不會被當成入口執行。'},
 inputs:{title:'輸入參數',description:'執行時需要提供的參數與型別。'},
 outputs:{title:'結果與資料格式',description:'執行結果的 schema 與版本宣告。'},
 verification:{title:'測試與驗證',description:'測試案例、預期結果與驗證說明；有資料不代表測試已通過。'},
 dependencies:{title:'相依環境與套件',description:'需要的工具、套件版本與執行環境。'},
 permissions:{title:'權限與影響宣告',description:'需要的權限、讀寫範圍與可能副作用；宣告不代表已取得執行授權。'},
 guide:{title:'使用說明',description:'用途、使用方法、限制與結果判讀。'},
 assets:{title:'附加資源',description:'其他資料、圖片、模板或補充內容。'}
};
export const blockerLabels={
 runner_contract_missing:'尚未選定執行方式',
 runner_version_missing:'尚未指定執行契約版本',
 entrypoint_missing:'尚未提供執行入口：計畫與 routines 的文字內容不會自行執行',
 entrypoint_unavailable:'所宣告的入口檔案不存在，或不在 Recipe 目錄內',
 version_missing:'尚未指定 Recipe 版本',
 descriptor_version_missing:'尚未指定定義格式版本',
 output_schema_missing:'尚未定義執行結果的格式版本',
 static_validation_failed:'執行宣告或程式未通過靜態檢查'
};
export const fieldLabels={
 'runner.contract':'執行方式','runner.version':'執行契約版本','runner.entrypoint':'入口檔案',
 'runner.routines':'Routine 宣告','inputs.variables':'參數定義','output.schema_version':'結果格式版本',
 dependencies:'相依需求',verification:'驗證宣告',permissions:'權限需求',
 side_effects:'副作用',access_mode:'讀寫模式'
};
