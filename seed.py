import os
import random
import sys
from datetime import date, datetime, timedelta
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


random.seed(23042026)

NOMBRES = [
    'Ana', 'Carlos', 'Marina', 'Arturo', 'Lucia', 'Roberto', 'Gabriel', 'Sofia',
    'Valeria', 'Diego', 'Fernando', 'Daniela', 'Miguel', 'Andrea', 'Jorge',
    'Camila', 'Luis', 'Paola', 'Ricardo', 'Elena',
]
APELLIDOS = [
    'Garcia', 'Lopez', 'Hernandez', 'Martinez', 'Perez', 'Gonzalez', 'Ramirez',
    'Torres', 'Flores', 'Vega', 'Sanchez', 'Mendoza', 'Rios', 'Nava', 'Cruz',
    'Ruiz', 'Morales', 'Castillo', 'Ortega', 'Reyes',
]
CIUDADES = [
    'Colima', 'Guadalajara', 'Monterrey', 'Ciudad de Mexico', 'Zapopan',
    'Manzanillo', 'Morelia', 'Queretaro', 'Puebla', 'Leon',
]
MEDICAMENTOS_BASE = [
    ('Amoxicilina', 'Capsulas caja c/12', '500 mg', True, Decimal('82.00'), Decimal('125.00')),
    ('Paracetamol', 'Tabletas caja c/20', '500 mg', False, Decimal('31.50'), Decimal('60.00')),
    ('Ibuprofeno', 'Tabletas caja c/10', '400 mg', False, Decimal('42.00'), Decimal('79.00')),
    ('Loratadina', 'Tabletas caja c/10', '10 mg', False, Decimal('37.00'), Decimal('69.00')),
    ('Metformina', 'Tabletas caja c/30', '850 mg', True, Decimal('115.00'), Decimal('168.00')),
    ('Omeprazol', 'Capsulas caja c/14', '20 mg', False, Decimal('32.00'), Decimal('59.00')),
    ('Ambroxol', 'Frasco 120 ml', '30 mg/5 ml', False, Decimal('25.00'), Decimal('59.00')),
    ('Naproxeno', 'Tabletas caja c/20', '250 mg', False, Decimal('33.00'), Decimal('59.00')),
    ('Cetirizina', 'Tabletas caja c/10', '10 mg', False, Decimal('29.00'), Decimal('59.00')),
    ('Diclofenaco', 'Tabletas caja c/20', '100 mg', False, Decimal('40.00'), Decimal('75.00')),
]
METODOS_BASE = [
    ('Efectivo', 'Pago en caja con moneda nacional'),
    ('Tarjeta de debito', 'Pago con terminal bancaria'),
    ('Tarjeta de credito', 'Pago con tarjeta bancaria'),
    ('Transferencia SPEI', 'Transferencia bancaria inmediata'),
    ('Vales de despensa', 'Vales aceptados por la farmacia'),
]


def main():
    print('Reiniciando base de datos de prueba...')
    limpiar_datos()

    proveedores = crear_proveedores()
    clientes = crear_clientes()
    usuarios = crear_usuarios()
    metodos = crear_metodos_pago()
    lotes, medicamentos = crear_lotes_y_medicamentos(proveedores)
    crear_qr(medicamentos)
    crear_ventas(usuarios, clientes, metodos, medicamentos)

    print('\nDatos cargados:')
    print(f'- Proveedores: {Proveedor.objects.count()}')
    print(f'- Clientes: {Cliente.objects.count()}')
    print(f'- Usuarios: {Usuario.objects.count()}')
    print(f'- Metodos de pago: {MetodoPago.objects.count()}')
    print(f'- Lotes: {Lote.objects.count()}')
    print(f'- Medicamentos: {Medicamento.objects.count()}')
    print(f'- Codigos QR: {CodigoQR.objects.count()}')
    print(f'- Ventas: {Venta.objects.count()}')
    print(f'- Detalles de venta: {DetalleVenta.objects.count()}')
    print('\nListo. Usuario admin demo: lucia / Password123!')


