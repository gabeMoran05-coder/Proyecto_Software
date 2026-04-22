from django.urls import path
from . import views

urlpatterns = [
    path('',                   views.proveedor_list,   name='proveedor_list'),
    path('nuevo/',             views.proveedor_create, name='proveedor_create'),
    path('<int:pk>/',          views.proveedor_detail, name='proveedor_detail'),
    path('<int:pk>/editar/',   views.proveedor_update, name='proveedor_update'),
    path('<int:pk>/eliminar/', views.proveedor_delete, name='proveedor_delete'),
]