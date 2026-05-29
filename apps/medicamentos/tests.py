from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.medicamentos.models import Lote, Medicamento, MovimientoInventario
from apps.medicamentos.tasks import retirar_lotes_caducos_task
from apps.proveedores.models import Proveedor
from apps.usuarios.models import NotificacionSistema, Usuario


class InventarioTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create(
            usuario='admin_test',
            rol=Usuario.ROL_ADMIN,
            nombre='Admin',
            ap_pat='Pruebas',
            activo=True,
        )
        self.proveedor = Proveedor.objects.create(nombre='Proveedor pruebas')
        self.lote = Lote.objects.create(
            id_prov=self.proveedor,
            numero_lote='test-001',
            stock_actual=10,
            activo=True,
        )
        self.medicamento = Medicamento.objects.create(
            id_lote=self.lote,
            nombre='Paracetamol',
            presentacion='Tabletas',
            concentracion='500 mg',
            stock_minimo=8,
        )
        self.client = Client(HTTP_HOST='localhost')
        session = self.client.session
        session['usuario_id'] = self.usuario.pk
        session.save()

    def test_lote_inactivo_se_oculta_automaticamente(self):
        lote = Lote.objects.create(
            id_prov=self.proveedor,
            numero_lote='test-002',
            stock_actual=10,
            activo=False,
        )

        self.assertTrue(lote.oculto_por_caducidad)
        self.assertTrue(lote.motivo_oculto)

    def test_ajuste_de_inventario_disminuye_stock_y_crea_kardex(self):
        response = self.client.post(
            reverse('lote_ajuste_inventario', args=[self.lote.pk]),
            {
                'tipo_ajuste': 'salida',
                'cantidad': '3',
                'motivo': 'merma',
                'notas': 'Frasco roto',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.stock_actual, 7)
        movimiento = MovimientoInventario.objects.get(id_lote=self.lote)
        self.assertEqual(movimiento.cantidad, -3)
        self.assertEqual(movimiento.motivo, 'merma')
        self.assertEqual(movimiento.stock_antes, 10)
        self.assertEqual(movimiento.stock_despues, 7)

    def test_conteo_fisico_actualiza_stock_y_crea_kardex(self):
        response = self.client.post(
            reverse('lote_conteo_fisico', args=[self.lote.pk]),
            {'stock_contado': '12', 'notas': 'Conteo de anaquel'},
        )

        self.assertEqual(response.status_code, 302)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.stock_actual, 12)
        movimiento = MovimientoInventario.objects.get(id_lote=self.lote)
        self.assertEqual(movimiento.tipo, MovimientoInventario.TIPO_CONTEO)
        self.assertEqual(movimiento.cantidad, 2)
        self.assertEqual(movimiento.stock_antes, 10)
        self.assertEqual(movimiento.stock_despues, 12)

    def test_ocultar_lote_defectuoso_guarda_motivo_y_abre_trazabilidad(self):
        response = self.client.post(
            reverse('lote_ocultar', args=[self.lote.pk]),
            {
                'motivo_oculto': Lote.MOTIVO_DEFECTUOSO,
                'detalle_oculto': 'Empaque alterado',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('venta_trazabilidad'), response['Location'])
        self.lote.refresh_from_db()
        self.assertFalse(self.lote.activo)
        self.assertTrue(self.lote.oculto_por_caducidad)
        self.assertEqual(self.lote.motivo_oculto, Lote.MOTIVO_DEFECTUOSO)
        self.assertEqual(self.lote.detalle_oculto, 'Empaque alterado')
        movimiento = MovimientoInventario.objects.get(id_lote=self.lote)
        self.assertEqual(movimiento.tipo, MovimientoInventario.TIPO_OCULTAMIENTO)
        self.assertEqual(movimiento.motivo, Lote.MOTIVO_DEFECTUOSO)
        self.assertEqual(movimiento.cantidad, -10)
        self.assertEqual(movimiento.stock_antes, 10)
        self.assertEqual(movimiento.stock_despues, 0)
        self.assertEqual(movimiento.cantidad_kardex, -10)

    def test_stock_minimo_configurable_se_aplica_al_grupo(self):
        response = self.client.post(
            reverse('medicamento_stock_minimo', args=[self.medicamento.pk]),
            {'stock_minimo': '15'},
        )

        self.assertEqual(response.status_code, 302)
        self.medicamento.refresh_from_db()
        self.assertEqual(self.medicamento.stock_minimo, 15)

    def test_alerta_caducidad_configurable_cambia_estado_del_lote(self):
        self.lote.fecha_caducidad = timezone.localdate() + timezone.timedelta(days=45)
        self.lote.save(update_fields=['fecha_caducidad'])

        response = self.client.post(
            reverse('medicamento_alerta_caducidad', args=[self.medicamento.pk]),
            {'dias_alerta_caducidad': '30'},
        )

        self.assertEqual(response.status_code, 302)
        self.medicamento.refresh_from_db()
        self.assertEqual(self.medicamento.dias_alerta_caducidad, 30)
        self.assertEqual(self.lote.estado_caducidad, Lote.CADUCIDAD_VERDE)

        self.client.post(
            reverse('medicamento_alerta_caducidad', args=[self.medicamento.pk]),
            {'dias_alerta_caducidad': '60'},
        )
        self.assertEqual(self.lote.estado_caducidad, Lote.CADUCIDAD_AMARILLO)

    def test_detalle_marca_bajo_minimo_con_stock_total_menor_al_configurado(self):
        self.medicamento.stock_minimo = 15
        self.medicamento.save(update_fields=['stock_minimo'])

        response = self.client.get(reverse('medicamento_detail', args=[self.medicamento.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['estado_stock'], 'amarillo')
        self.assertEqual(response.context['estado_stock_display'], 'Bajo mínimo')

    def test_lote_caduco_tiene_un_dia_de_revision_antes_de_ocultarse(self):
        hoy = timezone.localdate()
        self.lote.fecha_caducidad = hoy - timezone.timedelta(days=1)
        self.lote.save(update_fields=['fecha_caducidad'])

        resultado = retirar_lotes_caducos_task.apply(kwargs={'force': True}).get()

        self.lote.refresh_from_db()
        self.assertTrue(self.lote.activo)
        self.assertFalse(self.lote.oculto_por_caducidad)
        self.assertEqual(resultado['lotes'], 0)
        self.assertTrue(
            NotificacionSistema.objects.filter(
                clave='inventario.lotes_caducos_revision',
                activa=True,
            ).exists()
        )

    def test_lote_caduco_mas_de_un_dia_se_oculta_y_genera_kardex(self):
        hoy = timezone.localdate()
        self.lote.fecha_caducidad = hoy - timezone.timedelta(days=2)
        self.lote.save(update_fields=['fecha_caducidad'])

        resultado = retirar_lotes_caducos_task.apply(kwargs={'force': True}).get()

        self.lote.refresh_from_db()
        self.assertFalse(self.lote.activo)
        self.assertTrue(self.lote.oculto_por_caducidad)
        self.assertEqual(self.lote.motivo_oculto, Lote.MOTIVO_CADUCIDAD)
        self.assertEqual(resultado['lotes'], 1)
        movimiento = MovimientoInventario.objects.get(id_lote=self.lote)
        self.assertEqual(movimiento.tipo, MovimientoInventario.TIPO_OCULTAMIENTO)
        self.assertEqual(movimiento.cantidad, -10)
        self.assertEqual(movimiento.stock_antes, 10)
        self.assertEqual(movimiento.stock_despues, 0)
