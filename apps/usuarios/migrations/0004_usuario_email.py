from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0003_usuario_activo_usuario_fecha_baja_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='email',
            field=models.EmailField(
                blank=True,
                max_length=254,
                null=True,
                verbose_name='Correo electronico',
            ),
        ),
    ]
