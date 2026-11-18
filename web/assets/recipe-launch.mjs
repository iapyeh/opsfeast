// Launch guidance is independent of static runner readiness.
export const directRecipe=item=>!!item?.runnable&&item.launch?.mode!=='agent';
export function agentMeal(set,data,path=new Set()) {
 if(path.has(set.id))return false;
 const items=new Map((data.items||[]).map(item=>[item.reference,item]));
 const meals=new Map([...(data.sets||[]),...(data.user_sets||[])].map(meal=>[meal.id,meal]));
 const next=new Set([...path,set.id]);
 return (set.recipes||set.references||[]).some(ref=>items.get(ref)?.launch?.mode==='agent')||
  (set.meals||[]).some(id=>meals.has(id)&&agentMeal(meals.get(id),data,next));
}
