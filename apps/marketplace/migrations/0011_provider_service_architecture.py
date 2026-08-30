from django.db import migrations, models
import django.db.models.deletion


def backfill_provider_service_architecture(apps, schema_editor):
    ProviderProfile = apps.get_model('accounts', 'ProviderProfile')
    ManagedService = apps.get_model('marketplace', 'ManagedService')
    ProviderService = apps.get_model('marketplace', 'ProviderService')
    Service = apps.get_model('marketplace', 'Service')
    # Preserve the central approvals already present.
    for approval in ProviderService.objects.exclude(catalog_service_id=None).iterator():
        approval.managed_service_id = approval.catalog_service_id
        approval.save(update_fields=['managed_service'])
    # Every historic commercial service receives one deterministic central
    # service and provider approval; no service or category is discarded.
    for listing in Service.objects.filter(provider_service_id=None).iterator():
        managed, _ = ManagedService.objects.get_or_create(
            name=('عرض قديم #%s: ' % listing.category_id) + listing.title[:96],
            defaults={'category_id': listing.category_id, 'description': 'خدمة مركزية أنشئت لحفظ عرض تجاري قديم.'},
        )
        profile, _ = ProviderProfile.objects.get_or_create(user_id=listing.provider_id)
        approval, _ = ProviderService.objects.get_or_create(
            provider_id=profile.pk, managed_service_id=managed.pk,
            defaults={'catalog_service_id': managed.pk, 'is_active': True, 'approval_status': 'approved', 'price': 0, 'price_type': 'fixed', 'estimated_duration': 1, 'description': ''},
        )
        listing.provider_service_id = approval.pk
        listing.save(update_fields=['provider_service'])

class Migration(migrations.Migration):
    dependencies = [('marketplace', '0010_service_provider_service'), ('accounts', '0012_remove_providerprofile_business_name')]
    operations = [
        migrations.RemoveConstraint(model_name='providerservice', name='unique_provider_listing_service'),
        migrations.RemoveConstraint(model_name='providerservice', name='unique_provider_catalog_service'),
        migrations.RemoveConstraint(model_name='providerservice', name='provider_service_exactly_one_source'),
        migrations.AddField(model_name='providerservice', name='managed_service', field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name='provider_services', to='marketplace.managedservice', verbose_name='الخدمة المركزية')),
        migrations.RunPython(backfill_provider_service_architecture, migrations.RunPython.noop),
        migrations.RemoveIndex(model_name='managedservice', name='marketplace_categor_4785a5_idx'),
        migrations.RemoveIndex(model_name='providerservice', name='marketplace_service_893bff_idx'),
        migrations.RemoveIndex(model_name='service', name='marketplace_categor_e8a41c_idx'),
        migrations.RemoveField(model_name='providerservice', name='catalog_service'),
        migrations.RemoveField(model_name='providerservice', name='description'),
        migrations.RemoveField(model_name='providerservice', name='estimated_duration'),
        migrations.RemoveField(model_name='providerservice', name='price'),
        migrations.RemoveField(model_name='providerservice', name='price_type'),
        migrations.RemoveField(model_name='providerservice', name='service'),
        migrations.RemoveField(model_name='service', name='category'),
        migrations.AlterField(model_name='providerservice', name='managed_service', field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='provider_services', to='marketplace.managedservice', verbose_name='الخدمة المركزية')),
        migrations.AlterField(model_name='managedservice', name='category', field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='managed_services', to='marketplace.category', verbose_name='التصنيف')),
        migrations.AlterField(model_name='service', name='provider_service', field=models.ForeignKey(help_text='الخدمة المركزية المعتمدة التي ينتمي إليها هذا العرض التجاري', on_delete=django.db.models.deletion.PROTECT, related_name='commercial_services', to='marketplace.providerservice', verbose_name='اعتماد مقدم الخدمة')),
        migrations.AddIndex(model_name='managedservice', index=models.Index(fields=['is_active', 'order'], name='marketplace_is_acti_16eb75_idx')),
        migrations.AddIndex(model_name='providerservice', index=models.Index(fields=['managed_service', 'is_active'], name='marketplace_managed_53976c_idx')),
        migrations.AddConstraint(model_name='providerservice', constraint=models.UniqueConstraint(fields=('provider','managed_service'), name='unique_provider_managed_service')),
        migrations.AddConstraint(model_name='service', constraint=models.UniqueConstraint(fields=('provider','provider_service','title'), name='unique_provider_provider_service_title')),
    ]
