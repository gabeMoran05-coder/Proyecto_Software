from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0004_usuario_email'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificacionSistema',
            fields=[
                ('id_notificacion', models.AutoField(primary_key=True, serialize=False)),
                ('clave', models.CharField(max_length=120, unique=True)),
                ('titulo', models.CharField(max_length=120)),
                ('mensaje', models.CharField(max_length=255)),
                ('categoria', models.CharField(blank=True, max_length=60)),
                ('nivel', models.CharField(choices=[('info', 'Informacion'), ('success', 'Correcto'), ('warning', 'Advertencia'), ('danger', 'Critico')], default='info', max_length=20)),
                ('url', models.CharField(blank=True, max_length=255)),
                ('activa', models.BooleanField(default=True)),
                ('fecha_creacion', models.DateTimeField(default=django.utils.timezone.now)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Notificacion del sistema',
                'verbose_name_plural': 'Notificaciones del sistema',
                'db_table': 'notificacion_sistema',
                'ordering': ['-fecha_actualizacion', '-fecha_creacion'],
            },
        ),
        migrations.CreateModel(
            name='NotificacionSistemaDescartada',
            fields=[
                ('id_descartada', models.AutoField(primary_key=True, serialize=False)),
                ('fecha_descartada', models.DateTimeField(default=django.utils.timezone.now)),
                ('id_notificacion', models.ForeignKey(db_column='id_notificacion', on_delete=django.db.models.deletion.CASCADE, to='usuarios.notificacionsistema')),
                ('id_usuario', models.ForeignKey(db_column='id_usuario', on_delete=django.db.models.deletion.CASCADE, to='usuarios.usuario')),
            ],
            options={
                'verbose_name': 'Notificacion descartada',
                'verbose_name_plural': 'Notificaciones descartadas',
                'db_table': 'notificacion_sistema_descartada',
                'unique_together': {('id_usuario', 'id_notificacion')},
            },
        ),
    ]
