from django.db import migrations


def marcar_lotes_ocultos_inactivos(apps, schema_editor):
    Lote = apps.get_model('medicamentos', 'Lote')
    Lote.objects.filter(oculto_por_caducidad=True, activo=True).update(activo=False)


class Migration(migrations.Migration):

    dependencies = [
        ('medicamentos', '0012_medicamento_dias_alerta_caducidad'),
    ]

    operations = [
        migrations.RunPython(marcar_lotes_ocultos_inactivos, migrations.RunPython.noop),
    ]
