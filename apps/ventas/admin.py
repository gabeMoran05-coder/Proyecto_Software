from django.contrib import admin
from .models import MetodoPago, Venta, DetalleVenta

admin.site.register(MetodoPago)
admin.site.register(Venta)
admin.site.register(DetalleVenta)