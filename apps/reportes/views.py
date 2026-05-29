import calendar
from io import BytesIO
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.medicamentos.models import Lote
from apps.usuarios.security import get_current_usuario
from apps.ventas.models import DetalleVenta, Venta


REPORT_SECTIONS = {'ventas', 'clientes', 'medicamentos', 'inventario'}


def reportes_dashboard(request):
    context = _build_report_context(request)
    return render(request, 'reportes/dashboard.html', context)


def reportes_pdf(request):
    context = _build_report_context(request)
    section = _valid_report_section(request.GET.get('section'))
    pdf_buffer = _build_report_pdf(context, section=section)
    section_slug = f"-{section}" if section else ""
    filename = (
        f"reporte-farmacia{section_slug}-{context['fecha_desde'].strftime('%Y%m%d')}"
        f"-{context['fecha_hasta'].strftime('%Y%m%d')}.pdf"
    )
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def reportes_excel(request):
    context = _build_report_context(request)
    section = _valid_report_section(request.GET.get('section'))
    context['export_section'] = section
    html = render_to_string('reportes/export_excel.html', context)
    section_slug = f"-{section}" if section else ""
    filename = (
        f"reporte-farmacia{section_slug}-{context['fecha_desde'].strftime('%Y%m%d')}"
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
    usuario_actual = get_current_usuario(request) if hasattr(request, 'session') else None
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
            date_error_message = 'Rango de fechas inválido: la fecha "Hasta" debe ser igual o posterior a "Desde".'
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
    payment_chart = _payment_chart(metodos_pago)

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
        'payment_chart': payment_chart,
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
        'generado_por': usuario_actual.nombre_completo() if usuario_actual else 'Usuario no identificado',
        'empresa_nombre': 'Farmacia Inclusiva',
        'empresa_rfc': 'No registrado',
        'empresa_domicilio': 'No registrado',
        'fecha_generacion': timezone.localtime(),
        'date_error_message': date_error_message,
        'export_query': export_query,
    }


def _fmt_money(value):
    return f"{Decimal(value or 0):.2f}"


def _join_parts(*parts):
    return ' '.join(str(part).strip() for part in parts if part)


