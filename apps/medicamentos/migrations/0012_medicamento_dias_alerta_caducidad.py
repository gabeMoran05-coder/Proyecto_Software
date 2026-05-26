from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('medicamentos', '0011_configuracioninventario'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicamento',
            name='dias_alerta_caducidad',
            field=models.PositiveSmallIntegerField(default=90),
        ),
    ]
