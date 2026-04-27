from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import LoginForm, UsuarioForm
from .models import Usuario
from .security import SESSION_USER_ID, first_allowed_path


def home_redirect(request):
    usuario_id = request.session.get(SESSION_USER_ID)
    if not usuario_id:
        return redirect('usuario_login')
    usuario = get_object_or_404(Usuario, pk=usuario_id)
    return redirect(first_allowed_path(usuario))


def usuario_login(request):
    form = LoginForm(request.POST or None)
    next_url = request.GET.get('next') or request.POST.get('next') or ''

    if request.method == 'POST' and form.is_valid():
        usuario_key = form.cleaned_data['usuario'].strip()
        password = form.cleaned_data['password']

        try:
            usuario = Usuario.objects.get(usuario=usuario_key)
        except Usuario.DoesNotExist:
            usuario = None

        if usuario and not usuario.activo:
            messages.warning(request, 'Este usuario esta inhabilitado. Solicita acceso al administrador.')
        elif usuario and usuario.check_password(password):
            request.session[SESSION_USER_ID] = usuario.pk
            usuario.ultima_conexion = timezone.now()
            usuario.save(update_fields=['ultima_conexion'])
            return redirect(next_url or first_allowed_path(usuario))
        else:
            messages.error(request, 'Usuario o contrasena incorrectos.')

    return render(request, 'usuarios/login.html', {
        'form': form,
        'next': next_url,
    })


def usuario_logout(request):
    request.session.pop(SESSION_USER_ID, None)
    messages.success(request, 'Sesion cerrada correctamente.')
    return redirect('usuario_login')


def usuario_list(request):
    return _usuario_list(request, ocultos=False)


def usuario_ocultos(request):
    return _usuario_list(request, ocultos=True)


def _usuario_list(request, ocultos=False):
    usuarios = Usuario.objects.filter(activo=not ocultos)

    q = request.GET.get('q', '').strip()
    rol_filter = request.GET.get('rol', '').strip()
    orden_filter = request.GET.get('orden', 'nombre_asc').strip()
    per_page = 10

    if q:
        usuarios = usuarios.filter(
            Q(nombre__icontains=q)
            | Q(ap_pat__icontains=q)
            | Q(ap_mat__icontains=q)
            | Q(usuario__icontains=q)
        )
    if rol_filter:
        usuarios = usuarios.filter(rol=rol_filter)

    ordenes = {
        'id_asc': 'id_usuario',
        'id_desc': '-id_usuario',
        'usuario_asc': 'usuario',
        'usuario_desc': '-usuario',
        'nombre_asc': 'nombre',
        'nombre_desc': '-nombre',
        'telefono_asc': 'telefono',
        'telefono_desc': '-telefono',
        'puesto_asc': 'puesto',
        'puesto_desc': '-puesto',
        'rol_asc': 'rol',
        'rol_desc': '-rol',
        'estado_asc': 'activo',
        'estado_desc': '-activo',
        'contratacion_asc': 'fecha_contratacion',
        'contratacion_desc': '-fecha_contratacion',
        'conexion_asc': 'ultima_conexion',
        'conexion_desc': '-ultima_conexion',
    }
    usuarios = usuarios.order_by(ordenes.get(orden_filter, 'nombre'), 'ap_pat', 'ap_mat')

    query_params = ''
    if q: query_params += f'&q={q}'
    if rol_filter: query_params += f'&rol={rol_filter}'
    filter_query_params = query_params
    if orden_filter: query_params += f'&orden={orden_filter}'
    paginator = Paginator(usuarios, per_page)
    try:
        page_obj = paginator.page(request.GET.get('page', 1))
    except Exception:
        page_obj = paginator.page(1)

    return render(request, 'usuarios/usuario_list.html', {
        'object_list': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'ocultos': ocultos,
        'q': q,
        'rol_filtro': rol_filter,
        'roles': Usuario.ROL_CHOICES,
        'orden': orden_filter,
        'orden_filter': orden_filter,
        'query_params': query_params,
        'filter_query_params': filter_query_params,
    })


def usuario_detail(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    ventas_recientes = usuario.venta_set.select_related(
        'id_metPag', 'id_cliente'
    ).order_by('-fecha_venta')[:10]

    return render(request, 'usuarios/usuario_detail.html', {
        'object': usuario,
        'usuario': usuario,
        'ventas_recientes': ventas_recientes,
    })


def usuario_create(request):
    form = UsuarioForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        return redirect('usuario_detail', pk=usuario.pk)

    return render(request, 'usuarios/usuario_form.html', {'form': form})


def usuario_update(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    form = UsuarioForm(request.POST or None, instance=usuario)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('usuario_detail', pk=pk)

    return render(request, 'usuarios/usuario_form.html', {
        'form': form,
        'usuario': usuario,
    })


def usuario_delete(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    ventas_count = usuario.venta_set.count()

    if request.method == 'POST':
        accion = request.POST.get('accion', 'eliminar')

        if accion == 'desactivar':
            usuario.activo = False
            usuario.fecha_baja = usuario.fecha_baja or timezone.now().date()
            usuario.save(update_fields=['activo', 'fecha_baja'])
            messages.warning(
                request,
                f'{usuario.nombre_completo()} fue inhabilitado. Sus ventas historicas se conservaron.'
            )
            return redirect('usuario_ocultos')

        try:
            usuario.delete()
        except ProtectedError:
            messages.warning(
                request,
                'No se puede eliminar este usuario porque tiene ventas registradas. '
                'Puedes inhabilitarlo para que no aparezca en nuevas ventas.'
            )
            return redirect('usuario_delete', pk=pk)

        messages.success(request, 'Usuario eliminado correctamente.')
        return redirect('usuario_list')

    return render(request, 'usuarios/usuario_confirm_delete.html', {
        'object': usuario,
        'usuario': usuario,
        'ventas_count': ventas_count,
    })


def usuario_restaurar(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        usuario.activo = True
        usuario.fecha_baja = None
        usuario.save(update_fields=['activo', 'fecha_baja'])
        messages.success(request, f'{usuario.nombre_completo()} fue restaurado como usuario activo.')
    return redirect('usuario_ocultos')
