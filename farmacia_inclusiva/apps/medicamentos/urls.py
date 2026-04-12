from django.urls import path
from . import views

app_name = 'medicamentos'

urlpatterns = [
    path('',                          views.lista,            name='lista'),
    path('crear/',                    views.crear,            name='crear'),
    path('<int:pk>/',                 views.detalle,          name='detalle'),
    path('<int:pk>/editar/',          views.editar,           name='editar'),
    path('<int:pk>/eliminar/',        views.eliminar,         name='eliminar'),
    # Lotes
    path('<int:med_pk>/lote/crear/',       views.crear_lote,   name='crear_lote'),
    path('lote/<int:pk>/eliminar/',        views.eliminar_lote, name='eliminar_lote'),
    # QR
    path('<int:med_pk>/qr/generar/',  views.generar_qr,       name='generar_qr'),
    path('<int:med_pk>/qr/',          views.vista_qr,         name='vista_qr'),
    # Pública (sin login)
    path('qr/<uuid:token>/',          views.pagina_qr_publica, name='qr_publica'),
]
