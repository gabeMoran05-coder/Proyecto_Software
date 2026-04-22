from django.shortcuts import get_object_or_404, redirect, render

from .models import Proveedor
from apps.medicamentos.models import Medicamento


def proveedor_list(request):
    proveedores   = Proveedor.objects.all()
    nombre_filter = request.GET.get('nombre', '').strip()

    if nombre_filter:
        proveedores = proveedores.filter(nombre__icontains=nombre_filter)

    return render(request, 'proveedores/proveedor_list.html', {
        'proveedores':  proveedores.order_by('nombre'),
        'nombre_filter': nombre_filter,
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
        proveedor.delete()
        return redirect('proveedor_list')
    return render(request, 'proveedores/proveedor_confirm_delete.html', {'proveedor': proveedor})


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
