from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
import secrets
from collections import defaultdict
from datetime import datetime
from types import SimpleNamespace
import json

import qrcode
from django.conf import settings
from django.contrib import messages # pyright: ignore[reportMissingModuleSource]
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.db.models import Avg, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from .models import MetodoPago, Venta, DetalleVenta
from apps.clientes.models import Cliente
from apps.usuarios.models import Usuario
from apps.usuarios.security import get_current_usuario
from apps.medicamentos.models import Lote, Medicamento, CodigoQR, MovimientoInventario
from .whatsapp import (
    WhatsAppIntegrationError,
    _generar_audio_ticket_mp3,
    construir_preview_ticket,
    enviar_aviso_producto_defectuoso,
    enviar_ticket_por_whatsapp,
    texto_audio_ticket,
)
from apps.medicamentos.whatsapp import (
    normalizar_telefono_con_pais,
    telefono_form_context,
)
from apps.reportes.views import _SelectableReportPdf
from apps.text_utils import first_upper, first_upper_or_none


# ═══════════════════════════════════════════════════════════════
# MÉTODOS DE PAGO  (sin app propia — vive en ventas)
# ═══════════════════════════════════════════════════════════════

def metodo_pago_list(request):
    metodos = MetodoPago.objects.all().order_by('nombre_metodo')
    return render(request, 'ventas/metodo_pago_list.html', {'metodos': metodos})


def metodo_pago_create(request):
    if request.method == 'POST':
        nombre = first_upper(request.POST.get('nombre_metodo'))
        if not nombre:
            return render(request, 'ventas/metodo_pago_form.html', {
                'errors': ['El nombre del método de pago es obligatorio.'],
            })
        MetodoPago.objects.create(
            nombre_metodo = nombre,
            descripcion   = first_upper_or_none(request.POST.get('descripcion')),
        )
        return redirect('metodo_pago_list')
    return render(request, 'ventas/metodo_pago_form.html')


def metodo_pago_update(request, pk):
    metodo = get_object_or_404(MetodoPago, pk=pk)
    if request.method == 'POST':
        nombre = first_upper(request.POST.get('nombre_metodo'))
        if not nombre:
            return render(request, 'ventas/metodo_pago_form.html', {
                'errors': ['El nombre del método de pago es obligatorio.'],
                'metodo': metodo,
            })
        metodo.nombre_metodo = nombre
        metodo.descripcion   = first_upper_or_none(request.POST.get('descripcion'))
        metodo.save()
        return redirect('metodo_pago_list')
    return render(request, 'ventas/metodo_pago_form.html', {'metodo': metodo})


def metodo_pago_delete(request, pk):
    metodo = get_object_or_404(MetodoPago, pk=pk)
    if request.method == 'POST':
        metodo.delete()
        return redirect('metodo_pago_list')
    return render(request, 'ventas/metodo_pago_confirm_delete.html', {'metodo': metodo})


# ═══════════════════════════════════════════════════════════════
# VENTAS — LISTA
# ═══════════════════════════════════════════════════════════════

def venta_list(request):
    usuario_actual = get_current_usuario(request)
    es_cajero = bool(
        usuario_actual and usuario_actual.rol_normalizado() == Usuario.ROL_CAJERO
    )
    ventas = Venta.objects.select_related(
        'id_usuario', 'id_metPag', 'id_cliente'
    )

    fecha_desde    = request.GET.get('fecha_desde', '').strip()
    fecha_hasta    = request.GET.get('fecha_hasta', '').strip()
    metodo_filter  = request.GET.get('metodo_pago', '').strip()
    usuario_filter = '' if es_cajero else request.GET.get('usuario', '').strip()
    orden_filter   = request.GET.get('orden', 'fecha_desc').strip()

    hoy = timezone.localdate()
    fecha_desde_date, fecha_hasta_date, date_error_message = _validar_rango_fechas(
        fecha_desde,
        fecha_hasta,
        hoy,
    )

    if es_cajero:
        ventas = ventas.filter(id_usuario=usuario_actual)
    if not date_error_message:
        if fecha_desde_date and not fecha_hasta_date:
            ventas = ventas.filter(fecha_venta__date=fecha_desde_date)
        else:
            if fecha_desde_date: ventas = ventas.filter(fecha_venta__date__gte=fecha_desde_date)
            if fecha_hasta_date: ventas = ventas.filter(fecha_venta__date__lte=fecha_hasta_date)
    else:
        ventas = ventas.none()
    if metodo_filter:  ventas = ventas.filter(id_metPag__id_metPag=metodo_filter)
    if usuario_filter: ventas = ventas.filter(id_usuario__id_usuario=usuario_filter)
    ordenes = {
        'folio_asc': 'id_ventas',
        'folio_desc': '-id_ventas',
        'fecha_asc': 'fecha_venta',
        'fecha_desc': '-fecha_venta',
        'vendedor_asc': 'id_usuario__nombre',
        'vendedor_desc': '-id_usuario__nombre',
        'cliente_asc': 'id_cliente__nombre',
        'cliente_desc': '-id_cliente__nombre',
        'metodo_asc': 'id_metPag__nombre_metodo',
        'metodo_desc': '-id_metPag__nombre_metodo',
        'total_asc': 'total_venta',
        'total_desc': '-total_venta',
    }
    ventas = ventas.order_by(ordenes.get(orden_filter, '-fecha_venta'), '-id_ventas')
    total_ventas_filtradas = ventas.count()
    ingresos_filtrados = ventas.aggregate(total=Sum('total_venta'))['total'] or Decimal('0.00')
    vendedor_groups = list(_agrupar_ventas_por_vendedor(ventas))
    vendedores_filtrados = len(vendedor_groups)
    vendedor_destacado = vendedor_groups[0] if vendedor_groups else None

    # Stats del día
    ventas_base_qs = Venta.objects.all()
    if es_cajero:
        ventas_base_qs = ventas_base_qs.filter(id_usuario=usuario_actual)
    ventas_hoy_qs  = ventas_base_qs.filter(fecha_venta__date=hoy)
    ingresos_hoy   = sum(v.total_venta or 0 for v in ventas_hoy_qs)
    ventas_mes_qs  = ventas_base_qs.filter(
        fecha_venta__year=hoy.year, fecha_venta__month=hoy.month
    )

    ticket_promedio = ventas_base_qs.aggregate(avg=Avg('total_venta'))['avg'] or 0

    paginator = Paginator(ventas, 10)
    try:
        page_obj = paginator.page(request.GET.get('page', 1))
    except Exception:
        page_obj = paginator.page(1)

    query_params = ''
    if fecha_desde:    query_params += f'&fecha_desde={fecha_desde}'
    if fecha_hasta:    query_params += f'&fecha_hasta={fecha_hasta}'
    if metodo_filter:  query_params += f'&metodo_pago={metodo_filter}'
    if usuario_filter: query_params += f'&usuario={usuario_filter}'
    filter_query_params = query_params
    if orden_filter:   query_params += f'&orden={orden_filter}'

    return render(request, 'ventas/venta_list.html', {
        'ventas':          page_obj.object_list,
        'page_obj':        page_obj,
        'paginator':       paginator,
        'is_paginated':    paginator.num_pages > 1,
        'total_ventas':    ventas_base_qs.count(),
        'total_ventas_filtradas': total_ventas_filtradas,
        'ingresos_filtrados': ingresos_filtrados,
        'vendedores_filtrados': vendedores_filtrados,
        'vendedor_destacado': vendedor_destacado,
        'ingresos_hoy':    ingresos_hoy,
        'ventas_mes':      ventas_mes_qs.count(),
        'ticket_promedio': round(ticket_promedio, 2),
        'vendedor_groups': vendedor_groups,
        'metodos_pago':    MetodoPago.objects.all(),
        'usuarios':        Usuario.objects.filter(rol=Usuario.ROL_CAJERO, activo=True).order_by('nombre', 'ap_pat'),
        'fecha_desde':     fecha_desde,
        'fecha_hasta':     fecha_hasta,
        'date_error_message': date_error_message,
        'fecha_maxima':    hoy.strftime('%Y-%m-%d'),
        'fecha_maxima_display': _format_date_filter(hoy),
        'metodo_filter':   metodo_filter,
        'usuario_filter':  usuario_filter,
        'orden_filter':    orden_filter,
        'query_params':    query_params,
        'filter_query_params': filter_query_params,
    })


