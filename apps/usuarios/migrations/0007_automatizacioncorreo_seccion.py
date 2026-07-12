# Generated manually for section-specific report automations.

import datetime

from django.db import migrations, models


def sembrar_automatizaciones_por_seccion(apps, schema_editor):
    AutomatizacionCorreo = apps.get_model('usuarios', 'AutomatizacionCorreo')
    AutomatizacionCorreo.objects.filter(clave='ventas.resumen_diario').update(seccion_reporte='ventas')
    AutomatizacionCorreo.objects.filter(clave__in=[
        'reportes.reporte_semanal',
        'reportes.reporte_mensual',
    ]).update(seccion_reporte='general')

    secciones = [
        ('ventas', 'Ventas'),
        ('clientes', 'Clientes'),
        ('medicamentos', 'Medicamentos'),
        ('inventario', 'Inventario y caducidad'),
    ]
    for seccion, etiqueta in secciones:
        AutomatizacionCorreo.objects.get_or_create(
            clave=f'reportes.{seccion}.semanal',
            defaults={
                'nombre': f'{etiqueta} semanal',
                'descripcion': f'Envia PDF y Excel solo de {etiqueta.lower()} de la semana anterior.',
                'tarea': 'reporte_semanal',
                'seccion_reporte': seccion,
                'activa': False,
                'hora_envio': datetime.time(8, 0),
                'dia_semana': 0,
                'dia_mes': 1,
            },
        )
        AutomatizacionCorreo.objects.get_or_create(
            clave=f'reportes.{seccion}.mensual',
            defaults={
                'nombre': f'{etiqueta} mensual',
                'descripcion': f'Envia PDF y Excel solo de {etiqueta.lower()} del mes anterior.',
                'tarea': 'reporte_mensual',
                'seccion_reporte': seccion,
                'activa': False,
                'hora_envio': datetime.time(8, 15),
                'dia_semana': 0,
                'dia_mes': 1,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0006_automatizacioncorreo'),
    ]

    operations = [
        migrations.AddField(
            model_name='automatizacioncorreo',
            name='seccion_reporte',
            field=models.CharField(choices=[('general', 'Reporte general'), ('ventas', 'Ventas'), ('clientes', 'Clientes'), ('medicamentos', 'Medicamentos'), ('inventario', 'Inventario y caducidad')], default='general', max_length=30),
        ),
        migrations.RunPython(sembrar_automatizaciones_por_seccion, migrations.RunPython.noop),
    ]
