from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0003_usuario_activo_usuario_fecha_baja_and_more'),
        ('medicamentos', '0004_medicamento_lote_nullable'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificacionCaducidadDescartada',
            fields=[
                ('id_notificacion', models.AutoField(primary_key=True, serialize=False)),
                ('fecha_descartada', models.DateTimeField(default=django.utils.timezone.now)),
                ('id_lote', models.ForeignKey(db_column='id_lote', on_delete=django.db.models.deletion.CASCADE, to='medicamentos.lote')),
                ('id_usuario', models.ForeignKey(db_column='id_usuario', on_delete=django.db.models.deletion.CASCADE, to='usuarios.usuario')),
            ],
            options={
                'db_table': 'notificacion_caducidad_descartada',
                'unique_together': {('id_usuario', 'id_lote')},
            },
        ),
    ]
