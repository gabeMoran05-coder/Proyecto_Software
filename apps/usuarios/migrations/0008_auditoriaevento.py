# Generated manually for audit events.

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0007_automatizacioncorreo_seccion'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditoriaEvento',
            fields=[
                ('id_evento', models.AutoField(primary_key=True, serialize=False)),
                ('accion', models.CharField(max_length=80)),
                ('modulo', models.CharField(max_length=60)),
                ('objeto_tipo', models.CharField(blank=True, max_length=80)),
                ('objeto_id', models.CharField(blank=True, max_length=80)),
                ('descripcion', models.TextField(blank=True)),
                ('motivo', models.CharField(blank=True, max_length=160)),
                ('nivel', models.CharField(choices=[('info', 'Informacion'), ('warning', 'Advertencia'), ('danger', 'Critico')], default='info', max_length=20)),
                ('url', models.CharField(blank=True, max_length=255)),
                ('fecha', models.DateTimeField(default=django.utils.timezone.now)),
                ('id_usuario', models.ForeignKey(blank=True, db_column='id_usuario', null=True, on_delete=django.db.models.deletion.SET_NULL, to='usuarios.usuario')),
            ],
            options={
                'verbose_name': 'Evento de auditoria',
                'verbose_name_plural': 'Eventos de auditoria',
                'db_table': 'auditoria_evento',
                'ordering': ['-fecha', '-id_evento'],
            },
        ),
    ]
