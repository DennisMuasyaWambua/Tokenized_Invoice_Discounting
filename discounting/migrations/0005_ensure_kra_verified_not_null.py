# Generated manually to ensure kra_verified has proper database constraints
from django.db import migrations


def set_kra_verified_defaults_sql(apps, schema_editor):
    """Use raw SQL to ensure kra_verified has proper NOT NULL constraint with default"""
    if schema_editor.connection.vendor == 'postgresql':
        # First, update any NULL values to False
        schema_editor.execute(
            "UPDATE discounting_invoice SET kra_verified = FALSE WHERE kra_verified IS NULL;"
        )
        # Then ensure the column has a default value at database level
        schema_editor.execute(
            "ALTER TABLE discounting_invoice ALTER COLUMN kra_verified SET DEFAULT FALSE;"
        )
        # Ensure NOT NULL constraint
        schema_editor.execute(
            "ALTER TABLE discounting_invoice ALTER COLUMN kra_verified SET NOT NULL;"
        )


def reverse_sql(apps, schema_editor):
    """Reverse is a no-op since we don't want to undo these safety measures"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('discounting', '0004_fix_kra_verified_default'),
    ]

    operations = [
        migrations.RunPython(set_kra_verified_defaults_sql, reverse_sql),
    ]
