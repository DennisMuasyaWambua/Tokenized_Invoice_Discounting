#!/usr/bin/env python
import os
import sys
import django

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvoiceDiscounting.settings')
    
    # Override the database URL temporarily
    os.environ['DATABASE_URL'] = 'sqlite:///db.sqlite3'
    
    django.setup()
    
    from discounting.models import User, Role

    # Create admin role if it doesn't exist
    admin_role, created = Role.objects.get_or_create(
        short_name='admin',
        defaults={
            'name': 'Administrator',
            'description': 'System administrator with full access'
        }
    )

    # Update admin user to have admin role
    try:
        admin_user = User.objects.get(email='admin@test.com')
        admin_user.role = admin_role
        admin_user.save()
        print(f'Admin role created: {created}')
        print(f'Admin user role updated: {admin_user.role.short_name}')
    except User.DoesNotExist:
        print('Admin user not found')