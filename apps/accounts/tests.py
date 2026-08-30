from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.accounts.models import User
from apps.core.models import City, District
from apps.marketplace.models import Category, ManagedService, ProviderService, Service
from apps.orders.models import Order
from apps.reviews.models import Review

class DomainArchitectureTests(TestCase):
    def setUp(self):
        self.city=City.objects.create(name='Sanaa')
        self.district=District.objects.create(city=self.city,name='Hadda')
        self.customer=User.objects.create_user(username='customer',email='customer@example.com',password='pass',role='customer',location_city=self.city,location_district=self.district)
        self.provider=User.objects.create_user(username='provider',email='provider@example.com',password='pass',role='provider')
        self.profile=self.provider.provider_profile
        self.profile.status='active'; self.profile.verification_status='verified'; self.profile.location_city=self.city; self.profile.location_district=self.district; self.profile.save()
        self.category=Category.objects.create(name='Development')
        self.managed=ManagedService.objects.create(name='Web development',category=self.category)
        self.approval=ProviderService.objects.create(provider=self.profile,managed_service=self.managed,approval_status='approved')
        self.service=Service.objects.create(provider=self.provider,provider_service=self.approval,title='Professional web development',description='A complete web application',price=100,delivery_time=2,status='active')

    def test_category_is_derived_from_approved_managed_service(self):
        self.assertEqual(self.service.category, self.category)
        with self.assertRaises(Exception):
            ProviderService.objects.create(provider=self.profile,managed_service=self.managed)

    def test_order_and_review_ownership_rules(self):
        order=Order(customer=self.customer,provider=self.provider,service=self.service,title=self.service.title,description='requirements',agreed_price=100,delivery_days=2,status=Order.STATUS_COMPLETED)
        order.full_clean(); order.save()
        review=Review(order=order,customer=self.customer,provider=self.provider,service=self.service,service_rating=5,provider_rating=5,comment='Excellent delivery')
        review.full_clean(); review.save()
        other=User.objects.create_user(username='other',email='other@example.com',password='pass')
        invalid=Review(order=order,customer=other,provider=self.provider,service=self.service,service_rating=4,provider_rating=4,comment='Invalid ownership')
        with self.assertRaises(ValidationError): invalid.full_clean()
