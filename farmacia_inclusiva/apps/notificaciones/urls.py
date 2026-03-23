from django.urls import path
from . import views
app_name = 'notificaciones'
urlpatterns = [
    path('whatsapp/<int:venta_id>/', views.enviar_whatsapp, name='whatsapp'),
]