# ═══════════════════════════════════════════════════════════════
# VENTAS — DETALLE
# ═══════════════════════════════════════════════════════════════

def _agrupar_ventas_por_vendedor(ventas):
    grupos = {}
    for venta in ventas:
        vendedor = venta.id_usuario
        if vendedor.id_usuario not in grupos:
            grupos[vendedor.id_usuario] = {
                'vendedor': vendedor,
                'ventas': [],
                'total': Decimal('0.00'),
                'cantidad': 0,
            }
        grupos[vendedor.id_usuario]['ventas'].append(venta)
        grupos[vendedor.id_usuario]['total'] += venta.total_venta or Decimal('0.00')
        grupos[vendedor.id_usuario]['cantidad'] += 1
    return sorted(grupos.values(), key=lambda group: group['total'], reverse=True)


def _parse_date_filter(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def _validar_rango_fechas(fecha_desde, fecha_hasta, hoy=None):
    hoy = hoy or timezone.localdate()
    fecha_desde_date = _parse_date_filter(fecha_desde)
    fecha_hasta_date = _parse_date_filter(fecha_hasta)

    if fecha_desde and not fecha_desde_date:
        return fecha_desde_date, fecha_hasta_date, 'La fecha inicial no tiene un formato valido.'
    if fecha_hasta and not fecha_hasta_date:
        return fecha_desde_date, fecha_hasta_date, 'La fecha final no tiene un formato valido.'
    if fecha_desde_date and fecha_hasta_date and fecha_desde_date > fecha_hasta_date:
        return fecha_desde_date, fecha_hasta_date, 'Rango de fechas inválido: la fecha "Hasta" debe ser igual o posterior a "Desde".'
    if (fecha_desde_date and fecha_desde_date > hoy) or (fecha_hasta_date and fecha_hasta_date > hoy):
        return (
            fecha_desde_date,
            fecha_hasta_date,
            f'No se pueden buscar ventas con fechas posteriores a hoy ({_format_date_filter(hoy)}).',
        )
    return fecha_desde_date, fecha_hasta_date, ''


def _format_date_filter(value):
    return value.strftime('%d/%m/%Y')


def venta_detail(request, pk):
    venta_qs = Venta.objects.select_related('id_usuario')
    usuario_actual = get_current_usuario(request)
    if usuario_actual and usuario_actual.rol_normalizado() == Usuario.ROL_CAJERO:
        venta_qs = venta_qs.filter(id_usuario=usuario_actual)
    venta    = get_object_or_404(venta_qs, pk=pk)
    venta.ensure_ticket_token()
    detalles = venta.detalleventa_set.select_related(
        'id_medicamento__id_lote__id_prov'
    ).all()
    return render(request, 'ventas/venta_detail.html', {
        'venta':    venta,
        'detalles': detalles,
        **_ticket_totales_iva(venta),
    })


def venta_trazabilidad(request):
    return render(request, 'ventas/trazabilidad.html', _trazabilidad_context(request))


def venta_trazabilidad_pdf(request):
    context = _trazabilidad_context(request)
    pdf_buffer = _build_trazabilidad_pdf(request, context)
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = (
        f"attachment; filename=\"trazabilidad-{timezone.localdate().strftime('%Y%m%d')}.pdf\""
    )
    return response


def _trazabilidad_context(request):
    medicamento_id = request.GET.get('medicamento', '').strip()
    lote_id = request.GET.get('lote', '').strip()
    fecha_desde = request.GET.get('fecha_desde', '').strip()
    fecha_hasta = request.GET.get('fecha_hasta', '').strip()
    tipo_cliente = request.GET.get('tipo_cliente', '').strip()
    busqueda_activa = any([medicamento_id, lote_id, fecha_desde, fecha_hasta, tipo_cliente])
    hoy = timezone.localdate()
    fecha_desde_date, fecha_hasta_date, date_error_message = _validar_rango_fechas(
        fecha_desde,
        fecha_hasta,
        hoy,
    )

    detalles = DetalleVenta.objects.none()
    medicamento_seleccionado = None
    lote_seleccionado = None

    if busqueda_activa and not date_error_message:
        detalles = DetalleVenta.objects.select_related(
            'id_ventas',
            'id_ventas__id_cliente',
            'id_ventas__id_usuario',
            'id_medicamento',
            'id_medicamento__id_lote',
            'id_medicamento__id_lote__id_prov',
        )

        if lote_id:
            lote_seleccionado = get_object_or_404(Lote, pk=lote_id)
            detalles = detalles.filter(id_medicamento__id_lote=lote_seleccionado)
        elif medicamento_id:
            medicamento_seleccionado = get_object_or_404(Medicamento, pk=medicamento_id)
            detalles = detalles.filter(
                id_medicamento__nombre__iexact=medicamento_seleccionado.nombre,
                id_medicamento__presentacion=medicamento_seleccionado.presentacion,
                id_medicamento__tamano_presentacion=medicamento_seleccionado.tamano_presentacion,
                id_medicamento__concentracion=medicamento_seleccionado.concentracion,
                id_medicamento__requiere_receta=medicamento_seleccionado.requiere_receta,
            )

        if fecha_desde_date:
            detalles = detalles.filter(id_ventas__fecha_venta__date__gte=fecha_desde_date)
        if fecha_hasta_date:
            detalles = detalles.filter(id_ventas__fecha_venta__date__lte=fecha_hasta_date)
        if tipo_cliente == 'registrados':
            detalles = detalles.filter(id_ventas__id_cliente__isnull=False)
        elif tipo_cliente == 'publico':
            detalles = detalles.filter(id_ventas__id_cliente__isnull=True)

        detalles = detalles.order_by('-id_ventas__fecha_venta', '-id_ventas__id_ventas')

    detalles_lista = list(detalles)
    ventas_afectadas = {detalle.id_ventas_id for detalle in detalles_lista}
    clientes_contactables = {
        detalle.id_ventas.id_cliente_id
        for detalle in detalles_lista
        if detalle.id_ventas.id_cliente_id
    }
    ventas_publico_general = sum(1 for detalle in detalles_lista if not detalle.id_ventas.id_cliente_id)
    unidades_afectadas = sum(detalle.cantidad or 0 for detalle in detalles_lista)

    return {
        'detalles': detalles_lista,
        'medicamentos': _medicamentos_catalogo_trazabilidad(),
        'lotes': _lotes_catalogo_trazabilidad(),
        'medicamento_id': medicamento_id,
        'lote_id': lote_id,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'date_error_message': date_error_message,
        'fecha_maxima': hoy.strftime('%Y-%m-%d'),
        'fecha_maxima_display': _format_date_filter(hoy),
        'tipo_cliente': tipo_cliente,
        'busqueda_activa': busqueda_activa,
        'medicamento_seleccionado': medicamento_seleccionado,
        'lote_seleccionado': lote_seleccionado,
        'ventas_afectadas_total': len(ventas_afectadas),
        'clientes_contactables_total': len(clientes_contactables),
        'ventas_publico_general_total': ventas_publico_general,
        'unidades_afectadas_total': unidades_afectadas,
    }


def _build_trazabilidad_pdf(request, context):
    pdf = _SelectableReportPdf()
    usuario = get_current_usuario(request)
    generado_por = usuario.nombre_completo() if usuario else 'Sistema'
    periodo = _trazabilidad_periodo_display(context)
    criterio = _trazabilidad_criterio_display(context)
    tipo_cliente = {
        'registrados': 'Clientes registrados',
        'publico': 'Publico general',
    }.get(context.get('tipo_cliente'), 'Todos')

    pdf.text(pdf.margin, pdf.y - 8, 'Reporte de trazabilidad', size=20, bold=True, color=(0.02, 0.12, 0.18))
    pdf.text(pdf.margin, pdf.y - 26, 'Rastreo de ventas y clientes afectados por medicamento o lote', size=9, color=(0.25, 0.35, 0.42))
    pdf.y -= 44

    pdf.two_column_facts([
        ('Empresa', 'Farmacia Inclusiva'),
        ('Reporte elaborado por', generado_por),
        ('Fecha de emision', timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')),
        ('Periodo', periodo),
        ('Busqueda activa', criterio),
        ('Tipo de cliente', tipo_cliente),
        ('Registros encontrados', str(len(context['detalles']))),
        ('Formato', 'PDF con texto seleccionable'),
    ])

    lote = context.get('lote_seleccionado')
    if lote and getattr(lote, 'oculto_por_caducidad', False):
        motivo = lote.get_motivo_oculto_display() if lote.motivo_oculto else 'Sin motivo registrado'
        detalle = lote.detalle_oculto or 'Sin detalle adicional.'
        pdf.note(f'Lote oculto del inventario operativo. Motivo: {motivo}. Detalle: {detalle}')

    pdf.section('Resumen')
    pdf.kpi_grid([
        ('Ventas afectadas', str(context['ventas_afectadas_total']), 'Folios distintos'),
        ('Clientes rastreables', str(context['clientes_contactables_total']), 'Con registro en sistema'),
        ('Publico general', str(context['ventas_publico_general_total']), 'Lineas sin cliente'),
        ('Unidades', str(context['unidades_afectadas_total']), 'Vendidas en resultados'),
    ])

    rows = [_trazabilidad_pdf_row(detalle) for detalle in context['detalles']]
    pdf.table(
        'Compradores encontrados',
        ['Venta', 'Fecha', 'Cliente', 'Teléfono', 'Medicamento', 'Lote', 'Cant.', 'Estado'],
        rows,
        [42, 70, 100, 70, 105, 70, 35, 48],
    )
    pdf.note(
        'Este documento fue generado por el sistema de Farmacia Inclusiva. '
        'Cuando el motivo sea defectuoso o danino, se recomienda contactar a los clientes registrados antes de cerrar el seguimiento.'
    )
    return pdf.to_buffer()


def _trazabilidad_pdf_row(detalle):
    venta = detalle.id_ventas
    cliente = venta.id_cliente
    medicamento = detalle.id_medicamento
    lote = medicamento.id_lote
    fecha = timezone.localtime(venta.fecha_venta).strftime('%d/%m/%Y %H:%M') if venta.fecha_venta else '-'
    cliente_nombre = cliente.nombre_completo() if cliente else 'Publico general'
    telefono = cliente.telefono if cliente and cliente.telefono else '-'
    estado = 'Contactable' if cliente and cliente.telefono else 'No rastreable'
    return [
        f'#{venta.id_ventas}',
        fecha,
        cliente_nombre,
        telefono,
        _medicamento_pdf_nombre(medicamento),
        lote.numero_lote if lote else '-',
        str(detalle.cantidad or 0),
        estado,
    ]


def _medicamento_pdf_nombre(medicamento):
    partes = [medicamento.nombre]
    if medicamento.presentacion_completa:
        partes.append(medicamento.presentacion_completa)
    if medicamento.concentracion:
        partes.append(medicamento.concentracion)
    return ' - '.join(str(parte) for parte in partes if parte)


def _trazabilidad_periodo_display(context):
    desde = context.get('fecha_desde') or 'Inicio'
    hasta = context.get('fecha_hasta') or context.get('fecha_maxima_display') or 'Hoy'
    return f'{desde} - {hasta}'


def _trazabilidad_criterio_display(context):
    lote = context.get('lote_seleccionado')
    medicamento = context.get('medicamento_seleccionado')
    if lote:
        return f'Lote {lote.numero_lote}'
    if medicamento:
        return _medicamento_pdf_nombre(medicamento)
    return 'Filtros generales'


def venta_trazabilidad_whatsapp(request, detalle_id):
    if request.method != 'POST':
        return redirect('venta_trazabilidad')

    detalle = get_object_or_404(
        DetalleVenta.objects.select_related(
            'id_ventas',
            'id_ventas__id_cliente',
            'id_medicamento',
            'id_medicamento__id_lote',
        ),
        pk=detalle_id,
    )
    next_url = request.POST.get('next') or reverse('venta_trazabilidad')

    try:
        telefono = enviar_aviso_producto_defectuoso(request, detalle)
        messages.success(
            request,
            f'Aviso de producto defectuoso enviado por WhatsApp a {telefono}.',
        )
    except WhatsAppIntegrationError as exc:
        messages.error(request, str(exc))

    return redirect(next_url)


def venta_ticket(request, pk):
    venta_qs = Venta.objects.select_related('id_usuario', 'id_metPag', 'id_cliente')
    usuario_actual = get_current_usuario(request)
    if usuario_actual and usuario_actual.rol_normalizado() == Usuario.ROL_CAJERO:
        venta_qs = venta_qs.filter(id_usuario=usuario_actual)
    venta = get_object_or_404(
        venta_qs,
        pk=pk,
    )
    return render(request, 'ventas/ticket.html', _ticket_context(request, venta))


def venta_ticket_public(request, token):
    venta = get_object_or_404(
        Venta.objects.select_related('id_usuario', 'id_metPag', 'id_cliente'),
        ticket_token=token,
    )
    return render(
        request,
        'ventas/ticket.html',
        _ticket_context(request, venta, public=True),
    )


def venta_ticket_qr_image(request, token):
    venta = get_object_or_404(Venta, ticket_token=token)
    img = qrcode.make(_ticket_public_url(request, venta))
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='image/png')
    disposition = 'attachment' if request.GET.get('download') == '1' else 'inline'
    response['Content-Disposition'] = (
        f'{disposition}; filename="ticket-venta-{venta.id_ventas}-qr.png"'
    )
    return response


def venta_ticket_qr_pdf(request, token):
    venta = get_object_or_404(Venta, ticket_token=token)
    qr_img = qrcode.make(_ticket_public_url(request, venta)).convert('RGB')
    qr_img = qr_img.resize((420, 420))

    page = Image.new('RGB', (620, 760), 'white')
    draw = ImageDraw.Draw(page)
    font_title = _font(30)
    font_body = _font(18)

    draw.text((50, 45), 'QR del ticket', fill='black', font=font_title)
    draw.text((50, 92), f'Venta #{venta.id_ventas}', fill='black', font=font_body)
    page.paste(qr_img, (100, 150))
    draw.text((50, 610), _ticket_public_url(request, venta), fill='black', font=_font(13))

    buffer = BytesIO()
    page.save(buffer, format='PDF', resolution=100.0)
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="ticket-venta-{venta.id_ventas}-qr.pdf"'
    )
    return response


