from django.urls import path # pyright: ignore[reportMissingModuleSource]
from . import views

urlpatterns = [
    # ── Ventas ──────────────────────────────────────────────────
    path('',                   views.venta_list,   name='venta_list'),
    path('nueva/',             views.venta_create, name='venta_create'),
    path('<int:pk>/ticket/',    views.venta_ticket, name='venta_ticket'),
    path(
        '<int:pk>/ticket/whatsapp/',
        views.venta_ticket_whatsapp,
        name='venta_ticket_whatsapp',
    ),
    path(
        'ticket/<str:token>/',
        views.venta_ticket_public,
        name='venta_ticket_public',
    ),
    path(
        'ticket/<str:token>/imagen/',
        views.venta_ticket_image,
        name='venta_ticket_image',
    ),
    path(
        'ticket/<str:token>/qr.png',
        views.venta_ticket_qr_image,
        name='venta_ticket_qr_image',
    ),
    path(
        'ticket/<str:token>/qr.pdf',
        views.venta_ticket_qr_pdf,
        name='venta_ticket_qr_pdf',
    ),
    path('<int:pk>/',          views.venta_detail, name='venta_detail'),
    path('<int:pk>/cancelar/', views.venta_delete, name='venta_delete'),

    # ── Métodos de pago (CRUD simple, sin app separada) ─────────
    path('metodos-pago/',                   views.metodo_pago_list,   name='metodo_pago_list'),
    path('metodos-pago/nuevo/',             views.metodo_pago_create, name='metodo_pago_create'),
    path('metodos-pago/<int:pk>/editar/',   views.metodo_pago_update, name='metodo_pago_update'),
    path('metodos-pago/<int:pk>/eliminar/', views.metodo_pago_delete, name='metodo_pago_delete'),
]
