import os
import django
import sys

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmacia.settings')
django.setup()

from datetime import date, datetime
from apps.proveedores.models import Proveedor
from apps.clientes.models import Cliente
from apps.usuarios.models import Usuario
from apps.ventas.models import MetodoPago, Venta, DetalleVenta
from apps.medicamentos.models import Lote, Medicamento, CodigoQR
import uuid

print("Cargando datos de prueba...")

# =====================
# PROVEEDORES
# =====================
proveedores = [
    Proveedor(nombre="Laboratorios Pisa", telefono="3331234567", correo="ventas@pisa.com.mx", direccion="Av. Patria 1501, Guadalajara, Jalisco"),
    Proveedor(nombre="Distribuidora Nadro", telefono="5551234567", correo="contacto@nadro.com.mx", direccion="Av. Insurgentes Sur 800, CDMX"),
    Proveedor(nombre="Grupo Farmacos", telefono="8181234567", correo="pedidos@grupofarmacos.com", direccion="Av. Gonzalitos 600, Monterrey, NL"),
    Proveedor(nombre="Laboratorios Silanes", telefono="5559876543", correo="ventas@silanes.com.mx", direccion="Periferico Sur 7800, CDMX"),
    Proveedor(nombre="Medix Farmaceutica", telefono="3339876543", correo="info@medix.com.mx", direccion="Av. López Mateos 2000, Guadalajara"),
]
Proveedor.objects.bulk_create(proveedores)
print("✓ Proveedores creados")

# =====================
# CLIENTES
# =====================
clientes = [
    Cliente(nombre="María", ap_pat="González", ap_mat="López", fecha_registro=date(2024, 1, 15), telefono="3121234567"),
    Cliente(nombre="José", ap_pat="Martínez", ap_mat="Pérez", fecha_registro=date(2024, 2, 20), telefono="3129876543"),
    Cliente(nombre="Ana", ap_pat="Hernández", ap_mat="Ruiz", fecha_registro=date(2024, 3, 10), telefono="3123456789"),
    Cliente(nombre="Carlos", ap_pat="Ramírez", ap_mat="Torres", fecha_registro=date(2024, 4, 5), telefono="3127654321"),
    Cliente(nombre="Laura", ap_pat="Flores", ap_mat="Vega", fecha_registro=date(2024, 5, 18), telefono="3125551234"),
]
Cliente.objects.bulk_create(clientes)
print("✓ Clientes creados")

# =====================
# USUARIOS
# =====================
usuarios_data = [
    {"username": "jperez", "first_name": "Juan", "last_name": "Pérez", "rol": "farmaceutico", "telefono": "3121112233"},
    {"username": "mlopez", "first_name": "Marina", "last_name": "López", "rol": "cajero", "telefono": "3122223344"},
    {"username": "rsanchez", "first_name": "Roberto", "last_name": "Sánchez", "rol": "farmaceutico", "telefono": "3123334455"},
    {"username": "lmendoza", "first_name": "Lucía", "last_name": "Mendoza", "rol": "administrador", "telefono": "3124445566"},
    {"username": "agarcia", "first_name": "Arturo", "last_name": "García", "rol": "cajero", "telefono": "3125556677"},
]
usuarios_creados = []
for u in usuarios_data:
    usuario = Usuario(
        username=u["username"],
        first_name=u["first_name"],
        last_name=u["last_name"],
        rol=u["rol"],
        telefono=u["telefono"],
    )
    usuario.set_password("Password123!")
    usuario.save()
    usuarios_creados.append(usuario)
print("✓ Usuarios creados")

# =====================
# MÉTODOS DE PAGO
# =====================
metodos = [
    MetodoPago(nombre_metodo="Efectivo", descripcion="Pago en efectivo en caja"),
    MetodoPago(nombre_metodo="Tarjeta de débito", descripcion="Pago con tarjeta de débito"),
    MetodoPago(nombre_metodo="Tarjeta de crédito", descripcion="Pago con tarjeta de crédito"),
    MetodoPago(nombre_metodo="Transferencia", descripcion="Transferencia bancaria SPEI"),
    MetodoPago(nombre_metodo="Vales de medicina", descripcion="Vales del seguro o empresa"),
]
MetodoPago.objects.bulk_create(metodos)
print("✓ Métodos de pago creados")

