from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='password_hash',
            field=models.CharField(blank=True, max_length=128, verbose_name='Contrasena'),
        ),
    ]
