from django.contrib import admin
from .models import Notificacion

@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ['venta', 'enviado', 'fecha_envio']
    list_filter  = ['enviado']
