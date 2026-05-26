import os
import sys
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmacia.settings')
sys.path.append(str(Path(__file__).resolve().parent.parent))

import django

django.setup()

from django.utils import timezone

from apps.medicamentos.models import Lote, Medicamento


def main():
    hoy = timezone.localdate()
    ahora = timezone.now()
    corregidos = {
        'lotes': 0,
        'fabricacion_futura': 0,
        'compra_futura': 0,
        'compra_antes_fabricacion': 0,
        'caducidad_antes_fabricacion': 0,
        'caducidad_antes_compra': 0,
        'medicamento_registro_futuro': 0,
    }

    for lote in Lote.objects.all():
        changed = set()

        if lote.fecha_fabricacion and lote.fecha_fabricacion > hoy:
            lote.fecha_fabricacion = hoy
            corregidos['fabricacion_futura'] += 1
            changed.add('fecha_fabricacion')

        if lote.fecha_compra and lote.fecha_compra > hoy:
            lote.fecha_compra = hoy
            corregidos['compra_futura'] += 1
            changed.add('fecha_compra')

        if lote.fecha_fabricacion and lote.fecha_compra and lote.fecha_compra < lote.fecha_fabricacion:
            lote.fecha_compra = lote.fecha_fabricacion
            corregidos['compra_antes_fabricacion'] += 1
            changed.add('fecha_compra')

        if lote.fecha_fabricacion and lote.fecha_caducidad and lote.fecha_caducidad < lote.fecha_fabricacion:
            lote.fecha_caducidad = lote.fecha_fabricacion
            corregidos['caducidad_antes_fabricacion'] += 1
            changed.add('fecha_caducidad')

        if lote.fecha_compra and lote.fecha_caducidad and lote.fecha_caducidad < lote.fecha_compra:
            lote.fecha_caducidad = lote.fecha_compra
            corregidos['caducidad_antes_compra'] += 1
            changed.add('fecha_caducidad')

        if changed:
            lote.save(update_fields=changed)
            corregidos['lotes'] += 1

    for medicamento in Medicamento.objects.filter(fecha_registro__date__gt=hoy):
        medicamento.fecha_registro = ahora
        medicamento.save(update_fields=['fecha_registro'])
        corregidos['medicamento_registro_futuro'] += 1

    print(corregidos)


if __name__ == '__main__':
    main()
