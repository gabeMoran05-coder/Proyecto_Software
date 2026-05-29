from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.medicamentos.models import Lote, Medicamento, MovimientoInventario
from apps.proveedores.models import Proveedor
from apps.usuarios.models import Usuario
from apps.ventas.models import DetalleVenta, MetodoPago, Venta


class VentaStockTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create(
            usuario='cajero_test',
            rol=Usuario.ROL_CAJERO,
            nombre='Cajero',
            ap_pat='Pruebas',
            activo=True,
        )
        self.cliente = Cliente.objects.create(nombre='Cliente', ap_pat='Prueba')
        self.metodo = MetodoPago.objects.create(nombre_metodo='Efectivo')
        self.proveedor = Proveedor.objects.create(nombre='Proveedor pruebas')
        self.lote = Lote.objects.create(
            id_prov=self.proveedor,
            numero_lote='venta-001',
            stock_actual=5,
            activo=True,
            precio_venta=Decimal('20.00'),
        )
        self.medicamento = Medicamento.objects.create(
            id_lote=self.lote,
            nombre='Ibuprofeno',
            presentacion='Tabletas',
            concentracion='400 mg',
        )
        self.client = Client(HTTP_HOST='localhost')
        session = self.client.session
        session['usuario_id'] = self.usuario.pk
        session.save()

    def test_cancelar_venta_restaura_stock_y_crea_kardex(self):
        venta = Venta.objects.create(
            id_usuario=self.usuario,
            id_metPag=self.metodo,
            id_cliente=self.cliente,
            fecha_venta=timezone.now(),
            total_venta=Decimal('40.00'),
        )
        DetalleVenta.objects.create(
            id_ventas=venta,
            id_medicamento=self.medicamento,
            cantidad=2,
            precio_unitario=Decimal('20.00'),
            subtotal=Decimal('40.00'),
        )

        response = self.client.post(reverse('venta_delete', args=[venta.pk]))

        self.assertEqual(response.status_code, 302)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.stock_actual, 7)
        movimiento = MovimientoInventario.objects.get(id_lote=self.lote)
        self.assertEqual(movimiento.tipo, MovimientoInventario.TIPO_CANCELACION)
        self.assertEqual(movimiento.cantidad, 2)
        self.assertEqual(movimiento.stock_antes, 5)
        self.assertEqual(movimiento.stock_despues, 7)
        self.assertFalse(Venta.objects.filter(pk=venta.pk).exists())
