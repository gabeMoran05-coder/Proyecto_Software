from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Medicamento, Lote, CodigoQR
from apps.proveedores.models import Proveedor
import secrets, datetime
from django.shortcuts import render, get_object_or_404
# ── MEDICAMENTOS ──────────────────────────────────────────

def medicamento_list(request):
    qs = Medicamento.objects.select_related('id_lote__id_prov').order_by('id_med')
    
    nombre_filter = request.GET.get('nombre', '')
    estado_filter = request.GET.get('estado', '')
    receta_filter = request.GET.get('receta', '')

    if nombre_filter:
        qs = qs.filter(nombre__icontains=nombre_filter)
    if estado_filter:
        qs = qs.filter(estado_colorimetria=estado_filter)
    if receta_filter == 'si':
        qs = qs.filter(requiere_receta=True)
    elif receta_filter == 'no':
        qs = qs.filter(requiere_receta=False)

    # query_params para mantener filtros en paginación
    params = []
    if nombre_filter: params.append(f'&nombre={nombre_filter}')
    if estado_filter: params.append(f'&estado={estado_filter}')
    if receta_filter: params.append(f'&receta={receta_filter}')
    query_params = ''.join(params)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'medicamento/medicamento_list.html', {
        'medicamentos': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'nombre_filter': nombre_filter,
        'estado_filter': estado_filter,
        'receta_filter': receta_filter,
        'query_params': query_params,
    })


def medicamento_detail(request, pk):
    medicamento = get_object_or_404(Medicamento, pk=pk)
    qr_codes = CodigoQR.objects.filter(id_medicamento=medicamento)
    return render(request, 'medicamento/medicamento_detail.html', {
        'medicamento': medicamento,
        'qr_codes': qr_codes,
    })


def medicamento_create(request):
    lotes = Lote.objects.select_related('id_prov').all()
    errors = []

    if request.method == 'POST':
        nombre        = request.POST.get('nombre', '').strip()
        presentacion  = request.POST.get('presentacion', '').strip()
        concentracion = request.POST.get('concentracion', '').strip()
        requiere_receta = request.POST.get('requiere_receta') == 'true'
        fecha_registro  = request.POST.get('fecha_registro') or None
        id_lote_id      = request.POST.get('id_lote')
        estado          = request.POST.get('estado_colorimetria', 'sin_stock')

        if not nombre:
            errors.append('El nombre es obligatorio.')
        if not id_lote_id:
            errors.append('Debe seleccionar un lote.')

        if not errors:
            Medicamento.objects.create(
                nombre=nombre,
                presentacion=presentacion or None,
                concentracion=concentracion or None,
                requiere_receta=requiere_receta,
                fecha_registro=fecha_registro,
                id_lote_id=id_lote_id,
                estado_colorimetria=estado,
            )
            messages.success(request, 'Medicamento registrado correctamente.')
            return redirect('medicamento_list')

    return render(request, 'medicamento/medicamento_form.html', {
        'lotes': lotes,
        'errors': errors,
        'medicamento': None,
    })


def medicamento_update(request, pk):
    medicamento = get_object_or_404(Medicamento, pk=pk)
    lotes = Lote.objects.select_related('id_prov').all()
    errors = []

    if request.method == 'POST':
        nombre        = request.POST.get('nombre', '').strip()
        presentacion  = request.POST.get('presentacion', '').strip()
        concentracion = request.POST.get('concentracion', '').strip()
        requiere_receta = request.POST.get('requiere_receta') == 'true'
        fecha_registro  = request.POST.get('fecha_registro') or None
        id_lote_id      = request.POST.get('id_lote')
        estado          = request.POST.get('estado_colorimetria', 'sin_stock')

        if not nombre:
            errors.append('El nombre es obligatorio.')
        if not id_lote_id:
            errors.append('Debe seleccionar un lote.')

        if not errors:
            medicamento.nombre          = nombre
            medicamento.presentacion    = presentacion or None
            medicamento.concentracion   = concentracion or None
            medicamento.requiere_receta = requiere_receta
            medicamento.fecha_registro  = fecha_registro
            medicamento.id_lote_id      = id_lote_id
            medicamento.estado_colorimetria = estado
            medicamento.save()
            messages.success(request, 'Medicamento actualizado correctamente.')
            return redirect('medicamento_detail', pk=medicamento.pk)

    return render(request, 'medicamento/medicamento_form.html', {
        'medicamento': medicamento,
        'lotes': lotes,
        'errors': errors,
    })


def medicamento_delete(request, pk):
    medicamento = get_object_or_404(Medicamento, pk=pk)
    if request.method == 'POST':
        medicamento.delete()
        messages.success(request, 'Medicamento eliminado.')
        return redirect('medicamento_list')
    return render(request, 'medicamento/medicamento_confirm_detail.html', {
        'medicamento': medicamento,
    })


# ── QR ────────────────────────────────────────────────────

