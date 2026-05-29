from datetime import timedelta

from celery import shared_task
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.medicamentos.models import (
    ConfiguracionInventario,
    Lote,
    Medicamento,
    MovimientoInventario,
    NotificacionCaducidadDescartada,
)
from apps.usuarios.email_utils import public_url, send_admin_email
from apps.usuarios.models import NotificacionSistemaDescartada
from apps.usuarios.notifications import (
    crear_notificacion_sistema,
    desactivar_notificacion_sistema,
)
from apps.ventas.models import DetalleVenta


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
)
def enviar_alertas_caducidad_task(self):
    call_command('enviar_alertas_caducidad')


def _medicamento_nombre(medicamento):
    partes = [
        medicamento.nombre,
        medicamento.presentacion_completa,
        medicamento.concentracion,
    ]
    return ' - '.join(str(parte) for parte in partes if parte)


def _lote_medicamentos(lote):
    medicamentos = list(lote.medicamento_set.all())
    if not medicamentos:
        return 'Sin medicamento asignado'
    nombres = [_medicamento_nombre(medicamento) for medicamento in medicamentos[:3]]
    if len(medicamentos) > 3:
        nombres.append(f'+{len(medicamentos) - 3} mas')
    return ', '.join(nombres)


def _fecha(value):
    return value.strftime('%d/%m/%Y') if value else 'Sin fecha'


