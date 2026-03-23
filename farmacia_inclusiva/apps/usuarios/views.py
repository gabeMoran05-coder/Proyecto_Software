from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Usuario
from .forms import UsuarioForm, LoginForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect('medicamentos:lista')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )
        if user:
            login(request, user)
            user.ultima_conexion = timezone.now()
            user.save(update_fields=['ultima_conexion'])
            return redirect('medicamentos:lista')
        messages.error(request, 'Credenciales incorrectas.')
    return render(request, 'usuarios/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('usuarios:login')


@login_required
def lista(request):
    if request.user.rol != 'admin':
        messages.error(request, 'Sin acceso.')
        return redirect('medicamentos:lista')
    usuarios = Usuario.objects.all()
    return render(request, 'usuarios/lista.html', {'usuarios': usuarios})


@login_required
def crear(request):
    if request.user.rol != 'admin':
        return redirect('medicamentos:lista')
    form = UsuarioForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        u = form.save(commit=False)
        u.set_password(form.cleaned_data['password'])
        u.save()
        messages.success(request, 'Usuario creado correctamente.')
        return redirect('usuarios:lista')
    return render(request, 'usuarios/form.html', {'form': form, 'titulo': 'Nuevo usuario'})


@login_required
def editar(request, pk):
    if request.user.rol != 'admin':
        return redirect('medicamentos:lista')
    usuario = get_object_or_404(Usuario, pk=pk)
    form = UsuarioForm(request.POST or None, instance=usuario)
    if request.method == 'POST' and form.is_valid():
        u = form.save(commit=False)
        pwd = form.cleaned_data.get('password')
        if pwd:
            u.set_password(pwd)
        u.save()
        messages.success(request, 'Usuario actualizado.')
        return redirect('usuarios:lista')
    return render(request, 'usuarios/form.html', {'form': form, 'titulo': 'Editar usuario'})


@login_required
def eliminar(request, pk):
    if request.user.rol != 'admin':
        return redirect('medicamentos:lista')
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        usuario.delete()
        messages.success(request, 'Usuario eliminado.')
        return redirect('usuarios:lista')
    return render(request, 'usuarios/confirmar_eliminar.html', {'objeto': usuario})
