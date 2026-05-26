import os
import sys
import random
from datetime import datetime, date, time, timedelta
from decimal import Decimal

import django
from django.utils import timezone


sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmacia.settings')
django.setup()

from apps.clientes.models import Cliente
from apps.medicamentos.models import Medicamento
from apps.usuarios.models import Usuario
from apps.ventas.models import DetalleVenta, MetodoPago, Venta


def main():
    if os.environ.get('ALLOW_DEMO_SEED', '').strip().lower() not in {'1', 'true', 'yes', 'on'}:
        raise RuntimeError(
            'Siembra de ventas demo bloqueada. Define ALLOW_DEMO_SEED=true solo en desarrollo.'
        )

    DetalleVenta.objects.all().delete()
    Venta.objects.all().delete()

    cajeros = list(Usuario.objects.filter(rol=Usuario.ROL_CAJERO, activo=True).order_by('id_usuario'))
    clientes = list(Cliente.objects.order_by('id_cliente'))
    metodos = list(MetodoPago.objects.order_by('id_metPag'))
    medicamentos = list(
        Medicamento.objects.select_related('id_lote').filter(
            id_lote__isnull=False,
            id_lote__activo=True,
            id_lote__oculto_por_caducidad=False,
        ).order_by('id_med')
    )

    if not cajeros or not clientes or not metodos or len(medicamentos) < 5:
        raise RuntimeError('Faltan cajeros, clientes, metodos o medicamentos para crear ventas demo.')

    rng = random.Random(20260507)
    inicio = date(2022, 1, 1)
    fin = timezone.localdate() - timedelta(days=1)
    dias_disponibles = max((fin - inicio).days, 0)

    for index in range(1, 101):
        dia = inicio + timedelta(days=rng.randint(0, dias_disponibles))
        hora = time(hour=8 + (index % 10), minute=(index * 7) % 60)
        fecha = timezone.make_aware(datetime.combine(dia, hora))

        venta = Venta.objects.create(
            id_usuario=cajeros[index % len(cajeros)],
            id_metPag=metodos[index % len(metodos)],
            id_cliente=clientes[index % len(clientes)] if index % 6 else None,
            fecha_venta=fecha,
            total_venta=Decimal('0.00'),
        )

        total = Decimal('0.00')
        usados = set()
        lineas = 2 + (index % 4)
        for offset in range(lineas):
            med = medicamentos[(index * 7 + offset * 13) % len(medicamentos)]
            if med.id_med in usados:
                continue
            usados.add(med.id_med)
            cantidad = 1 + ((index + offset) % 3)
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

        venta.total_venta = total
        venta.save(update_fields=['total_venta'])

    print({
        'ventas_creadas': Venta.objects.count(),
        'detalles_creados': DetalleVenta.objects.count(),
        'rango': f'{inicio:%Y-%m-%d} a {fin:%Y-%m-%d}',
        'medicamentos_por_ticket': '2 a 5',
    })


if __name__ == '__main__':
    main()
