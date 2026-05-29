from datetime import timedelta

from django.utils import timezone

from apps.usuarios.security import get_current_usuario
from apps.usuarios.models import NotificacionSistema, NotificacionSistemaDescartada

from .models import Lote, NotificacionCaducidadDescartada


def lotes_con_alerta_caducidad(usuario=None, incluir_descartadas=False):
    hoy = timezone.localdate()
    lotes = list(
        Lote.objects.select_related('id_prov')
        .prefetch_related('medicamento_set')
        .filter(
            activo=True,
            oculto_por_caducidad=False,
            fecha_caducidad__isnull=False,
            stock_actual__gt=0,
        )
        .order_by('fecha_caducidad', 'numero_lote')
    )
    lotes = [lote for lote in lotes if lote.fecha_caducidad < hoy or lote.estado_caducidad == Lote.CADUCIDAD_AMARILLO]
    if incluir_descartadas or not usuario:
        return lotes

    vigencia = timezone.now() - timedelta(hours=24)
    descartadas = set(
        NotificacionCaducidadDescartada.objects.filter(
            id_usuario=usuario,
            fecha_descartada__gt=vigencia,
        ).values_list('id_lote_id', flat=True)
    )
    return [lote for lote in lotes if lote.id_lote not in descartadas]


def lotes_con_alerta_stock(usuario=None, incluir_descartadas=False):
    candidatos = list(
        Lote.objects.select_related('id_prov')
        .prefetch_related('medicamento_set')
        .filter(
            activo=True,
            oculto_por_caducidad=False,
        )
        .order_by('stock_actual', 'fecha_caducidad', 'numero_lote')
    )
    lotes = []
    for lote in candidatos:
        medicamentos = list(lote.medicamento_set.all())
        stock_minimo = min([med.stock_minimo for med in medicamentos] or [50])
        if (lote.stock_actual or 0) <= stock_minimo:
            lote.stock_minimo_alerta = stock_minimo
            lotes.append(lote)
    if incluir_descartadas or not usuario:
        return lotes

    vigencia = timezone.now() - timedelta(hours=24)
    descartadas = set(
        NotificacionCaducidadDescartada.objects.filter(
            id_usuario=usuario,
            fecha_descartada__gt=vigencia,
        ).values_list('id_lote_id', flat=True)
    )
    return [lote for lote in lotes if lote.id_lote not in descartadas]


def resumen_alertas_caducidad(lotes_en_alerta):
    caducos = sum(1 for lote in lotes_en_alerta if lote.estado_caducidad == Lote.CADUCIDAD_ROJO)
    proximos = sum(1 for lote in lotes_en_alerta if lote.estado_caducidad == Lote.CADUCIDAD_AMARILLO)
    return caducos, proximos


def resumen_alertas_stock(lotes_en_alerta):
    agotados = sum(1 for lote in lotes_en_alerta if (lote.stock_actual or 0) <= 0)
    bajo_stock = sum(1 for lote in lotes_en_alerta if (lote.stock_actual or 0) > 0)
    return agotados, bajo_stock


def vista_previa_alertas_caducidad(lotes_en_alerta, limite=8):
    caducos = [lote for lote in lotes_en_alerta if lote.estado_caducidad == Lote.CADUCIDAD_ROJO]
    proximos = [lote for lote in lotes_en_alerta if lote.estado_caducidad == Lote.CADUCIDAD_AMARILLO]

    if not caducos or not proximos:
        return lotes_en_alerta[:limite]

    espacio_caducos = min(len(caducos), limite // 2)
    espacio_proximos = min(len(proximos), limite - espacio_caducos)
    espacio_caducos = min(len(caducos), limite - espacio_proximos)
    return caducos[:espacio_caducos] + proximos[:espacio_proximos]


def vista_previa_alertas_stock(lotes_en_alerta, limite=8):
    agotados = [lote for lote in lotes_en_alerta if (lote.stock_actual or 0) <= 0]
    bajo_stock = [lote for lote in lotes_en_alerta if (lote.stock_actual or 0) > 0]

    if not agotados or not bajo_stock:
        return lotes_en_alerta[:limite]

    espacio_agotados = min(len(agotados), limite // 2)
    espacio_bajo_stock = min(len(bajo_stock), limite - espacio_agotados)
    espacio_agotados = min(len(agotados), limite - espacio_bajo_stock)
    return agotados[:espacio_agotados] + bajo_stock[:espacio_bajo_stock]


def notificaciones_caducidad(request):
    usuario = get_current_usuario(request)
    if not usuario:
        return {}

    lotes_en_alerta = lotes_con_alerta_caducidad(usuario)
    caducos, proximos = resumen_alertas_caducidad(lotes_en_alerta)
    lotes_stock_alerta = lotes_con_alerta_stock(usuario)
    agotados, bajo_stock = resumen_alertas_stock(lotes_stock_alerta)
    vigencia_descartes = timezone.now() - timedelta(hours=24)
    notificaciones_descartadas = NotificacionSistemaDescartada.objects.filter(
        id_usuario=usuario,
        fecha_descartada__gt=vigencia_descartes,
    ).values_list('id_notificacion_id', flat=True)
    notificaciones_sistema = list(
        NotificacionSistema.objects.filter(activa=True)
        .exclude(id_notificacion__in=notificaciones_descartadas)
        .order_by('-fecha_actualizacion')[:8]
    )
    total_sistema = len(notificaciones_sistema)

    return {
        'notificaciones_sistema': notificaciones_sistema,
        'notificaciones_sistema_total': total_sistema,
        'notificaciones_lotes_stock': vista_previa_alertas_stock(lotes_stock_alerta),
        'notificaciones_lotes_stock_total': agotados + bajo_stock,
        'notificaciones_lotes_agotados_total': agotados,
        'notificaciones_lotes_bajo_stock_total': bajo_stock,
        'notificaciones_lotes_caducidad': vista_previa_alertas_caducidad(lotes_en_alerta),
        'notificaciones_lotes_caducidad_total': caducos + proximos,
        'notificaciones_lotes_caducos_total': caducos,
        'notificaciones_lotes_proximos_total': proximos,
        'notificaciones_total': total_sistema + caducos + proximos + agotados + bajo_stock,
    }
