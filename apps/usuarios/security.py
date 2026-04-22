from django.shortcuts import redirect

from .models import Usuario


SESSION_USER_ID = 'usuario_id'

PUBLIC_PATHS = (
    '/usuarios/login/',
    '/admin/',
    '/static/',
    '/medicamentos/qr/leer/',
    '/ventas/ticket/',
)

ROLE_PATHS = {
    Usuario.ROL_CAJERO: (
        '/ventas/',
        '/clientes/',
        '/medicamentos/',
    ),
    Usuario.ROL_ALMACEN: (
        '/medicamentos/',
        '/proveedores/',
    ),
    Usuario.ROL_FARMACEUTICO: (
        '/medicamentos/',
        '/proveedores/',
    ),
}

CAJERO_BLOCKED_PATH_PARTS = (
    '/medicamentos/nuevo/',
    '/editar/',
    '/eliminar/',
    '/ocultar/',
    '/restaurar/',
    '/medicamentos/lotes/',
    '/medicamentos/qr/',
)


def get_current_usuario(request):
    cached = getattr(request, '_current_usuario', None)
    if cached is not None:
        return cached

    user_id = request.session.get(SESSION_USER_ID)
    if not user_id:
        request._current_usuario = None
        return None

    try:
        usuario = Usuario.objects.get(pk=user_id)
    except Usuario.DoesNotExist:
        request.session.pop(SESSION_USER_ID, None)
        usuario = None

    request._current_usuario = usuario
    return usuario


def can_access_path(usuario, path):
    if usuario is None:
        return False
    if not usuario.activo:
        return False
    if path == '/':
        return True
    if usuario.es_admin():
        return True

    if usuario.rol_normalizado() == Usuario.ROL_CAJERO:
        if any(part in path for part in CAJERO_BLOCKED_PATH_PARTS):
            return False

    allowed_paths = ROLE_PATHS.get(usuario.rol_normalizado(), ())
    return any(path == allowed or path.startswith(allowed) for allowed in allowed_paths)


def first_allowed_path(usuario):
    if usuario is None:
        return '/usuarios/login/'
    if usuario.es_admin():
        return '/medicamentos/'

    allowed_paths = ROLE_PATHS.get(usuario.rol_normalizado(), ('/usuarios/login/',))
    for path in allowed_paths:
        if path != '/':
            return path
    return allowed_paths[0]


class UsuarioAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        is_public_qr_image = path.startswith('/medicamentos/qr/') and path.endswith('/imagen/')

        if is_public_qr_image or any(path.startswith(public) for public in PUBLIC_PATHS):
            return self.get_response(request)

        usuario = get_current_usuario(request)
        if usuario is None:
            return redirect(f'/usuarios/login/?next={path}')
        if not usuario.activo:
            request.session.pop(SESSION_USER_ID, None)
            return redirect('/usuarios/login/')

        if path == '/usuarios/logout/':
            return self.get_response(request)

        if not can_access_path(usuario, path):
            return redirect(first_allowed_path(usuario))

        return self.get_response(request)


def usuario_context(request):
    usuario = get_current_usuario(request)
    return {
        'current_usuario': usuario,
        'current_usuario_is_admin': bool(usuario and usuario.es_admin()),
        'current_usuario_role': usuario.rol_normalizado() if usuario else '',
    }
