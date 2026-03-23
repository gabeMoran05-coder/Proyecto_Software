from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Proveedor
from .forms import ProveedorForm

@login_required
def lista(request):
    proveedores = Proveedor.objects.all()
    return render(request, 'proveedores/lista.html', {'proveedores': proveedores})

@login_required
def crear(request):
    form = ProveedorForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Proveedor registrado.')
        return redirect('proveedores:lista')
    return render(request, 'proveedores/form.html', {'form': form, 'titulo': 'Nuevo proveedor'})

@login_required
def editar(request, pk):
    prov = get_object_or_404(Proveedor, pk=pk)
    form = ProveedorForm(request.POST or None, instance=prov)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Proveedor actualizado.')
        return redirect('proveedores:lista')
    return render(request, 'proveedores/form.html', {'form': form, 'titulo': 'Editar proveedor'})

@login_required
def eliminar(request, pk):
    prov = get_object_or_404(Proveedor, pk=pk)
    if request.method == 'POST':
        prov.delete()
        messages.success(request, 'Proveedor eliminado.')
        return redirect('proveedores:lista')
    return render(request, 'proveedores/confirmar_eliminar.html', {'objeto': prov})
