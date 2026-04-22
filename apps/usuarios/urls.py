from django.urls import path
from . import views

urlpatterns = [
    path('login/',             views.usuario_login,  name='usuario_login'),
    path('logout/',            views.usuario_logout, name='usuario_logout'),
    path('',                   views.usuario_list,   name='usuario_list'),
    path('ocultos/',           views.usuario_ocultos, name='usuario_ocultos'),
    path('nuevo/',             views.usuario_create, name='usuario_create'),
    path('<int:pk>/',          views.usuario_detail, name='usuario_detail'),
    path('<int:pk>/editar/',   views.usuario_update, name='usuario_update'),
    path('<int:pk>/eliminar/', views.usuario_delete, name='usuario_delete'),
    path('<int:pk>/restaurar/', views.usuario_restaurar, name='usuario_restaurar'),
]