def venta_ticket_image(request, token):
    venta = get_object_or_404(
        Venta.objects.select_related('id_usuario', 'id_metPag', 'id_cliente'),
        ticket_token=token,
    )
    detalles = venta.detalleventa_set.select_related(
        'id_medicamento__id_lote__id_prov'
    ).all()
    img = _ticket_png(request, venta, detalles)
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='image/png')
    disposition = 'attachment' if request.GET.get('download') == '1' else 'inline'
    response['Content-Disposition'] = (
        f'{disposition}; filename="ticket-venta-{venta.id_ventas}.png"'
    )
    return response


def _telefono_cliente_para_whatsapp(venta):
    cliente = getattr(venta, 'id_cliente', None)
    telefono = getattr(cliente, 'telefono', '') or ''
    digitos = ''.join(ch for ch in telefono if ch.isdigit())

    if not digitos:
        return '52', ''

    codigo_pais = '52'
    if digitos.startswith(codigo_pais) and len(digitos) > 10:
        digitos = digitos[len(codigo_pais):]

    return codigo_pais, _formatear_telefono_local(digitos)


def _formatear_telefono_local(digitos):
    digitos = ''.join(ch for ch in str(digitos) if ch.isdigit())[:14]
    if len(digitos) <= 3:
        return digitos
    if len(digitos) <= 6:
        return f'{digitos[:3]} {digitos[3:]}'
    if len(digitos) <= 10:
        return f'{digitos[:3]} {digitos[3:6]} {digitos[6:]}'
    return f'{digitos[:3]} {digitos[3:6]} {digitos[6:10]} {digitos[10:]}'


