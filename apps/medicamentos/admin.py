from django.contrib import admin
from .models import Lote, Medicamento, CodigoQR

admin.site.register(Lote)
admin.site.register(Medicamento)
admin.site.register(CodigoQR)