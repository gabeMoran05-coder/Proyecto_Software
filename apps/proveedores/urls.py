from django.urls import path
from . import views

urlpatterns = [
    path('',                   views.proveedor_list,   name='proveedor_list'),
    path('ocultos/',           views.proveedor_ocultos, name='proveedor_ocultos'),
    path('nuevo/',             views.proveedor_create, name='proveedor_create'),
    path('<int:pk>/',          views.proveedor_detail, name='proveedor_detail'),
    path('<int:pk>/editar/',   views.proveedor_update, name='proveedor_update'),
    path('<int:pk>/eliminar/', views.proveedor_delete, name='proveedor_delete'),
    path('<int:pk>/ocultar/',  views.proveedor_ocultar, name='proveedor_ocultar'),
    path('<int:pk>/restaurar/', views.proveedor_restaurar, name='proveedor_restaurar'),
]
