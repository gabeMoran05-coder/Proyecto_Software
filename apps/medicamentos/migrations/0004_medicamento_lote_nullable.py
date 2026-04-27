from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('medicamentos', '0003_alter_lote_fecha_ingreso_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='medicamento',
            name='id_lote',
            field=models.ForeignKey(
                blank=True,
                db_column='id_lote',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='medicamentos.lote',
            ),
        ),
    ]