def venta_ticket_whatsapp(request, pk):
    venta_qs = Venta.objects.select_related('id_usuario', 'id_metPag', 'id_cliente')
    usuario_actual = get_current_usuario(request)
    if usuario_actual and usuario_actual.rol_normalizado() == Usuario.ROL_CAJERO:
        venta_qs = venta_qs.filter(id_usuario=usuario_actual)
    venta = get_object_or_404(
        venta_qs,
        pk=pk,
    )
    venta.ensure_ticket_token()
    country_code, telefono_local = _telefono_cliente_para_whatsapp(venta)
    context = {
        'venta': venta,
        'preview': construir_preview_ticket(request, venta),
        **telefono_form_context(country_code, telefono_local),
        'telefono_precargado': bool(telefono_local),
    }

    if request.method == 'POST':
        country_code = request.POST.get('pais_codigo', '52')
        telefono_local = request.POST.get('telefono_local', '')
        enviar_audio = request.POST.get('enviar_audio') == 'on'
        try:
            telefono = normalizar_telefono_con_pais(country_code, telefono_local)
            enviar_ticket_por_whatsapp(request, venta, telefono, enviar_audio=enviar_audio)
        except WhatsAppIntegrationError as exc:
            context.update(telefono_form_context(country_code, telefono_local))
            context['enviar_audio'] = enviar_audio
            context['errors'] = [str(exc)]
            return render(request, 'ventas/ticket_whatsapp_form.html', context)

        extra = ' con audio accesible' if enviar_audio else ''
        messages.success(request, f'WhatsApp aceptó el ticket{extra} para entrega a {telefono}.')
        return redirect('venta_detail', pk=venta.pk)

    return render(request, 'ventas/ticket_whatsapp_form.html', context)


