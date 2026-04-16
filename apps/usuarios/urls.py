from django.urls import path
from django.http import HttpResponse

def placeholder(request):
    return HttpResponse("Próximamente")

urlpatterns = [
    path('', placeholder, name='usuario_list'),
]