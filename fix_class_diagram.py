import json,re
from pathlib import Path
D=json.load(open('/home/ubuntu/selvvv/db_inspection.json'))
root=Path('/home/ubuntu/selvvv/docs/diagrams')
mapn={'accounts_user':'User','accounts_providerprofile':'ProviderProfile','accounts_providerdocumenttype':'ProviderDocumentType','accounts_providerdocument':'ProviderDocument','accounts_providerverificationrequest':'ProviderVerificationRequest','core_city':'City','core_district':'District','core_notification':'Notification','core_auditlog':'AuditLog','core_termsandconditions':'TermsAndConditions','core_termsacceptance':'TermsAcceptance','core_platformsetting':'PlatformSetting','marketplace_category':'Category','marketplace_managedservice':'ManagedService','marketplace_specialization':'Specialization','marketplace_qualification':'Qualification','marketplace_providerservice':'ProviderService','marketplace_service':'Service','orders_order':'Order','orders_delivery':'Delivery','orders_milestone':'Milestone','orders_ordermessage':'OrderMessage','payments_wallet':'Wallet','payments_providerwallet':'ProviderWallet','payments_payment':'Payment','payments_commissionrecord':'CommissionRecord','reviews_review':'Review','chat_conversation':'Conversation','chat_message':'Message'}
Dmap={t['name']:t for t in D['tables']}
cd=['classDiagram']
for table,cls in mapn.items():
 t=Dmap[table]; cd.append(f'    class {cls} {{')
 chosen=[]
 for c in t['columns']:
  official=any(f['from']==c['name'] for f in t['foreign_keys'])
  if c['pk'] or official or c['name'] in ['name','title','status','role','amount','price','is_active','created_at']:
   chosen.append(c)
 for c in chosen:
  official=any(f['from']==c['name'] for f in t['foreign_keys'])
  mark=' <<PK>>' if c['pk'] else (' <<FK>>' if official else '')
  cd.append(f'        {c["type"]} {c["name"]}{mark}')
 cd.append('    }')
for table,cls in mapn.items():
 for f in Dmap[table]['foreign_keys']:
  if f['table'] in mapn:
   cd.append(f'    {mapn[f["table"]]} <.. {cls} : {f["from"]}')
root.joinpath('02_class_diagram.mmd').write_text('\n'.join(cd)+'\n')
print('classes',sum(1 for x in cd if x.startswith('    class ')))
