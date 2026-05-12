from django.contrib import admin
from django.urls import include, path

from apps.usuarios.views import home_redirect
from apps.ventas.webhooks import whatsapp_webhook


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_redirect, name='home'),
    path('medicamentos/', include('apps.medicamentos.urls')),
    path('proveedores/', include('apps.proveedores.urls')),
    path('clientes/', include('apps.clientes.urls')),
    path('usuarios/', include('apps.usuarios.urls')),
    path('ventas/', include('apps.ventas.urls')),
    path('whatsapp/webhook/', whatsapp_webhook, name='whatsapp_webhook'),
    path('reportes/', include('apps.reportes.urls')),
]
