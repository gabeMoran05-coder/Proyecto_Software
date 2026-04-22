# Generated manually to match BaseDeDatos/farmacia_inclusiva.sql

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Usuario',
            fields=[
                ('id_usuario', models.AutoField(primary_key=True, serialize=False)),
                ('usuario', models.CharField(max_length=60, unique=True, verbose_name='Usuario')),
                ('rol', models.CharField(choices=[('admin', 'Administrador'), ('administrador', 'Administrador'), ('cajero', 'Cajero'), ('almacen', 'Almacen'), ('farmaceutico', 'Farmaceutico')], max_length=30, verbose_name='Rol')),
                ('fecha_creacion', models.DateField(blank=True, null=True, verbose_name='Fecha de creacion')),
                ('ultima_conexion', models.DateTimeField(blank=True, null=True, verbose_name='Ultima conexion')),
                ('nombre', models.CharField(max_length=80, verbose_name='Nombre(s)')),
                ('ap_pat', models.CharField(blank=True, max_length=60, null=True, verbose_name='Apellido paterno')),
                ('ap_mat', models.CharField(blank=True, max_length=60, null=True, verbose_name='Apellido materno')),
                ('telefono', models.CharField(blank=True, max_length=15, null=True, verbose_name='Telefono')),
            ],
            options={
                'verbose_name': 'Usuario',
                'verbose_name_plural': 'Usuarios',
                'db_table': 'usuario',
                'ordering': ['nombre', 'ap_pat'],
            },
        ),
    ]
