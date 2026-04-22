import os
import sys
from datetime import date, datetime
from decimal import Decimal

import django
from django.urls import reverse
from django.utils import timezone


sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmacia.settings')
django.setup()

from apps.clientes.models import Cliente
from apps.medicamentos.models import CodigoQR, Lote, Medicamento
from apps.proveedores.models import Proveedor
from apps.usuarios.models import Usuario
from apps.ventas.models import DetalleVenta, MetodoPago, Venta


def upsert(model, lookup, defaults=None):
    obj, created = model.objects.update_or_create(**lookup, defaults=defaults or {})
    return obj, created


def main():
    print('Cargando datos de prueba realistas...')

    proveedores_data = [
        {
            'nombre': 'Laboratorios Pisa',
            'telefono': '3331234567',
            'correo': 'ventas@pisa.com.mx',
            'direccion': 'Av. Espana 1840, Guadalajara, Jalisco',
        },
        {
            'nombre': 'Nadro S.A.P.I.',
            'telefono': '5551234567',
            'correo': 'contacto@nadro.com.mx',
            'direccion': 'Av. Insurgentes Sur 863, Ciudad de Mexico',
        },
        {
            'nombre': 'Farmacos Nacionales',
            'telefono': '8181234567',
            'correo': 'pedidos@farmacosnacionales.mx',
            'direccion': 'Av. Gonzalitos 600, Monterrey, Nuevo Leon',
        },
        {
            'nombre': 'Laboratorios Silanes',
            'telefono': '5559876543',
            'correo': 'atencion@silanes.com.mx',
            'direccion': 'Periferico Sur 3395, Ciudad de Mexico',
        },
        {
            'nombre': 'Medix Farmaceutica',
            'telefono': '3339876543',
            'correo': 'servicio@medix.com.mx',
            'direccion': 'Av. Lopez Mateos Sur 2077, Zapopan, Jalisco',
        },
    ]

    proveedores = []
    for data in proveedores_data:
        proveedor, _ = upsert(
            Proveedor,
            {'nombre': data['nombre']},
            {
                'telefono': data['telefono'],
                'correo': data['correo'],
                'direccion': data['direccion'],
            },
        )
        proveedores.append(proveedor)
    print(f'- Proveedores listos: {len(proveedores)}')

    clientes_data = [
        ('Maria', 'Gonzalez', 'Lopez', date(2024, 1, 15), '3121234567'),
        ('Jose', 'Martinez', 'Perez', date(2024, 2, 20), '3129876543'),
        ('Ana', 'Hernandez', 'Ruiz', date(2024, 3, 10), '3123456789'),
        ('Carlos', 'Ramirez', 'Torres', date(2024, 4, 5), '3127654321'),
        ('Laura', 'Flores', 'Vega', date(2024, 5, 18), '3125551234'),
    ]

    clientes = []
    for nombre, ap_pat, ap_mat, fecha_registro, telefono in clientes_data:
        cliente, _ = upsert(
            Cliente,
            {'nombre': nombre, 'ap_pat': ap_pat},
            {
                'ap_mat': ap_mat,
                'fecha_registro': fecha_registro,
                'telefono': telefono,
            },
        )
        clientes.append(cliente)
    print(f'- Clientes listos: {len(clientes)}')

    usuarios_data = [
        ('jperez', 'Juan', 'Perez', 'Soto', 'farmaceutico', '3121112233'),
        ('mlopez', 'Marina', 'Lopez', 'Diaz', 'cajero', '3122223344'),
        ('rsanchez', 'Roberto', 'Sanchez', 'Cruz', 'farmaceutico', '3123334455'),
        ('lmendoza', 'Lucia', 'Mendoza', 'Rios', 'administrador', '3124445566'),
        ('agarcia', 'Arturo', 'Garcia', 'Nava', 'cajero', '3125556677'),
        ('aalmacen', 'Adriana', 'Alvarez', 'Mora', 'almacen', '3126667788'),
    ]

    usuarios = []
    for usuario_key, nombre, ap_pat, ap_mat, rol, telefono in usuarios_data:
        usuario, _ = upsert(
            Usuario,
            {'usuario': usuario_key},
            {
                'nombre': nombre,
                'ap_pat': ap_pat,
                'ap_mat': ap_mat,
                'rol': rol,
                'telefono': telefono,
                'fecha_creacion': date(2024, 1, 10),
                'ultima_conexion': timezone.make_aware(datetime(2026, 4, 18, 9, 30)),
            },
        )
        usuario.set_password('Password123!')
        usuario.save(update_fields=['password_hash'])
        usuarios.append(usuario)
    print(f'- Usuarios listos: {len(usuarios)}')

    metodos_data = [
        ('Efectivo', 'Pago en caja con moneda nacional'),
        ('Tarjeta de debito', 'Pago con terminal bancaria'),
        ('Tarjeta de credito', 'Pago con tarjeta bancaria'),
        ('Transferencia SPEI', 'Transferencia bancaria inmediata'),
        ('Vales de despensa', 'Vales aceptados por la farmacia'),
    ]

    metodos = []
    for nombre_metodo, descripcion in metodos_data:
        metodo, _ = upsert(
            MetodoPago,
            {'nombre_metodo': nombre_metodo},
            {'descripcion': descripcion},
        )
        metodos.append(metodo)
    print(f'- Metodos de pago listos: {len(metodos)}')

    lotes_data = [
        (proveedores[0], 'PISA-2026-001', date(2025, 12, 1), date(2027, 12, 1), 120, Decimal('85.50'), Decimal('125.00')),
        (proveedores[1], 'NADRO-2026-015', date(2025, 11, 15), date(2027, 11, 15), 95, Decimal('32.00'), Decimal('58.00')),
        (proveedores[2], 'FN-2026-032', date(2025, 10, 10), date(2027, 10, 10), 65, Decimal('44.00'), Decimal('79.00')),
        (proveedores[3], 'SIL-2026-008', date(2025, 9, 20), date(2027, 9, 20), 80, Decimal('120.00'), Decimal('168.00')),
        (proveedores[4], 'MDX-2026-021', date(2025, 8, 5), date(2027, 8, 5), 70, Decimal('38.00'), Decimal('69.00')),
    ]

    lotes = []
    for proveedor, numero, fabricacion, caducidad, stock, compra, venta in lotes_data:
        lote, _ = upsert(
            Lote,
            {'numero_lote': numero},
            {
                'id_prov': proveedor,
                'fecha_fabricacion': fabricacion,
                'fecha_caducidad': caducidad,
                'fecha_ingreso': date(2026, 1, 15),
                'stock_actual': stock,
                'activo': True,
                'fecha_compra': date(2026, 1, 12),
                'precio_compra': compra,
                'precio_venta': venta,
            },
        )
        lotes.append(lote)
    print(f'- Lotes listos: {len(lotes)}')

    medicamentos_data = [
        (lotes[0], 'Amoxicilina 500 mg', 'Capsulas caja c/12', '500 mg', True, 'verde'),
        (lotes[1], 'Paracetamol 500 mg', 'Tabletas caja c/20', '500 mg', False, 'verde'),
        (lotes[2], 'Ibuprofeno 400 mg', 'Tabletas caja c/10', '400 mg', False, 'amarillo'),
        (lotes[3], 'Metformina 850 mg', 'Tabletas caja c/30', '850 mg', True, 'verde'),
        (lotes[4], 'Loratadina 10 mg', 'Tabletas caja c/10', '10 mg', False, 'verde'),
    ]

    medicamentos = []
    for lote, nombre, presentacion, concentracion, requiere_receta, color in medicamentos_data:
        medicamento, _ = upsert(
            Medicamento,
            {'nombre': nombre},
            {
                'id_lote': lote,
                'presentacion': presentacion,
                'concentracion': concentracion,
                'requiere_receta': requiere_receta,
                'fecha_registro': date(2026, 1, 16),
                'estado_colorimetria': color,
            },
        )
        medicamentos.append(medicamento)
    print(f'- Medicamentos listos: {len(medicamentos)}')

    for index, medicamento in enumerate(medicamentos, start=1):
        upsert(
            CodigoQR,
            {'token': f'DEMO-QR-{index:03d}-{medicamento.id_med}'},
            {
                'id_medicamento': medicamento,
                'url_qr': reverse('qr_scan', kwargs={'token': f'DEMO-QR-{index:03d}-{medicamento.id_med}'}),
                'fecha_generacion': date(2026, 1, 16),
                'fecha_regeneracion': None,
                'contador_escaneos': index * 3,
                'activo': True,
            },
        )
    print('- Codigos QR listos: 5')

    ventas_data = [
        (usuarios[1], metodos[0], clientes[0], datetime(2026, 4, 14, 10, 30), [(medicamentos[1], 2), (medicamentos[4], 1)]),
        (usuarios[4], metodos[1], clientes[1], datetime(2026, 4, 15, 11, 15), [(medicamentos[0], 1)]),
        (usuarios[1], metodos[2], clientes[2], datetime(2026, 4, 16, 12, 0), [(medicamentos[2], 2)]),
        (usuarios[4], metodos[3], clientes[3], datetime(2026, 4, 17, 9, 45), [(medicamentos[3], 1)]),
        (usuarios[1], metodos[4], clientes[4], datetime(2026, 4, 18, 14, 20), [(medicamentos[0], 1), (medicamentos[1], 1)]),
    ]

    ventas_creadas = []
    for index, (usuario, metodo, cliente, fecha, lineas) in enumerate(ventas_data, start=1):
        fecha_aware = timezone.make_aware(fecha)
        total = sum(med.id_lote.precio_venta * cantidad for med, cantidad in lineas)
        venta, _ = upsert(
            Venta,
            {'id_usuario': usuario, 'fecha_venta': fecha_aware},
            {
                'id_metPag': metodo,
                'id_cliente': cliente,
                'total_venta': total,
            },
        )
        venta.detalleventa_set.all().delete()
        for medicamento, cantidad in lineas:
            precio = medicamento.id_lote.precio_venta
            DetalleVenta.objects.create(
                id_ventas=venta,
                id_medicamento=medicamento,
                cantidad=cantidad,
                precio_unitario=precio,
                subtotal=precio * cantidad,
            )
        ventas_creadas.append(venta)
        print(f'  Venta demo {index}: #{venta.id_ventas} total ${total}')

    print(f'- Ventas listas: {len(ventas_creadas)}')
    print('\nDatos de prueba cargados correctamente.')


if __name__ == '__main__':
    main()
