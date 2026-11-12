"""Synthetic browser fixture; requires reviewed local three.js r180 module/core files."""
from pathlib import Path
import argparse,io,json,socket,tempfile,zipfile
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--three-dir",type=Path,required=True);parser.add_argument("--metadata",type=Path,required=True);args=parser.parse_args()
import uvicorn
from PIL import Image
from opsfeast.storage import initialize_data_root
from opsfeast.profile_settings import create,inspect
from opsfeast import host_notes,note_bundles,admin
from opsfeast.web.app import create_app
base=Path(tempfile.mkdtemp(prefix='opsfeast-bundle-browser-'));product=base/'product';product.mkdir();data=base/'data';initialize_data_root(product,data)
create(product,data,name='main',expected_revision=inspect(product)['revision'])
root=data/'profiles/main';(root/'hosts.yaml').write_text('hosts:\n  sample:\n    connection: {local: true}\n')
state=host_notes.inspect(product,profile='main',host_id='sample');note=host_notes.mutate(product,profile='main',host_id='sample',action='create',expected_revision=state['revision'],changes={'title':'Synthetic nginx analysis','content':'Synthetic report attachments','source':'user'})['note'];scope=dict(profile='main',host_id='sample',note_uuid=note['uuid'])
module=b'''import * as THREE from './vendor/three.module.js';
const data=await fetch('./data.json').then(response=>response.json());
let parentBlocked=false,cookieBlocked=false,networkBlocked=false;
try{void parent.document.body;}catch{parentBlocked=true;}
try{void document.cookie;}catch{cookieBlocked=true;}
try{await fetch('__MAIN__/api/v1/setup');}catch{networkBlocked=true;}
let webgl=false,error='';
try{const renderer=new THREE.WebGLRenderer();renderer.setSize(160,100);document.body.append(renderer.domElement);renderer.render(new THREE.Scene(),new THREE.PerspectiveCamera());webgl=true;}catch(e){error=e.message;}
parent.postMessage({bundleReady:true,three:THREE.REVISION,data:data.value,parentBlocked,cookieBlocked,networkBlocked,webgl,error},'*');
window.addEventListener('message',event=>{if(event.data==='test-navigation')location.href='__MAIN__/api/v1/setup?leak=synthetic';});
'''
listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(2048);port=listener.getsockname()[1];origin=f'http://127.0.0.1:{port}'
lib=args.three_dir
if not all((lib/name).is_file() for name in ['three.module.js','three.core.js']):raise SystemExit('Provide reviewed local three.module.js and three.core.js (r180).')
files={'index.html':b'<!doctype html><title>Synthetic three report</title><script type="module" src="app.mjs"></script>','app.mjs':module.replace(b'__MAIN__',origin.encode()),'data.json':b'{"value":"package-local-json"}',**{'vendor/'+p.name:p.read_bytes() for p in lib.glob('three.*.js')}}
created=note_bundles.create(product,**scope,expected_revision=host_notes.inspect(product,profile='main',host_id='sample')['revision'],title='Three.js r180 test',entry='index.html',files=files);html_scope={**scope,'bundle_uuid':created['bundle']['uuid']}
image=io.BytesIO();Image.new('RGB',(16,12),'red').save(image,'PNG')
zipfile_path=base/'markdown-report.zip'
with zipfile.ZipFile(zipfile_path,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('index.md','# Nginx report\n\n| Check | Result |\n| --- | --- |\n| TLS | Review |\n\n![diagram](images/diagram.png)\n\n```nginx\nserver {\n  listen 443;\n}\n```\n\n<script>window.markdownUnsafe=true</script>')
 z.writestr('images/diagram.png',image.getvalue())
admin.configure(data,username='test-owner',password='synthetic-browser-test',expected_revision=0)
settings={'origin':origin,'html_scope':html_scope,'upload_zip':str(zipfile_path),'product':str(product),'data':str(data)}
metadata=args.metadata
with metadata.open('x') as target:target.write(json.dumps(settings))
metadata.chmod(0o600)
print(json.dumps({'ready':True,'origin':origin}),flush=True)
app=create_app(product,data_root=data)
uvicorn.Server(uvicorn.Config(app,access_log=False,log_level='error')).run(sockets=[listener])
