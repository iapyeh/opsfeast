// Browser upload helpers; immutable document files stay scoped to one host note.
export const bundleScope=(scope,note_uuid,bundle_uuid)=>({...scope,note_uuid,bundle_uuid});
export function bundleReaderUrl(scope){return '/note-attachments?'+new URLSearchParams(scope);}
export function bundleAttachmentMarkup(note,e,scope){
  return `<section class="note-attachments"><h4>文件包附件</h4>${(note.attachments||[]).map(bundle=>`<div class="note-attachment"><a href="${e(bundleReaderUrl(bundleScope(scope,note.uuid,bundle.uuid)))}" target="_blank" rel="noopener noreferrer">${e(bundle.title)} ↗</a><small>${bundle.kind==='html'?'HTML／互動文件':'Markdown 文件'} · ${bundle.file_count} 個檔案 · ${e(bundle.entry)}</small><a href="/api/v1/note-bundles/export?${e(new URLSearchParams(bundleScope(scope,note.uuid,bundle.uuid)).toString())}">下載 ZIP</a><button class="text-button danger" type="button" data-bundle-delete="${e(bundle.uuid)}" data-bundle-note="${e(note.uuid)}">刪除附件</button></div>`).join('')||'<p class="field-hint">尚無附件。</p>'}<button class="button" type="button" data-note-attach="${e(note.uuid)}">加入文件包</button></section>`;
}
export function folderFiles(files){
  return [...files].map(file=>({file,path:file.webkitRelativePath?file.webkitRelativePath.split('/').slice(1).join('/'):file.name}));
}
export async function encodedFiles(files){
  const entries=folderFiles(files);
  if(!entries.length||entries.length>256||entries.some(({file})=>file.size>16*1024*1024)||entries.reduce((sum,{file})=>sum+file.size,0)>64*1024*1024)throw new Error('文件包最多 256 個檔案、合計 64 MiB，單檔最多 16 MiB。');
  return Promise.all(entries.map(async({file,path})=>{
    const bytes=new Uint8Array(await file.arrayBuffer());let text='';
    for(let i=0;i<bytes.length;i+=32768)text+=String.fromCharCode(...bytes.subarray(i,i+32768));
    return {path,base64:btoa(text)};
  }));
}
export function mountBundleUpload(target,{scope,note,revision,e,request,onSaved,onCancel,onBusy=()=>{}}){
  target.innerHTML=`<form class="panel managed-host-form" id="bundle-form"><h3>加入文件包：${e(note.title)}</h3><p>選擇 ZIP、單一 Markdown／HTML，或整個資料夾。保留相對路徑；不會執行上傳內容。圖片與 three.js 等相依資源請一併放入。</p><label>附件名稱<input name="title" required maxlength="200" value="${e(note.title)}"></label><label>入口檔案路徑<input name="entry" required value="index.md" placeholder="report.md 或 index.html"></label><label>ZIP 或單一文件<input type="file" name="archive" accept=".zip,.md,.html,.htm"></label><label>或選擇資料夾<input type="file" name="folder" webkitdirectory multiple></label><p>ZIP 最多 65 MiB；最多 256 個檔案、解壓合計 64 MiB、單檔 16 MiB。使用 UTF-8 文件；請先確認是否含需遮蔽的敏感資料。</p><p role="status" id="bundle-upload-status"></p><div class="setup-actions"><button class="button primary" type="submit">儲存附件</button><button class="button" type="button" id="bundle-cancel">取消</button></div></form>`;
  const form=target.querySelector('form');let busy=false;
  const choose=(selected,other)=>{
    other.value='';const paths=folderFiles(selected.files).map(item=>item.path);
    const preferred=['index.md','index.html','index.htm'].find(path=>paths.includes(path))||paths.find(path=>/\.(md|html?)$/i.test(path));
    if(preferred)form.elements.entry.value=preferred;
  };
  form.elements.archive.onchange=()=>choose(form.elements.archive,form.elements.folder);
  form.elements.folder.onchange=()=>choose(form.elements.folder,form.elements.archive);
  target.querySelector('#bundle-cancel').onclick=()=>{if(!busy)onCancel();};
  form.onsubmit=async event=>{
    event.preventDefault();if(busy)return;busy=true;onBusy(true);
    const controls=target.querySelectorAll('button');controls.forEach(button=>button.disabled=true);
    const status=target.querySelector('#bundle-upload-status');status.textContent='正在檢查並保存文件包…';
    try{
      const selected=form.elements.archive.files[0];let options;
      if(selected?.name.toLowerCase().endsWith('.zip')){
        if(selected.size>65*1024*1024)throw new Error('ZIP 最多 65 MiB。');
        options={headers:{'Content-Type':'application/zip'},body:selected};
      }else options={headers:{'Content-Type':'application/json'},body:JSON.stringify({files:await encodedFiles(selected?[selected]:form.elements.folder.files)})};
      const query=new URLSearchParams({...scope,note_uuid:note.uuid,expected_revision:revision,title:form.elements.title.value,entry:form.elements.entry.value});
      await request('/api/v1/note-bundles?'+query,{method:'POST',...options});
      await onSaved();
    }catch(error){
      const messages={bundle_entry_missing:'找不到入口檔案，請確認它在文件包中的相對路徑。',invalid_bundle_path:'文件包包含不支援的路徑或符號連結。',duplicate_bundle_path:'文件包含重複檔名（不區分大小寫）。',note_revision_conflict:'筆記已變更。請重新載入核對，再加入附件。',bundle_expansion_limit:'文件包超過解壓大小或壓縮比例限制。',invalid_bundle_entry:'入口須為 UTF-8 Markdown 或 HTML，最多 2 MiB。',bundle_entry_requires_utf8:'入口文件須使用 UTF-8 編碼。'};
      status.textContent=messages[error.code]||(error.code?'無法保存附件（'+error.code+'）。請保留原檔，重新載入核對；不會自動重試。':error.message||'附件未能保存。請重新載入核對。');
    }finally{busy=false;onBusy(false);controls.forEach(button=>button.disabled=false);}
  };
}
