from django.core.paginator import Paginator
from django.db.models import F, Q, Sum
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from datetime import time, timedelta
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.dateparse import parse_date

from apps.clientes.models import Cliente
from apps.medicamentos.models import ConfiguracionInventario, Lote, Medicamento, MovimientoInventario
from apps.ventas.models import DetalleVenta, Venta
from .forms import LoginForm, UsuarioForm
from .email_utils import usuario_email
from .models import AuditoriaEvento, AutomatizacionCorreo, NotificacionSistema, NotificacionSistemaDescartada, Usuario
from .security import SESSION_USER_ID, first_allowed_path, get_current_usuario


def _query_params_without_page(request):
    params = request.GET.copy()
    params.pop('page', None)
    encoded = params.urlencode()
    return f'&{encoded}' if encoded else ''


def _safe_reverse_url(name, *args):
    try:
        from django.urls import reverse

        return reverse(name, args=args)
    except Exception:
        return ''


def _actividad_movimiento_item(movimiento):
    medicamento = movimiento.id_medicamento
    if not medicamento and movimiento.id_lote_id:
        medicamento = movimiento.id_lote.medicamento_set.first()

    lote = movimiento.id_lote
    cantidad = movimiento.cantidad_kardex
    stock_despues = movimiento.stock_despues_kardex
    stock = f'{movimiento.stock_antes} -> {stock_despues}'
    titulo = movimiento.get_tipo_display()
    subtitulo = medicamento.nombre if medicamento else 'Medicamento no especificado'
    if lote:
        subtitulo = f'{subtitulo} · Lote {lote.numero_lote}'

    return {
        'fecha': movimiento.fecha,
        'fuente': 'Inventario',
        'fuente_key': 'inventario',
        'nivel': 'danger' if movimiento.tipo == MovimientoInventario.TIPO_OCULTAMIENTO else 'info',
        'titulo': f'{titulo} · {cantidad}',
        'subtitulo': subtitulo,
        'detalle': movimiento.notas or movimiento.get_motivo_display(),
        'referencia': movimiento.referencia or 'Kardex',
        'usuario': movimiento.id_usuario.nombre_completo() if movimiento.id_usuario else 'Sistema',
        'url': _safe_reverse_url('lote_detail', lote.pk) if lote else '',
        'cantidad': cantidad,
        'stock': stock,
    }


def _actividad_auditoria_item(evento):
    return {
        'fecha': evento.fecha,
        'fuente': 'Auditoria',
        'fuente_key': 'auditoria',
        'nivel': evento.nivel,
        'titulo': evento.accion,
        'subtitulo': evento.modulo,
        'detalle': evento.descripcion or evento.motivo or evento.objeto_tipo,
        'referencia': evento.objeto_id or evento.objeto_tipo or 'Evento',
        'usuario': evento.id_usuario.nombre_completo() if evento.id_usuario else 'Sistema',
        'url': evento.url,
        'cantidad': '',
        'stock': '',
    }


def home_redirect(request):
    usuario_id = request.session.get(SESSION_USER_ID)
    if not usuario_id:
        return redirect('usuario_login')
    usuario = get_object_or_404(Usuario, pk=usuario_id)
    return redirect(first_allowed_path(usuario))


