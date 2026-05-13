from datetime import timedelta

from celery import shared_task
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.reportes.views import _build_report_context, _build_report_pdf
from apps.usuarios.email_utils import send_admin_email
from apps.usuarios.notifications import crear_notificacion_sistema


def _money(value):
    return f'${value or 0:.2f}'


def _nombre_vendedor(item):
    if not item:
        return 'Sin ventas'
    partes = [
        item.get('id_usuario__nombre'),
        item.get('id_usuario__ap_pat'),
        item.get('id_usuario__ap_mat'),
    ]
    return ' '.join(parte for parte in partes if parte) or 'Sin vendedor'


def _period_request(fecha_desde, fecha_hasta):
    factory = RequestFactory()
    return factory.get(
        '/reportes/',
        {
            'desde': fecha_desde.isoformat(),
            'hasta': fecha_hasta.isoformat(),
        },
    )


def _report_context(fecha_desde, fecha_hasta):
    return _build_report_context(_period_request(fecha_desde, fecha_hasta))


def _periodo_archivo(prefix, fecha_desde, fecha_hasta):
    return f'{prefix}-{fecha_desde:%Y%m%d}-{fecha_hasta:%Y%m%d}'


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
)
def enviar_resumen_ventas_diario_task(self):
    hoy = timezone.localdate()
    context = _report_context(hoy, hoy)
    vendedor = context.get('vendedor_del_mes')
    vendedor_nombre = _nombre_vendedor(vendedor)
    vendedor_ventas = vendedor.get('ventas') if vendedor else 0
    vendedor_ingresos = vendedor.get('ingresos') if vendedor else 0

    body = (
        f'Resumen de ventas del {hoy:%d/%m/%Y}\n\n'
        f"Ventas: {context['total_ventas']}\n"
        f"Ingresos: {_money(context['ingresos'])}\n"
        f"Productos vendidos: {context['productos_vendidos']}\n"
        f'Vendedor destacado: {vendedor_nombre} ({vendedor_ventas} venta(s), {_money(vendedor_ingresos)})\n'
    )
    html = (
        '<h2>Resumen diario de ventas</h2>'
        f'<p>Periodo: {hoy:%d/%m/%Y}</p>'
        '<ul>'
        f"<li><strong>Ventas:</strong> {context['total_ventas']}</li>"
        f"<li><strong>Ingresos:</strong> {_money(context['ingresos'])}</li>"
        f"<li><strong>Productos vendidos:</strong> {context['productos_vendidos']}</li>"
        f'<li><strong>Vendedor destacado:</strong> {vendedor_nombre} ({vendedor_ventas} venta(s), {_money(vendedor_ingresos)})</li>'
        '</ul>'
    )
    emails = send_admin_email(
        f'Farmacia Inclusiva - resumen diario {hoy:%d/%m/%Y}',
        body,
        html,
    )
    crear_notificacion_sistema(
        clave=f'ventas.resumen_diario.{hoy:%Y%m%d}',
        titulo='Resumen diario de ventas',
        mensaje=f"{context['total_ventas']} venta(s) · {_money(context['ingresos'])}",
        categoria='Ventas',
        nivel='success' if context['total_ventas'] else 'info',
        url=reverse('reportes_dashboard') + f"?desde={hoy:%Y-%m-%d}&hasta={hoy:%Y-%m-%d}",
    )
    return {'ventas': context['total_ventas'], 'emails': emails}


def _enviar_reporte_periodico(fecha_desde, fecha_hasta, etiqueta):
    context = _report_context(fecha_desde, fecha_hasta)
    base_filename = _periodo_archivo('reporte-farmacia', fecha_desde, fecha_hasta)
    pdf_content = _build_report_pdf(context).getvalue()
    excel_content = render_to_string('reportes/export_excel.html', context).encode('utf-8')

    vendedor = context.get('vendedor_del_mes')
    body = (
        f'Reporte {etiqueta} de Farmacia Inclusiva\n\n'
        f'Periodo: {fecha_desde:%d/%m/%Y} - {fecha_hasta:%d/%m/%Y}\n'
        f"Ventas: {context['total_ventas']}\n"
        f"Ingresos: {_money(context['ingresos'])}\n"
        f"Productos vendidos: {context['productos_vendidos']}\n"
        f'Vendedor destacado: {_nombre_vendedor(vendedor)}\n\n'
        'Se adjunta el reporte en PDF y Excel.'
    )
    html = (
        f'<h2>Reporte {etiqueta}</h2>'
        f'<p>Periodo: {fecha_desde:%d/%m/%Y} - {fecha_hasta:%d/%m/%Y}</p>'
        '<ul>'
        f"<li><strong>Ventas:</strong> {context['total_ventas']}</li>"
        f"<li><strong>Ingresos:</strong> {_money(context['ingresos'])}</li>"
        f"<li><strong>Productos vendidos:</strong> {context['productos_vendidos']}</li>"
        f'<li><strong>Vendedor destacado:</strong> {_nombre_vendedor(vendedor)}</li>'
        '</ul>'
        '<p>Se adjunta el reporte en PDF y Excel.</p>'
    )
    emails = send_admin_email(
        f'Farmacia Inclusiva - reporte {etiqueta} {fecha_desde:%d/%m/%Y} al {fecha_hasta:%d/%m/%Y}',
        body,
        html,
        attachments=[
            (f'{base_filename}.pdf', pdf_content, 'application/pdf'),
            (f'{base_filename}.xls', excel_content, 'application/vnd.ms-excel'),
        ],
    )
    crear_notificacion_sistema(
        clave=f'reportes.{etiqueta}.{fecha_desde:%Y%m%d}.{fecha_hasta:%Y%m%d}',
        titulo=f'Reporte {etiqueta} generado',
        mensaje=f"{context['total_ventas']} venta(s) · {_money(context['ingresos'])} · PDF/Excel enviado",
        categoria='Reportes',
        nivel='success',
        url=reverse('reportes_dashboard') + f"?desde={fecha_desde:%Y-%m-%d}&hasta={fecha_hasta:%Y-%m-%d}",
    )
    return {
        'periodo': etiqueta,
        'desde': fecha_desde.isoformat(),
        'hasta': fecha_hasta.isoformat(),
        'ventas': context['total_ventas'],
        'emails': emails,
    }


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
)
def enviar_reporte_semanal_task(self):
    hoy = timezone.localdate()
    inicio_semana_actual = hoy - timedelta(days=hoy.weekday())
    fecha_desde = inicio_semana_actual - timedelta(days=7)
    fecha_hasta = inicio_semana_actual - timedelta(days=1)
    return _enviar_reporte_periodico(fecha_desde, fecha_hasta, 'semanal')


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
)
def enviar_reporte_mensual_task(self):
    hoy = timezone.localdate()
    primer_dia_mes_actual = hoy.replace(day=1)
    fecha_hasta = primer_dia_mes_actual - timedelta(days=1)
    fecha_desde = fecha_hasta.replace(day=1)
    return _enviar_reporte_periodico(fecha_desde, fecha_hasta, 'mensual')
