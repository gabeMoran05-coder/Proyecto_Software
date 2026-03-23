from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from .models import Venta, DetalleVenta, MetodoPago, Cliente
import json


@login_required
def lista(request):
    ventas = Venta.objects.select_related('usuario', 'cliente', 'metodo_pago').all()
    return render(request, 'ventas/lista.html', {'ventas': ventas})


@login_required
def detalle(request, pk):
    venta    = get_object_or_404(Venta, pk=pk)
    detalles = venta.detalles.select_related('medicamento').all()
    return render(request, 'ventas/detalle.html', {'venta': venta, 'detalles': detalles})


@login_required
def punto_venta(request):
    from apps.medicamentos.models import Medicamento
    metodos = MetodoPago.objects.all()
    meds    = Medicamento.objects.filter(
        lotes__stock_actual__gt=0, lotes__activo=True
    ).distinct()

    if request.method == 'POST':
        try:
            data      = json.loads(request.body)
            items     = data.get('items', [])
            metodo_id = data.get('metodo_pago')
            telefono  = data.get('telefono', '').strip()

            if not items:
                return JsonResponse({'ok': False, 'error': 'Sin productos.'})

            with transaction.atomic():
                cliente = None
                if telefono:
                    cliente, _ = Cliente.objects.get_or_create(
                        telefono=telefono,
                        defaults={'nombre': 'Cliente', 'ap_pat': 'Farmacia'}
                    )
                metodo = get_object_or_404(MetodoPago, pk=metodo_id)
                venta  = Venta.objects.create(
                    usuario=request.user, cliente=cliente, metodo_pago=metodo
                )
                from apps.medicamentos.models import Medicamento as Med
                for item in items:
                    med  = get_object_or_404(Med, pk=item['med_id'])
                    lote = med.lotes.filter(activo=True, stock_actual__gt=0)\
                                    .order_by('fecha_caducidad').first()
                    if not lote:
                        raise ValueError(f'Sin stock para {med.nombre}')
                    cantidad = int(item['cantidad'])
                    if lote.stock_actual < cantidad:
                        raise ValueError(f'Stock insuficiente para {med.nombre}')
                    DetalleVenta.objects.create(
                        venta=venta, medicamento=med, lote=lote,
                        cantidad=cantidad, precio_unitario=lote.precio_venta,
                    )
                venta.calcular_total()
            return JsonResponse({'ok': True, 'venta_id': venta.pk})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})

    return render(request, 'ventas/punto_venta.html', {'metodos': metodos, 'meds': meds})


@login_required
def buscar_medicamento(request):
    from apps.medicamentos.models import Medicamento
    q    = request.GET.get('q', '')
    meds = Medicamento.objects.filter(
        nombre__icontains=q,
        lotes__stock_actual__gt=0,
        lotes__activo=True
    ).distinct()[:10]

    data = []
    for m in meds:
        lote = m.lotes.filter(activo=True, stock_actual__gt=0)\
                      .order_by('fecha_caducidad').first()
        if lote:
            data.append({
                'id':     m.pk,
                'nombre': str(m),
                'estado': m.estado_colorimetria,
                'precio': str(lote.precio_venta),
            })
    return JsonResponse(data, safe=False)


@login_required
def reporte(request):
    from django.db.models import Sum
    ventas = Venta.objects.select_related('usuario').all()
    total  = ventas.aggregate(Sum('total_venta'))['total_venta__sum'] or 0
    return render(request, 'ventas/reporte.html', {'ventas': ventas, 'total': total})
