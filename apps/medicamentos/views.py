import secrets
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from types import SimpleNamespace

import qrcode
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import Medicamento, Lote, CodigoQR
from .whatsapp import (
    WhatsAppIntegrationError,
    construir_preview_whatsapp,
    enviar_paquete_qr_por_whatsapp,
    normalizar_telefono_con_pais,
    telefono_form_context,
)
from apps.proveedores.models import Proveedor


# ═══════════════════════════════════════════════════════════════
# MEDICAMENTOS
# ═══════════════════════════════════════════════════════════════

def medicamento_list(request):
    meds = Medicamento.objects.select_related('id_lote__id_prov').filter(
        id_lote__oculto_por_caducidad=False
    )

    nombre_filter = request.GET.get('nombre', '').strip()
    estado_filter = request.GET.get('estado', '').strip()
    caducidad_filter = request.GET.get('caducidad', '').strip()
    receta_filter = request.GET.get('receta', '').strip()
    orden_filter = request.GET.get('orden', 'nombre_asc').strip()

    if nombre_filter:
        meds = meds.filter(nombre__icontains=nombre_filter)
    if receta_filter == 'si':
        meds = meds.filter(requiere_receta=True)
    elif receta_filter == 'no':
        meds = meds.filter(requiere_receta=False)

    meds = _agrupar_medicamentos(meds)
    if estado_filter:
        meds = [med for med in meds if med.estado_colorimetria == estado_filter]
    if caducidad_filter:
        meds = [
            med for med in meds
            if any(lote.estado_caducidad == caducidad_filter for lote in med.lotes)
        ]
    meds = _ordenar_medicamentos_agrupados(meds, orden_filter)

    paginator = Paginator(meds, 10)
    try:
        page_obj = paginator.page(request.GET.get('page', 1))
    except Exception:
        page_obj = paginator.page(1)

    query_params = ''
    if nombre_filter: query_params += f'&nombre={nombre_filter}'
    if estado_filter: query_params += f'&estado={estado_filter}'
    if caducidad_filter: query_params += f'&caducidad={caducidad_filter}'
    if receta_filter: query_params += f'&receta={receta_filter}'
    filter_query_params = query_params
    if orden_filter: query_params += f'&orden={orden_filter}'

    return render(request, 'medicamentos/medicamento_list.html', {
        'medicamentos':   page_obj.object_list,
        'page_obj':       page_obj,
        'paginator':      paginator,
        'nombre_filter':  nombre_filter,
        'estado_filter':  estado_filter,
        'caducidad_filter': caducidad_filter,
        'receta_filter':  receta_filter,
        'orden_filter':   orden_filter,
        'query_params':   query_params,
        'filter_query_params': filter_query_params,
    })


def medicamento_detail(request, pk):
    med = get_object_or_404(
        Medicamento.objects.select_related('id_lote__id_prov'),
        pk=pk,
    )
    medicamentos_grupo = _medicamentos_mismo_grupo(med)
    lotes = [item.id_lote for item in medicamentos_grupo]
    stock_total = sum(lote.stock_actual or 0 for lote in lotes if not lote.oculto_por_caducidad)
    estado_stock = _estado_stock_total(stock_total)
    qr_codes = CodigoQR.objects.filter(
        id_medicamento__in=medicamentos_grupo
    ).select_related('id_medicamento').order_by('-fecha_generacion')
    qr_por_medicamento = {qr.id_medicamento_id: qr for qr in qr_codes if qr.activo}
    lote_items = [
        SimpleNamespace(
            medicamento=item,
            lote=item.id_lote,
            qr=qr_por_medicamento.get(item.id_med),
        )
        for item in _ordenar_medicamentos_por_lote(medicamentos_grupo)
    ]
    return render(request, 'medicamentos/medicamento_detail.html', {
        'medicamento': med,
        'medicamentos_grupo': medicamentos_grupo,
        'lotes':       _ordenar_lotes_para_venta(lotes),
        'lote_items':  lote_items,
        'stock_total': stock_total,
        'estado_stock': estado_stock,
        'estado_stock_display': _estado_stock_display(stock_total),
        'qr_codes':    qr_codes,
    })


