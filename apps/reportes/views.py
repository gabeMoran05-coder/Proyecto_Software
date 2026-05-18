import calendar
from io import BytesIO
from datetime import date, timedelta
from decimal import Decimal

from PIL import Image, ImageDraw, ImageFont
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.medicamentos.models import Lote
from apps.ventas.models import DetalleVenta, Venta


def reportes_dashboard(request):
    context = _build_report_context(request)
    return render(request, 'reportes/dashboard.html', context)


def reportes_pdf(request):
    context = _build_report_context(request)
    pdf_buffer = _build_report_pdf(context)
    filename = (
        f"reporte-farmacia-{context['fecha_desde'].strftime('%Y%m%d')}"
        f"-{context['fecha_hasta'].strftime('%Y%m%d')}.pdf"
    )
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def reportes_excel(request):
    context = _build_report_context(request)
    html = render_to_string('reportes/export_excel.html', context)
    filename = (
        f"reporte-farmacia-{context['fecha_desde'].strftime('%Y%m%d')}"
        f"-{context['fecha_hasta'].strftime('%Y%m%d')}.xls"
    )
    response = HttpResponse(
        html,
        content_type='application/vnd.ms-excel; charset=utf-8',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _build_report_context(request):
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    desde_raw = request.GET.get('desde', '').strip()
    hasta_raw = request.GET.get('hasta', '').strip()
    mes_filter = _parse_int(request.GET.get('mes'))
    anio_filter = _parse_int(request.GET.get('anio'))
    usa_filtro_mes = mes_filter and anio_filter and 1 <= mes_filter <= 12
    date_error_message = ''

    if usa_filtro_mes:
        ultimo_dia = calendar.monthrange(anio_filter, mes_filter)[1]
        fecha_desde = date(anio_filter, mes_filter, 1)
        fecha_hasta = date(anio_filter, mes_filter, ultimo_dia)
        if fecha_desde > hoy:
            date_error_message = (
                f'No se pueden generar reportes de periodos futuros. '
                f'Hoy es {_format_date_es(hoy)}; elige un periodo hasta esa fecha.'
            )
            fecha_desde = inicio_mes
            fecha_hasta = hoy
            usa_filtro_mes = False
        elif fecha_hasta > hoy:
            fecha_hasta = hoy
    else:
        fecha_desde = _parse_date(desde_raw) or inicio_mes
        fecha_hasta = _parse_date(hasta_raw)
        if not fecha_hasta:
            fecha_hasta = fecha_desde if desde_raw else hoy
        if fecha_desde > hoy or fecha_hasta > hoy:
            date_error_message = (
                f'No se pueden generar reportes con fechas posteriores a hoy '
                f'({_format_date_es(hoy)}). Elige un periodo que ya haya pasado.'
            )
            fecha_desde = inicio_mes
            fecha_hasta = hoy
        elif fecha_desde > fecha_hasta:
            date_error_message = 'Rango de fechas invalido: la fecha "Hasta" debe ser igual o posterior a "Desde".'
            fecha_desde = inicio_mes
            fecha_hasta = hoy

    ventas = Venta.objects.select_related('id_usuario', 'id_metPag').filter(
        fecha_venta__date__gte=fecha_desde,
        fecha_venta__date__lte=fecha_hasta,
    )
    detalles = DetalleVenta.objects.select_related(
        'id_ventas', 'id_medicamento', 'id_medicamento__id_lote__id_prov'
    ).filter(id_ventas__in=ventas)

    total_ventas = ventas.count()
    ingresos = ventas.aggregate(total=Sum('total_venta'))['total'] or Decimal('0.00')
    productos_vendidos = detalles.aggregate(total=Sum('cantidad'))['total'] or 0
    ticket_promedio = ingresos / total_ventas if total_ventas else Decimal('0.00')
    costo_vendido = sum(
        (
            detalle.id_medicamento.id_lote.precio_compra
            if detalle.id_medicamento.id_lote and detalle.id_medicamento.id_lote.precio_compra
            else Decimal('0.00')
        ) * (detalle.cantidad or 0)
        for detalle in detalles
    )
    utilidad_estimada = ingresos - costo_vendido
    margen_estimado = (utilidad_estimada / ingresos * 100) if ingresos else Decimal('0.00')
    margen_estimado_percent = max(0, min(100, int(margen_estimado))) if ingresos else 0
    lotes_recibidos = Lote.objects.filter(
        fecha_ingreso__date__gte=fecha_desde,
        fecha_ingreso__date__lte=fecha_hasta,
    )
    total_compra_recibida = sum(
        (lote.precio_compra or Decimal('0.00')) * (lote.stock_actual or 0)
        for lote in lotes_recibidos
    )

    clientes_nuevos = Cliente.objects.filter(
        fecha_registro__gte=fecha_desde,
        fecha_registro__lte=fecha_hasta,
    )
    total_clientes_nuevos = clientes_nuevos.count()
    clientes_con_compra_total = ventas.exclude(id_cliente__isnull=True).values('id_cliente').distinct().count()
    ventas_clientes_nuevos = Venta.objects.filter(
        id_cliente__in=clientes_nuevos,
        fecha_venta__date__gte=fecha_desde,
        fecha_venta__date__lte=fecha_hasta,
    )
    clientes_nuevos_con_compra_total = ventas_clientes_nuevos.values('id_cliente').distinct().count()
    clientes_nuevos_sin_compra_total = max(
        total_clientes_nuevos - clientes_nuevos_con_compra_total,
        0,
    )
    clientes_nuevos_detalle = list(
        clientes_nuevos.order_by('-fecha_registro', 'nombre', 'ap_pat')[:10]
    )
    ventas_por_cliente_nuevo = {
        item['id_cliente']: item
        for item in ventas_clientes_nuevos.values('id_cliente').annotate(
            compras=Count('id_ventas'),
            ingresos=Sum('total_venta'),
        )
    }
    for cliente in clientes_nuevos_detalle:
        stats = ventas_por_cliente_nuevo.get(cliente.id_cliente, {})
        cliente.compras_periodo = stats.get('compras') or 0
        cliente.ingresos_periodo = stats.get('ingresos') or Decimal('0.00')

    top_medicamentos = list(
        detalles.values(
            'id_medicamento__nombre',
            'id_medicamento__presentacion',
            'id_medicamento__tamano_presentacion',
            'id_medicamento__concentracion',
        )
        .annotate(
            cantidad=Sum('cantidad'),
            ingresos=Sum('subtotal'),
            ventas=Count('id_ventas', distinct=True),
        )
        .order_by('-cantidad', '-ingresos')[:8]
    )

    top_vendedores = list(
        ventas.values(
            'id_usuario__id_usuario',
            'id_usuario__nombre',
            'id_usuario__ap_pat',
            'id_usuario__ap_mat',
        )
        .annotate(
            ventas=Count('id_ventas'),
            ingresos=Sum('total_venta'),
        )
        .order_by('-ingresos', '-ventas')[:8]
    )

    metodos_pago = list(
        ventas.values('id_metPag__nombre_metodo')
        .annotate(ventas=Count('id_ventas'), ingresos=Sum('total_venta'))
        .order_by('-ingresos', '-ventas')
    )
    for metodo in metodos_pago:
        metodo['porcentaje'] = _percent(metodo['ingresos'], ingresos)

    ventas_por_dia_raw = list(
        ventas.annotate(dia=TruncDate('fecha_venta'))
        .values('dia')
        .annotate(ventas=Count('id_ventas'), ingresos=Sum('total_venta'))
        .order_by('dia')
    )
    ventas_por_dia = _ventas_por_dia_chart(ventas_por_dia_raw, fecha_desde, fecha_hasta)

    lotes_bajo_stock = Lote.objects.select_related('id_prov').prefetch_related('medicamento_set').filter(
        activo=True,
        oculto_por_caducidad=False,
        stock_actual__gt=0,
        stock_actual__lt=50,
    ).order_by('stock_actual', 'fecha_caducidad')[:8]

    limite_caducidad_periodo = fecha_hasta + timedelta(days=90)
    lotes_caducidad_periodo_qs = (
        Lote.objects.select_related('id_prov')
        .prefetch_related('medicamento_set')
        .filter(
            activo=True,
            oculto_por_caducidad=False,
            fecha_caducidad__isnull=False,
            fecha_caducidad__gte=fecha_desde,
            fecha_caducidad__lte=limite_caducidad_periodo,
        )
        .order_by('fecha_caducidad', 'numero_lote')
    )
    lotes_caducos_periodo_total = lotes_caducidad_periodo_qs.filter(
        fecha_caducidad__lte=fecha_hasta
    ).count()
    lotes_proximos_periodo_total = lotes_caducidad_periodo_qs.filter(
        fecha_caducidad__gt=fecha_hasta
    ).count()
    lotes_caducidad_periodo = list(lotes_caducidad_periodo_qs[:10])
    for lote in lotes_caducidad_periodo:
        if lote.fecha_caducidad <= fecha_hasta:
            lote.alerta_periodo_estado = 'Caducó en el periodo'
            lote.alerta_periodo_clase = 'danger'
        else:
            lote.alerta_periodo_estado = 'Próximo al cierre'
            lote.alerta_periodo_clase = 'warning'
        lote.alerta_periodo_dias = (lote.fecha_caducidad - fecha_hasta).days

    lotes_activos_base = Lote.objects.filter(
        activo=True,
        oculto_por_caducidad=False,
    )
    lotes_activos = list(lotes_activos_base)
    lotes_activos_total = len(lotes_activos)
    lotes_sin_stock_total = sum(1 for lote in lotes_activos if (lote.stock_actual or 0) <= 0)
    lotes_bajo_stock_total = sum(1 for lote in lotes_activos if 0 < (lote.stock_actual or 0) < 50)
    lotes_caducos_total = sum(1 for lote in lotes_activos if lote.estado_caducidad == Lote.CADUCIDAD_ROJO)
    lotes_proximos_total = sum(1 for lote in lotes_activos if lote.estado_caducidad == Lote.CADUCIDAD_AMARILLO)
    lotes_vigentes_total = sum(1 for lote in lotes_activos if lote.estado_caducidad == Lote.CADUCIDAD_VERDE)
    stock_total_unidades = sum(lote.stock_actual or 0 for lote in lotes_activos)
    inventario_salud = [
        {
            'label': 'Vigentes',
            'value': lotes_vigentes_total,
            'percent': _percent(lotes_vigentes_total, lotes_activos_total),
            'class': 'ok',
        },
        {
            'label': 'Próximos',
            'value': lotes_proximos_total,
            'percent': _percent(lotes_proximos_total, lotes_activos_total),
            'class': 'warning',
        },
        {
            'label': 'Caducos',
            'value': lotes_caducos_total,
            'percent': _percent(lotes_caducos_total, lotes_activos_total),
            'class': 'danger',
        },
    ]

    export_query = (
        f"?desde={fecha_desde.strftime('%Y-%m-%d')}"
        f"&hasta={fecha_hasta.strftime('%Y-%m-%d')}"
    )

    return {
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'total_ventas': total_ventas,
        'ingresos': ingresos,
        'productos_vendidos': productos_vendidos,
        'ticket_promedio': ticket_promedio,
        'costo_vendido': costo_vendido,
        'utilidad_estimada': utilidad_estimada,
        'margen_estimado': margen_estimado,
        'margen_estimado_percent': margen_estimado_percent,
        'total_compra_recibida': total_compra_recibida,
        'total_clientes_nuevos': total_clientes_nuevos,
        'clientes_con_compra_total': clientes_con_compra_total,
        'clientes_nuevos_con_compra_total': clientes_nuevos_con_compra_total,
        'clientes_nuevos_sin_compra_total': clientes_nuevos_sin_compra_total,
        'clientes_nuevos_detalle': clientes_nuevos_detalle,
        'medicamento_mas_vendido': top_medicamentos[0] if top_medicamentos else None,
        'vendedor_del_mes': top_vendedores[0] if top_vendedores else None,
        'top_medicamentos': top_medicamentos,
        'top_vendedores': top_vendedores,
        'metodos_pago': metodos_pago,
        'ventas_por_dia': ventas_por_dia,
        'lotes_bajo_stock': lotes_bajo_stock,
        'lotes_caducidad_periodo': lotes_caducidad_periodo,
        'lotes_caducos_periodo_total': lotes_caducos_periodo_total,
        'lotes_proximos_periodo_total': lotes_proximos_periodo_total,
        'lotes_activos_total': lotes_activos_total,
        'lotes_sin_stock_total': lotes_sin_stock_total,
        'lotes_bajo_stock_total': lotes_bajo_stock_total,
        'lotes_caducos_total': lotes_caducos_total,
        'lotes_proximos_total': lotes_proximos_total,
        'lotes_vigentes_total': lotes_vigentes_total,
        'stock_total_unidades': stock_total_unidades,
        'inventario_salud': inventario_salud,
        'mes_filter': mes_filter if usa_filtro_mes else None,
        'anio_filter': anio_filter if usa_filtro_mes else None,
        'meses': _meses(),
        'anios': range(hoy.year - 5, hoy.year + 2),
        'desde_raw': desde_raw,
        'hasta_raw': hasta_raw,
        'fecha_maxima': hoy.strftime('%Y-%m-%d'),
        'fecha_maxima_display': _format_date_es(hoy),
        'date_error_message': date_error_message,
        'export_query': export_query,
    }


def _build_report_pdf(context):
    page_width, page_height = 1500, 900
    margin_x, margin_y = 38, 34
    content_width = page_width - (margin_x * 2)
    page_bg = '#07131B'
    surface = '#0F202B'
    surface_2 = '#142B38'
    primary = '#1670A8'
    primary_2 = '#55B0DF'
    primary_3 = '#17384B'
    accent = '#2387C4'
    warning = '#F0A83A'
    danger = '#E45A4F'
    ink = '#EDF7FC'
    muted = '#A9C3D1'
    line = '#274657'
    soft = '#102A3A'

    title_font = _font(50, bold=True)
    subtitle_font = _font(25)
    section_font = _font(24, bold=True)
    label_font = _font(22, bold=True)
    body_font = _font(22)
    small_font = _font(19)
    kpi_font = _font(48, bold=True)
    table_font = _font(20)

    pages = []
    image = None
    draw = None
    y = margin_y
    page_number = 0

    def start_page():
        nonlocal image, draw, y, page_number
        image = Image.new('RGB', (page_width, page_height), page_bg)
        draw = ImageDraw.Draw(image)
        y = margin_y
        page_number += 1
        draw_decor()

    def finish_page():
        draw.line((margin_x, page_height - 48, page_width - margin_x, page_height - 48), fill=line, width=2)
        footer = 'Farmacia Inclusiva'
        footer_w = text_width(footer, small_font)
        draw.text(((page_width - footer_w) // 2, page_height - 32), footer, fill=muted, font=small_font)
        page_text = f'Página {page_number}'
        right = text_width(page_text, small_font)
        draw.text((page_width - margin_x - right, page_height - 31), page_text, fill=muted, font=small_font)
        pages.append(image)

    def ensure(space):
        nonlocal y
        if y + space <= page_height - 62:
            return
        finish_page()
        start_page()

    def text_width(value, font):
        return draw.textbbox((0, 0), str(value), font=font)[2]

    def fit_text(value, font, max_width):
        value = str(value or '')
        if text_width(value, font) <= max_width:
            return value
        ellipsis = '...'
        while value and text_width(value + ellipsis, font) > max_width:
            value = value[:-1]
        return value + ellipsis if value else ellipsis

    def draw_wrapped(value, x, top, max_width, font, fill, line_height=26, max_lines=2):
        words = str(value or '').split()
        lines = []
        current = ''
        for word in words:
            candidate = f'{current} {word}'.strip()
            if text_width(candidate, font) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
            if len(lines) == max_lines:
                break
        if current and len(lines) < max_lines:
            lines.append(current)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
        for index, line_text in enumerate(lines):
            if index == max_lines - 1 and words:
                line_text = fit_text(line_text, font, max_width)
            draw.text((x, top + (index * line_height)), line_text, fill=fill, font=font)

    def rounded_box(x1, y1, x2, y2, fill, outline=None, radius=18, width=2):
        draw.rounded_rectangle((x1, y1, x2, y2), radius=radius, fill=fill, outline=outline, width=width)

    def draw_decor():
        rounded_box(
            margin_x - 26,
            margin_y - 28,
            page_width - margin_x + 26,
            page_height - margin_y + 8,
            surface,
            outline=line,
            radius=22,
            width=2,
        )

    def draw_header():
        nonlocal y
        draw.text((margin_x, y), 'Reportes', fill=ink, font=title_font)
        y += 56
        draw.text((margin_x, y), 'Indicadores de ventas, medicamentos e inventario', fill=muted, font=subtitle_font)
        y += 54
        rounded_box(margin_x, y, page_width - margin_x, y + 58, surface_2, outline=line, radius=10)
        period = f"Periodo  Desde  {context['fecha_desde'].strftime('%d/%m/%Y')}    Hasta  {context['fecha_hasta'].strftime('%d/%m/%Y')}"
        draw.text((margin_x + 20, y + 17), period, fill=primary_2, font=label_font)
        y += 76

    def draw_kpis():
        nonlocal y
        kpis = [
            ('VENTAS', context['total_ventas'], f"{context['fecha_desde'].strftime('%d/%m/%Y')} - {context['fecha_hasta'].strftime('%d/%m/%Y')}"),
            ('INGRESOS', f"${_fmt_money(context['ingresos'])}", 'Total vendido'),
            ('PRODUCTOS', context['productos_vendidos'], 'Unidades vendidas'),
            ('TICKET PROMEDIO', f"${_fmt_money(context['ticket_promedio'])}", 'Promedio por venta'),
            ('COMPRA RECIBIDA', f"${_fmt_money(context['total_compra_recibida'])}", 'Total a precio de compra'),
        ]
        gap = 14
        card_w = (content_width - (gap * 4)) // 5
        for index, (label, value, detail) in enumerate(kpis):
            x = margin_x + index * (card_w + gap)
            rounded_box(x, y, x + card_w, y + 126, surface, outline=line, radius=10, width=2)
            draw.text((x + 18, y + 18), label, fill=muted, font=small_font)
            draw.text((x + 18, y + 48), fit_text(value, kpi_font, card_w - 30), fill=primary, font=kpi_font)
            draw.text((x + 18, y + 94), fit_text(detail, small_font, card_w - 30), fill=primary_2, font=small_font)
        y += 142

    def draw_section(title):
        nonlocal y
        ensure(54)
        draw.text((margin_x, y), title.upper(), fill=muted, font=section_font)
        y += 34

    def draw_bar_chart():
        nonlocal y
        draw_section('Ventas por día')
        panel_top = y
        chart_panel_w = int(content_width * 0.58)
        rounded_box(margin_x, panel_top, margin_x + chart_panel_w, panel_top + 250, surface, outline=line, radius=10)
        total_text = f"${_fmt_money(context['ingresos'])}"
        draw.text((margin_x + 22, panel_top + 18), 'VENTAS POR DIA', fill=muted, font=label_font)
        draw.text((margin_x + chart_panel_w - text_width(total_text, label_font) - 22, panel_top + 18), total_text, fill=primary, font=label_font)
        items = context['ventas_por_dia'][:8]
        chart_x = margin_x + 36
        chart_y = panel_top + 62
        chart_w = chart_panel_w - 72
        chart_h = 150
        max_value = max([float(item['ingresos'] or 0) for item in items] + [1])
        if not items:
            draw.text((chart_x + 170, chart_y + 95), 'Sin ventas en el periodo', fill=muted, font=body_font)
        else:
            group_w = chart_w / len(items)
            bar_w = min(42, int(group_w * 0.55))
            for index, item in enumerate(items):
                value = float(item['ingresos'] or 0)
                h = max(6, int((value / max_value) * (chart_h - 18))) if max_value else 6
                x = int(chart_x + index * group_w + (group_w - bar_w) / 2)
                y1 = chart_y + chart_h - h
                draw.rounded_rectangle((x, y1, x + bar_w, chart_y + chart_h), radius=7, fill=primary_2)
                day = item['dia'].strftime('%d/%m')
                day_w = text_width(day, small_font)
                draw.text((x + (bar_w - day_w) // 2, chart_y + chart_h + 12), day, fill=muted, font=small_font)

        health_x = margin_x + chart_panel_w + 20
        rounded_box(health_x, panel_top, page_width - margin_x, panel_top + 250, surface, outline=line, radius=10)
        draw.text((health_x + 22, panel_top + 18), 'SALUD DE INVENTARIO', fill=muted, font=label_font)
        lotes_text = f"{context['lotes_activos_total']} lotes"
        draw.text((page_width - margin_x - text_width(lotes_text, label_font) - 22, panel_top + 18), lotes_text, fill=primary, font=label_font)
        row_y = panel_top + 66
        colors = {'ok': primary_2, 'warning': warning, 'danger': danger}
        for item in context['inventario_salud']:
            draw.text((health_x + 24, row_y), item['label'], fill=ink, font=body_font)
            value = str(item['value'])
            draw.text((page_width - margin_x - text_width(value, label_font) - 24, row_y), value, fill=primary, font=label_font)
            track_x = health_x + 24
            track_y = row_y + 38
            track_w = page_width - margin_x - health_x - 48
            draw.rounded_rectangle((track_x, track_y, track_x + track_w, track_y + 14), radius=8, fill=soft)
            fill_w = max(6, int(track_w * (item['percent'] or 0) / 100))
            draw.rounded_rectangle((track_x, track_y, track_x + fill_w, track_y + 14), radius=8, fill=colors.get(item['class'], primary_2))
            row_y += 60
        y = panel_top + 274

    def draw_donut(center_x, center_y, radius, values, colors, label=None):
        total = sum(max(0, float(value or 0)) for value in values) or 1
        start = -90
        box = (center_x - radius, center_y - radius, center_x + radius, center_y + radius)
        for value, color in zip(values, colors):
            extent = max(3, 360 * max(0, float(value or 0)) / total)
            draw.pieslice(box, start, start + extent, fill=color)
            start += extent
        inner = int(radius * 0.62)
        draw.ellipse((center_x - inner, center_y - inner, center_x + inner, center_y + inner), fill='#FFFFFF')
        if label:
            label_w = text_width(label, label_font)
            draw.text((center_x - label_w // 2, center_y - 13), label, fill=primary, font=label_font)

    def draw_profit_section():
        nonlocal y
        top = y
        gap = 18
        cards = [
            ('UTILIDAD ESTIMADA', f"${_fmt_money(context['utilidad_estimada'])}", f"Costo vendido: ${_fmt_money(context['costo_vendido'])}"),
            ('INVENTARIO ACTIVO', context['lotes_activos_total'], f"{context['stock_total_unidades']} unidades disponibles"),
            ('ALERTAS DE CADUCIDAD', context['lotes_caducos_total'] + context['lotes_proximos_total'], f"{context['lotes_caducos_total']} caducos - {context['lotes_proximos_total']} próximos"),
        ]
        card_w = (content_width - gap * 2) // 3
        for index, (label, value, detail) in enumerate(cards):
            x = margin_x + index * (card_w + gap)
            rounded_box(x, top, x + card_w, top + 148, surface, outline=line, radius=10)
            draw.text((x + 24, top + 20), label, fill=muted, font=label_font)
            draw.text((x + 24, top + 58), fit_text(value, kpi_font, card_w - 48), fill=primary, font=kpi_font)
            draw.text((x + 24, top + 108), fit_text(detail, body_font, card_w - 48), fill=primary_2, font=body_font)
            if index == 0:
                margen = max(0, min(100, int(context['margen_estimado_percent'] or 0)))
                draw_donut(x + card_w - 74, top + 76, 54, [margen, 100 - margen], [primary_2, primary_3], f'{margen}%')
        y = top + 168
    def draw_table(title, headers, rows, widths, row_height=54):
        nonlocal y
        draw_section(title)
        if not rows:
            ensure(64)
            rounded_box(margin_x, y, page_width - margin_x, y + 64, surface, outline=line, radius=14)
            draw.text((margin_x + 22, y + 20), 'Sin datos en el periodo.', fill=muted, font=body_font)
            y += 92
            return

        header_height = 52
        ensure(header_height + row_height + 28)
        x = margin_x
        rounded_box(margin_x, y, page_width - margin_x, y + header_height, surface_2, outline=line, radius=10)
        for header, width in zip(headers, widths):
            draw.text((x + 14, y + 16), fit_text(header, label_font, width - 22), fill=muted, font=label_font)
            x += width
        y += header_height

        for index, row in enumerate(rows):
            ensure(row_height + 28)
            fill = surface if index % 2 == 0 else soft
            draw.rectangle((margin_x, y, page_width - margin_x, y + row_height), fill=fill)
            draw.line((margin_x, y + row_height, page_width - margin_x, y + row_height), fill=line, width=1)
            x = margin_x
            for cell, width in zip(row, widths):
                draw_wrapped(cell, x + 14, y + 14, width - 24, table_font, ink, line_height=22, max_lines=2)
                x += width
            y += row_height
        y += 34

    def vendedor_nombre(item):
        return ' '.join(
            part for part in [
                item.get('id_usuario__nombre'),
                item.get('id_usuario__ap_pat'),
                item.get('id_usuario__ap_mat'),
            ] if part
        ) or 'Sin nombre'

    start_page()
    draw_header()
    draw_kpis()
    draw_profit_section()
    draw_bar_chart()
    finish_page()
    start_page()
    y = margin_y + 30
    draw.text((margin_x, y), 'Detalle del Reporte', fill=ink, font=title_font)
    y += 62

    med = context['medicamento_mas_vendido']
    vend = context['vendedor_del_mes']
    highlights = []
    if med:
        highlights.append([
            'Medicamento mas vendido',
            med['id_medicamento__nombre'],
            f"{med['cantidad']} uds / ${_fmt_money(med['ingresos'])}",
        ])
    if vend:
        highlights.append([
            'Vendedor destacado',
            vendedor_nombre(vend),
            f"{vend['ventas']} ventas / ${_fmt_money(vend['ingresos'])}",
        ])
    draw_table('Resumen destacado', ['Indicador', 'Nombre', 'Resultado'], highlights, [360, 620, 440], row_height=64)

    clientes_rows = [
        [
            cliente.nombre_completo(),
            cliente.telefono or '-',
            cliente.fecha_registro.strftime('%d/%m/%Y') if cliente.fecha_registro else '-',
            cliente.compras_periodo,
            f"${_fmt_money(cliente.ingresos_periodo)}",
        ]
        for cliente in context['clientes_nuevos_detalle'][:8]
    ]
    draw_table('Clientes nuevos', ['Cliente', 'Teléfono', 'Alta', 'Compras', 'Ingresos'], clientes_rows, [430, 260, 220, 180, 330])

    med_rows = [
        [
            item['id_medicamento__nombre'],
            _join_parts(item.get('id_medicamento__presentacion'), item.get('id_medicamento__tamano_presentacion')) or '-',
            item.get('id_medicamento__concentracion') or '-',
            item['cantidad'],
            f"${_fmt_money(item['ingresos'])}",
        ]
        for item in context['top_medicamentos'][:8]
    ]
    draw_table('Top medicamentos', ['Medicamento', 'Presentación', 'Concentración', 'Uds', 'Ingresos'], med_rows, [430, 320, 270, 150, 250])

    vendedor_rows = [
        [vendedor_nombre(item), item['ventas'], f"${_fmt_money(item['ingresos'])}"]
        for item in context['top_vendedores'][:8]
    ]
    draw_table('Top vendedores', ['Vendedor', 'Ventas', 'Ingresos'], vendedor_rows, [820, 240, 360])

    metodo_rows = [
        [item['id_metPag__nombre_metodo'] or 'Sin método', item['ventas'], f"${_fmt_money(item['ingresos'])}"]
        for item in context['metodos_pago']
    ]
    draw_table('Métodos de pago', ['Método', 'Ventas', 'Ingresos'], metodo_rows, [820, 240, 360])

    ventas_rows = [
        [item['dia'].strftime('%d/%m/%Y'), item['ventas'], f"${_fmt_money(item['ingresos'])}"]
        for item in context['ventas_por_dia'][:16]
    ]
    draw_table('Ventas por día', ['Día', 'Ventas', 'Ingresos'], ventas_rows, [540, 300, 580])

    finish_page()
    buffer = BytesIO()
    first, *rest = pages
    first.save(buffer, format='PDF', resolution=100.0, save_all=True, append_images=rest)
    buffer.seek(0)
    return buffer


def _lines_to_pdf_pages(lines):
    page_width, page_height = 1240, 1754
    margin_x, margin_y = 70, 70
    line_height = 34
    title_font = _font(30, bold=True)
    body_font = _font(20)
    pages = []
    image = Image.new('RGB', (page_width, page_height), 'white')
    draw = ImageDraw.Draw(image)
    y = margin_y

    for index, line in enumerate(lines):
        font = title_font if index == 0 else body_font
        if y + line_height > page_height - margin_y:
            pages.append(image)
            image = Image.new('RGB', (page_width, page_height), 'white')
            draw = ImageDraw.Draw(image)
            y = margin_y
        draw.text((margin_x, y), str(line), fill='black', font=font)
        y += 46 if index == 0 else line_height

    pages.append(image)
    return pages


def _font(size, bold=False):
    try:
        name = 'arialbd.ttf' if bold else 'arial.ttf'
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def _fmt_money(value):
    return f"{Decimal(value or 0):.2f}"


def _join_parts(*parts):
    return ' '.join(str(part).strip() for part in parts if part)


def _compact_money(value):
    amount = Decimal(value or 0)
    sign = '-' if amount < 0 else ''
    amount = abs(amount)
    if amount >= Decimal('1000000'):
        compact = amount / Decimal('1000000')
        return f"{sign}{compact:.1f}M".replace('.0M', 'M')
    if amount >= Decimal('1000'):
        compact = amount / Decimal('1000')
        return f"{sign}{compact:.1f}K".replace('.0K', 'K')
    return f"{sign}{amount:.0f}"


def _percent(value, total):
    total = Decimal(total or 0)
    if total <= 0:
        return 0
    return int((Decimal(value or 0) / total * 100).quantize(Decimal('1')))


def _ventas_por_dia_chart(items, fecha_desde, fecha_hasta):
    por_dia = {item['dia']: item for item in items}
    rango = (fecha_hasta - fecha_desde).days
    if 0 <= rango <= 31:
        días = [fecha_desde + timedelta(days=offset) for offset in range(rango + 1)]
    else:
        días = [item['dia'] for item in items]

    max_ingresos = max(
        [Decimal(por_dia.get(dia, {}).get('ingresos') or 0) for dia in días] or [Decimal('0.00')]
    )
    chart = []
    for dia in días:
        item = por_dia.get(dia, {})
        ingresos = Decimal(item.get('ingresos') or 0)
        chart.append({
            'dia': dia,
            'ventas': item.get('ventas') or 0,
            'ingresos': ingresos,
            'height': max(5, _percent(ingresos, max_ingresos)) if max_ingresos else 5,
        })
    return chart


def _parse_date(value):
    if not value:
        return None
    try:
        return timezone.datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def _parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _format_date_es(value):
    return value.strftime('%d/%m/%Y')


def _meses():
    return [
        (1, 'Enero'),
        (2, 'Febrero'),
        (3, 'Marzo'),
        (4, 'Abril'),
        (5, 'Mayo'),
        (6, 'Junio'),
        (7, 'Julio'),
        (8, 'Agosto'),
        (9, 'Septiembre'),
        (10, 'Octubre'),
        (11, 'Noviembre'),
        (12, 'Diciembre'),
    ]
