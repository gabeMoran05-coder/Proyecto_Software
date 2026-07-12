# Generated manually for configurable email automations.

import datetime

from django.db import migrations, models


def crear_automatizaciones(apps, schema_editor):
    AutomatizacionCorreo = apps.get_model('usuarios', 'AutomatizacionCorreo')
    defaults = [
        {
            'clave': 'ventas.resumen_diario',
            'nombre': 'Resumen diario de ventas',
            'descripcion': 'Envia por correo el resumen de ventas del dia.',
            'tarea': 'resumen_diario',
            'hora_envio': datetime.time(21, 0),
            'dia_semana': 0,
            'dia_mes': 1,
        },
        {
            'clave': 'reportes.reporte_semanal',
            'nombre': 'Reporte semanal',
            'descripcion': 'Envia PDF y Excel con el reporte de la semana anterior.',
            'tarea': 'reporte_semanal',
            'hora_envio': datetime.time(8, 0),
            'dia_semana': 0,
            'dia_mes': 1,
        },
        {
            'clave': 'reportes.reporte_mensual',
            'nombre': 'Reporte mensual',
            'descripcion': 'Envia PDF y Excel con el reporte del mes anterior.',
            'tarea': 'reporte_mensual',
            'hora_envio': datetime.time(8, 15),
            'dia_semana': 0,
            'dia_mes': 1,
        },
    ]
    for data in defaults:
        clave = data.pop('clave')
        AutomatizacionCorreo.objects.get_or_create(clave=clave, defaults=data)


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0005_notificacionsistema_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AutomatizacionCorreo',
            fields=[
                ('id_automatizacion', models.AutoField(primary_key=True, serialize=False)),
                ('clave', models.CharField(max_length=120, unique=True)),
                ('nombre', models.CharField(max_length=120)),
                ('descripcion', models.CharField(blank=True, max_length=255)),
                ('tarea', models.CharField(choices=[('resumen_diario', 'Resumen diario de ventas'), ('reporte_semanal', 'Reporte semanal'), ('reporte_mensual', 'Reporte mensual')], max_length=40)),
                ('activa', models.BooleanField(default=True)),
                ('hora_envio', models.TimeField(default=datetime.time(8, 0))),
                ('dia_semana', models.PositiveSmallIntegerField(choices=[(0, 'Lunes'), (1, 'Martes'), (2, 'Miercoles'), (3, 'Jueves'), (4, 'Viernes'), (5, 'Sabado'), (6, 'Domingo')], default=0)),
                ('dia_mes', models.PositiveSmallIntegerField(default=1)),
                ('ultimo_envio', models.DateField(blank=True, null=True)),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Automatizacion de correo',
                'verbose_name_plural': 'Automatizaciones de correo',
                'db_table': 'automatizacion_correo',
                'ordering': ['id_automatizacion'],
            },
        ),
        migrations.RunPython(crear_automatizaciones, migrations.RunPython.noop),
    ]
