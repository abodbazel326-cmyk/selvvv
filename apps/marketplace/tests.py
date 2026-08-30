from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from apps.accounts.models import User
from .forms import ServiceForm
from .models import Category, ManagedService, Service, ProviderService

class ProviderActivationTests(TestCase):
    def setUp(self):
        self.category=Category.objects.create(name='Design')
        self.provider=User.objects.create_user(username='p', email='p@example.com', password='x', role='provider')
    def test_unverified_provider_cannot_add_service_backend(self):
        self.client.force_login(self.provider)
        response=self.client.post(reverse('marketplace:service_create'), {'title':'Logo','category':self.category.pk,'description':'x','price_type':'fixed','currency':'YER','price':'100','delivery_time':'2'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Service.objects.filter(title='Logo').exists())
    def test_verified_provider_can_add_service(self):
        profile=self.provider.provider_profile; profile.status='active'; profile.verification_status='verified'; profile.save()
        managed=ManagedService.objects.create(name='Logo design', category=self.category)
        approval=ProviderService.objects.create(provider=profile, catalog_service=managed, price=0, approval_status='approved', is_active=True)
        self.client.force_login(self.provider)
        response=self.client.post(reverse('marketplace:service_create'), {'provider_service':approval.pk,'title':'Logo','description':'x','price_type':'fixed','currency':'YER','price':'100','delivery_time':'2'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Service.objects.filter(title='Logo').exists())
    def test_unverified_provider_service_model_validation(self):
        service=Service(provider=self.provider, category=self.category, title='Catalog', description='x', price=10, delivery_time=1)
        provider_service=ProviderService(provider=self.provider.provider_profile, service=service, price=10)
        with self.assertRaises(ValidationError):
            provider_service.full_clean()

class SearchTests(TestCase):
    def setUp(self):
        self.category=Category.objects.create(name='Design')
        self.provider=User.objects.create_user(username='designer', email='d@example.com', password='x', role='provider')
        profile=self.provider.provider_profile; profile.status='active'; profile.verification_status='verified'; profile.city='Sanaa'; profile.district='Hadda'; profile.latitude='15.350000'; profile.longitude='44.200000'; profile.specialization='Logo Design'; profile.save()
        managed=ManagedService.objects.create(name='Logo design', category=self.category)
        approval=ProviderService.objects.create(provider=profile, catalog_service=managed, price=0, approval_status='approved', is_active=True)
        self.service=Service.objects.create(provider=self.provider, provider_service=approval, category=self.category, title='Logo Design', description='Branding', price=100, delivery_time=2, status='active')
    def test_global_search_backend_returns_public_database_results(self):
        from .search import filter_public_services, filter_public_providers, filter_public_categories
        self.assertIn(self.service, list(filter_public_services({'q':'Logo'})))
        self.assertIn(self.provider, list(filter_public_providers({'q':'Logo'})))
        self.assertIn(self.category, list(filter_public_categories({'q':'Design'})))
    def test_provider_search_filters_by_city_district_and_distance(self):
        from .search import filter_public_providers
        providers = filter_public_providers({'q':'Logo','city':'Sanaa','district':'Hadda','lat':'15.35','lng':'44.20','radius':'5'})
        self.assertIn(self.provider, providers)


class ManagedServiceRelationshipTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Development')
        self.provider = User.objects.create_user(username='managed-provider', email='managed@example.com', password='x', role='provider')
        profile = self.provider.provider_profile
        profile.status = 'active'
        profile.verification_status = 'verified'
        profile.save()
        self.managed = ManagedService.objects.create(name='Web development', category=self.category)
        self.approval = ProviderService.objects.create(
            provider=profile,
            catalog_service=self.managed,
            approval_status='approved',
            is_active=True,
            price=0,
        )

    def test_new_service_requires_an_explicit_approved_provider_service(self):
        form = ServiceForm(
            data={
                'title': 'Unlinked service',
                'description': 'x',
                'price_type': 'fixed',
                'currency': 'YER',
                'price': '10',
                'delivery_time': '1',
            },
            provider_user=self.provider,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('provider_service', form.errors)

    def test_service_form_uses_selected_managed_service_and_derives_category(self):
        form = ServiceForm(
            data={
                'provider_service': str(self.approval.pk),
                'title': 'Linked service',
                'description': 'x',
                'price_type': 'fixed',
                'currency': 'YER',
                'price': '10',
                'delivery_time': '1',
            },
            provider_user=self.provider,
        )
        self.assertTrue(form.is_valid(), form.errors)
        service = form.save(commit=False)
        service.provider = self.provider
        self.assertEqual(service.provider_service_id, self.approval.pk)
        self.assertEqual(service.category_id, self.category.pk)
        service.full_clean()

    def test_public_search_excludes_service_without_active_approval_link(self):
        from .search import filter_public_services
        legacy = Service.objects.create(
            provider=self.provider,
            category=self.category,
            title='Legacy unlinked service',
            description='x',
            price=10,
            delivery_time=1,
            status='active',
        )
        self.assertNotIn(legacy, list(filter_public_services({})))
