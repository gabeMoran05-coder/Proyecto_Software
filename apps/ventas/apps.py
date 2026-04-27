from django.apps import AppConfig # pyright: ignore[reportMissingModuleSource]


class VentasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'apps.ventas'
    verbose_name       = 'Ventas'