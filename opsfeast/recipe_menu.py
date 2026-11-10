"""Recipe menu 0.1.0: static guidance over the shared recipe/profiling catalogs.

No recipe imports, connections, dependency installation or scheduling here.
"""
from pathlib import Path
from .profiling import catalog as profiling_catalog

VERSION = '0.1.0'

# Guidance is product-owned; execution metadata always comes from the descriptor.
GUIDANCE = {
    'system/inventory/overview': ('系統全貌基礎盤點', 'hardware', '主機規格、OS、套件、儲存、網路、服務及資源指標。', '預設十組工作；展開參數可自選工作／欄位與溫度／風扇。不是完整硬體清冊或應用探索。'),
    'system/inventory/hardware': ('硬體與製造資訊', 'hardware', 'CPU、記憶體規格、製造商、型號、序號與 UUID。', 'Linux 序號與 UUID 使用 root routine；權限或工具不足會留下缺口。'),
    'system/inventory/system': ('作業系統與主機識別', 'software', '主機名稱、核心、OS 與時區。', '依平台可用來源觀測；不代表完整套件或服務清冊。'),
    'system/inventory/network-configuration': ('網路組態', 'network', '網路介面、IPv4／IPv6、路由及 DNS。', '不包含防火牆有效政策或外部可達性驗證。'),
    'system/inventory/software': ('系統套件清冊', 'software', '平台套件管理器提供的已安裝套件與版本。', '只涵蓋已實作來源；不自動遍歷所有使用者的虛擬環境。'),
    'system/inventory/storage-layout': ('儲存配置', 'storage', '可見區塊裝置、分割與掛載配置。', '不是完整 RAID／LVM／LUKS／SAN 拓撲；控制器需另選 recipe。'),
    'system/inventory/storage-capacity': ('檔案系統容量', 'storage', '掛載點空間、inode 與 swap 使用狀態。', '單次快照；各平台未支援的欄位會標示缺口。'),
    'system/inventory/services': ('服務與監聽端點', 'workloads', '服務狀態與可見的監聽 socket。', '不推論實際外部暴露或應用健康；可見性依權限而異。'),
    'system/inventory/network-state': ('網路活動計數', 'network', '介面收送計數與 TCP 狀態統計。', '累積計數與單次快照；不等同流量速率或完整連線事件。'),
    'system/inventory/system-runtime': ('系統運作狀態', 'software', '系統 uptime 與開機時間。', '依平台提供快照；不代表持續監測。'),
    'system/inventory/resource-metrics': ('資源負載指標', 'software', 'CPU、負載、記憶體、I/O 與壓力指標。', '取樣窗口與來源時間會保留；缺少 PSI 等來源時不補值。'),
    'system/inventory/hardware-sensors': ('溫度與風扇', 'hardware', '可見的溫度與風扇感測資料。', '需明確選取；硬體、驅動與工具未提供時留下 unavailable 缺口。'),
    'system/storage/inventory/disks-raid': ('磁碟與 RAID', 'storage', '實體磁碟、備援碟、虛擬磁碟與陣列健康。', '需要支援的控制器工具與權限；不含完整 LVM／LUKS／ZFS／SAN 拓撲。'),
    'database/mysql/check/replication': ('MySQL 複寫檢查', 'workloads', '已配置實例的複寫通道、延遲與健康。', '需先私下配置實例與資料庫憑證；不會自動探索資料庫。'),
    'system/account/inventory/local-users': ('本機帳號與群組', 'identity', '本機使用者、群組、UID／GID、家目錄及 shell。', '只讀本機帳號檔；不代表有效登入資格或目錄服務全體帳號。'),
    'system/process/inventory/snapshot': ('行程快照', 'workloads', '可見行程、父子關係、執行身分、記憶體、累積 CPU 與執行檔。', '單次快照；不含 argv／環境、完整生命週期或即時 I/O 速率。'),
    'system/access/inventory/ssh-policy': ('SSH 存取政策', 'identity', 'OpenSSH 選定設定；完整連線情境可查對應 Match 條件。', '預設設定查詢不代表正在運行的 daemon 或實際登入成功。'),
    'system/account/inventory/sudo-policy': ('sudo 授權摘要', 'identity', '本次執行帳號可查到的 sudo 授權。', '只查目前 actor；省略 Defaults／指令參數等細節並標示部分完成。'),
    'system/network/inventory/firewall-policy': ('防火牆政策', 'network', '分別採集 nftables、iptables、firewalld、ufw 的可用視圖。', '保留各來源語意；不合併推論跨後端有效政策或外部可達性。'),
    'system/time/inventory/synchronization': ('時間同步', 'workloads', '時鐘、時間來源與 chrony／NTP／timesyncd 同步狀態。', '未同步與查詢失敗分開；缺少工具或權限會留下缺口。'),
    'system/logging/inventory/configuration': ('日誌設定與輪替', 'observability', '選定 journald／syslog／應用日誌目的地及輪替設定。', '不讀事件內容；不推論完整有效設定合併或日誌管線健康。'),
    'system/network/check/port': ('TCP 連通測試', 'network', '由指定主機對明確的位址與 TCP port 連線一次。', '會發出連線；TCP 成功不等於應用健康。'),
    'system/account/check/identity': ('執行身分確認', 'identity', '觀測供應給 recipe 的 session 身分。', '不是帳號清冊；不自行提升權限。'),
    'feast/report/execution-summary': ('執行結果報告', 'reports', '將明確選取的既有結果產生為 HTML／JSON。', '離線報告；需指定已保存結果 JSON，沒有新採集。'),
    'feast/report/retention-summary': ('保存資料報告', 'reports', '將既有 retention 整理為 Markdown／HTML。', '離線報告；只讀所選資料並產生本機成果，沒有新採集。'),
}

