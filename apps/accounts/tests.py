from decimal import Decimal
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from apps.marketplace.models import Category, Service, ManagedService, Specialization, Qualification
from apps.core.models import TermsAndConditions, TermsAcceptance, City, District
from .forms import ProviderDocumentForm, ProviderProfileForm, ProviderVerificationRequestForm
from .models import ProviderDocument, ProviderDocumentType, ProviderVerificationRequest, User

class ProviderDocumentValidationTests(TestCase):
    def setUp(self):
        self.doc_type=ProviderDocumentType.objects.get(code='IDENTITY')
    def test_rejects_executable_upload(self):
        form=ProviderDocumentForm(data={'document_type':self.doc_type.pk}, files={'file':SimpleUploadedFile('bad.exe', b'MZ', content_type='application/x-msdownload')})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)
    def test_accepts_pdf_upload_and_saves_private_document(self):
        user=User.objects.create_user(username='provider-doc', email='pd@example.com', password='x', role='provider')
        form=ProviderDocumentForm(data={'document_type':self.doc_type.pk}, files={'file':SimpleUploadedFile('id.pdf', b'%PDF-1.4', content_type='application/pdf')})
        self.assertTrue(form.is_valid(), form.errors)
        doc=form.save(commit=False); doc.provider=user.provider_profile; doc.save()
        self.assertTrue(doc.file.name.startswith('provider_documents/'))

    def test_staff_can_open_provider_document_securely(self):
        owner=User.objects.create_user(username='staff-owner', email='staff-owner@example.com', password='x', role='provider')
        staff=User.objects.create_user(username='staff-user', email='staff@example.com', password='x', role='admin', is_staff=True)
        doc=ProviderDocument.objects.create(provider=owner.provider_profile, document_type=self.doc_type, file=SimpleUploadedFile('id.pdf', b'%PDF', content_type='application/pdf'))
        self.client.force_login(staff)
        response=self.client.get(reverse('accounts:provider_document_download', args=[doc.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'].split(';')[0], 'attachment')
    def test_provider_cannot_download_another_provider_document(self):
        owner=User.objects.create_user(username='owner', email='owner@example.com', password='x', role='provider')
        other=User.objects.create_user(username='other', email='other@example.com', password='x', role='provider')
        doc=ProviderDocument.objects.create(provider=owner.provider_profile, document_type=self.doc_type, file=SimpleUploadedFile('id.pdf', b'%PDF', content_type='application/pdf'))
        self.client.force_login(other)
        response=self.client.get(reverse('accounts:provider_document_download', args=[doc.pk]))
        self.assertEqual(response.status_code, 302)

class ProviderLocationAndOnboardingTests(TestCase):
    def test_provider_profile_form_saves_location_coordinates(self):
        user=User.objects.create_user(username='map-provider', email='map@example.com', password='x', role='provider')
        form=ProviderProfileForm(data={'bio':'Bio','specialization':'Design','experience_years':3,'hourly_rate':'10.00','address':'Street','city':'Sanaa','district':'Old City','latitude':'15.369400','longitude':'44.191000','service_radius':10,'availability':'Daily','qualifications':'Cert','experience':'Work','is_available':'on'}, instance=user.provider_profile)
        self.assertTrue(form.is_valid(), form.errors)
        profile=form.save()
        self.assertEqual(profile.latitude, Decimal('15.369400'))
        self.assertEqual(profile.longitude, Decimal('44.191000'))
    def test_submit_review_requires_checklist(self):
        user=User.objects.create_user(username='incomplete', email='inc@example.com', password='x', role='provider')
        self.client.force_login(user)
        response=self.client.post(reverse('accounts:provider_submit_review'))
        user.provider_profile.refresh_from_db()
        self.assertNotEqual(user.provider_profile.verification_status, 'pending_review')
        self.assertEqual(response.status_code, 302)

from pathlib import Path
from tempfile import TemporaryDirectory
from django.test import override_settings

class ProviderEditPersistenceViewTests(TestCase):
    def test_provider_edit_saves_user_profile_provider_profile_and_location(self):
        user = User.objects.create_user(username='edit-provider', email='old@example.com', password='x', role='provider')
        self.client.force_login(user)
        response = self.client.post(reverse('accounts:provider_profile_edit'), {
            'user-first_name': 'Ali',
            'user-last_name': 'Provider',
            'user-email': 'ali@example.com',
            'user-phone': '771234567',
            'user-city': 'Sanaa User',
                        'provider-display_name': 'Ali Pro',
            'provider-bio': 'Experienced provider bio',
            'provider-phone': '778888888',
            'provider-email': 'work@example.com',
            'provider-specialization': 'Electrical',
            'provider-experience_years': '7',
            'provider-qualifications': 'Certified electrician',
            'provider-experience': 'Residential and commercial work',
            'provider-hourly_rate': '25.50',
            'provider-address': 'Main street',
            'provider-city': 'Sanaa Work',
            'provider-district': 'Old City',
            'provider-latitude': '15.369400',
            'provider-longitude': '44.191000',
            'provider-service_radius': '15',
            'provider-availability': 'Daily',
            'provider-is_available': 'on',
        })
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        profile = user.provider_profile
        profile.refresh_from_db()
        self.assertEqual(user.first_name, 'Ali')
        self.assertEqual(user.email, 'ali@example.com')
        self.assertEqual(profile.display_name, 'Ali Pro')
        self.assertEqual(profile.city, 'Sanaa Work')
        # Account and professional contact data remain independent.
        self.assertEqual(profile.phone, '778888888')
        self.assertEqual(profile.email, 'work@example.com')
        self.assertEqual(profile.district, 'Old City')
        self.assertEqual(profile.latitude, Decimal('15.369400'))
        self.assertEqual(profile.longitude, Decimal('44.191000'))

    def test_provider_profile_form_rejects_invalid_coordinates(self):
        user = User.objects.create_user(username='bad-map', email='bad-map@example.com', password='x', role='provider')
        form = ProviderProfileForm(data={
            'display_name': '', 'bio': '', 'phone': '', 'email': '',
            'experience_years': '0', 'qualifications': '', 'experience': '', 'hourly_rate': '', 'address': '',
            'city': '', 'district': '', 'latitude': '99.000000', 'longitude': '44.000000',
            'service_radius': '10', 'availability': '',
        }, instance=user.provider_profile)
        self.assertFalse(form.is_valid())
        self.assertIn('latitude', form.errors)

class ProviderDocumentStorageFallbackTests(TestCase):
    def test_secure_download_falls_back_to_legacy_media_file_without_public_url(self):
        with TemporaryDirectory() as media_dir, TemporaryDirectory() as private_dir:
            with override_settings(MEDIA_ROOT=media_dir, PRIVATE_MEDIA_ROOT=private_dir):
                owner = User.objects.create_user(username='legacy-owner', email='legacy-owner@example.com', password='x', role='provider')
                staff = User.objects.create_user(username='legacy-staff', email='legacy-staff@example.com', password='x', role='admin', is_staff=True)
                doc_type = ProviderDocumentType.objects.get(code='IDENTITY')
                legacy_rel = 'provider_documents/provider_%s/legacy.png' % owner.provider_profile.pk
                legacy_path = Path(media_dir) / legacy_rel
                legacy_path.parent.mkdir(parents=True, exist_ok=True)
                legacy_path.write_bytes(b'legacy-bytes')
                doc = ProviderDocument.objects.create(provider=owner.provider_profile, document_type=doc_type)
                doc.file.name = legacy_rel
                doc.save(update_fields=['file'])
                self.client.force_login(staff)
                response = self.client.get(reverse('accounts:provider_document_download', args=[doc.pk]))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(b''.join(response.streaming_content), b'legacy-bytes')


class ProviderVerificationWorkflowTests(TestCase):
    def setUp(self):
        self.city = City.objects.create(name='صنعاء')
        self.district = District.objects.create(city=self.city, name='التحرير')
        self.specialization = Specialization.objects.create(name='تصميم')
        self.qualification = Qualification.objects.create(name='شهادة مهنية')
        self.managed_service = ManagedService.objects.create(name='تصميم شعار')
        self.terms = TermsAndConditions.objects.create(
            version='workflow-v1', content='الشروط', commission_rate=10, is_active=True
        )
        self.provider = User.objects.create_user(
            username='workflow-provider', email='workflow@example.com', password='pass', role='provider'
        )
        self.identity_type = ProviderDocumentType.objects.get(code='IDENTITY')
        self.cv_type = ProviderDocumentType.objects.get(code='CV')

    def onboarding_payload(self):
        return {
            'wizard_action': 'submit_review',
            'user-first_name': 'مقدم',
            'user-last_name': 'الخدمة',
            'user-email': 'workflow@example.com',
            'user-phone': '771234567',
            'provider-display_name': 'مقدم خدمات',
            'provider-bio': 'خبرة مهنية طويلة في تقديم الخدمات.',
            'provider-phone': '778888888',
            'provider-email': 'work@example.com',
            'provider-specializations': [str(self.specialization.pk)],
            'provider-specialization': 'تصميم',
            'provider-experience_years': '4',
            'provider-qualification_choices': [str(self.qualification.pk)],
            'provider-qualifications': 'شهادة مهنية',
            'provider-experience': 'أربع سنوات من الخبرة العملية.',
            'provider-hourly_rate': '25.00',
            'provider-address': 'شارع رئيسي',
            'provider-location_city': str(self.city.pk),
            'provider-location_district': str(self.district.pk),
            'provider-city': 'صنعاء',
            'provider-district': 'التحرير',
            'provider-latitude': '15.369400',
            'provider-longitude': '44.191000',
            'provider-service_radius': '10',
            'provider-availability': 'يوميًا',
            'provider-is_available': 'on',
            'requested_services': [str(self.managed_service.pk)],
        }

    def add_required_documents(self):
        ProviderDocument.objects.create(
            provider=self.provider.provider_profile,
            document_type=self.identity_type,
            file=SimpleUploadedFile('identity.pdf', b'%PDF-identity', content_type='application/pdf'),
        )
        ProviderDocument.objects.create(
            provider=self.provider.provider_profile,
            document_type=self.cv_type,
            file=SimpleUploadedFile('cv.pdf', b'%PDF-cv', content_type='application/pdf'),
        )

    def test_provider_registration_redirects_to_onboarding(self):
        response = self.client.post(reverse('accounts:register'), {
            'first_name': 'مقدم',
            'last_name': 'جديد',
            'username': 'new-provider',
            'email': 'new-provider@example.com',
            'phone': '771111111',
            'role': 'provider',
            'password1': 'Strong-pass-123',
            'password2': 'Strong-pass-123',
        })
        self.assertRedirects(response, reverse('accounts:provider_onboarding'))

    def test_profile_edit_is_not_verification_page(self):
        self.client.force_login(self.provider)
        response = self.client.get(reverse('accounts:provider_profile_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'تعديل الملف الشخصي')
        self.assertNotContains(response, 'إرسال للمراجعة')
        self.assertNotContains(response, 'مستندات التوثيق')

    def test_onboarding_submission_creates_request_visible_to_admin_and_supports_re_review(self):
        self.add_required_documents()
        TermsAcceptance.objects.create(user=self.provider, terms=self.terms, commission_rate=self.terms.commission_rate)
        self.client.force_login(self.provider)

        response = self.client.post(reverse('accounts:provider_onboarding'), self.onboarding_payload())
        self.assertRedirects(response, reverse('accounts:provider_onboarding'))
        verification = ProviderVerificationRequest.objects.get(provider=self.provider.provider_profile)
        self.assertEqual(verification.status, 'pending')
        self.assertEqual(verification.requested_services.get(), self.managed_service)
        self.assertEqual(verification.documents.count(), 2)
        self.provider.provider_profile.refresh_from_db()
        self.assertEqual(self.provider.provider_profile.verification_status, 'pending_review')

        admin = User.objects.create_user(
            username='workflow-admin', email='workflow-admin@example.com', password='pass',
            role='admin', is_staff=True
        )
        self.client.force_login(admin)
        response = self.client.get(reverse('dashboard:verification'))
        self.assertContains(response, 'مقدم خدمات')
        self.assertContains(response, 'تصميم شعار')

        response = self.client.post(reverse('dashboard:verification_decision', args=[verification.pk]), {
            'status': 'needs_documents', 'admin_note': 'يرجى تحديث المستندات المطلوبة.'
        })
        self.assertRedirects(response, reverse('dashboard:verification_detail', args=[verification.pk]))
        verification.refresh_from_db()
        self.assertEqual(verification.status, 'needs_documents')
        self.provider.provider_profile.refresh_from_db()
        self.assertEqual(self.provider.provider_profile.verification_status, 'needs_documents')

        self.client.force_login(self.provider)
        response = self.client.get(reverse('accounts:provider_onboarding'))
        self.assertContains(response, 'يرجى تحديث المستندات المطلوبة.')
        response = self.client.post(reverse('accounts:provider_onboarding'), self.onboarding_payload())
        self.assertRedirects(response, reverse('accounts:provider_onboarding'))
        verification.refresh_from_db()
        self.assertEqual(verification.status, 'pending')
        self.assertEqual(ProviderVerificationRequest.objects.filter(provider=self.provider.provider_profile).count(), 1)

        self.client.force_login(admin)
        self.client.post(reverse('dashboard:verification_decision', args=[verification.pk]), {
            'status': 'approved', 'admin_note': 'تم الاعتماد.'
        })
        self.provider.provider_profile.refresh_from_db()
        self.assertEqual(self.provider.provider_profile.verification_status, 'verified')
        self.assertEqual(self.provider.provider_profile.status, 'active')

        self.client.force_login(self.provider)
        response = self.client.get(reverse('accounts:provider_onboarding'))
        self.assertRedirects(response, reverse('accounts:provider_profile_edit'))


class PartialVerificationSubmissionTests(TestCase):
    def test_choice_fields_use_dropdown_style_selectors(self):
        provider = User.objects.create_user(
            username='choices-provider', email='choices@example.com', password='pass', role='provider'
        )
        profile_form = ProviderProfileForm(instance=provider.provider_profile)
        verification_form = ProviderVerificationRequestForm(provider=provider.provider_profile)
        for field_name in ('specializations', 'qualification_choices'):
            widget = profile_form.fields[field_name].widget
            self.assertEqual(widget.__class__.__name__, 'SelectMultiple')
            self.assertEqual(widget.attrs['size'], 1)
        self.assertEqual(verification_form.fields['requested_services'].widget.attrs['size'], 1)
        self.assertEqual(verification_form.fields['requested_services'].widget.attrs['form'], 'provider-onboarding-form')

    def test_submit_review_rejects_incomplete_data_and_keeps_saved_draft(self):
        provider = User.objects.create_user(
            username='partial-provider', email='partial@example.com', password='pass', role='provider'
        )
        terms = TermsAndConditions.objects.create(
            version='partial-v1', content='الشروط', commission_rate=8, is_active=True
        )
        TermsAcceptance.objects.create(
            user=provider, terms=terms, commission_rate=terms.commission_rate
        )
        self.client.force_login(provider)

        response = self.client.post(reverse('accounts:provider_onboarding'), {
            'wizard_action': 'submit_review',
            'user-email': 'partial@example.com',
        })

        self.assertRedirects(response, reverse('accounts:provider_onboarding'))
        provider.provider_profile.refresh_from_db()
        self.assertNotEqual(provider.provider_profile.verification_status, 'pending_review')
        self.assertFalse(ProviderVerificationRequest.objects.filter(provider=provider.provider_profile, status='pending').exists())

