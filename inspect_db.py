import json, sqlite3, pathlib
p = pathlib.Path('/home/ubuntu/selvvv/db.sqlite3')
con = sqlite3.connect(p)
con.row_factory = sqlite3.Row
out = {'database': str(p), 'sqlite_version': sqlite3.sqlite_version, 'foreign_keys_pragma': con.execute('PRAGMA foreign_keys').fetchone()[0], 'tables': [], 'views': [], 'triggers': []}
objects = con.execute("SELECT type, name, sql FROM sqlite_master WHERE type IN ('table','view','trigger') ORDER BY type, name").fetchall()
for o in objects:
    if o['type']=='view': out['views'].append(dict(o)); continue
    if o['type']=='trigger': out['triggers'].append(dict(o)); continue
    t=o['name']
    if t.startswith('sqlite_'): continue
    cols=[]
    for r in con.execute(f'PRAGMA table_info("{t}")'):
        cols.append(dict(r))
    fks=[dict(r) for r in con.execute(f'PRAGMA foreign_key_list("{t}")')]
    idx=[]
    for r in con.execute(f'PRAGMA index_list("{t}")'):
        d=dict(r); name=d['name']; d['columns']=[dict(x) for x in con.execute(f'PRAGMA index_info("{name}")')]; d['sql']=con.execute("SELECT sql FROM sqlite_master WHERE type='index' AND name=?",(name,)).fetchone()[0]; idx.append(d)
    count=con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    out['tables'].append({'name':t,'sql':o['sql'],'columns':cols,'foreign_keys':fks,'indexes':idx,'row_count':count})
print(json.dumps(out, indent=2, ensure_ascii=False))
con.close()
