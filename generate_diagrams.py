import json, re
from pathlib import Path
D=json.load(open('/home/ubuntu/selvvv/db_inspection.json'))
root=Path('/home/ubuntu/selvvv/docs/diagrams'); root.mkdir(parents=True,exist_ok=True)

def ident(s):
    return re.sub(r'[^A-Za-z0-9_]', '_', s)
def short(s): return s.replace('accounts_','acc_').replace('marketplace_','mkt_').replace('payments_','pay_').replace('orders_','ord_').replace('reviews_','rev_').replace('core_','core_').replace('django_','dj_')
# Full ERD: every table and all columns, with explicit PK/FK markers.
fkmap={(t['name'],f['from']):f for t in D['tables'] for f in t['foreign_keys']}
er=['erDiagram']
for t in D['tables']:
    tn=ident(t['name']); er.append(f'    {tn} {{')
    for c in t['columns']:
        typ=re.sub(r'[^A-Za-z0-9_]','_',c['type']).lower() or 'text'
        note=[]
        if c['pk']: note.append('PK')
        if (t['name'],c['name']) in fkmap: note.append('FK')
        label=' '.join(note)
        er.append(f'        {typ} {ident(c["name"])} {label}'.rstrip())
    er.append('    }')
for t in D['tables']:
    for f in t['foreign_keys']:
        # Relationship is child-to-parent; exact cardinality is inferred from uniqueness where applicable.
        child=t['name']; parent=f['table']; uniq=False
        for ix in t['indexes']:
            if ix['unique'] and [x['name'] for x in ix['columns']]==[f['from']]: uniq=True
        card='||--o|' if uniq else '||--o{'
        er.append(f'    {ident(parent)} {card} {ident(child)} : "{f["from"]}"')
(root/'01_erd_full.mmd').write_text('\n'.join(er)+'\n')
# Class diagram: domain models represented by DB-backed Django classes, including association entities.
classes=['User','ProviderProfile','ProviderDocumentType','ProviderDocument','ProviderVerificationRequest','City','District','Notification','AuditLog','TermsAndConditions','TermsAcceptance','Category','ManagedService','Specialization','Qualification','ProviderService','Service','Order','Delivery','Milestone','OrderMessage','Wallet','ProviderWallet','Payment','CommissionRecord','Review','Conversation','Message']
classmap={c['name'].split('_')[-1].title().replace('Providerprofile','ProviderProfile').replace('Providerdocumenttype','ProviderDocumentType').replace('Providerdocument','ProviderDocument').replace('Providerverificationrequest','ProviderVerificationRequest').replace('Managedservice','ManagedService').replace('Providerservice','ProviderService').replace('Ordermessage','OrderMessage').replace('Termsandconditions','TermsAndConditions').replace('Termsacceptance','TermsAcceptance').replace('Auditlog','AuditLog'):c for c in D['tables']}
# use selected fields to keep class diagram readable; all fields remain in DB schema diagram and report.
cd=['classDiagram']
for c in classes:
    t=next((x for x in D['tables'] if x['name'].endswith('_'+re.sub(r'(?<!^)([A-Z])',r'_\\1',c).lower()) or x['name']==c.lower()),None)
    if not t:
        continue
    cd.append(f'    class {c} {{')
    selected=[]
    for col in t['columns']:
        if col['pk'] or col['name'].endswith('_id') or col['name'] in ['name','title','status','role','amount','price','is_active','created_at']:
            selected.append(col)
    for col in selected:
        mark=' <<PK>>' if col['pk'] else (' <<FK>>' if col['name'].endswith('_id') else '')
        cd.append(f'        {col["type"]} {col["name"]}{mark}')
    cd.append('    }')
# manually map class relationships from official FKs where both domain classes exist.
name_for={
'accounts_user':'User','accounts_providerprofile':'ProviderProfile','accounts_providerdocumenttype':'ProviderDocumentType','accounts_providerdocument':'ProviderDocument','accounts_providerverificationrequest':'ProviderVerificationRequest','core_city':'City','core_district':'District','core_notification':'Notification','core_auditlog':'AuditLog','core_termsandconditions':'TermsAndConditions','core_termsacceptance':'TermsAcceptance','marketplace_category':'Category','marketplace_managedservice':'ManagedService','marketplace_specialization':'Specialization','marketplace_qualification':'Qualification','marketplace_providerservice':'ProviderService','marketplace_service':'Service','orders_order':'Order','orders_delivery':'Delivery','orders_milestone':'Milestone','orders_ordermessage':'OrderMessage','payments_wallet':'Wallet','payments_providerwallet':'ProviderWallet','payments_payment':'Payment','payments_commissionrecord':'CommissionRecord','reviews_review':'Review','chat_conversation':'Conversation','chat_message':'Message'}
for t in D['tables']:
    for f in t['foreign_keys']:
        if t['name'] in name_for and f['table'] in name_for:
            a=name_for[t['name']]; b=name_for[f['table']]
            cd.append(f'    {b} <.. {a} : {f["from"]}')