class _SelectableReportPdf:
    def __init__(self):
        self.width = 612
        self.height = 792
        self.margin = 36
        self.content_width = self.width - (self.margin * 2)
        self.pages = []
        self.commands = []
        self.y = self.height - self.margin
        self.page_no = 0
        self.new_page()

    def new_page(self):
        if self.commands:
            self._footer()
            self.pages.append('\n'.join(self.commands))
        self.page_no += 1
        self.commands = []
        self.y = self.height - self.margin

    def _footer(self):
        self.line(self.margin, 36, self.width - self.margin, 36, color=(0.76, 0.82, 0.86))
        self.text(self.margin, 22, 'Farmacia Inclusiva', size=8, color=(0.25, 0.35, 0.42))
        self.text(self.width - self.margin - 48, 22, f'Página {self.page_no}', size=8, color=(0.25, 0.35, 0.42))

    def ensure(self, height):
        if self.y - height < 54:
            self.new_page()

    def text(self, x, y, value, size=9, bold=False, color=(0, 0, 0)):
        font = '/F2' if bold else '/F1'
        self.commands.append(
            f'{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} rg BT {font} {size} Tf {x:.2f} {y:.2f} Td ({_pdf_escape(value)}) Tj ET'
        )

    def line(self, x1, y1, x2, y2, color=(0, 0, 0), width=0.5):
        self.commands.append(
            f'{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} RG {width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S'
        )

    def rect(self, x, y, w, h, fill=None, stroke=(0.75, 0.79, 0.83), width=0.5):
        if fill:
            self.commands.append(
                f'{fill[0]:.3f} {fill[1]:.3f} {fill[2]:.3f} rg {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f'
            )
        self.commands.append(
            f'{stroke[0]:.3f} {stroke[1]:.3f} {stroke[2]:.3f} RG {width:.2f} w {x:.2f} {y:.2f} {w:.2f} {h:.2f} re S'
        )

    def title(self, value):
        self.text(self.margin, self.y - 8, value, size=20, bold=True, color=(0.02, 0.12, 0.18))
        self.text(self.margin, self.y - 26, 'Indicadores de ventas, medicamentos, clientes e inventario', size=9, color=(0.25, 0.35, 0.42))
        self.y -= 44

    def section(self, value):
        self.ensure(34)
        self.y -= 12
        self.text(self.margin, self.y, value.upper(), size=11, bold=True, color=(0.05, 0.38, 0.60))
        self.line(self.margin, self.y - 6, self.width - self.margin, self.y - 6, color=(0.75, 0.83, 0.88))
        self.y -= 20

    def two_column_facts(self, facts):
        self.ensure(112)
        row_h = 16
        left_x = self.margin
        right_x = self.margin + 285
        for index in range(0, len(facts), 2):
            y = self.y
            for x, item in ((left_x, facts[index]), (right_x, facts[index + 1] if index + 1 < len(facts) else None)):
                if not item:
                    continue
                label, value = item
                self.text(x, y, f'{label}:', size=8, bold=True)
                self.text(x + 92, y, value, size=8)
            self.y -= row_h
        self.y -= 8

    def kpi_grid(self, items):
        columns = 3
        gap = 10
        card_w = (self.content_width - gap * (columns - 1)) / columns
        card_h = 48
        for index, (label, value, detail) in enumerate(items):
            if index % columns == 0:
                self.ensure(card_h + 12)
            col = index % columns
            x = self.margin + col * (card_w + gap)
            y = self.y - card_h
            self.rect(x, y, card_w, card_h, fill=(0.95, 0.98, 1.00), stroke=(0.75, 0.86, 0.92))
            self.text(x + 8, y + 31, label.upper(), size=7, bold=True, color=(0.25, 0.35, 0.42))
            self.text(x + 8, y + 15, value, size=13, bold=True, color=(0.05, 0.38, 0.60))
            self.text(x + 8, y + 5, detail, size=7, color=(0.25, 0.35, 0.42))
            if col == columns - 1 or index == len(items) - 1:
                self.y -= card_h + 10

    def note(self, value):
        lines = _wrap_pdf_text(value, self.content_width, 8)
        self.ensure(20 + len(lines) * 11)
        self.y -= 8
        for line in lines:
            self.text(self.margin, self.y, line, size=8, color=(0.25, 0.35, 0.42))
            self.y -= 11

    def table(self, title, headers, rows, widths):
        self.section(title)
        if not rows:
            self.ensure(24)
            self.text(self.margin, self.y, 'Sin datos en el periodo.', size=8, color=(0.25, 0.35, 0.42))
            self.y -= 22
            return

        header_h = 18
        x_positions = [self.margin]
        for width in widths[:-1]:
            x_positions.append(x_positions[-1] + width)

        self.ensure(header_h + 28)
        self.rect(self.margin, self.y - header_h, sum(widths), header_h, fill=(0.86, 0.89, 0.92), stroke=(0.42, 0.48, 0.53))
        for x, header in zip(x_positions, headers):
            self.text(x + 4, self.y - 12, header, size=7, bold=True)
        self.y -= header_h

        for row_index, row in enumerate(rows):
            wrapped_cells = [
                _wrap_pdf_text(cell, widths[index] - 8, 7)
                for index, cell in enumerate(row)
            ]
            line_count = max(len(cell) for cell in wrapped_cells) if wrapped_cells else 1
            row_h = max(18, line_count * 9 + 8)
            self.ensure(row_h + 18)
            fill = (1, 1, 1) if row_index % 2 == 0 else (0.97, 0.99, 1.00)
            self.rect(self.margin, self.y - row_h, sum(widths), row_h, fill=fill, stroke=(0.82, 0.87, 0.90), width=0.35)
            for x, lines in zip(x_positions, wrapped_cells):
                text_y = self.y - 11
                for line in lines:
                    self.text(x + 4, text_y, line, size=7)
                    text_y -= 9
            self.y -= row_h
        self.y -= 8

    def to_buffer(self):
        if self.commands:
            self._footer()
            self.pages.append('\n'.join(self.commands))
            self.commands = []
        content = _build_pdf_bytes(self.pages, self.width, self.height)
        buffer = BytesIO(content)
        buffer.seek(0)
        return buffer


