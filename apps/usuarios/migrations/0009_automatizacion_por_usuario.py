from django.db import migrations, models
import django.db.models.deletion


def asignar_automatizaciones_a_primer_admin(apps, schema_editor):
    Usuario = apps.get_model('usuarios', 'Usuario')
    AutomatizacionCorreo = apps.get_model('usuarios', 'AutomatizacionCorreo')
    admin = (
        Usuario.objects.filter(activo=True, rol__in=['admin', 'administrador'])
        .exclude(email='')
        .order_by('id_usuario')
        .first()
    )
    if admin:
        AutomatizacionCorreo.objects.filter(id_usuario__isnull=True).update(id_usuario=admin)


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0008_auditoriaevento'),
    ]

    operations = [
        migrations.AddField(
            model_name='automatizacioncorreo',
            name='id_usuario',
            field=models.ForeignKey(blank=True, db_column='id_usuario', null=True, on_delete=django.db.models.deletion.CASCADE, to='usuarios.usuario'),
        ),
        migrations.AlterField(
            model_name='automatizacioncorreo',
            name='clave',
            field=models.CharField(max_length=120),
        ),
        migrations.RunPython(asignar_automatizaciones_a_primer_admin, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name='automatizacioncorreo',
            unique_together={('id_usuario', 'clave')},
        ),
    ]
