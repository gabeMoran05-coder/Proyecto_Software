from django.urls import path
from . import views
app_name = 'ventas'
urlpatterns = [
    path('',               views.lista,              name='lista'),
    path('<int:pk>/',      views.detalle,            name='detalle'),
    path('caja/',          views.punto_venta,        name='punto_venta'),
    path('buscar/',        views.buscar_medicamento, name='buscar'),
    path('reporte/',       views.reporte,            name='reporte'),
]