def qr_create(request, med_pk):
    medicamento = get_object_or_404(Medicamento, pk=med_pk)
    token = secrets.token_hex(32)
    CodigoQR.objects.create(
        id_medicamento=medicamento,
        token=token,
        url_qr=f'/qr/{token}/',
        fecha_generacion=datetime.date.today(),
        activo=True,
    )
    messages.success(request, 'Código QR generado.')
    return redirect('medicamento_detail', pk=med_pk)


def qr_regenerar(request, qr_pk):
    qr = get_object_or_404(CodigoQR, pk=qr_pk)
    qr.token = secrets.token_hex(32)
    qr.url_qr = f'/qr/{qr.token}/'
    qr.fecha_regeneracion = datetime.date.today()
    qr.save()
    messages.success(request, 'QR regenerado.')
    return redirect('medicamento_detail', pk=qr.id_medicamento.pk)


def qr_delete(request, qr_pk):
    qr = get_object_or_404(CodigoQR, pk=qr_pk)
    med_pk = qr.id_medicamento.pk
    qr.delete()
    messages.success(request, 'QR eliminado.')
    return redirect('medicamento_detail', pk=med_pk)



# ── LOTES ────────────────────────────────────────────────────

def lote_list(request):
    qs = Lote.objects.select_related('id_prov').order_by('id_lote')
    
    numero_filter = request.GET.get('numero', '') 
    activo_filter = request.GET.get('activo', '')

    if numero_filter:
        qs = qs.filter(numero_lote__icontains=numero_filter)
        
    if activo_filter == 'si':
        qs = qs.filter(activo=True)
    elif activo_filter == 'no':
        qs = qs.filter(activo=False)


    params = []
    if numero_filter: params.append(f'&numero={numero_filter}')
    if activo_filter: params.append(f'&activo={activo_filter}')
    query_params = ''.join(params)

    # Paginación 
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'lote/lote_list.html', {
        'lotes': page_obj,         
        'paginator': paginator,    
        'numero_filter': numero_filter,
        'activo_filter': activo_filter,
        'query_params': query_params,
    })

def lote_detail(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    return render(request, 'lote/lote_detail.html', {'lote': lote})

def lote_create(request):
    proveedores = Proveedor.objects.all()
    errors = []

    if request.method == 'POST':
        # CAPTURAMOS LOS NOMBRES EXACTOS DEL HTML
        numero = request.POST.get('numero_lote', '').strip()
        id_prov_id = request.POST.get('id_prov')
        fecha_cad = request.POST.get('fecha_caducidad') or None
        stock = request.POST.get('stock_actual') or 0
        p_compra = request.POST.get('precio_compra') or None
        p_venta = request.POST.get('precio_venta') or None
        activo = request.POST.get('activo') == 'true'

        # Validaciones
        if not numero:
            errors.append('El número de lote es obligatorio.')
        if not id_prov_id:
            errors.append('Debe seleccionar un proveedor.')

        if not errors:
            try:
                Lote.objects.create(
                    numero_lote=numero, 
                    id_prov_id=id_prov_id,
                    fecha_caducidad=fecha_cad,
                    stock_actual=stock,
                    precio_compra=p_compra,
                    precio_venta=p_venta,
                    activo=activo
                )
                messages.success(request, 'Lote registrado correctamente.')
                return redirect('lote_list')
            except Exception as e:
                errors.append(f"Error en la base de datos: {e}")

    return render(request, 'lote/lote_form.html', {
        'proveedores': proveedores,
        'errors': errors,
        'lote': None # Importante para que el HTML sepa que es "Nuevo"
    })

# ── VISTAS DE LOTES ──────────────────────────────────────────

def lote_update(request, pk):
    lote = get_object_or_404(Lote, pk=pk)
    proveedores = Proveedor.objects.all()
    errors = []

    if request.method == 'POST':
        # Capturamos los datos del formulario
        lote.numero_lote = request.POST.get('numero_lote')
        lote.id_prov_id = request.POST.get('id_prov')
        lote.stock_actual = request.POST.get('stock_actual')
        lote.precio_compra = request.POST.get('precio_compra') or None
        lote.precio_venta = request.POST.get('precio_venta') or None
        lote.fecha_caducidad = request.POST.get('fecha_caducidad') or None
        lote.activo = request.POST.get('activo') == 'true'

        if not lote.numero_lote:
            errors.append("El número de lote es obligatorio.")

        if not errors:
            lote.save()
            messages.success(request, 'Lote actualizado correctamente.')
            return redirect('lote_list')

    return render(request, 'lote/lote_form.html', {
        'lote': lote,
        'proveedores': proveedores,
        'errors': errors
    })

def lote_delete(request, pk):
    # Buscamos el lote o lanzamos error 404 si no existe
    lote = get_object_or_404(Lote, pk=pk)
    
    if request.method == 'POST':
        # Si el usuario le dio al botón de confirmar (envía un POST)
        lote.delete()
        messages.success(request, f'El lote {lote.numero_lote} ha sido eliminado.')
        return redirect('lote_list')
    
    # Si solo entró a la página por primera vez (GET), mostramos la confirmación
    return render(request, 'lote/lote_confirm_delete.html', {
        'lote': lote
    })