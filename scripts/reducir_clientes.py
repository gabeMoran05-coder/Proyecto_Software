import os
import sys
from datetime import date

import django


sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmacia.settings')
django.setup()

from apps.clientes.models import Cliente
from apps.ventas.models import Venta


CLIENTES_REALES = [
    ('Maria Fernanda', 'Gonzalez', 'Lopez', '3121456780'),
    ('Jose Antonio', 'Martinez', 'Perez', '3121456781'),
    ('Ana Lucia', 'Hernandez', 'Ruiz', '3121456782'),
    ('Carlos Alberto', 'Ramirez', 'Torres', '3121456783'),
    ('Laura Isabel', 'Flores', 'Vega', '3121456784'),
    ('Miguel Angel', 'Sanchez', 'Cruz', '3121456785'),
    ('Sofia Elena', 'Mendoza', 'Rios', '3121456786'),
    ('Diego Armando', 'Garcia', 'Nava', '3121456787'),
    ('Paola Andrea', 'Castillo', 'Morales', '3121456788'),
    ('Ricardo Javier', 'Ortega', 'Reyes', '3121456789'),
    ('Valeria', 'Navarro', 'Campos', '3122456780'),
    ('Fernando', 'Cervantes', 'Aguilar', '3122456781'),
    ('Daniela', 'Pineda', 'Salazar', '3122456782'),
    ('Jorge Luis', 'Vargas', 'Mora', '3122456783'),
    ('Camila', 'Contreras', 'Leon', '3122456784'),
    ('Luis Enrique', 'Dominguez', 'Santos', '3122456785'),
    ('Elena', 'Rangel', 'Figueroa', '3122456786'),
    ('Roberto', 'Cortes', 'Mejia', '3122456787'),
    ('Mariana', 'Arias', 'Nunez', '3122456788'),
    ('Arturo', 'Delgado', 'Soto', '3122456789'),
    ('Gabriela', 'Fuentes', 'Padilla', '3123456780'),
    ('Hector', 'Luna', 'Valdez', '3123456781'),
    ('Monica', 'Bravo', 'Herrera', '3123456782'),
    ('Raul', 'Cabrera', 'Ibarra', '3123456783'),
    ('Patricia', 'Espinoza', 'Orozco', '3123456784'),
    ('Alejandro', 'Medina', 'Carrillo', '3123456785'),
    ('Claudia', 'Robles', 'Silva', '3123456786'),
    ('Oscar', 'Acosta', 'Bautista', '3123456787'),
    ('Natalia', 'Molina', 'Juarez', '3123456788'),
    ('Eduardo', 'Quintero', 'Velasco', '3123456789'),
    ('Beatriz', 'Serrano', 'Zamora', '3124456780'),
    ('Ivan', 'Miranda', 'Rosales', '3124456781'),
    ('Carolina', 'Montes', 'Escobar', '3124456782'),
    ('Emmanuel', 'Saucedo', 'Galindo', '3124456783'),
    ('Adriana', 'Villanueva', 'Pacheco', '3124456784'),
    ('Sebastian', 'Palacios', 'Macias', '3124456785'),
    ('Diana', 'Esquivel', 'Benitez', '3124456786'),
    ('Francisco', 'Sepulveda', 'Cano', '3124456787'),
    ('Lorena', 'Corona', 'Solorio', '3124456788'),
    ('Andres', 'Cisneros', 'Tapia', '3124456789'),
    ('Veronica', 'Barrera', 'Mendez', '3125456780'),
    ('Rafael', 'Gallardo', 'Ponce', '3125456781'),
    ('Teresa', 'Zuniga', 'Arellano', '3125456782'),
    ('Omar', 'Valencia', 'Cordero', '3125456783'),
    ('Silvia', 'Camacho', 'Beltran', '3125456784'),
    ('Pablo', 'Trejo', 'Castañeda', '3125456785'),
    ('Rosa Maria', 'Alvarez', 'Farias', '3125456786'),
    ('Julian', 'Maldonado', 'Miramontes', '3125456787'),
    ('Karla', 'Salinas', 'Franco', '3125456788'),
    ('Manuel', 'Cuevas', 'Arce', '3125456789'),
]


def main():
    actuales = list(Cliente.objects.order_by('id_cliente'))
    keep = []

    for index, (nombre, ap_pat, ap_mat, telefono) in enumerate(CLIENTES_REALES):
        cliente = actuales[index] if index < len(actuales) else Cliente()
        cliente.nombre = nombre
        cliente.ap_pat = ap_pat
        cliente.ap_mat = ap_mat
        cliente.telefono = telefono
        cliente.fecha_registro = date(2023 + (index % 4), (index % 12) + 1, min((index * 2) + 1, 28))
        cliente.save()
        keep.append(cliente)

    ventas = list(Venta.objects.exclude(id_cliente__isnull=True).order_by('id_ventas'))
    for index, venta in enumerate(ventas):
        venta.id_cliente = keep[index % len(keep)]
        venta.save(update_fields=['id_cliente'])

    borrados = Cliente.objects.exclude(id_cliente__in=[cliente.id_cliente for cliente in keep]).delete()[0]

    print({
        'clientes_restantes': Cliente.objects.count(),
        'clientes_borrados': borrados,
        'ventas_reasignadas': len(ventas),
    })


if __name__ == '__main__':
    main()
