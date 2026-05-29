from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('medicamentos', '0009_etiquetas_danino'),
    ]

    operations = [
        migrations.AlterField(
            model_name='movimientoinventario',
            name='tipo',
            field=models.CharField(choices=[('entrada', 'Entrada'), ('salida', 'Salida'), ('ajuste', 'Ajuste'), ('venta', 'Venta'), ('cancelacion', 'Cancelacion'), ('conteo', 'Conteo fisico'), ('ocultamiento', 'Ocultamiento')], max_length=20),
        ),
    ]
