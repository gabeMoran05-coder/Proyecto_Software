import calendar
from datetime import timedelta

from celery import shared_task
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.reportes.views import _build_report_context, _build_report_pdf
from apps.usuarios.models import AutomatizacionCorreo, Usuario
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


def _destinatarios_automatizacion(automatizacion):
    email = automatizacion.destinatario_email() if automatizacion else ''
    return [email] if email else []


def _enviar_resumen_ventas_diario(automatizacion=None):
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
        recipients=_destinatarios_automatizacion(automatizacion),
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


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
)
def enviar_resumen_ventas_diario_task(self):
    return _enviar_resumen_ventas_diario()


def _seccion_label(seccion):
    labels = {
        None: 'general',
        'ventas': 'ventas',
        'clientes': 'clientes',
        'medicamentos': 'medicamentos',
        'inventario': 'inventario y caducidad',
    }
    return labels.get(seccion, 'general')


def _enviar_reporte_periodico(fecha_desde, fecha_hasta, etiqueta, seccion=None, automatizacion=None):
    context = _report_context(fecha_desde, fecha_hasta)
    seccion_slug = seccion or 'general'
    seccion_nombre = _seccion_label(seccion)
    base_filename = _periodo_archivo(f'reporte-farmacia-{seccion_slug}', fecha_desde, fecha_hasta)
    pdf_content = _build_report_pdf(context, section=seccion).getvalue()
    excel_context = context.copy()
    excel_context['export_section'] = seccion
    excel_content = render_to_string('reportes/export_excel.html', excel_context).encode('utf-8')

    vendedor = context.get('vendedor_del_mes')
    body = (
        f'Reporte {etiqueta} de {seccion_nombre} de Farmacia Inclusiva\n\n'
        f'Periodo: {fecha_desde:%d/%m/%Y} - {fecha_hasta:%d/%m/%Y}\n'
        f"Ventas: {context['total_ventas']}\n"
        f"Ingresos: {_money(context['ingresos'])}\n"
        f"Productos vendidos: {context['productos_vendidos']}\n"
        f'Vendedor destacado: {_nombre_vendedor(vendedor)}\n\n'
        'Se adjunta el reporte en PDF y Excel.'
    )
    html = (
        f'<h2>Reporte {etiqueta} de {seccion_nombre}</h2>'
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
        f'Farmacia Inclusiva - reporte {etiqueta} {seccion_nombre} {fecha_desde:%d/%m/%Y} al {fecha_hasta:%d/%m/%Y}',
        body,
        html,
        attachments=[
            (f'{base_filename}.pdf', pdf_content, 'application/pdf'),
            (f'{base_filename}.xls', excel_content, 'application/vnd.ms-excel'),
        ],
        recipients=_destinatarios_automatizacion(automatizacion),
    )
    crear_notificacion_sistema(
        clave=f'reportes.{seccion_slug}.{etiqueta}.{fecha_desde:%Y%m%d}.{fecha_hasta:%Y%m%d}',
        titulo=f'Reporte {etiqueta} de {seccion_nombre} generado',
        mensaje=f"{context['total_ventas']} venta(s) · {_money(context['ingresos'])} · PDF/Excel enviado",
        categoria='Reportes',
        nivel='success',
        url=reverse('reportes_dashboard') + f"?desde={fecha_desde:%Y-%m-%d}&hasta={fecha_hasta:%Y-%m-%d}",
    )
    return {
        'periodo': etiqueta,
        'seccion': seccion_slug,
        'desde': fecha_desde.isoformat(),
        'hasta': fecha_hasta.isoformat(),
        'ventas': context['total_ventas'],
        'emails': emails,
    }


def _enviar_reporte_semanal(seccion=None, automatizacion=None):
    hoy = timezone.localdate()
    inicio_semana_actual = hoy - timedelta(days=hoy.weekday())
    fecha_desde = inicio_semana_actual - timedelta(days=7)
    fecha_hasta = inicio_semana_actual - timedelta(days=1)
    return _enviar_reporte_periodico(fecha_desde, fecha_hasta, 'semanal', seccion=seccion, automatizacion=automatizacion)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
)
def enviar_reporte_semanal_task(self):
    return _enviar_reporte_semanal()


def _enviar_reporte_mensual(seccion=None, automatizacion=None):
    hoy = timezone.localdate()
    primer_dia_mes_actual = hoy.replace(day=1)
    fecha_hasta = primer_dia_mes_actual - timedelta(days=1)
    fecha_desde = fecha_hasta.replace(day=1)
    return _enviar_reporte_periodico(fecha_desde, fecha_hasta, 'mensual', seccion=seccion, automatizacion=automatizacion)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
)
def enviar_reporte_mensual_task(self):
    return _enviar_reporte_mensual()


def _automatizacion_debe_ejecutarse(automatizacion, ahora):
    hoy = ahora.date()
    if automatizacion.ultimo_envio == hoy:
        return False
    if ahora.time().replace(second=0, microsecond=0) < automatizacion.hora_envio:
        return False
    if automatizacion.tarea == AutomatizacionCorreo.TAREA_RESUMEN_DIARIO:
        return True
    if automatizacion.tarea == AutomatizacionCorreo.TAREA_REPORTE_SEMANAL:
        return hoy.weekday() == automatizacion.dia_semana
    if automatizacion.tarea == AutomatizacionCorreo.TAREA_REPORTE_MENSUAL:
        ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
        return hoy.day == min(automatizacion.dia_mes, ultimo_dia)
    return False


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
)
def ejecutar_automatizaciones_correo_task(self):
    for usuario in Usuario.objects.filter(
        activo=True,
        rol__in=[Usuario.ROL_ADMIN, Usuario.ROL_ADMINISTRADOR],
        email__isnull=False,
    ).exclude(email=''):
        AutomatizacionCorreo.ensure_defaults(usuario)
    ahora = timezone.localtime()
    resultados = []

    for automatizacion in AutomatizacionCorreo.objects.select_related('id_usuario').filter(
        activa=True,
        id_usuario__activo=True,
    ).exclude(id_usuario__email='').order_by('id_automatizacion'):
        if not _automatizacion_debe_ejecutarse(automatizacion, ahora):
            continue

        if automatizacion.tarea == AutomatizacionCorreo.TAREA_RESUMEN_DIARIO:
            resultado = _enviar_resumen_ventas_diario(automatizacion)
        elif automatizacion.tarea == AutomatizacionCorreo.TAREA_REPORTE_SEMANAL:
            resultado = _enviar_reporte_semanal(automatizacion.seccion_pdf, automatizacion)
        elif automatizacion.tarea == AutomatizacionCorreo.TAREA_REPORTE_MENSUAL:
            resultado = _enviar_reporte_mensual(automatizacion.seccion_pdf, automatizacion)
        else:
            continue

        automatizacion.ultimo_envio = ahora.date()
        automatizacion.save(update_fields=['ultimo_envio', 'fecha_actualizacion'])
        resultados.append({'clave': automatizacion.clave, 'resultado': resultado})

    return resultados