def medicamento_create(request):
    lotes = Lote.objects.select_related('id_prov').filter(activo=True).order_by('numero_lote')
    context = {'lotes': lotes, 'presentaciones': _presentaciones()}

    if request.method == 'POST':
        errors = _validar_medicamento(request.POST)
        if errors:
            context['errors'] = errors
            context['medicamento'] = _mock(request.POST)
            return render(request, 'medicamentos/medicamento_form.html', context)

        Medicamento.objects.create(
            id_lote             = get_object_or_404(Lote, pk=request.POST['id_lote']),
            nombre              = request.POST.get('nombre', '').strip(),
            presentacion        = request.POST.get('presentacion', '').strip() or None,
            concentracion       = request.POST.get('concentracion', '').strip() or None,
            requiere_receta     = request.POST.get('requiere_receta') == 'true',
        )
        return redirect('medicamento_list')

    return render(request, 'medicamentos/medicamento_form.html', context)


def medicamento_update(request, pk):
    med   = get_object_or_404(Medicamento, pk=pk)
    lotes = Lote.objects.select_related('id_prov').filter(activo=True).order_by('numero_lote')
    context = {'medicamento': med, 'lotes': lotes, 'presentaciones': _presentaciones()}

    if request.method == 'POST':
        errors = _validar_medicamento(request.POST)
        if errors:
            context['errors'] = errors
            return render(request, 'medicamentos/medicamento_form.html', context)

        med.id_lote             = get_object_or_404(Lote, pk=request.POST['id_lote'])
        med.nombre              = request.POST.get('nombre', '').strip()
        med.presentacion        = request.POST.get('presentacion', '').strip() or None
        med.concentracion       = request.POST.get('concentracion', '').strip() or None
        med.requiere_receta     = request.POST.get('requiere_receta') == 'true'
        med.save()
        return redirect('medicamento_detail', pk=pk)

    return render(request, 'medicamentos/medicamento_form.html', context)


def medicamento_delete(request, pk):
    med = get_object_or_404(Medicamento, pk=pk)
    if request.method == 'POST':
        med.delete()
        return redirect('medicamento_list')
    return render(request, 'medicamentos/medicamento_confirm_delete.html', {'medicamento': med})


# ═══════════════════════════════════════════════════════════════
# LOTES
# ═══════════════════════════════════════════════════════════════

def lote_list(request):
    return _lote_list(request, ocultos=False)


def lote_ocultos(request):
    return _lote_list(request, ocultos=True)


def _lote_list(request, ocultos=False):
    lotes = Lote.objects.select_related('id_prov').prefetch_related('medicamento_set').filter(
        oculto_por_caducidad=ocultos
    )

    numero_filter = request.GET.get('numero', '').strip()
    medicamento_filter = request.GET.get('medicamento', '').strip()
    activo_filter = request.GET.get('activo', '').strip()
    caducidad_filter = request.GET.get('caducidad', '').strip()
    orden_filter = request.GET.get('orden', 'fecha_desc').strip()

    if numero_filter:
        lotes = lotes.filter(numero_lote__icontains=numero_filter)
    if medicamento_filter:
        lotes = lotes.filter(
            medicamento__nombre__icontains=medicamento_filter
        ).distinct()
    if activo_filter == 'si':
        lotes = lotes.filter(activo=True)
    elif activo_filter == 'no':
        lotes = lotes.filter(activo=False)

    lotes = list(lotes)
    if caducidad_filter:
        lotes = [lote for lote in lotes if lote.estado_caducidad == caducidad_filter]
    lotes = _ordenar_lotes(lotes, orden_filter)

    paginator = Paginator(lotes, 10)
    try:
        page_obj = paginator.page(request.GET.get('page', 1))
    except Exception:
        page_obj = paginator.page(1)

    query_params = ''
    if numero_filter: query_params += f'&numero={numero_filter}'
    if medicamento_filter: query_params += f'&medicamento={medicamento_filter}'
    if activo_filter: query_params += f'&activo={activo_filter}'
    if caducidad_filter: query_params += f'&caducidad={caducidad_filter}'
    filter_query_params = query_params
    if orden_filter: query_params += f'&orden={orden_filter}'

    return render(request, 'medicamentos/lote_list.html', {
        'lotes':          page_obj.object_list,
        'page_obj':       page_obj,
        'paginator':      paginator,
        'numero_filter':  numero_filter,
        'medicamento_filter': medicamento_filter,
        'activo_filter':  activo_filter,
        'caducidad_filter': caducidad_filter,
        'orden_filter':   orden_filter,
        'query_params':   query_params,
        'filter_query_params': filter_query_params,
        'ocultos':        ocultos,
    })


