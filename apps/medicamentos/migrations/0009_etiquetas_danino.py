from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('medicamentos', '0008_inventario_kardex'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lote',
            name='motivo_oculto',
            field=models.CharField(blank=True, choices=[('caducidad', 'Caducidad'), ('defectuoso', 'Defectuoso'), ('danino', 'Dañino o riesgoso'), ('merma', 'Merma'), ('robo', 'Robo'), ('correccion', 'Correccion'), ('devolucion', 'Devolucion'), ('inactivo', 'Inactivo')], max_length=30),
        ),
        migrations.AlterField(
            model_name='movimientoinventario',
            name='motivo',
            field=models.CharField(choices=[('compra', 'Compra'), ('venta', 'Venta'), ('cancelacion', 'Cancelacion'), ('merma', 'Merma'), ('robo', 'Robo'), ('defectuoso', 'Defectuoso'), ('danino', 'Dañino o riesgoso'), ('correccion', 'Correccion'), ('devolucion', 'Devolucion'), ('conteo', 'Conteo fisico')], max_length=30),
        ),
    ]