# =====================
# LOTES
# =====================
proveedores_db = list(Proveedor.objects.all())
lotes = [
    Lote(id_prov=proveedores_db[0], numero_lote="PISA-2024-001", fecha_fabricacion=date(2024, 1, 1), fecha_caducidad=date(2026, 1, 1), fecha_ingreso=date(2024, 1, 20), stock_actual=100, activo=True, fecha_compra=date(2024, 1, 18), precio_compra=450.00, precio_venta=650.00),
    Lote(id_prov=proveedores_db[1], numero_lote="NADRO-2024-015", fecha_fabricacion=date(2024, 2, 1), fecha_caducidad=date(2026, 2, 1), fecha_ingreso=date(2024, 2, 15), stock_actual=80, activo=True, fecha_compra=date(2024, 2, 12), precio_compra=300.00, precio_venta=420.00),
    Lote(id_prov=proveedores_db[2], numero_lote="GF-2024-032", fecha_fabricacion=date(2024, 3, 1), fecha_caducidad=date(2025, 9, 1), fecha_ingreso=date(2024, 3, 10), stock_actual=50, activo=True, fecha_compra=date(2024, 3, 8), precio_compra=180.00, precio_venta=250.00),
    Lote(id_prov=proveedores_db[3], numero_lote="SIL-2024-008", fecha_fabricacion=date(2024, 4, 1), fecha_caducidad=date(2026, 4, 1), fecha_ingreso=date(2024, 4, 5), stock_actual=120, activo=True, fecha_compra=date(2024, 4, 3), precio_compra=520.00, precio_venta=720.00),
    Lote(id_prov=proveedores_db[4], numero_lote="MDX-2024-021", fecha_fabricacion=date(2024, 5, 1), fecha_caducidad=date(2026, 5, 1), fecha_ingreso=date(2024, 5, 20), stock_actual=60, activo=True, fecha_compra=date(2024, 5, 18), precio_compra=210.00, precio_venta=290.00),
]
Lote.objects.bulk_create(lotes)
print("✓ Lotes creados")

# =====================
# MEDICAMENTOS
# =====================
lotes_db = list(Lote.objects.all())
medicamentos = [
    Medicamento(id_lote=lotes_db[0], nombre="Amoxicilina 500mg", presentacion="Cápsulas c/12", concentracion="500mg", requiere_receta=True, fecha_registro=date(2024, 1, 20), estado_colorimetria="verde"),
    Medicamento(id_lote=lotes_db[1], nombre="Paracetamol 500mg", presentacion="Tabletas c/20", concentracion="500mg", requiere_receta=False, fecha_registro=date(2024, 2, 15), estado_colorimetria="verde"),
    Medicamento(id_lote=lotes_db[2], nombre="Ibuprofeno 400mg", presentacion="Tabletas c/10", concentracion="400mg", requiere_receta=False, fecha_registro=date(2024, 3, 10), estado_colorimetria="amarillo"),
    Medicamento(id_lote=lotes_db[3], nombre="Metformina 850mg", presentacion="Tabletas c/30", concentracion="850mg", requiere_receta=True, fecha_registro=date(2024, 4, 5), estado_colorimetria="verde"),
    Medicamento(id_lote=lotes_db[4], nombre="Loratadina 10mg", presentacion="Tabletas c/10", concentracion="10mg", requiere_receta=False, fecha_registro=date(2024, 5, 20), estado_colorimetria="verde"),
]
Medicamento.objects.bulk_create(medicamentos)
print("✓ Medicamentos creados")

