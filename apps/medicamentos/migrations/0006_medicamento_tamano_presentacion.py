from django.db import migrations, models


BASE_PRESENTACIONES = [
    'Tabletas',
    'Capsulas',
    'Jarabe',
    'Suspension',
    'Solucion',
    'Gotas',
    'Ampolleta',
    'Inyectable',
    'Crema',
    'Unguento',
    'Gel',
    'Aerosol',
    'Polvo',
    'Caja',
    'Frasco',
    'Sobre',
]


def separar_presentacion_y_tamano(apps, schema_editor):
    Medicamento = apps.get_model('medicamentos', 'Medicamento')
    bases = sorted(BASE_PRESENTACIONES, key=len, reverse=True)
    for medicamento in Medicamento.objects.exclude(presentacion__isnull=True).exclude(presentacion=''):
        presentacion = (medicamento.presentacion or '').strip()
        for base in bases:
            if presentacion.casefold() == base.casefold():
                break
            prefijo = f'{base} '
            if presentacion.casefold().startswith(prefijo.casefold()):
                medicamento.presentacion = base
                medicamento.tamano_presentacion = presentacion[len(prefijo):].strip() or None
                medicamento.save(update_fields=['presentacion', 'tamano_presentacion'])
                break


class Migration(migrations.Migration):

    dependencies = [
        ('medicamentos', '0005_notificacioncaducidaddescartada'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicamento',
            name='tamano_presentacion',
            field=models.CharField(blank=True, max_length=80, null=True),
        ),
        migrations.RunPython(separar_presentacion_y_tamano, migrations.RunPython.noop),
    ]
