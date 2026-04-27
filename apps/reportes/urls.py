from django.urls import path

from . import views


urlpatterns = [
    path('', views.reportes_dashboard, name='reportes_dashboard'),
    path('pdf/', views.reportes_pdf, name='reportes_pdf'),
    path('excel/', views.reportes_excel, name='reportes_excel'),
]
