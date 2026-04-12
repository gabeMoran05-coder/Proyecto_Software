from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_required(RedirectView.as_view(url='/medicamentos/')), name='home'),
    path('usuarios/', include('apps.usuarios.urls')),
    path('medicamentos/', include('apps.medicamentos.urls')),
    path('ventas/', include('apps.ventas.urls')),
    path('clientes/', include('apps.clientes.urls')),
    path('proveedores/', include('apps.proveedores.urls')),
    path('notificaciones/', include('apps.notificaciones.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
