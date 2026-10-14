"""Shared synthetic recipe browser data; never reads private Feast records."""
def snapshot():
    return {'catalog': {'status':'success','sources':[{'name':'repository','root':'/fixture/recipes','status':'available'}],
            'recipes':[{'reference': name,'source':'repository','directory':'/fixture/recipes/'+name,'id':name,'runnable':True} for name in ('first','second','third')]},
            'history': {'status':'success','results':[
                {'recipe_source':'repository','recipe_reference':name,'recipe_id':name,'started_at':'2026-10-14T00:00:00Z',
                 'status':'success','host_id':'host-01','result_id':name+'.json','kind':'operation'} for name in ('first','second','third')], 'errors':[]},
            'root':'/fixture/feast','message':'Synthetic Feast'}