def venta_ticket_audio(request, pk):
    venta_qs = Venta.objects.select_related('id_usuario', 'id_metPag', 'id_cliente')
    usuario_actual = get_current_usuario(request)
    if usuario_actual and usuario_actual.rol_normalizado() == Usuario.ROL_CAJERO:
        venta_qs = venta_qs.filter(id_usuario=usuario_actual)
    venta = get_object_or_404(venta_qs, pk=pk)

    try:
        audio_mp3 = _generar_audio_ticket_mp3(texto_audio_ticket(venta))
    except WhatsAppIntegrationError as exc:
        messages.error(request, str(exc))
        return redirect('venta_ticket_whatsapp', pk=venta.pk)

    disposition = 'attachment' if request.GET.get('download') == '1' else 'inline'
    response = HttpResponse(audio_mp3, content_type='audio/mpeg')
    response['Content-Disposition'] = (
        f'{disposition}; filename="ticket-venta-{venta.id_ventas}-audio.mp3"'
    )
    return response




# ═══════════════════════════════════════════════════════════════
# VENTAS — CREAR  (punto de venta)
# ═══════════════════════════════════════════════════════════════

def venta_create(request):
    fecha_servidor = timezone.localtime(timezone.now())
    context = {
        'usuarios':     Usuario.objects.filter(rol=Usuario.ROL_CAJERO, activo=True).order_by('nombre', 'ap_pat'),
        'metodos_pago': MetodoPago.objects.all(),
        'clientes':     Cliente.objects.all().order_by('nombre', 'ap_pat'),
        'medicamentos': _medicamentos_para_venta(),
        'fecha_actual': fecha_servidor.strftime('%Y-%m-%d %H:%M'),
    }

    if request.method == 'POST':
        errors         = []
        usuario_id     = request.POST.get('id_usuario')
        metpag_id      = request.POST.get('id_metPag')
        cliente_id     = request.POST.get('id_cliente') or None
        med_ids        = request.POST.getlist('medicamento_ids[]')
        cantidades     = request.POST.getlist('cantidades[]')
        precios        = request.POST.getlist('precios_unitarios[]')
        recetas_confirmadas = set(request.POST.getlist('recetas_confirmadas[]'))

        if not usuario_id: errors.append('Debes seleccionar un cajero.')
        if not metpag_id:  errors.append('Debes seleccionar un método de pago.')
        if not med_ids:    errors.append('Debes agregar al menos un producto.')

        if errors:
            context['errors'] = errors
            return render(request, 'ventas/venta_form.html', context)

        try:
            with transaction.atomic():
                total  = Decimal('0.00')
                lineas_por_medicamento = {}
                stock_reservado_por_lote = defaultdict(int)

                for seleccion, cant_str, precio_str in zip(med_ids, cantidades, precios):
                    tipo_seleccion, med_id, proveedor_id = _parsear_seleccion_medicamento(seleccion)
                    med      = get_object_or_404(Medicamento.objects.select_related('id_lote'), pk=med_id)
                    cantidad = int(cant_str)
                    if med.requiere_receta and seleccion not in recetas_confirmadas:
                        raise ValueError(f'Debes confirmar receta para {med.nombre}.')

                    lotes_disponibles = _medicamentos_para_descontar(
                        med,
                        tipo_seleccion=tipo_seleccion,
                        proveedor_id=proveedor_id,
                    )
                    stock_disponible = sum(
                        max((item.id_lote.stock_actual or 0) - stock_reservado_por_lote[item.id_lote_id], 0)
                        for item in lotes_disponibles
                    )
                    if cantidad > stock_disponible:
                        raise ValueError(
                            f'Stock insuficiente para {med.nombre}. '
                            f'Disponible: {stock_disponible}.'
                        )

                    restante = cantidad
                    for med_lote in lotes_disponibles:
                        if restante <= 0:
                            break
                        lote = med_lote.id_lote
                        disponible_lote = max((lote.stock_actual or 0) - stock_reservado_por_lote[lote.id_lote], 0)
                        cantidad_lote = min(restante, disponible_lote)
                        if cantidad_lote <= 0:
                            continue
                        precio = lote.precio_venta if lote.precio_venta is not None else Decimal(precio_str)
                        subtotal = precio * cantidad_lote
                        if med_lote.id_med in lineas_por_medicamento:
                            lineas_por_medicamento[med_lote.id_med]['cantidad'] += cantidad_lote
                            lineas_por_medicamento[med_lote.id_med]['subtotal'] += subtotal
                        else:
                            lineas_por_medicamento[med_lote.id_med] = {
                                'med': med_lote,
                                'cantidad': cantidad_lote,
                                'precio': precio,
                                'subtotal': subtotal,
                            }
                        stock_reservado_por_lote[lote.id_lote] += cantidad_lote
                        total += subtotal
                        restante -= cantidad_lote

                venta = Venta.objects.create(
                    id_usuario  = get_object_or_404(Usuario,     pk=usuario_id),
                    id_metPag   = get_object_or_404(MetodoPago,  pk=metpag_id),
                    id_cliente  = get_object_or_404(Cliente, pk=cliente_id) if cliente_id else None,
                    fecha_venta = timezone.now(),
                    total_venta = total,
                )

                for linea in lineas_por_medicamento.values():
                    med = linea['med']
                    cantidad = linea['cantidad']
                    precio = linea['precio']
                    subtotal = linea['subtotal']
                    DetalleVenta.objects.create(
                        id_ventas       = venta,
                        id_medicamento  = med,
                        cantidad        = cantidad,
                        precio_unitario = precio,
                        subtotal        = subtotal,
                    )
                    lote              = med.id_lote
                    stock_antes = lote.stock_actual or 0
                    lote.stock_actual = max((lote.stock_actual or 0) - cantidad, 0)
                    lote.save()
                    MovimientoInventario.objects.create(
                        id_lote=lote,
                        id_medicamento=med,
                        id_usuario=venta.id_usuario,
                        tipo=MovimientoInventario.TIPO_VENTA,
                        motivo='venta',
                        cantidad=-cantidad,
                        stock_antes=stock_antes,
                        stock_despues=lote.stock_actual,
                        referencia=f'Venta #{venta.id_ventas}',
                    )
                    _actualizar_colorimetria(med, lote.stock_actual)

                messages.success(request, f'Venta #{venta.id_ventas} registrada correctamente.')
                return redirect('venta_detail', pk=venta.pk)

        except ValueError as e:
            context['errors'] = [str(e)]
        except Exception as e:
            context['errors'] = [f'Error inesperado: {e}']

    return render(request, 'ventas/venta_form.html', context)


