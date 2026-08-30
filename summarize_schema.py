import json
from pathlib import Path
d=json.load(open('/home/ubuntu/selvvv/db_inspection.json'))
lines=[]
lines.append(f"SQLite {d['sqlite_version']} | foreign_keys PRAGMA={d['foreign_keys_pragma']}")
lines.append(f"TABLES={len(d['tables'])} VIEWS={len(d['views'])} TRIGGERS={len(d['triggers'])}")
for t in d['tables']:
    lines.append(f"\nTABLE {t['name']} rows={t['row_count']}")
    for c in t['columns']:
        flags=[]
        if c['pk']: flags.append('PK')
        if c['notnull']: flags.append('NOT NULL')
        if c['dflt_value'] is not None: flags.append('DEFAULT='+str(c['dflt_value']))
        lines.append(f"  COL {c['name']} {c['type']} {' '.join(flags)}")
    for fk in t['foreign_keys']:
        lines.append(f"  FK {fk['from']} -> {fk['table']}.{fk['to']} ON DELETE {fk['on_delete']} ON UPDATE {fk['on_update']}")
    for ix in t['indexes']:
        cols=','.join(x['name'] for x in ix['columns'])
        lines.append(f"  IDX {ix['name']} unique={ix['unique']} cols=({cols}) sql={ix['sql']}")
Path('/home/ubuntu/selvvv/schema_summary.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