# =====================
# CÓDIGOS QR
# =====================
medicamentos_db = list(Medicamento.objects.all())
qrs = [
    CodigoQR(id_medicamento=medicamentos_db[0], token=uuid.uuid4().hex[:64], url_qr="https://farmacia.com/qr/amoxicilina", fecha_generacion=date(2024, 1, 21), contador_escaneos=5, activo=True),
    CodigoQR(id_medicamento=medicamentos_db[1], token=uuid.uuid4().hex[:64], url_qr="https://farmacia.com/qr/paracetamol", fecha_generacion=date(2024, 2, 16), contador_escaneos=12, activo=True),
    CodigoQR(id_medicamento=medicamentos_db[2], token=uuid.uuid4().hex[:64], url_qr="https://farmacia.com/qr/ibuprofeno", fecha_generacion=date(2024, 3, 11), contador_escaneos=3, activo=True),
    CodigoQR(id_medicamento=medicamentos_db[3], token=uuid.uuid4().hex[:64], url_qr="https://farmacia.com/qr/metformina", fecha_generacion=date(2024, 4, 6), contador_escaneos=8, activo=True),
    CodigoQR(id_medicamento=medicamentos_db[4], token=uuid.uuid4().hex[:64], url_qr="https://farmacia.com/qr/loratadina", fecha_generacion=date(2024, 5, 21), contador_escaneos=2, activo=True),
]
CodigoQR.objects.bulk_create(qrs)
print("✓ Códigos QR creados")

# =====================
# VENTAS
# =====================
clientes_db = list(Cliente.objects.all())
metodos_db = list(MetodoPago.objects.all())
ventas = [
    Venta(id_usuario=usuarios_creados[0], id_metPag=metodos_db[0], id_cliente=clientes_db[0], fecha_venta=datetime(2024, 6, 1, 10, 30), total_venta=650.00),
    Venta(id_usuario=usuarios_creados[1], id_metPag=metodos_db[1], id_cliente=clientes_db[1], fecha_venta=datetime(2024, 6, 2, 11, 15), total_venta=420.00),
    Venta(id_usuario=usuarios_creados[0], id_metPag=metodos_db[2], id_cliente=clientes_db[2], fecha_venta=datetime(2024, 6, 3, 12, 0), total_venta=500.00),
    Venta(id_usuario=usuarios_creados[2], id_metPag=metodos_db[0], id_cliente=clientes_db[3], fecha_venta=datetime(2024, 6, 4, 9, 45), total_venta=290.00),
    Venta(id_usuario=usuarios_creados[1], id_metPag=metodos_db[3], id_cliente=clientes_db[4], fecha_venta=datetime(2024, 6, 5, 14, 20), total_venta=970.00),
]
Venta.objects.bulk_create(ventas)
print("✓ Ventas creadas")

# =====================
# DETALLE VENTAS
# =====================
ventas_db = list(Venta.objects.all())
detalles = [
    DetalleVenta(id_ventas=ventas_db[0], id_medicamento=medicamentos_db[0], cantidad=1, precio_unitario=650.00, subtotal=650.00),
    DetalleVenta(id_ventas=ventas_db[1], id_medicamento=medicamentos_db[1], cantidad=1, precio_unitario=420.00, subtotal=420.00),
    DetalleVenta(id_ventas=ventas_db[2], id_medicamento=medicamentos_db[1], cantidad=1, precio_unitario=420.00, subtotal=420.00),
    DetalleVenta(id_ventas=ventas_db[2], id_medicamento=medicamentos_db[2], cantidad=1, precio_unitario=250.00, subtotal=250.00),
    DetalleVenta(id_ventas=ventas_db[3], id_medicamento=medicamentos_db[4], cantidad=1, precio_unitario=290.00, subtotal=290.00),
    DetalleVenta(id_ventas=ventas_db[4], id_medicamento=medicamentos_db[0], cantidad=1, precio_unitario=650.00, subtotal=650.00),
    DetalleVenta(id_ventas=ventas_db[4], id_medicamento=medicamentos_db[3], cantidad=1, precio_unitario=320.00, subtotal=320.00),
]
DetalleVenta.objects.bulk_create(detalles)
print("✓ Detalles de venta creados")

print("\n✅ Todos los datos cargados correctamente")