def venta_cliente_rapido(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'errors': ['Método no permitido.']}, status=405)

    nombre = request.POST.get('nombre', '').strip()
    ap_pat = request.POST.get('ap_pat', '').strip()
    ap_mat = request.POST.get('ap_mat', '').strip()
    telefono = request.POST.get('telefono', '').strip()

    errors = []
    if not nombre:
        errors.append('El nombre es obligatorio.')
    if telefono and (not telefono.isdigit() or len(telefono) > 15):
        errors.append('El teléfono debe tener solo números y máximo 15 dígitos.')
    if errors:
        return JsonResponse({'ok': False, 'errors': errors}, status=400)

    cliente = Cliente.objects.create(
        nombre=first_upper(nombre),
        ap_pat=first_upper_or_none(ap_pat),
        ap_mat=first_upper_or_none(ap_mat),
        telefono=telefono or None,
        fecha_registro=timezone.localdate(),
    )
    return JsonResponse({
        'ok': True,
        'cliente': {
            'id': cliente.id_cliente,
            'nombre': cliente.nombre_completo(),
            'telefono': cliente.telefono or '',
        },
    })


# ═══════════════════════════════════════════════════════════════
# VENTAS — CANCELAR
# ═══════════════════════════════════════════════════════════════

def venta_delete(request, pk):
    venta_qs = Venta.objects.all()
    usuario_actual = get_current_usuario(request)
    if usuario_actual and usuario_actual.rol_normalizado() == Usuario.ROL_CAJERO:
        venta_qs = venta_qs.filter(id_usuario=usuario_actual)
    venta = get_object_or_404(venta_qs, pk=pk)

    if request.method == 'POST':
        with transaction.atomic():
            for det in venta.detalleventa_set.select_related('id_medicamento__id_lote').all():
                lote               = det.id_medicamento.id_lote
                stock_antes = lote.stock_actual or 0
                lote.stock_actual += det.cantidad or 0
                lote.save()
                MovimientoInventario.objects.create(
                    id_lote=lote,
                    id_medicamento=det.id_medicamento,
                    id_usuario=venta.id_usuario,
                    tipo=MovimientoInventario.TIPO_CANCELACION,
                    motivo='cancelacion',
                    cantidad=det.cantidad or 0,
                    stock_antes=stock_antes,
                    stock_despues=lote.stock_actual,
                    referencia=f'Cancelacion venta #{venta.id_ventas}',
                )
                _actualizar_colorimetria(det.id_medicamento, lote.stock_actual)
            venta.delete()
        messages.success(request, 'Venta cancelada y stock restaurado.')
        return redirect('venta_list')

    return render(request, 'ventas/venta_confirm_delete.html', {'venta': venta})


# ═══════════════════════════════════════════════════════════════
# HELPER: colorimetría automática
# ═══════════════════════════════════════════════════════════════

def _ticket_context(request, venta, public=False):
    venta.ensure_ticket_token()
    detalles = venta.detalleventa_set.select_related(
        'id_medicamento__id_lote__id_prov'
    ).all()
    detalle_qrs = []
    for detalle in detalles:
        qr = _qr_medicamento(detalle.id_medicamento)
        qr.public_url_qr = _qr_public_url(request, qr)
        detalle_qrs.append((detalle, qr))
    return {
        'venta': venta,
        'detalle_qrs': detalle_qrs,
        'ticket_url': _ticket_public_url(request, venta),
        **_ticket_totales_iva(venta),
        'public': public,
        'public_page': public,
    }


