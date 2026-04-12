from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.ventas.models import Cliente


@login_required
def lista(request):
    clientes = Cliente.objects.all()
    return render(request, 'clientes/lista.html', {'clientes': clientes})


@login_required
def detalle(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    ventas  = cliente.ventas.select_related('metodo_pago').all()
    return render(request, 'clientes/detalle.html', {'cliente': cliente, 'ventas': ventas})
