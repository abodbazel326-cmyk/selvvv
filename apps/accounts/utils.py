REQUIRED_DOCUMENT_CODES = ['IDENTITY', 'CV']
DEFAULT_DOCUMENT_TYPES = [
    ('IDENTITY', 'الهوية', True),
    ('CV', 'CV / السيرة الذاتية', True),
    ('EXPERIENCE_CERTIFICATE', 'شهادة خبرة', False),
    ('PROFESSIONAL_CERTIFICATE', 'شهادة مهنية', False),
    ('ACADEMIC_CERTIFICATE', 'شهادة أكاديمية', False),
    ('COMMERCIAL_REGISTRATION', 'سجل تجاري', False),
    ('OTHER', 'مستندات أخرى', False),
]

def is_provider_verified(user):
    if not user.is_authenticated or not user.is_provider():
        return False
    profile = getattr(user, 'provider_profile', None)
    return bool(profile and profile.status == 'active' and profile.verification_status == 'verified')

def get_provider_onboarding_status(profile, requested_service_ids=None):
    """Return the real onboarding checklist and whether submission is complete."""
    from apps.core.models import TermsAcceptance, TermsAndConditions
    from apps.marketplace.models import ProviderService
    from apps.accounts.models import ProviderDocumentType
    from apps.payments.models import ProviderWallet, Wallet

    profile_ok = all([
        bool(profile.display_name.strip()),
        bool(profile.bio.strip()),
        profile.specializations.exists(),
    ])
    experience_ok = all([
        bool(profile.experience.strip()),
        profile.qualification_choices.exists(),
        profile.experience_years is not None,
    ])
    location_ok = all([
        bool(profile.location_city_id),
        bool(profile.location_district_id),
        profile.latitude is not None,
        profile.longitude is not None,
        bool(profile.address.strip()),
    ])

    required_codes = set(ProviderDocumentType.objects.filter(
        is_active=True, is_required=True
    ).values_list('code', flat=True))
    uploaded_codes = set(profile.documents.filter(
        status__in=['pending', 'approved']
    ).values_list('document_type__code', flat=True))
    documents_ok = required_codes.issubset(uploaded_codes) if required_codes else profile.documents.filter(status__in=['pending', 'approved']).exists()

    # Before approval, the provider has *requested* central services but does
    # not have approved ProviderService rows yet.  Treat that draft selection
    # as the onboarding requirement; ProviderService is created only by admin
    # approval and must never be required to submit the request.
    if requested_service_ids is None:
        services_ok = ProviderService.objects.filter(
            provider=profile, managed_service__is_active=True
        ).exists()
    else:
        services_ok = bool(requested_service_ids)

    active_terms = TermsAndConditions.objects.filter(is_active=True).order_by('-published_at', '-created_at').first()
    terms_ok = bool(active_terms and TermsAcceptance.objects.filter(
        user=profile.user, terms=active_terms
    ).exists())

    # If the administration has configured wallets, require at least one active
    # provider wallet; if no active wallets exist, payment setup is not blockable.
    has_active_wallet_catalog = Wallet.objects.filter(is_active=True).exists()
    wallet_ok = (not has_active_wallet_catalog) or ProviderWallet.objects.filter(
        provider=profile, is_active=True, wallet__is_active=True
    ).exists()

    checklist = {
        'profile': profile_ok,
        'services': services_ok,
        'experience': experience_ok,
        'documents': documents_ok,
        'location': location_ok,
        'terms': terms_ok,
        'wallet': wallet_ok,
    }
    return checklist, all(checklist.values())
