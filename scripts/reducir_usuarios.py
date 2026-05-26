import os
import sys
from datetime import date, datetime

import django
from django.utils import timezone


sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmacia.settings')
django.setup()

from apps.usuarios.models import Usuario
from apps.ventas.models import Venta


VENDEDORES = [
    ('marina', 'Marina', 'Lopez', 'Diaz'),
    ('arturo', 'Arturo', 'Garcia', 'Nava'),
    ('cajero03', 'Daniela', 'Pineda', 'Salazar'),
    ('cajero04', 'Carlos', 'Ramirez', 'Torres'),
    ('cajero05', 'Sofia', 'Mendoza', 'Rios'),
    ('cajero06', 'Miguel', 'Sanchez', 'Cruz'),
    ('cajero07', 'Laura', 'Flores', 'Vega'),
    ('cajero08', 'Diego', 'Castillo', 'Morales'),
    ('cajero09', 'Paola', 'Ortega', 'Reyes'),
    ('cajero10', 'Ricardo', 'Navarro', 'Campos'),
    ('cajero11', 'Valeria', 'Cervantes', 'Aguilar'),
    ('cajero12', 'Fernando', 'Vargas', 'Mora'),
    ('cajero13', 'Camila', 'Contreras', 'Leon'),
    ('cajero14', 'Luis', 'Dominguez', 'Santos'),
    ('cajero15', 'Elena', 'Rangel', 'Figueroa'),
    ('cajero16', 'Roberto', 'Cortes', 'Mejia'),
    ('cajero17', 'Mariana', 'Arias', 'Nunez'),
    ('cajero18', 'Gabriela', 'Fuentes', 'Padilla'),
    ('cajero19', 'Hector', 'Luna', 'Valdez'),
    ('cajero20', 'Monica', 'Bravo', 'Herrera'),
]

ALMACEN = [
    ('almacen01', 'Adriana', 'Alvarez', 'Mora'),
    ('almacen02', 'Raul', 'Cabrera', 'Ibarra'),
    ('almacen03', 'Patricia', 'Espinoza', 'Orozco'),
    ('almacen04', 'Alejandro', 'Medina', 'Carrillo'),
    ('almacen05', 'Claudia', 'Robles', 'Silva'),
    ('almacen06', 'Oscar', 'Acosta', 'Bautista'),
]

ADMINISTRADORES = [
    ('admin01', 'Lucia', 'Mendoza', 'Rios'),
    ('admin02', 'Natalia', 'Molina', 'Juarez'),
    ('admin03', 'Eduardo', 'Quintero', 'Velasco'),
]


def main():
    keep = []
    user = upsert_usuario(
        username='user',
        nombre='User',
        ap_pat='Administrador',
        ap_mat='Demo',
        rol=Usuario.ROL_ADMINISTRADOR,
        puesto='Administrador general',
        password='12345',
        index=0,
    )
    keep.append(user)

    for index, data in enumerate(ADMINISTRADORES, start=1):
        keep.append(upsert_usuario(*data, rol=Usuario.ROL_ADMINISTRADOR, puesto='Administrador', password='Password123!', index=index))

    for index, data in enumerate(ALMACEN, start=10):
        keep.append(upsert_usuario(*data, rol=Usuario.ROL_ALMACEN, puesto='Almacen', password='Password123!', index=index))

    cajeros = []
    for index, data in enumerate(VENDEDORES, start=20):
        cajero = upsert_usuario(*data, rol=Usuario.ROL_CAJERO, puesto='Cajero vendedor', password='Password123!', index=index)
        keep.append(cajero)
        cajeros.append(cajero)

    ventas = list(Venta.objects.order_by('id_ventas'))
    for index, venta in enumerate(ventas):
        venta.id_usuario = cajeros[index % len(cajeros)]
        venta.save(update_fields=['id_usuario'])

    ids_keep = [usuario.id_usuario for usuario in keep]
    borrados = Usuario.objects.exclude(id_usuario__in=ids_keep).delete()[0]

    print({
        'usuarios_restantes': Usuario.objects.count(),
        'usuarios_borrados': borrados,
        'ventas_reasignadas': len(ventas),
        'administradores': Usuario.objects.filter(rol=Usuario.ROL_ADMINISTRADOR).count(),
        'almacen': Usuario.objects.filter(rol=Usuario.ROL_ALMACEN).count(),
        'vendedores': Usuario.objects.filter(rol=Usuario.ROL_CAJERO).count(),
        'login': 'user / 12345',
    })


def upsert_usuario(username, nombre, ap_pat, ap_mat, rol, puesto, password, index):
    usuario, _ = Usuario.objects.get_or_create(usuario=username)
    usuario.nombre = nombre
    usuario.ap_pat = ap_pat
    usuario.ap_mat = ap_mat
    usuario.rol = rol
    usuario.telefono = f'31260{index:05d}'[:10]
    usuario.puesto = puesto
    usuario.fecha_creacion = date(2024, (index % 12) + 1, min((index * 2) + 1, 28))
    usuario.fecha_contratacion = date(2024, (index % 12) + 1, min((index * 2) + 3, 28))
    usuario.fecha_baja = None
    usuario.ultima_conexion = timezone.make_aware(datetime(2026, (index % 12) + 1, min((index * 2) + 1, 28), 9, 30))
    usuario.activo = True
    usuario.set_password(password)
    usuario.save()
    return usuario


if __name__ == '__main__':
    main()