def _ticket_totales_iva(venta):
    total = Decimal(venta.total_venta or 0)
    subtotal_sin_iva = (total / Decimal('1.16')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    iva = (total - subtotal_sin_iva).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return {
        'ticket_subtotal_sin_iva': subtotal_sin_iva,
        'ticket_iva': iva,
        'ticket_total': total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'ticket_iva_porcentaje': 16,
    }


def _ticket_public_url(request, venta):
    venta.ensure_ticket_token()
    path = reverse('venta_ticket_public', kwargs={'token': venta.ticket_token})
    if settings.SITE_PUBLIC_BASE_URL:
        return settings.SITE_PUBLIC_BASE_URL + path
    return request.build_absolute_uri(path)


def _qr_public_url(request, qr):
    if qr.url_qr.startswith(('http://', 'https://')):
        return qr.url_qr
    if settings.QR_PUBLIC_BASE_URL:
        return settings.QR_PUBLIC_BASE_URL + qr.url_qr
    return request.build_absolute_uri(qr.url_qr)


def _qr_medicamento(medicamento):
    qr = CodigoQR.objects.filter(id_medicamento=medicamento, activo=True).first()
    if qr:
        return qr

    token = secrets.token_hex(32)
    while CodigoQR.objects.filter(token=token).exists():
        token = secrets.token_hex(32)

    return CodigoQR.objects.create(
        id_medicamento=medicamento,
        token=token,
        url_qr=reverse('qr_scan', kwargs={'token': token}),
        fecha_generacion=timezone.localdate(),
        activo=True,
    )


def _ticket_png(request, venta, detalles):
    detalles = list(detalles)
    totales = _ticket_totales_iva(venta)
    width = 760
    margin = 62
    row_height = 124
    height = 920 + max(len(detalles), 1) * row_height
    primary = '#1670A8'
    primary_dark = '#0f547f'
    ink = '#0f2533'
    muted = '#5f7f95'
    border = '#cfe3ef'
    soft = '#eef7fc'
    table_soft = '#f8fcff'
    image = Image.new('RGB', (width, height), '#ffffff')
    draw = ImageDraw.Draw(image)
    font_title = _font(36)
    font_head = _font(19)
    font_body = _font(16)
    font_small = _font(13)
    font_tiny = _font(11)

    def text(x, y, value, fill=ink, font=font_body):
        draw.text((x, y), str(value), fill=fill, font=font)

    def centered(x1, x2, y, value, fill=ink, font=font_body):
        value = str(value)
        bbox = draw.textbbox((0, 0), value, font=font)
        text(x1 + (x2 - x1 - (bbox[2] - bbox[0])) / 2, y, value, fill, font)

    x = margin
    y = 58
    text(x, y, 'FARMACIA INCLUSIVA', primary, font_small)
    y += 24
    text(x, y, 'Ticket de compra', ink, font_title)
    y += 45
    fecha = venta.fecha_venta.strftime('%d/%m/%Y %H:%M') if venta.fecha_venta else 'No registrada'
    text(x, y, f'Folio #{venta.id_ventas} · {fecha}', muted, font_body)

    qr_size = 128
    qr_x = width - margin - qr_size
    qr_y = 54
    qr = qrcode.make(_ticket_public_url(request, venta)).convert('RGB').resize((qr_size, qr_size))
    draw.rounded_rectangle((qr_x - 10, qr_y - 10, qr_x + qr_size + 10, qr_y + qr_size + 10), radius=12, outline=border, width=2, fill='#ffffff')
    image.paste(qr, (qr_x, qr_y))

    y = 216
    draw.line((margin, y, width - margin, y), fill=primary, width=3)
    y += 20

    card_gap = 10
    card_w = (width - margin * 2 - card_gap * 2) // 3
    cards = [
        ('Cliente', venta.cliente_display()),
        ('Cajero', venta.id_usuario.nombre_completo()),
        ('Método de pago', venta.id_metPag.nombre_metodo),
    ]
    for index, (label, value) in enumerate(cards):
        cx = margin + index * (card_w + card_gap)
        draw.rounded_rectangle((cx, y, cx + card_w, y + 64), radius=9, fill=soft, outline=border, width=1)
        text(cx + 12, y + 12, label, ink, font_small)
        text(cx + 12, y + 34, _clip(value, 24), ink, font_small)

    y += 78
    draw.rounded_rectangle((margin, y, margin + card_w, y + 64), radius=9, fill=soft, outline=border, width=1)
    text(margin + 12, y + 12, 'Total', ink, font_small)
    text(margin + 12, y + 34, f'${totales["ticket_total"]:.2f}', primary, font_head)

    y += 90
    text(margin, y, 'Productos comprados', ink, font_head)
    y += 38

    table_x = margin
    table_w = width - margin * 2
    col_med = 178
    col_lote = 145
    col_cant = 54
    col_precio = 72
    col_subtotal = 82
    col_qr = table_w - col_med - col_lote - col_cant - col_precio - col_subtotal
    col_x = [
        table_x,
        table_x + col_med,
        table_x + col_med + col_lote,
        table_x + col_med + col_lote + col_cant,
        table_x + col_med + col_lote + col_cant + col_precio,
        table_x + col_med + col_lote + col_cant + col_precio + col_subtotal,
    ]

    draw.rectangle((table_x, y, table_x + table_w, y + 36), fill=primary_dark)
    headers = ['MEDICAMENTO', 'LOTE', 'CANT.', 'PRECIO', 'SUBTOTAL', 'QR MEDICAMENTO']
    widths = [col_med, col_lote, col_cant, col_precio, col_subtotal, col_qr]
    for hx, header in zip(col_x, headers):
        text(hx + 8, y + 11, header, '#ffffff', font_tiny)
    y += 36

    for index, detalle in enumerate(detalles):
        med = detalle.id_medicamento
        lote = med.id_lote
        row_top = y
        row_fill = '#ffffff' if index % 2 == 0 else table_soft
        draw.rectangle((table_x, row_top, table_x + table_w, row_top + row_height), fill=row_fill)
        draw.line((table_x, row_top + row_height, table_x + table_w, row_top + row_height), fill=border, width=1)

        text(col_x[0] + 8, y + 16, _clip(med.nombre, 23), ink, font_small)
        presentacion = _clip(f'{med.presentacion_completa or "Sin presentación"} · {med.concentracion or "Sin concentración"}', 28)
        text(col_x[0] + 8, y + 38, presentacion, muted, font_tiny)

        if lote:
            text(col_x[1] + 8, y + 16, _clip(lote.numero_lote, 15), ink, font_small)
            text(col_x[1] + 8, y + 38, _clip(lote.id_prov.nombre, 21), muted, font_tiny)
            caducidad = lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else 'Sin fecha'
            text(col_x[1] + 8, y + 58, f'Cad. {caducidad}', muted, font_tiny)
            text(col_x[1] + 8, y + 76, _clip(lote.estado_caducidad_display(), 18), muted, font_tiny)
        else:
            text(col_x[1] + 8, y + 16, 'Sin lote', muted, font_small)

        centered(col_x[2], col_x[2] + col_cant, y + 16, detalle.cantidad, primary_dark, font_small)
        text(col_x[3] + 8, y + 16, f'${detalle.precio_unitario:.2f}', primary_dark, font_small)
        text(col_x[4] + 8, y + 16, f'${detalle.subtotal:.2f}', primary_dark, font_small)

        qr = _qr_medicamento(med)
        med_qr_size = 68
        med_qr = qrcode.make(_qr_public_url(request, qr)).convert('RGB').resize((med_qr_size, med_qr_size))
        med_qr_x = col_x[5] + 12
        med_qr_y = y + 14
        draw.rounded_rectangle((med_qr_x - 5, med_qr_y - 5, med_qr_x + med_qr_size + 5, med_qr_y + med_qr_size + 5), radius=8, fill='#ffffff', outline=border, width=1)
        image.paste(med_qr, (med_qr_x, med_qr_y))
        text(col_x[5] + 12, y + 90, 'Ficha del', primary, font_tiny)
        text(col_x[5] + 12, y + 106, 'medicamento', primary, font_tiny)
        y += row_height

    totals_h = 92
    draw.rectangle((table_x, y, table_x + table_w, y + totals_h), fill=primary)
    text(table_x + table_w - 230, y + 12, 'Subtotal sin IVA', '#ffffff', font_small)
    text(table_x + table_w - 112, y + 12, f'${totales["ticket_subtotal_sin_iva"]:.2f}', '#ffffff', font_small)
    text(table_x + table_w - 230, y + 38, 'IVA 16%', '#ffffff', font_small)
    text(table_x + table_w - 112, y + 38, f'${totales["ticket_iva"]:.2f}', '#ffffff', font_small)
    text(table_x + table_w - 230, y + 64, 'Total', '#ffffff', font_small)
    text(table_x + table_w - 112, y + 64, f'${totales["ticket_total"]:.2f}', '#ffffff', font_small)
    y += totals_h + 20

    note_h = 86
    draw.rounded_rectangle((margin, y, width - margin, y + note_h), radius=9, fill=soft, outline=border, width=1)
    text(margin + 12, y + 14, 'Ticket digital', ink, font_small)
    text(margin + 12, y + 38, 'Escanea los QR para ver lote, proveedor y caducidad', ink, font_small)
    text(margin + 12, y + 60, 'de cada medicamento vendido.', ink, font_small)
    y += note_h + 38

    final_height = min(height, y)
    return image.crop((0, 0, width, final_height))


def _font(size):
    for name in ('arial.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _clip(text, limit):
    text = str(text)
    return text if len(text) <= limit else f'{text[:limit - 3]}...'


def _clave_medicamento(med):
    return (
        (med.nombre or '').strip().casefold(),
        (med.presentacion or '').strip().casefold(),
        (med.tamano_presentacion or '').strip().casefold(),
        (med.concentracion or '').strip().casefold(),
        bool(med.requiere_receta),
    )


def _medicamentos_para_venta():
    meds = Medicamento.objects.select_related('id_lote', 'id_lote__id_prov').filter(
        id_lote__activo=True,
        id_lote__oculto_por_caducidad=False,
        id_lote__stock_actual__gt=0,
    )
    meds = [
        med for med in meds
        if med.id_lote.estado_caducidad != 'rojo'
    ]

    grupos = defaultdict(list)
    for med in meds:
        grupos[_clave_medicamento(med)].append(med)

    opciones = []
    for grupo in grupos.values():
        grupo = _ordenar_medicamentos_para_venta(grupo)
        principal = grupo[0]
        stock_total = sum(med.id_lote.stock_actual or 0 for med in grupo)
        precio = principal.id_lote.precio_venta or Decimal('0.00')
        lotes = []
        for med in grupo:
            lote = med.id_lote
            lotes.append({
                'med_id': med.id_med,
                'lote_id': lote.id_lote,
                'proveedor_id': lote.id_prov_id,
                'proveedor': lote.id_prov.nombre,
                'numero': lote.numero_lote,
                'stock': lote.stock_actual or 0,
                'precio': float(lote.precio_venta or Decimal('0.00')),
                'caducidad': lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else 'Sin fecha',
            })
        nombre = principal.nombre
        if principal.presentacion:
            nombre += f' - {principal.presentacion}'
        if principal.concentracion:
            nombre += f' - {principal.concentracion}'

        opciones.append(SimpleNamespace(
            id_med=principal.id_med,
            nombre=nombre,
            precio_venta=precio,
            stock_total=stock_total,
            requiere_receta=principal.requiere_receta,
            lotes_json=json.dumps(lotes),
        ))

    return sorted(opciones, key=lambda med: med.nombre.lower())


def _medicamentos_catalogo_trazabilidad():
    vistos = set()
    catalogo = []
    medicamentos = Medicamento.objects.select_related('id_lote').order_by(
        'nombre',
        'presentacion',
        'tamano_presentacion',
        'concentracion',
        'id_med',
    )
    for med in medicamentos:
        clave = _clave_medicamento(med)
        if clave in vistos:
            continue
        vistos.add(clave)
        nombre = med.nombre
        detalles = []
        if med.presentacion_completa:
            detalles.append(med.presentacion_completa)
        if med.concentracion:
            detalles.append(med.concentracion)
        catalogo.append(SimpleNamespace(
            id_med=med.id_med,
            nombre=nombre,
            detalle=' - '.join(detalles),
            trazabilidad_clave='|'.join(str(part) for part in clave),
        ))
    return catalogo


def _lotes_catalogo_trazabilidad():
    lotes = Lote.objects.select_related('id_prov').prefetch_related('medicamento_set').order_by('numero_lote')
    catalogo = []
    for lote in lotes:
        claves = []
        for med in lote.medicamento_set.all():
            claves.append('|'.join(str(part) for part in _clave_medicamento(med)))
        lote.trazabilidad_claves = '||'.join(claves)
        catalogo.append(lote)
    return catalogo


def _parsear_seleccion_medicamento(seleccion):
    partes = str(seleccion).split('-')
    if len(partes) >= 2 and partes[0] in {'auto', 'lote'}:
        return partes[0], int(partes[1]), None
    if len(partes) >= 3 and partes[0] == 'prov':
        return 'prov', int(partes[1]), int(partes[2])
    return 'auto', int(seleccion), None


def _medicamentos_para_descontar(med, tipo_seleccion='auto', proveedor_id=None):
    if tipo_seleccion == 'lote':
        meds = [med]
    else:
        meds = _medicamentos_vigentes_mismo_grupo(med)
        if tipo_seleccion == 'prov' and proveedor_id:
            meds = [item for item in meds if item.id_lote.id_prov_id == proveedor_id]
    meds = [
        item for item in meds
        if item.id_lote.activo
        and not item.id_lote.oculto_por_caducidad
        and (item.id_lote.stock_actual or 0) > 0
        and item.id_lote.estado_caducidad != 'rojo'
    ]
    return _ordenar_medicamentos_para_venta(meds)


def _medicamentos_vigentes_mismo_grupo(med):
    meds = Medicamento.objects.select_related('id_lote', 'id_lote__id_prov').filter(
        nombre__iexact=med.nombre,
        presentacion=med.presentacion,
        concentracion=med.concentracion,
        requiere_receta=med.requiere_receta,
        id_lote__activo=True,
        id_lote__oculto_por_caducidad=False,
        id_lote__stock_actual__gt=0,
    )
    meds = [item for item in meds if item.id_lote.estado_caducidad != 'rojo']
    return _ordenar_medicamentos_para_venta(meds)


def _ordenar_medicamentos_para_venta(meds):
    fecha_maxima = datetime.max.date()
    return sorted(
        meds,
        key=lambda med: (
            med.id_lote.fecha_caducidad or fecha_maxima,
            med.id_lote.fecha_ingreso or timezone.now(),
            med.id_lote_id,
        ),
    )


def _actualizar_colorimetria(medicamento, stock_actual):
    if stock_actual <= 0:
        estado = 'sin_stock'
    elif stock_actual < 50:
        estado = 'amarillo'
    else:
        estado = 'verde'

    if medicamento.estado_colorimetria != estado:
        medicamento.estado_colorimetria = estado
        medicamento.save(update_fields=['estado_colorimetria'])
