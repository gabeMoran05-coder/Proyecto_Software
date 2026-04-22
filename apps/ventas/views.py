from decimal import Decimal
from io import BytesIO
import secrets
from collections import defaultdict
from datetime import datetime
from types import SimpleNamespace
import json

import qrcode
from django.contrib import messages # pyright: ignore[reportMissingModuleSource]
from django.http import HttpResponse
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from .models import MetodoPago, Venta, DetalleVenta
from apps.clientes.models import Cliente
from apps.usuarios.models import Usuario
from apps.usuarios.security import get_current_usuario
from apps.medicamentos.models import Medicamento, CodigoQR
from .whatsapp import (
    WhatsAppIntegrationError,
    construir_preview_ticket,
    enviar_ticket_por_whatsapp,
)
from apps.medicamentos.whatsapp import (
    normalizar_telefono_con_pais,
    telefono_form_context,
)


# ═══════════════════════════════════════════════════════════════
# MÉTODOS DE PAGO  (sin app propia — vive en ventas)
# ═══════════════════════════════════════════════════════════════

def metodo_pago_list(request):
    metodos = MetodoPago.objects.all().order_by('nombre_metodo')
    return render(request, 'ventas/metodo_pago_list.html', {'metodos': metodos})


def metodo_pago_create(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre_metodo', '').strip()
        if not nombre:
            return render(request, 'ventas/metodo_pago_form.html', {
                'errors': ['El nombre del método de pago es obligatorio.'],
            })
        MetodoPago.objects.create(
            nombre_metodo = nombre,
            descripcion   = request.POST.get('descripcion', '').strip() or None,
        )
        return redirect('metodo_pago_list')
    return render(request, 'ventas/metodo_pago_form.html')


def metodo_pago_update(request, pk):
    metodo = get_object_or_404(MetodoPago, pk=pk)
    if request.method == 'POST':
        nombre = request.POST.get('nombre_metodo', '').strip()
        if not nombre:
            return render(request, 'ventas/metodo_pago_form.html', {
                'errors': ['El nombre del método de pago es obligatorio.'],
                'metodo': metodo,
            })
        metodo.nombre_metodo = nombre
        metodo.descripcion   = request.POST.get('descripcion', '').strip() or None
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

    if es_cajero:
        ventas = ventas.filter(id_usuario=usuario_actual)
    if fecha_desde:    ventas = ventas.filter(fecha_venta__date__gte=fecha_desde)
    if fecha_hasta:    ventas = ventas.filter(fecha_venta__date__lte=fecha_hasta)
    if metodo_filter:  ventas = ventas.filter(id_metPag__id_metPag=metodo_filter)
    if usuario_filter: ventas = ventas.filter(id_usuario__id_usuario=usuario_filter)
    ordenes = {
        'folio_asc': 'id_ventas',
        'folio_desc': '-id_ventas',
        'fecha_asc': 'fecha_venta',
        'fecha_desc': '-fecha_venta',
        'total_asc': 'total_venta',
        'total_desc': '-total_venta',
    }
    ventas = ventas.order_by(ordenes.get(orden_filter, '-fecha_venta'))
    vendedor_groups = _agrupar_ventas_por_vendedor(ventas)

    # Stats del día
    hoy            = timezone.now().date()
    ventas_base_qs = Venta.objects.all()
    if es_cajero:
        ventas_base_qs = ventas_base_qs.filter(id_usuario=usuario_actual)
    ventas_hoy_qs  = ventas_base_qs.filter(fecha_venta__date=hoy)
    ingresos_hoy   = sum(v.total_venta or 0 for v in ventas_hoy_qs)
    ventas_mes_qs  = ventas_base_qs.filter(
        fecha_venta__year=hoy.year, fecha_venta__month=hoy.month
    )

    from django.db.models import Avg
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
        'total_ventas':    ventas_base_qs.count(),
        'ingresos_hoy':    ingresos_hoy,
        'ventas_mes':      ventas_mes_qs.count(),
        'ticket_promedio': round(ticket_promedio, 2),
        'vendedor_groups': vendedor_groups,
        'metodos_pago':    MetodoPago.objects.all(),
        'usuarios':        Usuario.objects.all().order_by('nombre'),
        'fecha_desde':     fecha_desde,
        'fecha_hasta':     fecha_hasta,
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
    return grupos.values()


def venta_detail(request, pk):
    venta_qs = Venta.objects.select_related('id_usuario')
    usuario_actual = get_current_usuario(request)
    if usuario_actual and usuario_actual.rol_normalizado() == Usuario.ROL_CAJERO:
        venta_qs = venta_qs.filter(id_usuario=usuario_actual)
    venta    = get_object_or_404(venta_qs, pk=pk)
    venta.ensure_ticket_token()
    detalles = venta.detalleventa_set.select_related('id_medicamento').all()
    return render(request, 'ventas/venta_detail.html', {
        'venta':    venta,
        'detalles': detalles,
    })


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
    detalles = venta.detalleventa_set.select_related('id_medicamento').all()
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
    context = {
        'venta': venta,
        'preview': construir_preview_ticket(request, venta),
        **telefono_form_context(),
    }

    if request.method == 'POST':
        country_code = request.POST.get('pais_codigo', '52')
        telefono_local = request.POST.get('telefono_local', '')
        try:
            telefono = normalizar_telefono_con_pais(country_code, telefono_local)
            enviar_ticket_por_whatsapp(request, venta, telefono)
        except WhatsAppIntegrationError as exc:
            context.update(telefono_form_context(country_code, telefono_local))
            context['errors'] = [str(exc)]
            return render(request, 'ventas/ticket_whatsapp_form.html', context)

        messages.success(request, f'Ticket enviado a WhatsApp {telefono}.')
        return redirect('venta_detail', pk=venta.pk)

    return render(request, 'ventas/ticket_whatsapp_form.html', context)


# ═══════════════════════════════════════════════════════════════
# VENTAS — CREAR  (punto de venta)
# ═══════════════════════════════════════════════════════════════

def venta_create(request):
    context = {
        'usuarios':     Usuario.objects.all().order_by('nombre'),
        'metodos_pago': MetodoPago.objects.all(),
        'clientes':     Cliente.objects.all().order_by('nombre', 'ap_pat'),
        'medicamentos': _medicamentos_para_venta(),
        'fecha_actual': timezone.now().strftime('%Y-%m-%dT%H:%M'),
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
                lineas = []

                for med_id, cant_str, precio_str in zip(med_ids, cantidades, precios):
                    med      = get_object_or_404(Medicamento.objects.select_related('id_lote'), pk=med_id)
                    cantidad = int(cant_str)
                    if med.requiere_receta and med_id not in recetas_confirmadas:
                        raise ValueError(f'Debes confirmar receta para {med.nombre}.')

                    lotes_disponibles = _medicamentos_vigentes_mismo_grupo(med)
                    stock_disponible = sum(item.id_lote.stock_actual or 0 for item in lotes_disponibles)
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
                        cantidad_lote = min(restante, lote.stock_actual or 0)
                        if cantidad_lote <= 0:
                            continue
                        precio = lote.precio_venta if lote.precio_venta is not None else Decimal(precio_str)
                        subtotal = precio * cantidad_lote
                        lineas.append((med_lote, cantidad_lote, precio, subtotal))
                        total += subtotal
                        restante -= cantidad_lote

                venta = Venta.objects.create(
                    id_usuario  = get_object_or_404(Usuario,     pk=usuario_id),
                    id_metPag   = get_object_or_404(MetodoPago,  pk=metpag_id),
                    id_cliente  = get_object_or_404(Cliente, pk=cliente_id) if cliente_id else None,
                    fecha_venta = request.POST.get('fecha_venta') or timezone.now(),
                    total_venta = total,
                )

                for med, cantidad, precio, subtotal in lineas:
                    DetalleVenta.objects.create(
                        id_ventas       = venta,
                        id_medicamento  = med,
                        cantidad        = cantidad,
                        precio_unitario = precio,
                        subtotal        = subtotal,
                    )
                    lote              = med.id_lote
                    lote.stock_actual -= cantidad
                    lote.save()
                    _actualizar_colorimetria(med, lote.stock_actual)

                messages.success(request, f'Venta #{venta.id_ventas} registrada correctamente.')
                return redirect('venta_detail', pk=venta.pk)

        except ValueError as e:
            context['errors'] = [str(e)]
        except Exception as e:
            context['errors'] = [f'Error inesperado: {e}']

    return render(request, 'ventas/venta_form.html', context)


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
                lote.stock_actual += det.cantidad or 0
                lote.save()
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
    detalles = venta.detalleventa_set.select_related('id_medicamento__id_lote').all()
    detalle_qrs = [(detalle, _qr_medicamento(detalle.id_medicamento)) for detalle in detalles]
    return {
        'venta': venta,
        'detalle_qrs': detalle_qrs,
        'ticket_url': _ticket_public_url(request, venta),
        'public': public,
    }


def _ticket_public_url(request, venta):
    venta.ensure_ticket_token()
    return request.build_absolute_uri(
        reverse('venta_ticket_public', kwargs={'token': venta.ticket_token})
    )


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
    width = 760
    line_height = 28
    height = 430 + max(detalles.count(), 1) * 72
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    font_title = _font(30)
    font_head = _font(20)
    font_body = _font(17)
    font_small = _font(14)

    x = 34
    y = 28
    draw.text((x, y), 'Farmacia Inclusiva', fill='black', font=font_head)
    y += 36
    draw.text((x, y), f'Ticket de compra #{venta.id_ventas}', fill='black', font=font_title)
    y += 48
    fecha = venta.fecha_venta.strftime('%d/%m/%Y %H:%M') if venta.fecha_venta else 'No registrada'
    draw.text((x, y), f'Fecha: {fecha}', fill='black', font=font_body)
    y += line_height
    draw.text((x, y), f'Cliente: {venta.cliente_display()}', fill='black', font=font_body)
    y += line_height
    draw.text((x, y), f'Cajero: {venta.id_usuario.nombre_completo()}', fill='black', font=font_body)
    y += line_height
    draw.text((x, y), f'Metodo de pago: {venta.id_metPag.nombre_metodo}', fill='black', font=font_body)

    qr = qrcode.make(_ticket_public_url(request, venta)).convert('RGB').resize((150, 150))
    image.paste(qr, (width - 190, 34))

    y += 48
    draw.line((x, y, width - x, y), fill='#222222', width=2)
    y += 18
    draw.text((x, y), 'Productos', fill='black', font=font_head)
    y += 38

    for detalle in detalles:
        draw.text((x, y), _clip(detalle.id_medicamento.nombre, 45), fill='black', font=font_body)
        y += line_height
        linea = (
            f'{detalle.cantidad} x ${detalle.precio_unitario:.2f} = '
            f'${detalle.subtotal:.2f}'
        )
        draw.text((x + 18, y), linea, fill='black', font=font_small)
        y += line_height + 12

    y += 6
    draw.line((x, y, width - x, y), fill='#222222', width=2)
    y += 24
    draw.text((x, y), f'Total: ${venta.total_venta:.2f}', fill='black', font=font_title)
    y += 48
    draw.text((x, y), 'Escanea el QR para abrir el ticket digital.', fill='black', font=font_small)
    return image


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
        (med.concentracion or '').strip().casefold(),
        bool(med.requiere_receta),
    )


def _medicamentos_para_venta():
    meds = Medicamento.objects.select_related('id_lote').filter(
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


def _medicamentos_vigentes_mismo_grupo(med):
    meds = Medicamento.objects.select_related('id_lote').filter(
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
    elif stock_actual <= 5:
        estado = 'rojo'
    elif stock_actual <= 20:
        estado = 'amarillo'
    else:
        estado = 'verde'

    if medicamento.estado_colorimetria != estado:
        medicamento.estado_colorimetria = estado
        medicamento.save(update_fields=['estado_colorimetria'])
