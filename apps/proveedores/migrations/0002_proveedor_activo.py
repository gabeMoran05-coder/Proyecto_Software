# Generated manually on 2026-04-23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proveedores', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='proveedor',
            name='activo',
            field=models.BooleanField(default=True),
        ),
    ]
