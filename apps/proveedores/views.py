from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .models import Proveedor
from apps.medicamentos.models import Medicamento


def proveedor_list(request):
    proveedores   = Proveedor.objects.filter(activo=True)
    nombre_filter = request.GET.get('nombre', '').strip()
    orden_filter = request.GET.get('orden', 'nombre_asc').strip()

    if nombre_filter:
        proveedores = proveedores.filter(nombre__icontains=nombre_filter)

    ordenes = {
        'id_asc': 'id_prov',
        'id_desc': '-id_prov',
        'nombre_asc': 'nombre',
        'nombre_desc': '-nombre',
        'telefono_asc': 'telefono',
        'telefono_desc': '-telefono',
        'correo_asc': 'correo',
        'correo_desc': '-correo',
        'direccion_asc': 'direccion',
        'direccion_desc': '-direccion',
    }
    proveedores = proveedores.order_by(ordenes.get(orden_filter, 'nombre'))

    paginator = Paginator(proveedores, 10)
    try:
        page_obj = paginator.page(request.GET.get('page', 1))
    except Exception:
        page_obj = paginator.page(1)

    query_params = ''
    if nombre_filter:
        query_params += f'&nombre={nombre_filter}'
    filter_query_params = query_params
    if orden_filter:
        query_params += f'&orden={orden_filter}'

    return render(request, 'proveedores/proveedor_list.html', {
        'proveedores':  page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'nombre_filter': nombre_filter,
        'orden_filter': orden_filter,
        'query_params': query_params,
        'filter_query_params': filter_query_params,
    })


def proveedor_detail(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    lotes = proveedor.lote_set.prefetch_related('medicamento_set').filter(
        oculto_por_caducidad=False
    )

    medicamento_filter = request.GET.get('medicamento', '').strip()
    presentacion_filter = request.GET.get('presentacion', '').strip()
    estado_filter = request.GET.get('estado', '').strip()

    if medicamento_filter:
        lotes = lotes.filter(medicamento__nombre__icontains=medicamento_filter)
    if presentacion_filter:
        lotes = lotes.filter(medicamento__presentacion__icontains=presentacion_filter)
    if estado_filter:
        lotes = lotes.filter(medicamento__estado_colorimetria=estado_filter)

    lotes = lotes.distinct().order_by('-fecha_ingreso')

    return render(request, 'proveedores/proveedor_detail.html', {
        'proveedor':            proveedor,
        'lotes':                lotes,
        'medicamento_filter':   medicamento_filter,
        'presentacion_filter':  presentacion_filter,
        'estado_filter':        estado_filter,
        'estado_choices':       Medicamento.ESTADO_CHOICES,
    })


def proveedor_create(request):
    if request.method == 'POST':
        errors = _validar(request.POST)
        if errors:
            return render(request, 'proveedores/proveedor_form.html', {
                'errors':     errors,
                'proveedor':  _mock(request.POST),
            })
        Proveedor.objects.create(
            nombre    = request.POST.get('nombre', '').strip(),
            telefono  = request.POST.get('telefono', '').strip() or None,
            correo    = request.POST.get('correo', '').strip() or None,
            direccion = request.POST.get('direccion', '').strip() or None,
        )
        return redirect('proveedor_list')

    return render(request, 'proveedores/proveedor_form.html')


def proveedor_update(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)

    if request.method == 'POST':
        errors = _validar(request.POST)
        if errors:
            return render(request, 'proveedores/proveedor_form.html', {
                'errors':    errors,
                'proveedor': proveedor,
            })
        proveedor.nombre    = request.POST.get('nombre', '').strip()
        proveedor.telefono  = request.POST.get('telefono', '').strip() or None
        proveedor.correo    = request.POST.get('correo', '').strip() or None
        proveedor.direccion = request.POST.get('direccion', '').strip() or None
        proveedor.save()
        return redirect('proveedor_detail', pk=pk)

    return render(request, 'proveedores/proveedor_form.html', {'proveedor': proveedor})


def proveedor_delete(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == 'POST':
        messages.error(
            request,
            'No se puede borrar un proveedor porque conserva historial de lotes y ventas. Usa Ocultar proveedor.'
        )

    lotes_count = proveedor.lote_set.count()
    return render(request, 'proveedores/proveedor_confirm_delete.html', {
        'proveedor': proveedor,
        'lotes_count': lotes_count,
    })


def proveedor_ocultar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == 'POST':
        lotes_actualizados = proveedor.lote_set.update(
            activo=False,
            oculto_por_caducidad=True,
        )
        proveedor.activo = False
        proveedor.save(update_fields=['activo'])
        messages.success(
            request,
            f'Proveedor ocultado. Tambien se ocultaron {lotes_actualizados} lote(s) relacionados.'
        )
        return redirect('proveedor_list')

    return render(request, 'proveedores/proveedor_ocultar_confirm.html', {
        'proveedor': proveedor,
        'lotes_count': proveedor.lote_set.count(),
    })


# ── Helpers ──────────────────────────────────────────────────────────────────

def _validar(data):
    errors = []
    if not data.get('nombre', '').strip():
        errors.append('El nombre del proveedor es obligatorio.')
    return errors


class _mock:
    def __init__(self, data):
        for k, v in data.items():
            setattr(self, k, v)
