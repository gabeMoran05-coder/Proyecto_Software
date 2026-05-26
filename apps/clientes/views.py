from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator

from .models import Cliente
from apps.text_utils import first_upper, first_upper_or_none


# ──────────────────────────────────────────────
# LISTA
# ──────────────────────────────────────────────
def cliente_list(request):
    clientes = Cliente.objects.all()

    # Filtro por nombre
    nombre_filter = request.GET.get('nombre', '').strip()
    orden_filter = request.GET.get('orden', 'nombre_asc').strip()
    if nombre_filter:
        clientes = clientes.filter(nombre__icontains=nombre_filter)

    ordenes = {
        'id_asc': 'id_cliente',
        'id_desc': '-id_cliente',
        'nombre_asc': 'nombre',
        'nombre_desc': '-nombre',
        'telefono_asc': 'telefono',
        'telefono_desc': '-telefono',
        'fecha_asc': 'fecha_registro',
        'fecha_desc': '-fecha_registro',
    }
    clientes = clientes.order_by(ordenes.get(orden_filter, 'nombre'), 'ap_pat', 'ap_mat')

    # Paginación
    paginator = Paginator(clientes, 10)
    try:
        page_obj = paginator.page(request.GET.get('page', 1))
    except Exception:
        page_obj = paginator.page(1)

    # Mantener filtros al páginar
    query_params = f'&nombre={nombre_filter}' if nombre_filter else ''
    filter_query_params = query_params
    if orden_filter:
        query_params += f'&orden={orden_filter}'

    context = {
        'clientes':      page_obj.object_list,
        'page_obj':      page_obj,
        'paginator':     paginator,
        'is_paginated':  paginator.num_pages > 1,
        'nombre_filter': nombre_filter,
        'orden_filter':  orden_filter,
        'query_params':  query_params,
        'filter_query_params': filter_query_params,
    }
    return render(request, 'clientes/cliente_list.html', context)


# ──────────────────────────────────────────────
# DETALLE
# ──────────────────────────────────────────────
def cliente_detail(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)

    # Historial de compras del cliente (relación inversa desde Venta)
    ventas = cliente.venta_set.select_related(
        'id_metPag', 'id_usuario'
    ).order_by('-fecha_venta')

    context = {
        'cliente': cliente,
        'ventas':  ventas,
    }
    return render(request, 'clientes/cliente_detail.html', context)


# ──────────────────────────────────────────────
# CREAR
# ──────────────────────────────────────────────
def cliente_create(request):
    if request.method == 'POST':
        errors = _validar_cliente(request.POST)
        if errors:
            return render(request, 'clientes/cliente_form.html', {
                'errors': errors,
                'cliente': _mock_cliente(request.POST),
            })

        Cliente.objects.create(
            nombre         = first_upper(request.POST.get('nombre')),
            ap_pat         = first_upper_or_none(request.POST.get('ap_pat')),
            ap_mat         = first_upper_or_none(request.POST.get('ap_mat')),
            telefono       = request.POST.get('telefono', '').strip() or None,
        )
        return redirect('cliente_list')

    return render(request, 'clientes/cliente_form.html')


# ──────────────────────────────────────────────
# EDITAR
# ──────────────────────────────────────────────
def cliente_update(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)

    if request.method == 'POST':
        errors = _validar_cliente(request.POST)
        if errors:
            return render(request, 'clientes/cliente_form.html', {
                'errors': errors,
                'cliente': cliente,
            })

        cliente.nombre         = first_upper(request.POST.get('nombre'))
        cliente.ap_pat         = first_upper_or_none(request.POST.get('ap_pat'))
        cliente.ap_mat         = first_upper_or_none(request.POST.get('ap_mat'))
        cliente.telefono       = request.POST.get('telefono', '').strip() or None
        cliente.save()
        return redirect('cliente_detail', pk=pk)

    return render(request, 'clientes/cliente_form.html', {'cliente': cliente})


# ──────────────────────────────────────────────
# ELIMINAR
# ──────────────────────────────────────────────
def cliente_delete(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)

    if request.method == 'POST':
        cliente.delete()
        return redirect('cliente_list')

    return render(request, 'clientes/cliente_confirm_delete.html', {'cliente': cliente})


# ──────────────────────────────────────────────
# HELPERS INTERNOS
# ──────────────────────────────────────────────
def _validar_cliente(data):
    errors = []
    if not data.get('nombre', '').strip():
        errors.append('El nombre es obligatorio.')
    return errors


def _mock_cliente(data):
    """Objeto temporal para repoblar el formulario tras un error."""
    class _C:
        nombre         = data.get('nombre', '')
        ap_pat         = data.get('ap_pat', '')
        ap_mat         = data.get('ap_mat', '')
        telefono       = data.get('telefono', '')
    return _C()
