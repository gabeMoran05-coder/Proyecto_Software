from django.urls import path
from django.http import HttpResponse
from . import views

def placeholder(request, pk=None):
    return HttpResponse("Pantalla en construcción - próximamente")

urlpatterns = [
    # Medicamentos
    path('', views.medicamento_list, name='medicamento_list'),
    path('nuevo/', views.medicamento_create, name='medicamento_create'),
    path('<int:pk>/', views.medicamento_detail, name='medicamento_detail'),
    path('<int:pk>/editar/', views.medicamento_update, name='medicamento_update'),
    path('<int:pk>/eliminar/', views.medicamento_delete, name='medicamento_delete'),

    # QR
    path('<int:med_pk>/qr/nuevo/', views.qr_create, name='qr_create'),
    path('qr/<int:qr_pk>/regenerar/', views.qr_regenerar, name='qr_regenerar'),
    path('qr/<int:qr_pk>/eliminar/', views.qr_delete, name='qr_delete'),

  # Lotes (Ahora sí, completos)
    path('lotes/', views.lote_list, name='lote_list'),
    path('lotes/nuevo/', views.lote_create, name='lote_create'),
    path('lotes/<int:pk>/', views.lote_detail, name='lote_detail'),
    path('lotes/<int:pk>/editar/', views.lote_update, name='lote_update'),
    path('lotes/<int:pk>/eliminar/', views.lote_delete, name='lote_delete'),
    path('lotes/<int:pk>/', views.lote_detail, name='lote_detail'),

    # Proveedor detail (placeholder temporal)
    path('proveedor/<int:pk>/', placeholder, name='proveedor_detail'),
]