def inicio_dashboard(request):
    usuario = get_current_usuario(request)
    if not usuario:
        return redirect('usuario_login')

    hoy = timezone.localdate()

    ventas_hoy = Venta.objects.filter(fecha_venta__date=hoy)
    total_ventas_hoy = ventas_hoy.count()
    ingresos_hoy = ventas_hoy.aggregate(total=Sum('total_venta'))['total'] or 0
    productos_hoy = DetalleVenta.objects.filter(
        id_ventas__fecha_venta__date=hoy,
    ).aggregate(total=Sum('cantidad'))['total'] or 0

    medicamentos_bajo_stock = Medicamento.objects.filter(
        id_lote__activo=True,
        id_lote__oculto_por_caducidad=False,
        id_lote__stock_actual__lt=F('stock_minimo'),
    ).select_related('id_lote').order_by('id_lote__stock_actual')[:6]
    bajo_stock_total = Medicamento.objects.filter(
        id_lote__activo=True,
        id_lote__oculto_por_caducidad=False,
        id_lote__stock_actual__lt=F('stock_minimo'),
    ).count()

    lotes_caducos = Lote.objects.filter(
        activo=True,
        oculto_por_caducidad=False,
        fecha_caducidad__lt=hoy,
    ).order_by('fecha_caducidad')
    lotes_proximos = Lote.objects.filter(
        activo=True,
        oculto_por_caducidad=False,
        fecha_caducidad__gte=hoy,
    ).prefetch_related('medicamento_set').order_by('fecha_caducidad')
    lotes_proximos = [lote for lote in lotes_proximos if lote.estado_caducidad == Lote.CADUCIDAD_AMARILLO]
    caducidades_total = lotes_caducos.count() + len(lotes_proximos)

    alertas_sistema = NotificacionSistema.objects.filter(activa=True).order_by('-fecha_actualizacion')[:5]
    movimientos_recientes = MovimientoInventario.objects.select_related(
        'id_lote',
        'id_medicamento',
        'id_usuario',
    ).order_by('-fecha')[:6]
    ventas_recientes_hoy = ventas_hoy.select_related(
        'id_cliente',
        'id_metPag',
        'id_usuario',
    ).order_by('-fecha_venta')[:5]
    auditoria_reciente = AuditoriaEvento.objects.select_related('id_usuario').order_by('-fecha')[:5]

    tareas = []
    if bajo_stock_total:
        tareas.append({
            'titulo': 'Revisar stock bajo',
            'detalle': f'{bajo_stock_total} lote(s) por debajo del mínimo del medicamento',
            'url': '/medicamentos/lotes/',
            'nivel': 'warning',
        })
    if lotes_caducos.count():
        tareas.append({
            'titulo': 'Ocultar o retirar lotes caducos',
            'detalle': f'{lotes_caducos.count()} lote(s) vencidos',
            'url': '/medicamentos/lotes/?caducidad=rojo',
            'nivel': 'danger',
        })
    if len(lotes_proximos):
        tareas.append({
            'titulo': 'Dar salida a próximos a caducar',
            'detalle': f'{len(lotes_proximos)} lote(s) vencen según su criterio personalizado',
            'url': '/medicamentos/lotes/?caducidad=amarillo',
            'nivel': 'warning',
        })
    if not tareas:
        tareas.append({
            'titulo': 'Operación estable',
            'detalle': 'No hay tareas críticas pendientes por ahora',
            'url': '',
            'nivel': 'success',
        })

    automatizaciones_activas = AutomatizacionCorreo.objects.filter(activa=True).count()
    integraciones = [
        ('Correo/Gmail', bool(getattr(settings, 'EMAIL_HOST', ''))),
        ('WhatsApp', bool(getattr(settings, 'WHATSAPP_ACCESS_TOKEN', ''))),
        ('Celery', bool(getattr(settings, 'CELERY_BROKER_URL', ''))),
        ('Reportes automáticos', automatizaciones_activas > 0),
    ]

    context = {
        'hoy': hoy,
        'total_ventas_hoy': total_ventas_hoy,
        'ingresos_hoy': ingresos_hoy,
        'productos_hoy': productos_hoy,
        'bajo_stock_total': bajo_stock_total,
        'caducidades_total': caducidades_total,
        'alertas_total': NotificacionSistema.objects.filter(activa=True).count(),
        'clientes_total': Cliente.objects.count(),
        'medicamentos_bajo_stock': medicamentos_bajo_stock,
        'lotes_caducos': lotes_caducos[:4],
        'lotes_proximos': lotes_proximos[:4],
        'alertas_sistema': alertas_sistema,
        'movimientos_recientes': movimientos_recientes,
        'ventas_recientes_hoy': ventas_recientes_hoy,
        'auditoria_reciente': auditoria_reciente,
        'tareas': tareas,
        'integraciones': integraciones,
    }
    return render(request, 'usuarios/inicio.html', context)


