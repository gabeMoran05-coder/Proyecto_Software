from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Proveedor


def proveedor_list(request):
    qs = Proveedor.objects.all().order_by('nombre')
    nombre_filter = request.GET.get('nombre', '')
    if nombre_filter:
        qs = qs.filter(nombre__icontains=nombre_filter)
    return render(request, 'proveedor/proveedor_list.html', {
        'proveedores': qs,
        'nombre_filter': nombre_filter,
    })


def proveedor_detail(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    from apps.medicamentos.models import Lote
    lotes = Lote.objects.filter(id_prov=proveedor).select_related('id_prov')
    return render(request, 'proveedor/proveedor_detail.html', {
        'proveedor': proveedor,
        'lotes': lotes,
    })


def proveedor_create(request):
    errors = []
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if not nombre:
            errors.append('El nombre es obligatorio.')
        if not errors:
            Proveedor.objects.create(
                nombre=nombre,
                telefono=request.POST.get('telefono', '').strip() or None,
                correo=request.POST.get('correo', '').strip() or None,
                direccion=request.POST.get('direccion', '').strip() or None,
            )
            messages.success(request, 'Proveedor registrado correctamente.')
            return redirect('proveedor_list')
    return render(request, 'proveedor/proveedor_form.html', {
        'errors': errors,
        'proveedor': None,
    })


def proveedor_update(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    errors = []
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if not nombre:
            errors.append('El nombre es obligatorio.')
        if not errors:
            proveedor.nombre = nombre
            proveedor.telefono = request.POST.get('telefono', '').strip() or None
            proveedor.correo = request.POST.get('correo', '').strip() or None
            proveedor.direccion = request.POST.get('direccion', '').strip() or None
            proveedor.save()
            messages.success(request, 'Proveedor actualizado correctamente.')
            return redirect('proveedor_detail', pk=pk)
    return render(request, 'proveedor/proveedor_form.html', {
        'proveedor': proveedor,
        'errors': errors,
    })


def proveedor_delete(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    if request.method == 'POST':
        proveedor.delete()
        messages.success(request, 'Proveedor eliminado.')
        return redirect('proveedor_list')
    return render(request, 'proveedor/proveedor_confirm_delete.html', {
        'proveedor': proveedor,
    })