def limpiar_datos():
    DetalleVenta.objects.all().delete()
    Venta.objects.all().delete()
    CodigoQR.objects.all().delete()
    Medicamento.objects.all().delete()
    Lote.objects.all().delete()
    MetodoPago.objects.all().delete()
    Cliente.objects.all().delete()
    Usuario.objects.all().delete()
    Proveedor.objects.all().delete()
    print('- Datos anteriores eliminados.')


def crear_proveedores():
    proveedores_reales = [
        ('Laboratorios Pisa', '3331234567', 'ventas@pisa.com.mx', 'Av. Espana 1840, Guadalajara, Jalisco'),
        ('Nadro S.A.P.I.', '5551234567', 'contacto@nadro.com.mx', 'Av. Insurgentes Sur 863, Ciudad de Mexico'),
        ('Farmacos Nacionales', '8181234567', 'pedidos@farmacosnacionales.mx', 'Av. Gonzalitos 600, Monterrey, Nuevo Leon'),
        ('Laboratorios Silanes', '5559876543', 'atencion@silanes.com.mx', 'Periferico Sur 3395, Ciudad de Mexico'),
        ('Medix Farmaceutica', '3339876543', 'servicio@medix.com.mx', 'Av. Lopez Mateos Sur 2077, Zapopan, Jalisco'),
    ]
    proveedores = []
    for nombre, telefono, correo, direccion in proveedores_reales:
        proveedores.append(Proveedor.objects.create(
            nombre=nombre,
            telefono=telefono,
            correo=correo,
            direccion=direccion,
            activo=True,
        ))
    print(f'- Proveedores creados: {len(proveedores)}')
    return proveedores


def crear_clientes():
    clientes_reales = [
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
        ('Pablo', 'Trejo', 'Castaneda', '3125456785'),
        ('Rosa Maria', 'Alvarez', 'Farias', '3125456786'),
        ('Julian', 'Maldonado', 'Miramontes', '3125456787'),
        ('Karla', 'Salinas', 'Franco', '3125456788'),
        ('Manuel', 'Cuevas', 'Arce', '3125456789'),
    ]
    clientes = []
    for index, (nombre, ap_pat, ap_mat, telefono) in enumerate(clientes_reales):
        clientes.append(Cliente.objects.create(
            nombre=nombre,
            ap_pat=ap_pat,
            ap_mat=ap_mat,
            fecha_registro=date(2023 + (index % 4), (index % 12) + 1, min((index * 2) + 1, 28)),
            telefono=telefono,
        ))
    print(f'- Clientes creados: {len(clientes)}')
    return clientes