def actividad_reciente(request):
    usuario = get_current_usuario(request)
    if not usuario:
        return redirect('usuario_login')
    if usuario.rol_normalizado() == Usuario.ROL_CAJERO and not usuario.es_admin():
        return redirect(first_allowed_path(usuario))

    hoy = timezone.localdate()
    fuente_filter = request.GET.get('fuente', '').strip()
    movimiento_filter = request.GET.get('movimiento', '').strip()
    usuario_filter = request.GET.get('usuario', '').strip()
    busqueda = request.GET.get('q', '').strip()
    fecha_desde_raw = request.GET.get('fecha_desde', '').strip()
    fecha_hasta_raw = request.GET.get('fecha_hasta', '').strip()
    fecha_desde = parse_date(fecha_desde_raw) if fecha_desde_raw else None
    fecha_hasta = parse_date(fecha_hasta_raw) if fecha_hasta_raw else None

    date_error_message = ''
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        date_error_message = 'La fecha "Desde" no puede ser posterior a la fecha "Hasta".'
    elif (fecha_desde and fecha_desde > hoy) or (fecha_hasta and fecha_hasta > hoy):
        date_error_message = 'No se pueden consultar actividades con fechas futuras.'

    movimientos = MovimientoInventario.objects.select_related(
        'id_lote',
        'id_medicamento',
        'id_usuario',
    ).prefetch_related(
        'id_lote__medicamento_set',
    )
    auditorias = AuditoriaEvento.objects.select_related('id_usuario')

    if not date_error_message:
        if fecha_desde:
            movimientos = movimientos.filter(fecha__date__gte=fecha_desde)
            auditorias = auditorias.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            movimientos = movimientos.filter(fecha__date__lte=fecha_hasta)
            auditorias = auditorias.filter(fecha__date__lte=fecha_hasta)

    if usuario_filter.isdigit():
        movimientos = movimientos.filter(id_usuario_id=usuario_filter)
        auditorias = auditorias.filter(id_usuario_id=usuario_filter)

    if movimiento_filter:
        movimientos = movimientos.filter(tipo=movimiento_filter)

    if busqueda:
        movimientos = movimientos.filter(
            Q(id_lote__numero_lote__icontains=busqueda)
            | Q(id_lote__medicamento__nombre__icontains=busqueda)
            | Q(id_medicamento__nombre__icontains=busqueda)
            | Q(referencia__icontains=busqueda)
            | Q(notas__icontains=busqueda)
            | Q(motivo__icontains=busqueda)
        ).distinct()
        auditorias = auditorias.filter(
            Q(accion__icontains=busqueda)
            | Q(modulo__icontains=busqueda)
            | Q(objeto_tipo__icontains=busqueda)
            | Q(objeto_id__icontains=busqueda)
            | Q(descripcion__icontains=busqueda)
            | Q(motivo__icontains=busqueda)
        )

    total_movimientos = movimientos.count()
    total_auditorias = auditorias.count()

    eventos = []
    if fuente_filter in ('', 'inventario'):
        eventos.extend(_actividad_movimiento_item(movimiento) for movimiento in movimientos[:250])
    if fuente_filter in ('', 'auditoria'):
        eventos.extend(_actividad_auditoria_item(evento) for evento in auditorias[:250])

    eventos.sort(key=lambda item: item['fecha'], reverse=True)
    paginator = Paginator(eventos, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'eventos': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'query_params': _query_params_without_page(request),
        'usuarios': Usuario.objects.filter(activo=True).order_by('nombre', 'ap_pat', 'usuario'),
        'movimiento_tipos': MovimientoInventario.TIPO_CHOICES,
        'fuente_filter': fuente_filter,
        'movimiento_filter': movimiento_filter,
        'usuario_filter': usuario_filter,
        'busqueda': busqueda,
        'fecha_desde': fecha_desde_raw,
        'fecha_hasta': fecha_hasta_raw,
        'fecha_maxima': hoy.isoformat(),
        'total_eventos': len(eventos),
        'total_movimientos': total_movimientos,
        'total_auditorias': total_auditorias,
        'date_error_message': date_error_message,
    }
    return render(request, 'usuarios/actividad.html', context)


def usuario_login(request):
    form = LoginForm(request.POST or None)
    next_url = request.GET.get('next') or request.POST.get('next') or ''

    if request.method == 'POST' and form.is_valid():
        usuario_key = form.cleaned_data['usuario'].strip()
        password = form.cleaned_data['password']

        try:
            usuario = Usuario.objects.get(usuario=usuario_key)
        except Usuario.DoesNotExist:
            usuario = None

        if usuario and not usuario.activo:
            messages.warning(request, 'Este usuario esta inhabilitado. Solicita acceso al administrador.')
        elif usuario and usuario.check_password(password):
            request.session[SESSION_USER_ID] = usuario.pk
            usuario.ultima_conexion = timezone.now()
            usuario.save(update_fields=['ultima_conexion'])
            return redirect(next_url or first_allowed_path(usuario))
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'usuarios/login.html', {
        'form': form,
        'next': next_url,
    })


def usuario_logout(request):
    request.session.pop(SESSION_USER_ID, None)
    messages.success(request, 'Sesion cerrada correctamente.')
    return redirect('usuario_login')


