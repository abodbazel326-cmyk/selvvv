import json
D=json.load(open('db_inspection.json'))
for t in D['tables']:
    cols=[]
    for c in t['columns']:
        tag=' PK' if c['pk'] else ''
        cols.append(f"{c['name']}:{c['type']}{tag}")
    print(f"{t['name']}|rows={t['row_count']}|"+';'.join(cols))
print('--- EDGES ---')
for t in D['tables']:
    for f in t['foreign_keys']:
        print(f"{t['name']}.{f['from']}->{f['table']}.{f['to']}")