def _estado_inventario(medicamento):
    lote = medicamento.id_lote
    stock_minimo = medicamento.stock_minimo or 50
    if not lote:
        return 'sin_stock'
    if (lote.stock_actual or 0) <= 0:
        return 'sin_stock'
    if lote.oculto_por_caducidad or not lote.activo:
        return 'rojo'
    if lote.estado_caducidad == Lote.CADUCIDAD_ROJO:
        return 'rojo'
    if lote.estado_caducidad == Lote.CADUCIDAD_AMARILLO or (lote.stock_actual or 0) < stock_minimo:
        return 'amarillo'
    return 'verde'


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
)
def enviar_alertas_bajo_stock_task(self):
    lotes = list(
        Lote.objects.select_related('id_prov')
        .prefetch_related('medicamento_set')
        .filter(
            activo=True,
            oculto_por_caducidad=False,
            stock_actual__lt=50,
        )
        .order_by('stock_actual', 'fecha_caducidad')
    )
    if not lotes:
        desactivar_notificacion_sistema('inventario.bajo_stock')
        return {'lotes': 0, 'emails': 0}

    agotados = sum(1 for lote in lotes if (lote.stock_actual or 0) <= 0)
    bajo_stock = len(lotes) - agotados
    lineas = [
        'Estos lotes tienen menos de 50 unidades disponibles o estan agotados:',
        '',
    ]
    filas = []
    for lote in lotes:
        medicamento = _lote_medicamentos(lote)
        proveedor = lote.id_prov.nombre if lote.id_prov_id else 'Sin proveedor'
        lineas.append(
            f'- {medicamento} | lote {lote.numero_lote} | stock {lote.stock_actual} | caduca {_fecha(lote.fecha_caducidad)}'
        )
        filas.append(
            '<tr>'
            f'<td>{medicamento}</td>'
            f'<td>{lote.numero_lote}</td>'
            f'<td>{proveedor}</td>'
            f'<td>{lote.stock_actual}</td>'
            f'<td>{_fecha(lote.fecha_caducidad)}</td>'
            '</tr>'
        )

    url = public_url(reverse('lote_list'))
    lineas.extend(['', f'Revisar lotes: {url}'])
    html = (
        '<h2>Alerta de bajo stock y agotados</h2>'
        '<p>Estos lotes tienen menos de 50 unidades disponibles o estan agotados.</p>'
        '<table border="1" cellpadding="6" cellspacing="0">'
        '<thead><tr><th>Medicamento</th><th>Lote</th><th>Proveedor</th><th>Stock</th><th>Caducidad</th></tr></thead>'
        f'<tbody>{"".join(filas)}</tbody>'
        '</table>'
        f'<p><a href="{url}">Revisar lotes</a></p>'
    )
    emails = send_admin_email(
        'Farmacia Inclusiva - alerta de bajo stock y agotados',
        '\n'.join(lineas),
        html,
    )
    crear_notificacion_sistema(
        clave='inventario.bajo_stock',
        titulo='Bajo stock y agotados',
        mensaje=f'{bajo_stock} bajo stock · {agotados} agotado(s)',
        categoria='Inventario',
        nivel='danger' if agotados else 'warning',
        url=reverse('lote_list') + '?orden=stock_asc',
    )
    return {'lotes': len(lotes), 'emails': emails}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
)
def retirar_lotes_caducos_task(self, force=False):
    hoy = timezone.localdate()
    ahora = timezone.localtime()
    configuracion = ConfiguracionInventario.obtener()
    if not force and ahora.time() < configuracion.hora_retiro_caducidad:
        return {
            'lotes': 0,
            'emails': 0,
            'omitida_por_hora': configuracion.hora_retiro_caducidad.strftime('%H:%M'),
        }
    dias_revision = configuracion.dias_revision_caducidad
    fecha_limite_revision = hoy - timedelta(days=dias_revision)
    lotes_caducos_en_revision = list(
        Lote.objects.select_related('id_prov')
        .prefetch_related('medicamento_set')
        .filter(
            activo=True,
            oculto_por_caducidad=False,
            fecha_caducidad__lt=hoy,
            fecha_caducidad__gte=fecha_limite_revision,
        )
        .order_by('fecha_caducidad', 'numero_lote')
    )
    if lotes_caducos_en_revision:
        crear_notificacion_sistema(
            clave='inventario.lotes_caducos_revision',
            titulo='Lotes caducos en revisión',
            mensaje=(
                f'{len(lotes_caducos_en_revision)} lote(s) caducaron. '
                f'Se ocultarán automáticamente después de {dias_revision} día(s).'
            ),
            categoria='Inventario',
            nivel='warning',
            url=reverse('lote_list') + '?caducidad=rojo',
        )
    else:
        desactivar_notificacion_sistema('inventario.lotes_caducos_revision')

    lotes_qs = Lote.objects.filter(
        activo=True,
        oculto_por_caducidad=False,
        fecha_caducidad__lt=fecha_limite_revision,
    )
    lotes = list(lotes_qs.prefetch_related('medicamento_set').order_by('fecha_caducidad'))
    lote_ids = [lote.pk for lote in lotes]
    if not lote_ids:
        desactivar_notificacion_sistema('inventario.lotes_retirados')
        return {'lotes': 0, 'emails': 0}

    fecha_oculto = timezone.now()
    for lote in lotes:
        stock_antes = lote.stock_actual or 0
        medicamento = lote.medicamento_set.order_by('id_med').first()
        lote.activo = False
        lote.oculto_por_caducidad = True
        lote.motivo_oculto = Lote.MOTIVO_CADUCIDAD
        lote.detalle_oculto = f'Ocultado automaticamente {dias_revision} dia(s) despues de caducar.'
        lote.fecha_oculto = fecha_oculto
        lote.save(update_fields=[
            'activo',
            'oculto_por_caducidad',
            'motivo_oculto',
            'detalle_oculto',
            'fecha_oculto',
        ])
        MovimientoInventario.objects.create(
            id_lote=lote,
            id_medicamento=medicamento,
            id_usuario=None,
            tipo=MovimientoInventario.TIPO_OCULTAMIENTO,
            motivo=Lote.MOTIVO_CADUCIDAD,
            cantidad=-stock_antes,
            stock_antes=stock_antes,
            stock_despues=0,
            referencia='Ocultamiento automático por caducidad',
            notas=f'Se oculto automaticamente despues de {dias_revision} dia(s) de revision fisica.',
        )

    Medicamento.objects.filter(id_lote_id__in=lote_ids).update(estado_colorimetria='rojo')

    lineas = ['Se retiraron automaticamente estos lotes caducos:', '']
    filas = []
    for lote in lotes:
        medicamento = _lote_medicamentos(lote)
        lineas.append(f'- {medicamento} | lote {lote.numero_lote} | caduco {_fecha(lote.fecha_caducidad)}')
        filas.append(
            '<tr>'
            f'<td>{medicamento}</td>'
            f'<td>{lote.numero_lote}</td>'
            f'<td>{_fecha(lote.fecha_caducidad)}</td>'
            '</tr>'
        )

    url = public_url(reverse('lote_ocultos'))
    lineas.extend(['', f'Ver lotes retirados: {url}'])
    html = (
        '<h2>Retiro automático de lotes caducos</h2>'
        '<p>Estos lotes fueron marcados como no disponibles para evitar nuevas ventas.</p>'
        '<table border="1" cellpadding="6" cellspacing="0">'
        '<thead><tr><th>Medicamento</th><th>Lote</th><th>Caducidad</th></tr></thead>'
        f'<tbody>{"".join(filas)}</tbody>'
        '</table>'
        f'<p><a href="{url}">Ver lotes retirados</a></p>'
    )
    emails = send_admin_email(
        'Farmacia Inclusiva - lotes caducos retirados',
        '\n'.join(lineas),
        html,
    )
    crear_notificacion_sistema(
        clave='inventario.lotes_retirados',
        titulo='Lotes caducos retirados',
        mensaje=f'{len(lotes)} lote(s) ocultados despues del dia de revision',
        categoria='Inventario',
        nivel='danger',
        url=reverse('lote_ocultos'),
    )
    return {'lotes': len(lotes), 'emails': emails}


@shared_task(bind=True)
def limpiar_notificaciones_descartadas_task(self):
    limite = timezone.now() - timedelta(hours=24)
    eliminadas, _ = NotificacionCaducidadDescartada.objects.filter(
        fecha_descartada__lt=limite,
    ).delete()
    sistema_eliminadas, _ = NotificacionSistemaDescartada.objects.filter(
        fecha_descartada__lt=limite,
    ).delete()
    return {
        'descartes_eliminados': eliminadas,
        'descartes_sistema_eliminados': sistema_eliminadas,
    }


