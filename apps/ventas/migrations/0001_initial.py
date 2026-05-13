# Generated manually to match apps/ventas/models.py

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('clientes', '0001_initial'),
        ('medicamentos', '0001_initial'),
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MetodoPago',
            fields=[
                ('id_metPag', models.AutoField(primary_key=True, serialize=False)),
                ('nombre_metodo', models.CharField(max_length=50, verbose_name='Metodo de pago')),
                ('descripcion', models.CharField(blank=True, max_length=150, null=True, verbose_name='Descripcion')),
            ],
            options={
                'verbose_name': 'Metodo de pago',
                'verbose_name_plural': 'Metodos de pago',
                'db_table': 'metodo_pago',
                'ordering': ['nombre_metodo'],
            },
        ),
        migrations.CreateModel(
            name='Venta',
            fields=[
                ('id_ventas', models.AutoField(primary_key=True, serialize=False)),
                ('fecha_venta', models.DateTimeField(blank=True, null=True, verbose_name='Fecha de venta')),
                ('total_venta', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Total')),
                ('id_cliente', models.ForeignKey(blank=True, db_column='id_cliente', null=True, on_delete=django.db.models.deletion.SET_NULL, to='clientes.cliente', verbose_name='Cliente')),
                ('id_metPag', models.ForeignKey(db_column='id_metPag', on_delete=django.db.models.deletion.PROTECT, to='ventas.metodopago', verbose_name='Metodo de pago')),
                ('id_usuario', models.ForeignKey(db_column='id_usuario', on_delete=django.db.models.deletion.PROTECT, to='usuarios.usuario', verbose_name='Cajero')),
            ],
            options={
                'verbose_name': 'Venta',
                'verbose_name_plural': 'Ventas',
                'db_table': 'ventas',
                'ordering': ['-fecha_venta'],
            },
        ),
        migrations.CreateModel(
            name='DetalleVenta',
            fields=[
                ('id_detalle', models.AutoField(primary_key=True, serialize=False)),
                ('cantidad', models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Cantidad')),
                ('precio_unitario', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Precio unitario')),
                ('subtotal', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Subtotal')),
                ('id_medicamento', models.ForeignKey(db_column='id_medicamento', on_delete=django.db.models.deletion.PROTECT, to='medicamentos.medicamento', verbose_name='Medicamento')),
                ('id_ventas', models.ForeignKey(db_column='id_ventas', on_delete=django.db.models.deletion.CASCADE, to='ventas.venta', verbose_name='Venta')),
            ],
            options={
                'verbose_name': 'Detalle de venta',
                'verbose_name_plural': 'Detalles de venta',
                'db_table': 'detalle_ventas_medicamento',
                'ordering': ['id_detalle'],
            },
        ),
    ]
