from django.apps import AppConfig


class MedicamentosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'apps.medicamentos'   # ← ruta completa del paquete
    verbose_name       = 'Medicamentos'