def lote_detail(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    medicamentos = lote.medicamento_set.all().order_by('nombre')
    return render(request, 'medicamentos/lote_detail.html', {
        'lote':         lote,
        'medicamentos': medicamentos,
    })


def lote_create(request):
    proveedores = Proveedor.objects.all().order_by('nombre')
    proveedor_preseleccionado = None
    proveedor_id = request.GET.get('proveedor') or request.POST.get('id_prov')
    if proveedor_id:
        proveedor_preseleccionado = Proveedor.objects.filter(pk=proveedor_id).first()

    context = {
        'proveedores': proveedores,
        'proveedor_preseleccionado': proveedor_preseleccionado,
        'volver_proveedor': request.GET.get('next') == 'proveedor_detail' or request.POST.get('next') == 'proveedor_detail',
    }

    if request.method == 'POST':
        errors = _validar_lote(request.POST)
        if errors:
            context['errors'] = errors
            context['lote'] = _mock(request.POST)
            return render(request, 'medicamentos/lote_form.html', context)

        lote = Lote.objects.create(
            id_prov          = get_object_or_404(Proveedor, pk=request.POST['id_prov']),
            numero_lote      = request.POST.get('numero_lote', '').strip(),
            stock_actual     = int(request.POST.get('stock_actual', 0)),
            activo           = request.POST.get('activo') == 'true',
            precio_compra    = request.POST.get('precio_compra') or None,
            precio_venta     = request.POST.get('precio_venta') or None,
            fecha_fabricacion = request.POST.get('fecha_fabricacion') or None,
            fecha_caducidad  = request.POST.get('fecha_caducidad') or None,
            fecha_compra     = request.POST.get('fecha_compra') or None,
        )
        if context['volver_proveedor']:
            return redirect('proveedor_detail', pk=lote.id_prov_id)
        return redirect('lote_list')

    return render(request, 'medicamentos/lote_form.html', context)


def lote_update(request, pk):
    lote        = get_object_or_404(Lote, pk=pk)
    proveedores = Proveedor.objects.all().order_by('nombre')
    context     = {'lote': lote, 'proveedores': proveedores}

    if request.method == 'POST':
        errors = _validar_lote(request.POST)
        if errors:
            context['errors'] = errors
            return render(request, 'medicamentos/lote_form.html', context)

        lote.id_prov           = get_object_or_404(Proveedor, pk=request.POST['id_prov'])
        lote.numero_lote       = request.POST.get('numero_lote', '').strip()
        lote.stock_actual      = int(request.POST.get('stock_actual', lote.stock_actual))
        lote.activo            = request.POST.get('activo') == 'true'
        lote.precio_compra     = request.POST.get('precio_compra') or None
        lote.precio_venta      = request.POST.get('precio_venta') or None
        lote.fecha_fabricacion = request.POST.get('fecha_fabricacion') or None
        lote.fecha_caducidad   = request.POST.get('fecha_caducidad') or None
        lote.fecha_compra      = request.POST.get('fecha_compra') or None
        lote.save()
        return redirect('lote_detail', pk=pk)

    return render(request, 'medicamentos/lote_form.html', context)


def lote_delete(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    if request.method == 'POST':
        lote.delete()
        return redirect('lote_list')
    return render(request, 'medicamentos/lote_confirm_delete.html', {'lote': lote})


def lote_ocultar(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    if request.method == 'POST':
        lote.oculto_por_caducidad = True
        lote.activo = False
        lote.save(update_fields=['oculto_por_caducidad', 'activo'])
        return redirect('lote_list')
    return render(request, 'medicamentos/lote_ocultar_confirm.html', {'lote': lote})


def lote_restaurar(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    if request.method == 'POST':
        lote.oculto_por_caducidad = False
        lote.activo = True
        lote.save(update_fields=['oculto_por_caducidad', 'activo'])
    return redirect('lote_ocultos')


# ═══════════════════════════════════════════════════════════════
# CÓDIGOS QR
# ═══════════════════════════════════════════════════════════════

def qr_list(request):
    qr_codes      = CodigoQR.objects.select_related('id_medicamento').all()
    med_filter    = request.GET.get('medicamento', '').strip()
    activo_filter = request.GET.get('activo', '').strip()

    if med_filter:
        qr_codes = qr_codes.filter(id_medicamento__id_med=med_filter)
    if activo_filter == 'si':
        qr_codes = qr_codes.filter(activo=True)
    elif activo_filter == 'no':
        qr_codes = qr_codes.filter(activo=False)

    return render(request, 'medicamentos/qr_list.html', {
        'qr_codes':     qr_codes.order_by('-fecha_generacion'),
        'medicamentos': Medicamento.objects.all().order_by('nombre'),
        'med_filter':   med_filter,
        'activo_filter': activo_filter,
    })


def qr_create(request, med_pk):
    med   = get_object_or_404(Medicamento, pk=med_pk)
    token = secrets.token_hex(32)
    qr = CodigoQR.objects.create(
        id_medicamento   = med,
        token            = token,
        url_qr           = reverse('qr_scan', kwargs={'token': token}),
        fecha_generacion = timezone.now().date(),
        activo           = True,
    )
    qr.save(update_fields=['url_qr'])
    return redirect('medicamento_detail', pk=med_pk)


def qr_regenerar(request, pk):
    qr              = get_object_or_404(CodigoQR, pk=pk)
    qr.token        = secrets.token_hex(32)
    qr.url_qr       = reverse('qr_scan', kwargs={'token': qr.token})
    qr.fecha_regeneracion = timezone.now().date()
    qr.save()
    return redirect('medicamento_detail', pk=qr.id_medicamento.id_med)


def qr_delete(request, pk):
    qr = get_object_or_404(CodigoQR, pk=pk)
    med_pk = qr.id_medicamento.id_med
    qr.delete()
    return redirect('medicamento_detail', pk=med_pk)


def qr_enviar_whatsapp(request, pk):
    qr = get_object_or_404(
        CodigoQR.objects.select_related('id_medicamento__id_lote__id_prov'),
        pk=pk,
        activo=True,
    )
    preview = construir_preview_whatsapp(request, qr)
    context = {
        'qr': qr,
        'medicamento': qr.id_medicamento,
        'preview': preview,
        **telefono_form_context(),
    }

    if request.method == 'POST':
        country_code = request.POST.get('pais_codigo', '52')
        telefono_local = request.POST.get('telefono_local', '')
        try:
            telefono = normalizar_telefono_con_pais(country_code, telefono_local)
            enviar_paquete_qr_por_whatsapp(request, qr, telefono)
        except WhatsAppIntegrationError as exc:
            context.update(telefono_form_context(country_code, telefono_local))
            context['errors'] = [str(exc)]
            return render(request, 'medicamentos/qr_whatsapp_form.html', context)

        messages.success(request, f'QR, informacion y audio enviados a WhatsApp {telefono}.')
        return redirect('medicamento_detail', pk=qr.id_medicamento_id)

    return render(request, 'medicamentos/qr_whatsapp_form.html', context)


def qr_image(request, pk):
    qr = get_object_or_404(CodigoQR, pk=pk)
    target_url = request.build_absolute_uri(
        reverse('qr_scan', kwargs={'token': qr.token})
    )

    img = qrcode.make(target_url)
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type='image/png')
    disposition = 'attachment' if request.GET.get('download') == '1' else 'inline'
    response['Content-Disposition'] = f'{disposition}; filename="qr-{qr.id_qr}.png"'
    return response


def qr_scan(request, token):
    qr = get_object_or_404(
        CodigoQR.objects.select_related('id_medicamento__id_lote__id_prov'),
        token=token,
        activo=True,
    )
    qr.contador_escaneos += 1
    qr.save(update_fields=['contador_escaneos'])

    return render(request, 'medicamentos/qr_scan.html', {
        'qr': qr,
        'medicamento': qr.id_medicamento,
    })


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _validar_medicamento(data):
    errors = []
    if not data.get('nombre', '').strip():
        errors.append('El nombre del medicamento es obligatorio.')
    if not data.get('id_lote'):
        errors.append('Debes seleccionar un lote.')
    return errors


def _presentaciones():
    return [
        'Tabletas',
        'Capsulas',
        'Jarabe',
        'Suspension',
        'Solucion',
        'Gotas',
        'Ampolleta',
        'Inyectable',
        'Crema',
        'Unguento',
        'Gel',
        'Aerosol',
        'Polvo',
        'Caja',
        'Frasco',
        'Sobre',
    ]


def _clave_medicamento(med):
    return (
        (med.nombre or '').strip().casefold(),
        (med.presentacion or '').strip().casefold(),
        (med.concentracion or '').strip().casefold(),
        bool(med.requiere_receta),
    )


def _medicamentos_mismo_grupo(med):
    return list(
        Medicamento.objects.select_related('id_lote__id_prov').filter(
            nombre__iexact=med.nombre,
            presentacion=med.presentacion,
            concentracion=med.concentracion,
            requiere_receta=med.requiere_receta,
            id_lote__oculto_por_caducidad=False,
        )
    )


def _agrupar_medicamentos(queryset):
    grupos = defaultdict(list)
    for med in queryset:
        grupos[_clave_medicamento(med)].append(med)

    medicamentos = []
    for grupo in grupos.values():
        grupo = sorted(grupo, key=lambda med: med.id_med)
        principal = grupo[0]
        lotes = [med.id_lote for med in grupo if med.id_lote and not med.id_lote.oculto_por_caducidad]
        stock_total = sum(lote.stock_actual or 0 for lote in lotes)
        medicamentos.append(SimpleNamespace(
            id_med=principal.id_med,
            nombre=principal.nombre,
            presentacion=principal.presentacion,
            concentracion=principal.concentracion,
            requiere_receta=principal.requiere_receta,
            fecha_registro=principal.fecha_registro,
            estado_colorimetria=_estado_stock_total(stock_total),
            estado_stock_display=_estado_stock_display(stock_total),
            stock_total=stock_total,
            lotes=lotes,
            lotes_count=len(lotes),
            lotes_bajo_stock=sum(1 for lote in lotes if lote.estado_stock in ('rojo', 'sin_stock')),
            lotes_proximos=sum(1 for lote in lotes if lote.estado_caducidad == 'amarillo'),
            lotes_caducos=sum(1 for lote in lotes if lote.estado_caducidad == 'rojo'),
            precio_venta=_precio_venta_referencia(lotes),
        ))
    return medicamentos


def _ordenar_medicamentos_agrupados(medicamentos, orden):
    reverse = orden.endswith('_desc')
    campo = orden.removesuffix('_asc').removesuffix('_desc')
    claves = {
        'id': lambda med: med.id_med,
        'nombre': lambda med: (med.nombre or '').lower(),
        'presentacion': lambda med: (med.presentacion or '').lower(),
        'concentracion': lambda med: (med.concentracion or '').lower(),
        'stock': lambda med: med.stock_total,
        'estado': lambda med: med.estado_colorimetria,
        'receta': lambda med: 1 if med.requiere_receta else 0,
    }
    return sorted(medicamentos, key=claves.get(campo, claves['nombre']), reverse=reverse)


def _estado_stock_total(stock):
    if stock <= 0:
        return 'sin_stock'
    if stock <= 5:
        return 'rojo'
    if stock <= 20:
        return 'amarillo'
    return 'verde'


def _estado_stock_display(stock):
    if stock <= 0:
        return 'Sin stock'
    if stock <= 5:
        return 'Rojo'
    if stock <= 20:
        return 'Amarillo'
    return 'Verde'


def _precio_venta_referencia(lotes):
    for lote in _ordenar_lotes_para_venta(lotes):
        if lote.activo and (lote.stock_actual or 0) > 0 and lote.estado_caducidad != 'rojo':
            return lote.precio_venta or 0
    return lotes[0].precio_venta if lotes else 0


def _ordenar_lotes_para_venta(lotes):
    fecha_maxima = datetime.max.date()
    return sorted(
        lotes,
        key=lambda lote: (
            lote.estado_caducidad == 'rojo',
            lote.fecha_caducidad or fecha_maxima,
            lote.fecha_ingreso or timezone.now(),
            lote.id_lote,
        ),
    )


def _ordenar_medicamentos_por_lote(medicamentos):
    fecha_maxima = datetime.max.date()
    return sorted(
        medicamentos,
        key=lambda med: (
            med.id_lote.estado_caducidad == 'rojo',
            med.id_lote.fecha_caducidad or fecha_maxima,
            med.id_lote.fecha_ingreso or timezone.now(),
            med.id_lote_id,
        ),
    )


def _validar_lote(data):
    errors = []
    if not data.get('numero_lote', '').strip():
        errors.append('El número de lote es obligatorio.')
    if not data.get('id_prov'):
        errors.append('Debes seleccionar un proveedor.')
    return errors


def _primer_medicamento_nombre(lote):
    nombres = [(med.nombre or '').lower() for med in lote.medicamento_set.all()]
    return sorted(nombres)[0] if nombres else ''


def _ordenar_lotes(lotes, orden):
    reverse = orden.endswith('_desc')
    campo = orden.removesuffix('_asc').removesuffix('_desc')

    fecha_minima = datetime.min.replace(
        tzinfo=timezone.get_current_timezone()
    )
    claves = {
        'numero': lambda lote: (lote.numero_lote or '').lower(),
        'medicamento': _primer_medicamento_nombre,
        'proveedor': lambda lote: (lote.id_prov.nombre or '').lower(),
        'stock': lambda lote: lote.stock_actual or 0,
        'compra': lambda lote: lote.precio_compra or 0,
        'venta': lambda lote: lote.precio_venta or 0,
        'caducidad': lambda lote: lote.fecha_caducidad or datetime.max.date(),
        'fecha': lambda lote: lote.fecha_ingreso or fecha_minima,
        'activo': lambda lote: 1 if lote.activo else 0,
    }
    return sorted(lotes, key=claves.get(campo, claves['fecha']), reverse=reverse)


class _mock:
    """Repobla el formulario con los datos POSTeados tras un error."""
    def __init__(self, data):
        for k, v in data.items():
            setattr(self, k, v)