def configuracion_cuenta(request):
    usuario = get_current_usuario(request)
    if not usuario or not usuario.es_admin():
        return redirect(first_allowed_path(usuario))

    AutomatizacionCorreo.ensure_defaults(usuario)
    automatizaciones = list(AutomatizacionCorreo.objects.filter(id_usuario=usuario))
    configuracion_inventario = ConfiguracionInventario.obtener()

    if request.method == 'POST':
        dias_revision_raw = request.POST.get('caducidad_dias_revision', '').strip()
        hora_retiro_raw = request.POST.get('caducidad_hora_retiro', '').strip()
        if dias_revision_raw.isdigit():
            configuracion_inventario.dias_revision_caducidad = max(0, min(30, int(dias_revision_raw)))
        try:
            hour, minute = [int(part) for part in hora_retiro_raw.split(':', 1)]
            configuracion_inventario.hora_retiro_caducidad = time(hour, minute)
        except (TypeError, ValueError):
            pass
        configuracion_inventario.save(update_fields=[
            'dias_revision_caducidad',
            'hora_retiro_caducidad',
            'fecha_actualizacion',
        ])

        for automatizacion in automatizaciones:
            prefix = f'automatizacion_{automatizacion.pk}'
            valores_originales = (
                automatizacion.activa,
                automatizacion.hora_envio,
                automatizacion.dia_semana,
                automatizacion.dia_mes,
            )
            activa = request.POST.get(f'{prefix}_activa') == 'on'
            hora_raw = request.POST.get(f'{prefix}_hora', '').strip()
            dia_semana_raw = request.POST.get(f'{prefix}_dia_semana', '').strip()
            dia_mes_raw = request.POST.get(f'{prefix}_dia_mes', '').strip()

            try:
                hour, minute = [int(part) for part in hora_raw.split(':', 1)]
                automatizacion.hora_envio = time(hour, minute)
            except (TypeError, ValueError):
                pass

            if dia_semana_raw.isdigit():
                automatizacion.dia_semana = max(0, min(6, int(dia_semana_raw)))
            if dia_mes_raw.isdigit():
                automatizacion.dia_mes = max(1, min(31, int(dia_mes_raw)))

            automatizacion.activa = activa
            valores_nuevos = (
                automatizacion.activa,
                automatizacion.hora_envio,
                automatizacion.dia_semana,
                automatizacion.dia_mes,
            )
            update_fields = [
                'activa',
                'hora_envio',
                'dia_semana',
                'dia_mes',
                'fecha_actualizacion',
            ]
            if valores_nuevos != valores_originales:
                automatizacion.ultimo_envio = None
                update_fields.append('ultimo_envio')
            automatizacion.save(update_fields=[
                *update_fields,
            ])

        messages.success(request, 'Configuración de automatizaciones actualizada.')
        return redirect('usuario_configuracion')

    tab_labels = {
        'resumen': 'Resumen diario',
        AutomatizacionCorreo.SECCION_GENERAL: 'General',
        AutomatizacionCorreo.SECCION_VENTAS: 'Ventas',
        AutomatizacionCorreo.SECCION_CLIENTES: 'Clientes',
        AutomatizacionCorreo.SECCION_MEDICAMENTOS: 'Medicamentos',
        AutomatizacionCorreo.SECCION_INVENTARIO: 'Inventario',
    }
    tabs = []
    for key, label in tab_labels.items():
        items = [automatizacion for automatizacion in automatizaciones if automatizacion.tab_key == key]
        if items:
            tabs.append({'key': key, 'label': label, 'automatizaciones': items})

    return render(request, 'usuarios/configuracion.html', {
        'tabs': tabs,
        'dias_semana': AutomatizacionCorreo.DIA_SEMANA_CHOICES,
        'destinatario_email': usuario_email(usuario),
        'configuracion_inventario': configuracion_inventario,
    })


def usuario_list(request):
    return _usuario_list(request, ocultos=False)


def usuario_ocultos(request):
    return _usuario_list(request, ocultos=True)


