from apps.usuarios.models import NotificacionSistema, NotificacionSistemaDescartada


def crear_notificacion_sistema(clave, titulo, mensaje, categoria, nivel='info', url=''):
    notificacion, _ = NotificacionSistema.objects.update_or_create(
        clave=clave,
        defaults={
            'titulo': titulo,
            'mensaje': mensaje,
            'categoria': categoria,
            'nivel': nivel,
            'url': url or '',
            'activa': True,
        },
    )
    NotificacionSistemaDescartada.objects.filter(id_notificacion=notificacion).delete()
    return notificacion


def desactivar_notificacion_sistema(clave):
    NotificacionSistema.objects.filter(clave=clave).update(activa=False)
