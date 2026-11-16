import {mountRecipeRun,mountRecipeRunHistory} from './recipe-run-view.mjs';
import {reviewPlate} from './recipe-execution.mjs';
import {mountMenuLayout} from './recipe-menu-layout.mjs';
import {mountRecipeDetail} from './recipe-detail.mjs';
import {mountReportViewer} from './report-viewer.mjs';
import {copy as c,states,renderCard,renderBlueprint,renderReview,renderRun} from './locales/recipe-menu-zh-TW.mjs';
export {domains,renderCard,renderBlueprint,renderReview,renderRun} from './locales/recipe-menu-zh-TW.mjs';
const url=(path,profile,extra={})=>path+'?'+new URLSearchParams({profile,...extra});
export function readVariables(form,definitions) {
  const result={};
  for(const [name,spec] of Object.entries(definitions)) {
    const value=form.get(name);
    if(value==null||value==='')continue;
    try {result[name]=spec.type==='string'?value:JSON.parse(value);}
    catch {throw new Error(c.jsonError(name,spec.type));}
    const parsed=result[name];
    const valid={string:typeof parsed==='string',integer:Number.isInteger(parsed),number:typeof parsed==='number'&&Number.isFinite(parsed),boolean:typeof parsed==='boolean',object:parsed!==null&&typeof parsed==='object'&&!Array.isArray(parsed),array:Array.isArray(parsed)};
    if(!valid[spec.type])throw new Error(c.typeError(name,spec.type));
  }
  return result;
}

export function readInventorySelection(form,catalog) {
  if(!catalog)return undefined;
  const mode=form.get('_inventory_mode');
  if(!mode||mode==='default')return undefined;
  const key=mode==='jobs'?'jobs':'properties';
  const names=form.getAll(key==='jobs'?'_inventory_job':'_inventory_property');
  if(!names.length)throw new Error(c.inventoryEmpty);
  return {[key]:names};
}

export async function mountRecipeMenu(root,{e,profile=null,profiles=null,search='',fetchImpl=fetch}) {
  const query=new URLSearchParams(search);
  const api=async(path,body)=>{
    const response=await fetchImpl(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail==='administrator_login_required'?c.unauthorized:c.failure(data.detail||response.status));
    return data;
  };
  root.innerHTML=`<p role="status">${e(c.loading)}</p>`;
  try {
    if(!profiles)profiles=await api('/api/v1/profiles');
    profile=profiles.default_profile;
    if(query.get('recipe'))return mountRecipeDetail(root,{profile,reference:query.get('recipe'),e,api});
    if(query.get('report')&&!profile)throw new Error(c.failure('explicit_profile_required'));
    if(query.get('report'))return mountReportViewer(root,{e,profile,identifier:query.get('report'),artifact:query.get('artifact'),api});
    if(query.get('history'))return mountRecipeRunHistory(root,{profile,e,api});
    if(query.get('run'))return mountRecipeRun(root,{profile,id:query.get('run'),e,api});
    const data=await api('/api/v1/recipe-menu'+(profile?'?'+new URLSearchParams({profile}):''));
    mountMenuLayout(root,{data,profiles,profile,initialRecipe:query.get('recipe'),e,api,onExecute:selection=>reviewPlate(root,{profile,selection,e,api,catalog:data,onEdit:()=>mountRecipeMenu(root,{e,profile,profiles,search,fetchImpl}),onStarted:run=>{location.href=url('/recipes',profile,{run:run.id});}}),onProfile:name=>{location.href=url('/recipes',name);}});
  }catch(exc){root.innerHTML=`<p role="alert">${e(exc.message)}</p>`;}
}