@shared_task(bind=True)
def actualizar_estados_inventario_task(self):
    medicamentos = Medicamento.objects.select_related('id_lote')
    actualizados = []
    for medicamento in medicamentos:
        nuevo_estado = _estado_inventario(medicamento)
        if medicamento.estado_colorimetria != nuevo_estado:
            medicamento.estado_colorimetria = nuevo_estado
            actualizados.append(medicamento)

    if actualizados:
        Medicamento.objects.bulk_update(actualizados, ['estado_colorimetria'])
        crear_notificacion_sistema(
            clave='inventario.estados_actualizados',
            titulo='Estados de inventario actualizados',
            mensaje=f'{len(actualizados)} medicamento(s) recalculados',
            categoria='Inventario',
            nivel='success',
            url=reverse('medicamento_list'),
        )
    else:
        desactivar_notificacion_sistema('inventario.estados_actualizados')
    return {'medicamentos_actualizados': len(actualizados)}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
)
def recordatorio_clientes_afectados_task(self):
    lotes = list(
        Lote.objects.prefetch_related('medicamento_set')
        .filter(oculto_por_caducidad=True)
        .order_by('fecha_caducidad', 'numero_lote')
    )
    lote_ids = [lote.pk for lote in lotes]
    if not lote_ids:
        desactivar_notificacion_sistema('trazabilidad.clientes_afectados')
        return {'clientes': 0, 'ventas_publico_general': 0, 'emails': 0}

    detalles = list(
        DetalleVenta.objects.select_related(
            'id_ventas',
            'id_ventas__id_cliente',
            'id_medicamento',
            'id_medicamento__id_lote',
        )
        .filter(id_medicamento__id_lote_id__in=lote_ids)
        .order_by('-id_ventas__fecha_venta')
    )
    if not detalles:
        desactivar_notificacion_sistema('trazabilidad.clientes_afectados')
        return {'clientes': 0, 'ventas_publico_general': 0, 'emails': 0}

    clientes = {}
    ventas_publico = set()
    for detalle in detalles:
        venta = detalle.id_ventas
        cliente = venta.id_cliente
        if not cliente:
            ventas_publico.add(venta.pk)
            continue
        data = clientes.setdefault(
            cliente.pk,
            {
                'cliente': cliente,
                'ventas': set(),
                'medicamentos': set(),
                'unidades': 0,
            },
        )
        data['ventas'].add(venta.pk)
        data['medicamentos'].add(_medicamento_nombre(detalle.id_medicamento))
        data['unidades'] += detalle.cantidad or 0

    if not clientes and not ventas_publico:
        desactivar_notificacion_sistema('trazabilidad.clientes_afectados')
        return {'clientes': 0, 'ventas_publico_general': 0, 'emails': 0}

    lineas = [
        'Clientes que compraron lotes retirados o marcados como no disponibles:',
        '',
    ]
    filas = []
    for data in sorted(clientes.values(), key=lambda item: item['cliente'].nombre_completo())[:50]:
        cliente = data['cliente']
        telefono = cliente.telefono or 'Sin teléfono'
        medicamentos = ', '.join(sorted(data['medicamentos'])[:4])
        ventas_count = len(data['ventas'])
        lineas.append(
            f"- {cliente.nombre_completo()} | tel. {telefono} | {ventas_count} venta(s) | {data['unidades']} unidad(es) | {medicamentos}"
        )
        filas.append(
            '<tr>'
            f'<td>{cliente.nombre_completo()}</td>'
            f'<td>{telefono}</td>'
            f'<td>{ventas_count}</td>'
            f'<td>{data["unidades"]}</td>'
            f'<td>{medicamentos}</td>'
            '</tr>'
        )

    url = public_url(reverse('venta_trazabilidad'))
    if ventas_publico:
        lineas.extend(['', f'Ventas a publico general afectadas: {len(ventas_publico)}'])
    lineas.extend(['', f'Revisar trazabilidad: {url}'])
    html = (
        '<h2>Recordatorio de clientes afectados</h2>'
        '<p>Listado diario basado en lotes retirados u ocultos que ya tuvieron ventas.</p>'
        '<table border="1" cellpadding="6" cellspacing="0">'
        '<thead><tr><th>Cliente</th><th>Teléfono</th><th>Ventas</th><th>Unidades</th><th>Medicamentos</th></tr></thead>'
        f'<tbody>{"".join(filas)}</tbody>'
        '</table>'
        f'<p>Ventas a publico general afectadas: {len(ventas_publico)}</p>'
        f'<p><a href="{url}">Revisar trazabilidad</a></p>'
    )
    emails = send_admin_email(
        'Farmacia Inclusiva - clientes pendientes por contactar',
        '\n'.join(lineas),
        html,
    )
    crear_notificacion_sistema(
        clave='trazabilidad.clientes_afectados',
        titulo='Clientes pendientes por contactar',
        mensaje=f'{len(clientes)} cliente(s) · {len(ventas_publico)} venta(s) publico general',
        categoria='Trazabilidad',
        nivel='danger',
        url=reverse('venta_trazabilidad'),
    )
    return {
        'clientes': len(clientes),
        'ventas_publico_general': len(ventas_publico),
        'emails': emails,
    }
