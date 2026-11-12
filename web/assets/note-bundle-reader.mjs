import {formatNoteTimestamp} from './host-notes.mjs';
const e=value=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
export async function mountBundleReader(root,{search=location.search,request=fetch}={}){
  const query=new URLSearchParams(search),scope=Object.fromEntries(['profile','host_id','note_uuid','bundle_uuid'].map(key=>[key,query.get(key)||'']));
  const params=new URLSearchParams(scope);
  async function json(path,options){const response=await request(path,options);if(!response.ok)throw new Error('附件讀取失敗（HTTP '+response.status+'）。請確認登入狀態、附件是否仍存在及檔案完整性。');return response.json();}
  let timer,generation=0;
  try{
    const state=await json('/api/v1/note-bundles?'+params),bundle=state.bundle;
    root.innerHTML=`<a href="/hosts?${e(new URLSearchParams({profile:scope.profile,host:scope.host_id,view:'notes'}).toString())}">← ${e(scope.host_id)} · 主機筆記</a><h1>${e(bundle.title)}</h1><p>${e(bundle.kind==='html'?'HTML／互動文件':'Markdown 文件')} · ${e(bundle.entry)} · ${e(formatNoteTimestamp(bundle.created_at))}</p><div class="setup-actions"><a class="button" href="/api/v1/note-bundles/export?${e(params)}">下載文件包 ZIP</a><button class="button" id="bundle-source" type="button">查看原文</button></div><p id="bundle-reader-status" role="status"></p><div id="bundle-content" class="note-document"></div><details><summary>檔案清單與 SHA-256</summary><ul>${state.files.map(file=>`<li><a href="/api/v1/note-bundles/file?${e(new URLSearchParams({...scope,path:file.path}).toString())}">${e(file.path)}</a> · ${file.bytes} bytes <code>${e(file.sha256)}</code></li>`).join('')}</ul></details>`;
    const content=root.querySelector('#bundle-content'),status=root.querySelector('#bundle-reader-status');
    const resourceWarnings=(state.warnings||[]).map(item=>item.file+' → '+(item.reference||'（檢查範圍限制）')+' ['+item.reason+']').join('；');
    if(resourceWarnings)status.textContent='資源檢查：'+resourceWarnings;
    const stop=()=>{generation++;clearTimeout(timer);const frame=content.querySelector('iframe');if(frame)frame.remove();};
    let sourceShowing=false;
    root.querySelector('#bundle-source').onclick=async()=>{
      stop();
      if(sourceShowing){await mountBundleReader(root,{search,request});return;}
      try{
        const response=await request('/api/v1/note-bundles/file?'+new URLSearchParams({...scope,path:bundle.entry}));if(!response.ok)throw new Error('無法讀取原文。');
        const text=await response.text();content.innerHTML='<pre class="note-document-source"></pre>';content.querySelector('pre').textContent=text;sourceShowing=true;root.querySelector('#bundle-source').textContent='返回閱讀模式';
      }catch(error){status.textContent=error.message;}
    };
    if(bundle.kind==='markdown'){
      const document=await json('/api/v1/note-bundles/markdown?'+params);content.innerHTML=document.html;
      status.textContent=document.warnings.length?'以下引用未載入，請核對文件包：'+document.warnings.map(item=>item.reference).join('、'):(resourceWarnings?'資源檢查：'+resourceWarnings:'');
    }else{
      content.innerHTML='<p>此文件含可執行的 HTML／JavaScript。預覽在獨立環境執行，隔離管理介面並限制一般資源／fetch 連線。請只開啟已審查的文件；這不是完整的作業系統網路隔離。ES modules、WebGL 與包內 JSON 可使用；不支援 Web Worker、Service Worker、需登入的 API 或外部 CDN。</p><button class="button primary" id="bundle-open-preview" type="button">開啟隔離互動預覽</button><button class="button" id="bundle-stop-preview" type="button">停止預覽</button><div id="bundle-frame"></div>';
      const frameRoot=content.querySelector('#bundle-frame');
      content.querySelector('#bundle-stop-preview').onclick=()=>{stop();status.textContent='預覽已停止。';};
      content.querySelector('#bundle-open-preview').onclick=async()=>{
        stop();const current=generation;status.textContent='正在準備隔離閱讀環境…';
        try{
          const preview=await json('/api/v1/note-bundles/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(scope)});
          if(current!==generation)return;
          const frame=document.createElement('iframe');frame.title=bundle.title;frame.setAttribute('sandbox','allow-scripts');frame.referrerPolicy='no-referrer';frame.src=preview.url;frameRoot.replaceChildren(frame);
          status.textContent='隔離預覽已開啟。'+(resourceWarnings?'資源檢查：'+resourceWarnings:'')+' 空白或缺圖時請核對檔案清單、相對路徑與外部引用；不會自動下載缺少的資源。';
          timer=setTimeout(()=>{stop();status.textContent='預覽授權已到期，請重新開啟。';},preview.expires_in*1000);
        }catch(error){if(current===generation)status.textContent=error.message;}
      };
    }
    return stop;
  }catch(error){root.textContent=error.message;}
}
if(typeof document!=='undefined'){
  const root=document.getElementById('note-bundle-reader');if(root)mountBundleReader(root);
}