def _wrap_pdf_text(value, max_width, font_size):
    text = str(value if value is not None else '-')
    max_chars = max(8, int(max_width / (font_size * 0.48)))
    words = text.split()
    lines = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word[:max_chars]
    if current:
        lines.append(current)
    return lines or ['-']


def _pdf_escape(value):
    text = str(value if value is not None else '')
    text = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    return text.encode('cp1252', errors='replace').decode('cp1252')


def _build_pdf_bytes(page_streams, width, height):
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>',
    ]
    kids = []
    for index, stream in enumerate(page_streams):
        content_obj = len(objects) + 1
        page_obj = content_obj + 1
        stream_bytes = stream.encode('cp1252', errors='replace')
        objects.append(
            b'<< /Length ' + str(len(stream_bytes)).encode('ascii') + b' >>\nstream\n' + stream_bytes + b'\nendstream'
        )
        objects.append(
            (
                f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] '
                f'/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_obj} 0 R >>'
            ).encode('ascii')
        )
        kids.append(f'{page_obj} 0 R')
    objects[1] = f'<< /Type /Pages /Kids [{" ".join(kids)}] /Count {len(kids)} >>'.encode('ascii')

    output = BytesIO()
    output.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f'{number} 0 obj\n'.encode('ascii'))
        output.write(obj)
        output.write(b'\nendobj\n')
    xref = output.tell()
    output.write(f'xref\n0 {len(objects) + 1}\n'.encode('ascii'))
    output.write(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        output.write(f'{offset:010d} 00000 n \n'.encode('ascii'))
    output.write(
        (
            f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n'
            f'startxref\n{xref}\n%%EOF\n'
        ).encode('ascii')
    )
    return output.getvalue()


def _build_report_pdf(context, section=None):
    pdf = _SelectableReportPdf()
    section = _valid_report_section(section)

    def vendedor_nombre(item):
        return ' '.join(
            part for part in [
                item.get('id_usuario__nombre'),
                item.get('id_usuario__ap_pat'),
                item.get('id_usuario__ap_mat'),
            ] if part
        ) or 'Sin nombre'

    def show(name):
        return section is None or section == name

    report_names = {
        None: 'Ventas, clientes, medicamentos e inventario',
        'ventas': 'Ventas',
        'clientes': 'Clientes',
        'medicamentos': 'Medicamentos',
        'inventario': 'Inventario y caducidad',
    }

    pdf.title('Reporte de indicadores')
    pdf.two_column_facts([
        ('Empresa', context['empresa_nombre']),
        ('RFC emisor', context['empresa_rfc']),
        ('Domicilio fiscal', context['empresa_domicilio']),
        ('Reporte elaborado por', context['generado_por']),
        ('Fecha de emision', context['fecha_generacion'].strftime('%d/%m/%Y %H:%M')),
        ('Periodo', f"{context['fecha_desde'].strftime('%d/%m/%Y')} - {context['fecha_hasta'].strftime('%d/%m/%Y')}"),
        ('Tipo de reporte', report_names[section]),
        ('Formato', 'PDF con texto seleccionable'),
    ])

    if section is None:
        pdf.section('Resumen ejecutivo')
        pdf.kpi_grid([
            ('Ventas', context['total_ventas'], 'Operaciones registradas'),
            ('Ingresos', f"${_fmt_money(context['ingresos'])}", 'Total vendido'),
            ('Productos', context['productos_vendidos'], 'Unidades vendidas'),
            ('Ticket promedio', f"${_fmt_money(context['ticket_promedio'])}", 'Promedio por venta'),
            ('Utilidad estimada', f"${_fmt_money(context['utilidad_estimada'])}", f"Costo vendido: ${_fmt_money(context['costo_vendido'])}"),
            ('Compra recibida', f"${_fmt_money(context['total_compra_recibida'])}", 'Total a precio de compra'),
        ])

    if section == 'ventas':
        pdf.section('Ventas')
        pdf.kpi_grid([
            ('Ventas', context['total_ventas'], 'Operaciones registradas'),
            ('Ingresos', f"${_fmt_money(context['ingresos'])}", 'Total vendido'),
            ('Productos', context['productos_vendidos'], 'Unidades vendidas'),
            ('Ticket promedio', f"${_fmt_money(context['ticket_promedio'])}", 'Promedio por venta'),
            ('Utilidad estimada', f"${_fmt_money(context['utilidad_estimada'])}", f"Costo vendido: ${_fmt_money(context['costo_vendido'])}"),
        ])

    if show('ventas'):
        vend = context['vendedor_del_mes']
        destacados = []
        if vend:
            destacados.append(['Vendedor destacado', vendedor_nombre(vend), f"{vend['ventas']} ventas / ${_fmt_money(vend['ingresos'])}"])
        pdf.table('Indicadores de ventas', ['Indicador', 'Nombre', 'Resultado'], destacados, [180, 230, 160])
        pdf.table(
            'Ventas por dia',
            ['Dia', 'Ventas', 'Ingresos'],
            [[item['dia'].strftime('%d/%m/%Y'), item['ventas'], f"${_fmt_money(item['ingresos'])}"] for item in context['ventas_por_dia']],
            [170, 170, 230],
        )
        pdf.table(
            'Top vendedores',
            ['Vendedor', 'Ventas', 'Ingresos'],
            [[vendedor_nombre(item), item['ventas'], f"${_fmt_money(item['ingresos'])}"] for item in context['top_vendedores']],
            [300, 120, 150],
        )
        pdf.table(
            'Métodos de pago',
            ['Método', 'Ventas', 'Ingresos'],
            [[item['id_metPag__nombre_metodo'] or 'Sin metodo', item['ventas'], f"${_fmt_money(item['ingresos'])}"] for item in context['metodos_pago']],
            [300, 120, 150],
        )

    if section == 'clientes':
        pdf.section('Clientes')
        pdf.kpi_grid([
            ('Clientes nuevos', context['total_clientes_nuevos'], 'Altas en el periodo'),
            ('Con compra', context['clientes_nuevos_con_compra_total'], 'Nuevos que ya compraron'),
            ('Sin compra', context['clientes_nuevos_sin_compra_total'], 'Pendientes de primera compra'),
            ('Clientes activos', context['clientes_con_compra_total'], 'Con compra en el periodo'),
        ])

    if show('clientes'):
        pdf.table(
            'Clientes nuevos',
            ['Cliente', 'Teléfono', 'Alta', 'Compras', 'Ingresos'],
            [[cliente.nombre_completo(), cliente.telefono or '-', cliente.fecha_registro.strftime('%d/%m/%Y') if cliente.fecha_registro else '-', cliente.compras_periodo, f"${_fmt_money(cliente.ingresos_periodo)}"] for cliente in context['clientes_nuevos_detalle']],
            [200, 115, 95, 80, 80],
        )

    if section == 'medicamentos':
        pdf.section('Medicamentos')
        med = context['medicamento_mas_vendido']
        pdf.kpi_grid([
            ('Compra recibida', f"${_fmt_money(context['total_compra_recibida'])}", 'Total a precio de compra'),
            ('Unidades vendidas', context['productos_vendidos'], 'Productos vendidos'),
            ('Medicamento lider', med['cantidad'] if med else 0, 'Unidades del mas vendido'),
        ])

    if show('medicamentos'):
        med = context['medicamento_mas_vendido']
        destacados = []
        if med:
            destacados.append(['Medicamento mas vendido', med['id_medicamento__nombre'], f"{med['cantidad']} uds / ${_fmt_money(med['ingresos'])}"])
        pdf.table('Indicadores de medicamentos', ['Indicador', 'Nombre', 'Resultado'], destacados, [180, 230, 160])
        pdf.table(
            'Top medicamentos',
            ['Medicamento', 'Presentacion', 'Concentracion', 'Uds', 'Ingresos'],
            [[item['id_medicamento__nombre'], _join_parts(item.get('id_medicamento__presentacion'), item.get('id_medicamento__tamano_presentacion')) or '-', item.get('id_medicamento__concentracion') or '-', item['cantidad'], f"${_fmt_money(item['ingresos'])}"] for item in context['top_medicamentos']],
            [190, 140, 120, 50, 70],
        )

    if section == 'inventario':
        pdf.section('Inventario y caducidad')
        pdf.kpi_grid([
            ('Lotes activos', context['lotes_activos_total'], 'Disponibles'),
            ('Unidades', context['stock_total_unidades'], 'Stock disponible'),
            ('Bajo stock', context['lotes_bajo_stock_total'], 'Lotes con alerta'),
            ('Caducos', context['lotes_caducos_total'], 'Lotes activos caducos'),
            ('Próximos', context['lotes_proximos_total'], 'Por caducar'),
        ])

    if show('inventario'):
        pdf.table(
            'Inventario y caducidad',
            ['Indicador', 'Valor'],
            [
                ['Lotes activos', context['lotes_activos_total']],
                ['Unidades disponibles', context['stock_total_unidades']],
                ['Bajo stock', context['lotes_bajo_stock_total']],
                ['Sin stock', context['lotes_sin_stock_total']],
                ['Caducos', context['lotes_caducos_total']],
                ['Próximos a caducar', context['lotes_proximos_total']],
            ],
            [350, 220],
        )
        pdf.table(
            'Lotes bajo stock',
            ['Lote', 'Proveedor', 'Stock', 'Caducidad'],
            [[lote.numero_lote, lote.id_prov.nombre if lote.id_prov else '-', lote.stock_actual, lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else '-'] for lote in context['lotes_bajo_stock']],
            [180, 190, 80, 120],
        )
        pdf.table(
            'Caducidad segun periodo',
            ['Lote', 'Proveedor', 'Caducidad', 'Estado'],
            [[lote.numero_lote, lote.id_prov.nombre if lote.id_prov else '-', lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else '-', lote.alerta_periodo_estado] for lote in context['lotes_caducidad_periodo']],
            [160, 190, 100, 120],
        )

    pdf.note(
        'Este documento fue generado por el sistema de Farmacia Inclusiva. '
        'Los datos se calculan con base en ventas, clientes, lotes y medicamentos registrados para el periodo indicado.'
    )
    return pdf.to_buffer()


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


def _payment_chart(metodos_pago):
    colors = ['#1670A8', '#55b0df', '#f0a83a', '#26a269', '#e45a4f', '#8b5cf6']
    segments = []
    cursor = 0
    total_items = len(metodos_pago)

    for index, metodo in enumerate(metodos_pago):
        percent = metodo.get('porcentaje') or 0
        start = cursor
        end = 100 if index == total_items - 1 else min(100, cursor + percent)
        color = colors[index % len(colors)]
        metodo['chart_color'] = color
        segments.append(f'{color} {start}% {end}%')
        cursor = end

    return ', '.join(segments) if segments else '#d9e8f1 0% 100%'


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


def _valid_report_section(value):
    section = (value or '').strip().lower()
    return section if section in REPORT_SECTIONS else None


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
