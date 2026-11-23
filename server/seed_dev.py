"""
Development Seed Script for QuoteFlow AI.
Provisions the initial organization and admin user in the active database (PostgreSQL or SQLite).
"""

import os
import sys
import django

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from users.services import register_user_with_organization

User = get_user_model()

def seed():
    email = 'admin@quoteflow.ai'
    password = 'Password123!'
    org_name = 'Acme Procurement'
    full_name = 'Admin User'

    user = User.objects.filter(email=email).first()
    if not user:
        user, org, tokens = register_user_with_organization(
            email=email,
            password=password,
            full_name=full_name,
            organization_name=org_name,
        )
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print(f"Created dev admin user: {email}")
        print(f"Password: {password}")
        print(f"Organization: {org.name}")
    else:
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        from organizations.models import Organization
        org = Organization.objects.filter(name=org_name).first() or Organization.objects.first()
        print(f"Updated existing user: {email} to superuser with password: {password}")

    # Seed sample suppliers matching our benchmark quotation documents
    from suppliers.models import Supplier, SupplierCategory, SupplierStatus
    suppliers_data = [
        {
            'company_name': 'Apex Precision Components Inc.',
            'contact_person': 'Sarah Jenkins',
            'email': 'sales@apexprecision.com',
            'phone': '+1 (555) 019-2831',
            'category': SupplierCategory.MACHINING,
            'country': 'US',
        },
        {
            'company_name': 'Titan Heavy Industries LLC',
            'contact_person': 'Marcus Vance',
            'email': 'quotes@titanheavy.com',
            'phone': '+1 (555) 438-9900',
            'category': SupplierCategory.MACHINING,
            'country': 'US',
        },
        {
            'company_name': 'Nexus Industrial Systems GmbH',
            'contact_person': 'Klaus Schneider',
            'email': 'angebote@nexus-sys.de',
            'phone': '+49 89 2345 6789',
            'category': SupplierCategory.MACHINING,
            'country': 'DE',
        },
        {
            'company_name': 'Delta Industrial Manufacturing Co.',
            'contact_person': 'Robert Chen',
            'email': 'bids@deltamfg.com',
            'phone': '+1 (555) 772-1144',
            'category': SupplierCategory.MACHINING,
            'country': 'US',
        },
    ]

    for s_data in suppliers_data:
        sup, created = Supplier.objects.get_or_create(
            organization=org,
            company_name=s_data['company_name'],
            defaults={
                'contact_person': s_data['contact_person'],
                'email': s_data['email'],
                'phone': s_data['phone'],
                'category': s_data['category'],
                'country': s_data['country'],
                'status': SupplierStatus.ACTIVE,
            }
        )
        if created:
            print(f"Created supplier: {sup.company_name}")
        else:
            print(f"Supplier already exists: {sup.company_name}")

if __name__ == '__main__':
    seed()
