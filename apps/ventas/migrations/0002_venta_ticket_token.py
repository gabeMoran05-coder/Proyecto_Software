from django.db import migrations, models


def crear_tokens(apps, schema_editor):
    import secrets

    Venta = apps.get_model('ventas', 'Venta')
    for venta in Venta.objects.filter(ticket_token__isnull=True):
        venta.ticket_token = secrets.token_urlsafe(32)
        venta.save(update_fields=['ticket_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='ticket_token',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.RunPython(crear_tokens, migrations.RunPython.noop),
    ]
