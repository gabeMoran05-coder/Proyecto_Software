from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('medicamentos', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='lote',
            name='oculto_por_caducidad',
            field=models.BooleanField(default=False),
        ),
    ]
