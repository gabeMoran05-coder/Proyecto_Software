from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from .models import Medicamento, Lote, CodigoQR
from .forms import MedicamentoForm, LoteForm


@login_required
def lista(request):
    q     = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
    meds  = Medicamento.objects.prefetch_related('lotes').all()
    if q:
        meds = meds.filter(nombre__icontains=q)
    if estado:
        meds = meds.filter(estado_colorimetria=estado)
    return render(request, 'medicamentos/lista.html', {
        'medicamentos': meds, 'q': q, 'estado': estado
    })


@login_required
def detalle(request, pk):
    med   = get_object_or_404(Medicamento, pk=pk)
    lotes = med.lotes.filter(activo=True).order_by('fecha_caducidad')
    return render(request, 'medicamentos/detalle.html', {'med': med, 'lotes': lotes})


@login_required
def crear(request):
    if request.user.rol != 'admin':
        messages.error(request, 'Sin acceso.')
        return redirect('medicamentos:lista')
    form = MedicamentoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        med = form.save()
        messages.success(request, f'Medicamento "{med.nombre}" registrado.')
        return redirect('medicamentos:detalle', pk=med.pk)
    return render(request, 'medicamentos/form.html', {'form': form, 'titulo': 'Registrar medicamento'})


@login_required
def editar(request, pk):
    if request.user.rol != 'admin':
        return redirect('medicamentos:lista')
    med  = get_object_or_404(Medicamento, pk=pk)
    form = MedicamentoForm(request.POST or None, instance=med)
    if request.method == 'POST' and form.is_valid():
        form.save()
        med.actualizar_colorimetria()
        messages.success(request, 'Medicamento actualizado.')
        return redirect('medicamentos:detalle', pk=med.pk)
    return render(request, 'medicamentos/form.html', {'form': form, 'titulo': 'Editar medicamento'})


@login_required
def eliminar(request, pk):
    if request.user.rol != 'admin':
        return redirect('medicamentos:lista')
    med = get_object_or_404(Medicamento, pk=pk)
    if request.method == 'POST':
        med.delete()
        messages.success(request, 'Medicamento eliminado.')
        return redirect('medicamentos:lista')
    return render(request, 'medicamentos/confirmar_eliminar.html', {'objeto': med})


# ── Lotes ─────────────────────────────────────────────────────────────────────

@login_required
def crear_lote(request, med_pk):
    med  = get_object_or_404(Medicamento, pk=med_pk)
    form = LoteForm(request.POST or None, initial={'medicamento': med})
    if request.method == 'POST' and form.is_valid():
        lote = form.save(commit=False)
        lote.medicamento = med
        lote.save()
        messages.success(request, f'Lote {lote.numero_lote} registrado.')
        return redirect('medicamentos:detalle', pk=med.pk)
    return render(request, 'medicamentos/lote_form.html', {
        'form': form, 'med': med, 'titulo': 'Registrar lote'
    })


@login_required
def eliminar_lote(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    med_pk = lote.medicamento_id
    if request.method == 'POST':
        lote.activo = False
        lote.save()
        messages.success(request, 'Lote desactivado.')
    return redirect('medicamentos:detalle', pk=med_pk)


# ── Códigos QR ────────────────────────────────────────────────────────────────

@login_required
def generar_qr(request, med_pk):
    med  = get_object_or_404(Medicamento, pk=med_pk)
    base = request.build_absolute_uri('/').rstrip('/')
    qr, created = CodigoQR.objects.get_or_create(medicamento=med)
    if not created:
        qr.fecha_regeneracion = timezone.now()
    qr.generar_imagen(base)
    messages.success(request, 'Código QR generado.')
    return redirect('medicamentos:vista_qr', med_pk=med.pk)


@login_required
def vista_qr(request, med_pk):
    med = get_object_or_404(Medicamento, pk=med_pk)
    qr  = getattr(med, 'codigo_qr', None)
    return render(request, 'medicamentos/vista_qr.html', {'med': med, 'qr': qr})


# ── Página pública accesible (cliente escanea QR) ────────────────────────────

def pagina_qr_publica(request, token):
    """Vista pública sin login para que el cliente consulte su medicamento."""
    qr  = get_object_or_404(CodigoQR, token=token, activo=True)
    qr.contador_escaneos += 1
    qr.save(update_fields=['contador_escaneos'])
    med   = qr.medicamento
    lotes = med.lotes.filter(activo=True).order_by('fecha_caducidad')
    lote  = lotes.first()
    hoy   = timezone.now().date()
    dias  = (lote.fecha_caducidad - hoy).days if lote else None
    return render(request, 'medicamentos/pagina_qr_publica.html', {
        'med': med, 'lote': lote, 'dias': dias
    })
