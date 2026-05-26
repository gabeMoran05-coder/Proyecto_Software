# Generated manually for inventory control features.

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0007_automatizacioncorreo_seccion'),
        ('medicamentos', '0007_ocultar_lotes_inactivos'),
    ]

    operations = [
        migrations.AddField(
            model_name='lote',
            name='detalle_oculto',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='lote',
            name='fecha_oculto',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='lote',
            name='motivo_oculto',
            field=models.CharField(blank=True, choices=[('caducidad', 'Caducidad'), ('defectuoso', 'Defectuoso'), ('danino', 'Danino o riesgoso'), ('merma', 'Merma'), ('robo', 'Robo'), ('correccion', 'Correccion'), ('devolucion', 'Devolucion'), ('inactivo', 'Inactivo')], max_length=30),
        ),
        migrations.AddField(
            model_name='medicamento',
            name='stock_minimo',
            field=models.PositiveIntegerField(default=50),
        ),
        migrations.CreateModel(
            name='MovimientoInventario',
            fields=[
                ('id_movimiento', models.AutoField(primary_key=True, serialize=False)),
                ('tipo', models.CharField(choices=[('entrada', 'Entrada'), ('salida', 'Salida'), ('ajuste', 'Ajuste'), ('venta', 'Venta'), ('cancelacion', 'Cancelacion'), ('conteo', 'Conteo fisico')], max_length=20)),
                ('motivo', models.CharField(choices=[('compra', 'Compra'), ('venta', 'Venta'), ('cancelacion', 'Cancelacion'), ('merma', 'Merma'), ('robo', 'Robo'), ('defectuoso', 'Defectuoso'), ('danino', 'Danino o riesgoso'), ('correccion', 'Correccion'), ('devolucion', 'Devolucion'), ('conteo', 'Conteo fisico')], max_length=30)),
                ('cantidad', models.IntegerField()),
                ('stock_antes', models.IntegerField()),
                ('stock_despues', models.IntegerField()),
                ('referencia', models.CharField(blank=True, max_length=120)),
                ('notas', models.TextField(blank=True)),
                ('fecha', models.DateTimeField(default=django.utils.timezone.now)),
                ('id_lote', models.ForeignKey(db_column='id_lote', on_delete=django.db.models.deletion.CASCADE, to='medicamentos.lote')),
                ('id_medicamento', models.ForeignKey(blank=True, db_column='id_medicamento', null=True, on_delete=django.db.models.deletion.SET_NULL, to='medicamentos.medicamento')),
                ('id_usuario', models.ForeignKey(blank=True, db_column='id_usuario', null=True, on_delete=django.db.models.deletion.SET_NULL, to='usuarios.usuario')),
            ],
            options={
                'db_table': 'movimiento_inventario',
                'ordering': ['-fecha', '-id_movimiento'],
            },
        ),
    ]
