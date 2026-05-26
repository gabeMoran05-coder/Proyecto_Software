import os
import random
import sys
from datetime import date, datetime, time, timedelta

import django
from django.utils import timezone


sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmacia.settings')
django.setup()

from apps.ventas.models import Venta


def main():
    hoy = timezone.localdate()
    inicio = date(2022, 1, 1)
    fin = hoy - timedelta(days=1)
    dias_disponibles = max((fin - inicio).days, 0)
    ventas = Venta.objects.filter(fecha_venta__date__gte=hoy).order_by('id_ventas')

    cambios = []
    for venta in ventas:
        rng = random.Random(20260507 + venta.id_ventas)
        dia = inicio + timedelta(days=rng.randint(0, dias_disponibles))
        hora = time(
            hour=rng.randint(8, 17),
            minute=rng.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]),
        )
        anterior = (
            timezone.localtime(venta.fecha_venta).strftime('%d/%m/%Y %H:%M')
            if venta.fecha_venta
            else '-'
        )

        venta.fecha_venta = timezone.make_aware(datetime.combine(dia, hora))
        venta.save(update_fields=['fecha_venta'])
        cambios.append((
            venta.id_ventas,
            anterior,
            timezone.localtime(venta.fecha_venta).strftime('%d/%m/%Y %H:%M'),
        ))

    print({
        'actualizadas': len(cambios),
        'restantes_hoy_o_futuro': Venta.objects.filter(fecha_venta__date__gte=hoy).count(),
        'cambios': cambios,
    })


if __name__ == '__main__':
    main()