def crear_usuarios():
    usuarios = []
    usuarios_data = [
        ('user', 'User', 'Administrador', 'Demo', Usuario.ROL_ADMINISTRADOR, 'Administrador general', '12345'),
        ('admin01', 'Lucia', 'Mendoza', 'Rios', Usuario.ROL_ADMINISTRADOR, 'Administrador', 'Password123!'),
        ('admin02', 'Natalia', 'Molina', 'Juarez', Usuario.ROL_ADMINISTRADOR, 'Administrador', 'Password123!'),
        ('admin03', 'Eduardo', 'Quintero', 'Velasco', Usuario.ROL_ADMINISTRADOR, 'Administrador', 'Password123!'),
        ('almacen01', 'Adriana', 'Alvarez', 'Mora', Usuario.ROL_ALMACEN, 'Almacen', 'Password123!'),
        ('almacen02', 'Raul', 'Cabrera', 'Ibarra', Usuario.ROL_ALMACEN, 'Almacen', 'Password123!'),
        ('almacen03', 'Patricia', 'Espinoza', 'Orozco', Usuario.ROL_ALMACEN, 'Almacen', 'Password123!'),
        ('almacen04', 'Alejandro', 'Medina', 'Carrillo', Usuario.ROL_ALMACEN, 'Almacen', 'Password123!'),
        ('almacen05', 'Claudia', 'Robles', 'Silva', Usuario.ROL_ALMACEN, 'Almacen', 'Password123!'),
        ('almacen06', 'Oscar', 'Acosta', 'Bautista', Usuario.ROL_ALMACEN, 'Almacen', 'Password123!'),
        ('marina', 'Marina', 'Lopez', 'Diaz', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('arturo', 'Arturo', 'Garcia', 'Nava', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero03', 'Daniela', 'Pineda', 'Salazar', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero04', 'Carlos', 'Ramirez', 'Torres', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero05', 'Sofia', 'Mendoza', 'Rios', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero06', 'Miguel', 'Sanchez', 'Cruz', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero07', 'Laura', 'Flores', 'Vega', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero08', 'Diego', 'Castillo', 'Morales', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero09', 'Paola', 'Ortega', 'Reyes', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero10', 'Ricardo', 'Navarro', 'Campos', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero11', 'Valeria', 'Cervantes', 'Aguilar', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero12', 'Fernando', 'Vargas', 'Mora', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero13', 'Camila', 'Contreras', 'Leon', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero14', 'Luis', 'Dominguez', 'Santos', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero15', 'Elena', 'Rangel', 'Figueroa', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero16', 'Roberto', 'Cortes', 'Mejia', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero17', 'Mariana', 'Arias', 'Nunez', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero18', 'Gabriela', 'Fuentes', 'Padilla', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero19', 'Hector', 'Luna', 'Valdez', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
        ('cajero20', 'Monica', 'Bravo', 'Herrera', Usuario.ROL_CAJERO, 'Cajero vendedor', 'Password123!'),
    ]

    for index, (username, nombre, ap_pat, ap_mat, rol, puesto, password) in enumerate(usuarios_data):
        usuario = Usuario(
            usuario=username,
            nombre=nombre,
            ap_pat=ap_pat,
            ap_mat=ap_mat,
            rol=rol,
            telefono=f'31260{index:05d}'[:10],
            puesto=puesto,
            fecha_creacion=date(2024, (index % 12) + 1, min((index * 2) + 1, 28)),
            fecha_contratacion=date(2024, (index % 12) + 1, min((index * 2) + 3, 28)),
            ultima_conexion=timezone.make_aware(datetime(2026, (index % 12) + 1, min((index * 2) + 1, 28), 9, 30)),
            activo=True,
        )
        usuario.set_password(password)
        usuario.save()
        usuarios.append(usuario)
    print(f'- Usuarios creados: {len(usuarios)}')
    return usuarios


def crear_metodos_pago():
    metodos = []
    for nombre, descripcion in METODOS_BASE:
        metodos.append(MetodoPago.objects.create(nombre_metodo=nombre, descripcion=descripcion))
    print(f'- Metodos de pago creados: {len(metodos)}')
    return metodos


def crear_lotes_y_medicamentos(proveedores):
    lotes = []
    medicamentos = []
    fecha_base = date(2023, 1, 1)

    for i in range(1, 101):
        base = MEDICAMENTOS_BASE[(i - 1) % len(MEDICAMENTOS_BASE)]
        nombre_base, presentacion, concentracion, receta, compra_base, venta_base = base
        proveedor = proveedores[(i * 7) % len(proveedores)]

        fabricacion = fecha_base + timedelta(days=i * 17)
        if i % 17 == 0:
            caducidad = date(2025, ((i - 1) % 12) + 1, min((i % 26) + 1, 28))
        elif i % 11 == 0:
            caducidad = timezone.localdate() + timedelta(days=(i % 75) + 5)
        else:
            caducidad = date(2026 + (i % 4), ((i - 1) % 12) + 1, min((i % 26) + 1, 28))

        stock = 0 if i % 19 == 0 else 45 + ((i * 13) % 180)
        activo = stock > 0 and caducidad >= timezone.localdate()
        oculto = i % 23 == 0
        lote = Lote.objects.create(
            id_prov=proveedor,
            numero_lote=f'DEMO-{i:03d}-{proveedor.id_prov:03d}',
            fecha_fabricacion=fabricacion,
            fecha_caducidad=caducidad,
            fecha_ingreso=timezone.make_aware(datetime(2023 + (i % 4), ((i - 1) % 12) + 1, min((i % 25) + 1, 28), 8, 0)),
            stock_actual=stock,
            activo=activo,
            fecha_compra=fabricacion + timedelta(days=10),
            precio_compra=compra_base + Decimal(i % 9),
            precio_venta=venta_base + Decimal((i % 6) * 5),
            oculto_por_caducidad=oculto,
        )
        lotes.append(lote)

        nombre = f'{nombre_base} {concentracion}'
        medicamento = Medicamento.objects.create(
            id_lote=lote,
            nombre=nombre,
            presentacion=presentacion,
            concentracion=concentracion,
            requiere_receta=receta,
            fecha_registro=lote.fecha_ingreso,
            estado_colorimetria=lote.estado_stock,
        )
        medicamentos.append(medicamento)

    print('- Lotes creados: 100')
    print('- Medicamentos creados: 100')
    return lotes, medicamentos


def crear_qr(medicamentos):
    for i, medicamento in enumerate(medicamentos, start=1):
        token = f'DEMOQR{i:03d}{medicamento.id_med:04d}'
        CodigoQR.objects.create(
            id_medicamento=medicamento,
            token=token,
            url_qr=reverse('qr_scan', kwargs={'token': token}),
            fecha_generacion=date(2023 + (i % 4), ((i - 1) % 12) + 1, min((i % 25) + 1, 28)),
            fecha_regeneracion=None,
            contador_escaneos=(i * 7) % 180,
            activo=True,
        )
    print('- Codigos QR creados: 100')


def crear_ventas(usuarios, clientes, metodos, medicamentos):
    cajeros = [u for u in usuarios if u.rol == Usuario.ROL_CAJERO]
    medicamentos_vendibles = [
        med for med in medicamentos
        if med.id_lote and med.id_lote.activo and not med.id_lote.oculto_por_caducidad and med.id_lote.stock_actual > 5
    ]
    fechas = []
    for i in range(100):
        anio = 2022 + (i % 5)
        mes = (i % 12) + 1
        dia = min(((i * 3) % 26) + 1, 28)
        fechas.append(timezone.make_aware(datetime(anio, mes, dia, 9 + (i % 9), (i * 7) % 60)))

    for i in range(1, 101):
        venta = Venta.objects.create(
            id_usuario=cajeros[i % len(cajeros)],
            id_metPag=metodos[i % len(metodos)],
            id_cliente=clientes[i % len(clientes)] if i % 7 else None,
            fecha_venta=fechas[i - 1],
            total_venta=Decimal('0.00'),
        )

        total = Decimal('0.00')
        cantidad_lineas = 2 + (i % 4)
        usados = set()
        for j in range(cantidad_lineas):
            med = medicamentos_vendibles[(i * 5 + j * 11) % len(medicamentos_vendibles)]
            if med.id_med in usados:
                continue
            usados.add(med.id_med)
            cantidad = 1 + ((i + j) % 4)
            precio = med.id_lote.precio_venta or Decimal('0.00')
            subtotal = precio * cantidad
            DetalleVenta.objects.create(
                id_ventas=venta,
                id_medicamento=med,
                cantidad=cantidad,
                precio_unitario=precio,
                subtotal=subtotal,
            )
            total += subtotal
            med.id_lote.stock_actual = max(0, med.id_lote.stock_actual - cantidad)
            med.id_lote.save(update_fields=['stock_actual'])

        venta.total_venta = total
        venta.save(update_fields=['total_venta'])

    print('- Ventas creadas: 100')


if __name__ == '__main__':
    main()
