from django.urls import path

from . import views


urlpatterns = [
    path('', views.medicamento_list, name='medicamento_list'),
    path('nuevo/', views.medicamento_create, name='medicamento_create'),
    path('<int:pk>/', views.medicamento_detail, name='medicamento_detail'),
    path('<int:pk>/editar/', views.medicamento_update, name='medicamento_update'),
    path('<int:pk>/eliminar/', views.medicamento_delete, name='medicamento_delete'),

    path('lotes/', views.lote_list, name='lote_list'),
    path('lotes/ocultos/', views.lote_ocultos, name='lote_ocultos'),
    path('lotes/nuevo/', views.lote_create, name='lote_create'),
    path('lotes/<int:pk>/', views.lote_detail, name='lote_detail'),
    path('lotes/<int:pk>/asignar-medicamento/', views.lote_asignar_medicamento, name='lote_asignar_medicamento'),
    path('lotes/<int:pk>/editar/', views.lote_update, name='lote_update'),
    path('lotes/<int:pk>/ocultar/', views.lote_ocultar, name='lote_ocultar'),
    path('lotes/<int:pk>/restaurar/', views.lote_restaurar, name='lote_restaurar'),
    path('lotes/<int:pk>/eliminar/', views.lote_delete, name='lote_delete'),

    path('qr/', views.qr_list, name='qr_list'),
    path('qr/leer/<str:token>/', views.qr_scan, name='qr_scan'),
    path('qr/nuevo/<int:med_pk>/', views.qr_create, name='qr_create'),
    path('qr/<int:pk>/imagen/', views.qr_image, name='qr_image'),
    path('qr/<int:pk>/whatsapp/', views.qr_enviar_whatsapp, name='qr_enviar_whatsapp'),
    path('qr/<int:pk>/regenerar/', views.qr_regenerar, name='qr_regenerar'),
    path('qr/<int:pk>/eliminar/', views.qr_delete, name='qr_delete'),
]