(root/'02_class_diagram.mmd').write_text('\n'.join(cd)+'\n')
# Database schema overview uses table names only and FK edges for quick comprehension.
sc=['flowchart LR','    classDef table fill:#e8f1ff,stroke:#2563eb,color:#0f172a,stroke-width:1px','    classDef infra fill:#f1f5f9,stroke:#64748b,color:#0f172a']
for t in D['tables']:
    label='<b>'+t['name']+'</b><br/>rows='+str(t['row_count'])+'<br/>'+ '<br/>'.join((('🔑 ' if c['pk'] else '')+('🔗 ' if (t['name'],c['name']) in fkmap else '')+c['name']+' : '+c['type']) for c in t['columns'])
    sc.append(f'    {ident(t["name"])}["{label}"]')
for t in D['tables']:
    for f in t['foreign_keys']:
        sc.append(f'    {ident(t["name"])} -->|{f["from"]}| {ident(f["table"])}')
(root/'06_database_schema.mmd').write_text('\n'.join(sc)+'\n')
# Context DFD / Level 0 based on concrete routes and process domains in apps.
ctx='''flowchart LR\n    C[Customer] -->|registration, login, search, order requests, messages, reviews| S((selvvv marketplace system))\n    P[Provider] -->|profile, services, documents, verification, order updates, messages| S\n    A[Administrator] -->|catalog management, verification review, payment review, audit/report queries| S\n    S -->|service listings, order status, notifications, chat, payment/review results| C\n    S -->|customer orders, notifications, verification decisions, payment status| P\n    S -->|dashboards, reports, audit records, management results| A\n    G[Manual wallet / payment gateway] -->|payment status or payment reference| S\n    S -->|payment request / proof for review| G'''
(root/'03_context_dfd_level0.mmd').write_text(ctx+'\n')
# DFD level 1, naming only processes observable in views/services/urls.
dfd1='''flowchart LR\n    C[Customer] --> P1((1. Account & authentication))\n    P[Provider] --> P1\n    A[Administrator] --> P1\n    P1 <--> D1[(User / session / permission stores)]\n    P1 --> D2[(Notifications / audit)]\n    C --> P2((2. Browse & manage marketplace services))\n    P --> P2\n    A --> P2\n    P2 <--> D3[(Categories, managed services, specializations, qualifications)]\n    P2 <--> D4[(Provider services / services)]\n    P --> P3((3. Provider verification & documents))\n    A --> P3\n    P3 <--> D5[(Provider profiles, documents, verification requests)]\n    C --> P4((4. Create and manage orders))\n    P --> P4\n    P4 <--> D6[(Orders, deliveries, milestones, order messages)]\n    P4 --> D2\n    C --> P5((5. Payments and commission review))\n    A --> P5\n    P --> P5\n    P5 <--> D7[(Payments, wallets, provider wallets, commission records)]\n    P5 <--> G[Manual wallet / payment gateway]\n    C --> P6((6. Reviews and conversations))\n    P --> P6\n    P6 <--> D8[(Reviews, conversations, messages)]\n    P6 --> D2\n    A --> P7((7. Dashboard, reports, exports and catalog administration))\n    P7 <--> D1\n    P7 <--> D2\n    P7 <--> D3\n    P7 <--> D5\n    P7 <--> D7'''
(root/'04_dfd_level1.mmd').write_text(dfd1+'\n')
# Level 2 for the demonstrably complex provider verification workflow.
dfd2='''flowchart TD\n    P[Provider] --> A1((2.1 Edit profile and select services))\n    A1 --> D1[(Provider profile / service selections)]\n    P --> A2((2.2 Upload provider documents))\n    A2 --> D2[(Provider documents)]\n    P --> A3((2.3 Submit verification request))\n    A3 --> D3[(Verification request + profile snapshot)]\n    D1 --> A3\n    D2 --> A3\n    A[Administrator] --> A4((2.4 Review request and documents))\n    A4 <--> D2\n    A4 <--> D3\n    A4 --> A5{Decision}\n    A5 -->|approved| A6((2.5 Activate / verify provider))\n    A5 -->|rejected or needs documents| A7((2.6 Record note and request changes))\n    A6 --> D1\n    A7 --> D3\n    A6 --> N[(Notifications / audit)]\n    A7 --> N\n    N --> P'''
(root/'05_dfd_level2_verification.mmd').write_text(dfd2+'\n')
print('generated',len(list(root.glob('*.mmd'))),'diagram sources')
