from django.db import migrations, models

def migrate_legacy_provider_data(apps, schema_editor):
    Profile=apps.get_model('accounts','ProviderProfile'); Specialization=apps.get_model('marketplace','Specialization')
    for p in Profile.objects.exclude(specialization='').iterator():
        value=p.specialization.strip()
        if value:
            item, _=Specialization.objects.get_or_create(name=value, defaults={'is_active': True})
            p.specializations.add(item)
    Profile.objects.exclude(qualifications='').update(qualification_notes=models.F('qualifications'))

class Migration(migrations.Migration):
    dependencies=[('accounts','0012_remove_providerprofile_business_name'),('marketplace','0010_service_provider_service')]
    operations=[
      migrations.AddField(model_name='providerprofile',name='qualification_notes',field=models.TextField(blank=True,verbose_name='ملاحظات إضافية عن المؤهلات')),
      migrations.RunPython(migrate_legacy_provider_data,migrations.RunPython.noop),
      migrations.RemoveIndex(model_name='providerprofile',name='accounts_pr_verific_6808a8_idx'),
      migrations.RemoveField(model_name='providerprofile',name='city'),migrations.RemoveField(model_name='providerprofile',name='district'),migrations.RemoveField(model_name='providerprofile',name='email'),migrations.RemoveField(model_name='providerprofile',name='phone'),migrations.RemoveField(model_name='providerprofile',name='qualifications'),migrations.RemoveField(model_name='providerprofile',name='specialization'),migrations.RemoveField(model_name='user',name='city'),
      migrations.AddIndex(model_name='providerprofile',index=models.Index(fields=['verification_status','location_city'],name='accounts_pr_verific_593a77_idx')),
    ]