SETS = [
    {'id': 'foundation', 'title': '基礎盤點', 'description': '先取得共通系統事實，再補上本機帳號與行程。', 'references': ['system/inventory/overview', 'system/account/inventory/local-users', 'system/process/inventory/snapshot']},
    {'id': 'policies', 'title': '存取、時間與日誌', 'description': '選定範圍的政策與設定；不是完整安全稽核。', 'references': ['system/access/inventory/ssh-policy', 'system/account/inventory/sudo-policy', 'system/network/inventory/firewall-policy', 'system/time/inventory/synchronization', 'system/logging/inventory/configuration']},
    {'id': 'linux-profile', 'title': 'Linux 現有採集組合', 'description': '基礎盤點加上存取、時間與日誌設定；感測、磁碟控制器與資料庫需另行選擇。不代表原始藍圖已全數完成。', 'references': ['system/inventory/overview', 'system/account/inventory/local-users', 'system/process/inventory/snapshot', 'system/access/inventory/ssh-policy', 'system/account/inventory/sudo-policy', 'system/network/inventory/firewall-policy', 'system/time/inventory/synchronization', 'system/logging/inventory/configuration']},
]


def menu(profile=None):
    from recipe_catalog import catalog
    data = catalog(profile.root if profile else None)
    blueprint = profiling_catalog()
    items = []
    for source in data['recipes']:
        ref = source['reference']
        meta = source['descriptor']
        title, domain, purpose, limitation = GUIDANCE.get(ref, (source['title'] or ref, 'reports' if source['kind'] == 'report' else 'custom', source['description'], '使用者／外部來源：請先審閱程式、相依性與副作用。'))
        items.append({key: source.get(key) for key in ('reference', 'source', 'version', 'kind', 'runnable', 'status', 'inputs', 'dependencies', 'verification', 'availability_evidence', 'author', 'license')})
        items[-1].update(title=title, domain=domain, purpose=purpose, limitation=limitation,
                         is_meal=meta.get('runner',{}).get('contract')=='recipe-meal',access_mode=meta.get('access_mode', 'not_declared'), platforms=meta.get('platforms', {}),
                         side_effects=meta.get('side_effects', []), permissions=meta.get('permissions', {}),
                         guide=('recipes/' + ref + '/README.md') if ref in GUIDANCE else None)
        if source['runnable'] and (meta.get('collection') or meta.get('inventory') or meta.get('runner',{}).get('contract')=='recipe-meal'):
            from inventory_jobs import inspect_collection
            items[-1]['inventory_catalog'] = inspect_collection(Path(source['directory']), meta)
    # Catalog's expanded properties carry their provider IDs; keep one source of truth.
    for item in items:
        providers = {p['id'] for p in blueprint['providers'] if p['recipe_reference'] == item['reference']}
        selected=set(item.get('inventory_catalog',{}).get('properties',{}))
        item['capabilities'] = [c['id'] for c in blueprint['capabilities'] if any(p['provider_id'] in providers or p['provider_id']=='system-inventory' and p['id'] in selected for p in c['properties'])]
    order = {ref: i for i, ref in enumerate(GUIDANCE)}
    items.sort(key=lambda i: (i['source'] == 'repository', i['kind'] == 'report', order.get(i['reference'], len(order)), i['reference']))
    from .menu_preferences import inspect as preferences
    saved=preferences(profile) if profile else {'schema_version':'0.1.0','revision':None,'categories':[],'assignments':{},'sets':[]}
    for item in items:
        if item['reference'] in saved['assignments']:item['category_ids']=saved['assignments'][item['reference']]
    from .routine_contract import validate as meal_definition
    from . import REPOSITORY_RECIPES,read_yaml
    members=meal_definition(REPOSITORY_RECIPES/'system/inventory/overview',read_yaml(REPOSITORY_RECIPES/'system/inventory/overview/recipe.yaml'))['members']
    general=[m['reference'] for m in members if m['enabled']]
    sets=[{'id':'inventory-overview','title':'系統全貌盤點套餐','description':'十道獨立盤點 recipes；同一主機共用連線，先一般權限、後 root。感測另行選擇。','references':general}]
    sets += [{**s,'references':[ref for reference in s['references'] for ref in (general if reference=='system/inventory/overview' else [reference])]} for s in SETS]
    return {'schema_version': VERSION, 'profile': profile.name if profile else None,
            'items': items, 'sets': sets, 'sources': [{key: s[key] for key in ('name', 'enabled', 'status')} for s in data['sources']],
            'status': data['status'], 'blueprint': blueprint,'preferences':saved,
            'custom_categories':saved['categories'],'user_sets':saved['sets']}
