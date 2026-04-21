# Generated manually to fix kra_verified NOT NULL constraint issue
from django.db import migrations, models


def fix_null_kra_verified(apps, schema_editor):
    """Set any NULL kra_verified values to False"""
    Invoice = apps.get_model('discounting', 'Invoice')
    Invoice.objects.filter(kra_verified__isnull=True).update(kra_verified=False)


class Migration(migrations.Migration):

    dependencies = [
        ('discounting', '0003_invoice_buyer_kra_pin_invoice_kra_verification_date_and_more'),
    ]

    operations = [
        # First, fix any existing NULL values
        migrations.RunPython(fix_null_kra_verified, migrations.RunPython.noop),

        # Then ensure the field has the proper default
        migrations.AlterField(
            model_name='invoice',
            name='kra_verified',
            field=models.BooleanField(
                default=False,
                help_text='Verified with KRA eTIMS system'
            ),
        ),
    ]
