from decimal import Decimal

from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.medicamentos.models import Lote, Medicamento
from apps.proveedores.models import Proveedor
from apps.reportes.views import _build_report_context, _build_report_pdf
from apps.usuarios.models import AutomatizacionCorreo, Usuario
from apps.ventas.models import DetalleVenta, MetodoPago, Venta


class ReportesTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create(
            usuario='admin_reportes',
            rol=Usuario.ROL_ADMIN,
            nombre='Admin',
            activo=True,
        )
        cliente = Cliente.objects.create(nombre='Cliente', ap_pat='Reporte')
        metodo = MetodoPago.objects.create(nombre_metodo='Efectivo')
        proveedor = Proveedor.objects.create(nombre='Proveedor reportes')
        lote = Lote.objects.create(
            id_prov=proveedor,
            numero_lote='rep-001',
            stock_actual=20,
            precio_compra=Decimal('10.00'),
            precio_venta=Decimal('18.00'),
        )
        medicamento = Medicamento.objects.create(
            id_lote=lote,
            nombre='Loratadina',
            presentacion='Tabletas',
            concentracion='10 mg',
        )
        venta = Venta.objects.create(
            id_usuario=self.usuario,
            id_metPag=metodo,
            id_cliente=cliente,
            fecha_venta=timezone.now(),
            total_venta=Decimal('36.00'),
        )
        DetalleVenta.objects.create(
            id_ventas=venta,
            id_medicamento=medicamento,
            cantidad=2,
            precio_unitario=Decimal('18.00'),
            subtotal=Decimal('36.00'),
        )

    def test_pdf_general_y_por_seccion_son_validos(self):
        request = RequestFactory().get('/reportes/')
        context = _build_report_context(request)

        general = _build_report_pdf(context).getvalue()
        ventas = _build_report_pdf(context, section='ventas').getvalue()

        self.assertTrue(general.startswith(b'%PDF-1.4'))
        self.assertTrue(ventas.startswith(b'%PDF-1.4'))
        self.assertGreater(len(general), len(ventas))

    def test_automatizaciones_default_incluyen_reportes_por_seccion(self):
        AutomatizacionCorreo.ensure_defaults()
        claves = set(AutomatizacionCorreo.objects.values_list('clave', flat=True))

        self.assertIn('ventas.resumen_diario', claves)
        self.assertIn('reportes.reporte_semanal', claves)
        self.assertIn('reportes.ventas.semanal', claves)
        self.assertIn('reportes.clientes.mensual', claves)
        self.assertIn('reportes.inventario.mensual', claves)