def _usuario_list(request, ocultos=False):
    usuarios = Usuario.objects.filter(activo=not ocultos)

    q = request.GET.get('q', '').strip()
    rol_filter = request.GET.get('rol', '').strip()
    orden_filter = request.GET.get('orden', 'nombre_asc').strip()
    per_page = 10

    if q:
        usuarios = usuarios.filter(
            Q(nombre__icontains=q)
            | Q(ap_pat__icontains=q)
            | Q(ap_mat__icontains=q)
            | Q(usuario__icontains=q)
        )
    if rol_filter:
        if rol_filter == Usuario.ROL_ADMIN:
            usuarios = usuarios.filter(rol__in=[Usuario.ROL_ADMIN, Usuario.ROL_ADMINISTRADOR])
        else:
            usuarios = usuarios.filter(rol=rol_filter)

    ordenes = {
        'id_asc': 'id_usuario',
        'id_desc': '-id_usuario',
        'usuario_asc': 'usuario',
        'usuario_desc': '-usuario',
        'nombre_asc': 'nombre',
        'nombre_desc': '-nombre',
        'telefono_asc': 'telefono',
        'telefono_desc': '-telefono',
        'puesto_asc': 'puesto',
        'puesto_desc': '-puesto',
        'rol_asc': 'rol',
        'rol_desc': '-rol',
        'estado_asc': 'activo',
        'estado_desc': '-activo',
        'contratacion_asc': 'fecha_contratacion',
        'contratacion_desc': '-fecha_contratacion',
        'conexion_asc': 'ultima_conexion',
        'conexion_desc': '-ultima_conexion',
    }
    usuarios = usuarios.order_by(ordenes.get(orden_filter, 'nombre'), 'ap_pat', 'ap_mat')

    query_params = ''
    if q: query_params += f'&q={q}'
    if rol_filter: query_params += f'&rol={rol_filter}'
    filter_query_params = query_params
    if orden_filter: query_params += f'&orden={orden_filter}'
    paginator = Paginator(usuarios, per_page)
    try:
        page_obj = paginator.page(request.GET.get('page', 1))
    except Exception:
        page_obj = paginator.page(1)

    return render(request, 'usuarios/usuario_list.html', {
        'object_list': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'ocultos': ocultos,
        'q': q,
        'rol_filtro': rol_filter,
        'roles': Usuario.ROL_PUBLIC_CHOICES,
        'orden': orden_filter,
        'orden_filter': orden_filter,
        'query_params': query_params,
        'filter_query_params': filter_query_params,
    })


def usuario_detail(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    ventas_recientes = usuario.venta_set.select_related(
        'id_metPag', 'id_cliente'
    ).order_by('-fecha_venta')[:10]

    return render(request, 'usuarios/usuario_detail.html', {
        'object': usuario,
        'usuario': usuario,
        'ventas_recientes': ventas_recientes,
    })


def usuario_create(request):
    form = UsuarioForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        return redirect('usuario_detail', pk=usuario.pk)

    return render(request, 'usuarios/usuario_form.html', {'form': form})


def usuario_update(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    form = UsuarioForm(request.POST or None, instance=usuario)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('usuario_detail', pk=pk)

    return render(request, 'usuarios/usuario_form.html', {
        'form': form,
        'usuario': usuario,
    })


def usuario_delete(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    ventas_count = usuario.venta_set.count()

    if request.method == 'POST':
        accion = request.POST.get('accion', 'eliminar')

        if accion == 'desactivar':
            usuario.activo = False
            usuario.fecha_baja = usuario.fecha_baja or timezone.now().date()
            usuario.save(update_fields=['activo', 'fecha_baja'])
            messages.warning(
                request,
                f'{usuario.nombre_completo()} fue inhabilitado. Sus ventas historicas se conservaron.'
            )
            return redirect('usuario_ocultos')

        try:
            usuario.delete()
        except ProtectedError:
            messages.warning(
                request,
                'No se puede eliminar este usuario porque tiene ventas registradas. '
                'Puedes inhabilitarlo para que no aparezca en nuevas ventas.'
            )
            return redirect('usuario_delete', pk=pk)

        messages.success(request, 'Usuario eliminado correctamente.')
        return redirect('usuario_list')

    return render(request, 'usuarios/usuario_confirm_delete.html', {
        'object': usuario,
        'usuario': usuario,
        'ventas_count': ventas_count,
    })


def usuario_restaurar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        usuario.activo = True
        usuario.fecha_baja = None
        usuario.save(update_fields=['activo', 'fecha_baja'])
        messages.success(request, f'{usuario.nombre_completo()} fue restaurado como usuario activo.')
    return redirect('usuario_ocultos')


def notificacion_sistema_descartar(request, pk):
    usuario = get_current_usuario(request)
    if request.method == 'POST' and usuario:
        notificacion = get_object_or_404(NotificacionSistema, pk=pk, activa=True)
        NotificacionSistemaDescartada.objects.update_or_create(
            id_usuario=usuario,
            id_notificacion=notificacion,
            defaults={'fecha_descartada': timezone.now()},
        )

    siguiente = request.POST.get('next') or request.META.get('HTTP_REFERER') or '/'
    if not url_has_allowed_host_and_scheme(
        siguiente,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        siguiente = '/'
    return redirect(siguiente)
