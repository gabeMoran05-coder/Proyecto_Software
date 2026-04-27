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
    mes_filter = _parse_int(request.GET.get('mes'))
    anio_filter = _parse_int(request.GET.get('anio'))

    if mes_filter and anio_filter and 1 <= mes_filter <= 12:
        ultimo_dia = calendar.monthrange(anio_filter, mes_filter)[1]
        fecha_desde = date(anio_filter, mes_filter, 1)
        fecha_hasta = date(anio_filter, mes_filter, ultimo_dia)
    else:
        fecha_desde = _parse_date(request.GET.get('desde')) or inicio_mes
        fecha_hasta = _parse_date(request.GET.get('hasta')) or hoy
        mes_filter = fecha_desde.month
        anio_filter = fecha_desde.year

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
    lotes_recibidos = Lote.objects.filter(
        fecha_ingreso__date__gte=fecha_desde,
        fecha_ingreso__date__lte=fecha_hasta,
    )
    total_compra_recibida = sum(
        (lote.precio_compra or Decimal('0.00')) * (lote.stock_actual or 0)
        for lote in lotes_recibidos
    )

    top_medicamentos = list(
        detalles.values(
            'id_medicamento__nombre',
            'id_medicamento__presentacion',
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

    ventas_por_dia = list(
        ventas.annotate(dia=TruncDate('fecha_venta'))
        .values('dia')
        .annotate(ventas=Count('id_ventas'), ingresos=Sum('total_venta'))
        .order_by('dia')
    )

    lotes_bajo_stock = Lote.objects.select_related('id_prov').prefetch_related('medicamento_set').filter(
        activo=True,
        oculto_por_caducidad=False,
        stock_actual__lte=20,
    ).order_by('stock_actual', 'fecha_caducidad')[:8]

    lotes_por_caducar = [
        lote for lote in Lote.objects.select_related('id_prov').prefetch_related('medicamento_set').filter(
            activo=True,
            oculto_por_caducidad=False,
            fecha_caducidad__isnull=False,
            fecha_caducidad__gte=hoy,
            fecha_caducidad__lte=hoy + timedelta(days=90),
        ).order_by('fecha_caducidad')[:8]
    ]

    export_query = ''
    if request.GET.get('desde'):
        export_query += f"?desde={request.GET.get('desde')}"
        if request.GET.get('hasta'):
            export_query += f"&hasta={request.GET.get('hasta')}"
    elif request.GET.get('mes') and request.GET.get('anio'):
        export_query = f"?mes={request.GET.get('mes')}&anio={request.GET.get('anio')}"
    else:
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
        'total_compra_recibida': total_compra_recibida,
        'medicamento_mas_vendido': top_medicamentos[0] if top_medicamentos else None,
        'vendedor_del_mes': top_vendedores[0] if top_vendedores else None,
        'top_medicamentos': top_medicamentos,
        'top_vendedores': top_vendedores,
        'metodos_pago': metodos_pago,
        'ventas_por_dia': ventas_por_dia,
        'lotes_bajo_stock': lotes_bajo_stock,
        'lotes_por_caducar': lotes_por_caducar,
        'mes_filter': mes_filter,
        'anio_filter': anio_filter,
        'meses': _meses(),
        'anios': range(hoy.year - 5, hoy.year + 2),
        'export_query': export_query,
    }


def _build_report_pdf(context):
    lines = [
        'Reporte general de farmacia',
        f"Periodo: {context['fecha_desde'].strftime('%d/%m/%Y')} - {context['fecha_hasta'].strftime('%d/%m/%Y')}",
        '',
        f"Ventas: {context['total_ventas']}",
        f"Ingresos: ${_fmt_money(context['ingresos'])}",
        f"Productos vendidos: {context['productos_vendidos']}",
        f"Ticket promedio: ${_fmt_money(context['ticket_promedio'])}",
        f"Compra recibida: ${_fmt_money(context['total_compra_recibida'])}",
        '',
        'Medicamento mas vendido:',
    ]
    if context['medicamento_mas_vendido']:
        med = context['medicamento_mas_vendido']
        lines.extend([
            f"- {med['id_medicamento__nombre']}",
            f"  Cantidad: {med['cantidad']} | Ingresos: ${_fmt_money(med['ingresos'])}",
        ])
    else:
        lines.append('- Sin datos.')

    lines.extend(['', 'Vendedor del mes:'])
    if context['vendedor_del_mes']:
        vend = context['vendedor_del_mes']
        nombre = ' '.join(
            part for part in [
                vend.get('id_usuario__nombre'),
                vend.get('id_usuario__ap_pat'),
                vend.get('id_usuario__ap_mat'),
            ] if part
        )
        lines.extend([
            f"- {nombre}",
            f"  Ventas: {vend['ventas']} | Ingresos: ${_fmt_money(vend['ingresos'])}",
        ])
    else:
        lines.append('- Sin datos.')

    lines.extend(['', 'Top medicamentos:'])
    if context['top_medicamentos']:
        for item in context['top_medicamentos'][:8]:
            lines.append(
                f"- {item['id_medicamento__nombre']} | {item['cantidad']} uds | ${_fmt_money(item['ingresos'])}"
            )
    else:
        lines.append('- Sin datos.')

    lines.extend(['', 'Top vendedores:'])
    if context['top_vendedores']:
        for item in context['top_vendedores'][:8]:
            nombre = ' '.join(
                part for part in [
                    item.get('id_usuario__nombre'),
                    item.get('id_usuario__ap_pat'),
                    item.get('id_usuario__ap_mat'),
                ] if part
            )
            lines.append(f"- {nombre} | {item['ventas']} ventas | ${_fmt_money(item['ingresos'])}")
    else:
        lines.append('- Sin datos.')

    lines.extend(['', 'Metodos de pago:'])
    if context['metodos_pago']:
        for item in context['metodos_pago']:
            lines.append(f"- {item['id_metPag__nombre_metodo']} | {item['ventas']} ventas | ${_fmt_money(item['ingresos'])}")
    else:
        lines.append('- Sin datos.')

    lines.extend(['', 'Ventas por dia:'])
    if context['ventas_por_dia']:
        for item in context['ventas_por_dia']:
            lines.append(
                f"- {item['dia'].strftime('%d/%m/%Y')} | {item['ventas']} ventas | ${_fmt_money(item['ingresos'])}"
            )
    else:
        lines.append('- Sin datos.')

    pages = _lines_to_pdf_pages(lines)
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
