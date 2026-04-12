from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('',        views.lista,       name='lista'),
    path('crear/',  views.crear,       name='crear'),
    path('<int:pk>/editar/',   views.editar,   name='editar'),
    path('<int:pk>/eliminar/', views.eliminar, name='eliminar'),
]
