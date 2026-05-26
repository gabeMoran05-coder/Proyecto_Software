from django.db import migrations


def ocultar_lotes_inactivos(apps, schema_editor):
    Lote = apps.get_model('medicamentos', 'Lote')
    Lote.objects.filter(activo=False, oculto_por_caducidad=False).update(
        oculto_por_caducidad=True
    )


class Migration(migrations.Migration):

    dependencies = [
        ('medicamentos', '0006_medicamento_tamano_presentacion'),
    ]

    operations = [
        migrations.RunPython(ocultar_lotes_inactivos, migrations.RunPython.noop),
    ]
