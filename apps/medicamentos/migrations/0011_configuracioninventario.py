from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('medicamentos', '0010_tipo_movimiento_ocultamiento'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfiguracionInventario',
            fields=[
                ('id_configuracion', models.AutoField(primary_key=True, serialize=False)),
                ('dias_revision_caducidad', models.PositiveSmallIntegerField(default=1)),
                ('hora_retiro_caducidad', models.TimeField(default=datetime.time(7, 10))),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Configuracion de inventario',
                'verbose_name_plural': 'Configuraciones de inventario',
                'db_table': 'configuracion_inventario',
            },
        ),
    ]
