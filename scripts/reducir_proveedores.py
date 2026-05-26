import os
import sys

import django


sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'farmacia.settings')
django.setup()

from apps.medicamentos.models import Lote
from apps.proveedores.models import Proveedor


PROVEEDORES_REALES = [
    ('Laboratorios Pisa', '3331234567', 'ventas@pisa.com.mx', 'Av. Espana 1840, Guadalajara, Jalisco'),
    ('Nadro S.A.P.I.', '5551234567', 'contacto@nadro.com.mx', 'Av. Insurgentes Sur 863, Ciudad de Mexico'),
    ('Farmacos Nacionales', '8181234567', 'pedidos@farmacosnacionales.mx', 'Av. Gonzalitos 600, Monterrey, Nuevo Leon'),
    ('Laboratorios Silanes', '5559876543', 'atencion@silanes.com.mx', 'Periferico Sur 3395, Ciudad de Mexico'),
    ('Medix Farmaceutica', '3339876543', 'servicio@medix.com.mx', 'Av. Lopez Mateos Sur 2077, Zapopan, Jalisco'),
]


def main():
    actuales = list(Proveedor.objects.order_by('id_prov'))
    keep = []

    for index, data in enumerate(PROVEEDORES_REALES):
        proveedor = actuales[index] if index < len(actuales) else Proveedor()
        proveedor.nombre, proveedor.telefono, proveedor.correo, proveedor.direccion = data
        proveedor.activo = True
        proveedor.save()
        keep.append(proveedor)

    for index, lote in enumerate(Lote.objects.order_by('id_lote')):
        lote.id_prov = keep[index % len(keep)]
        lote.save(update_fields=['id_prov'])

    borrados = Proveedor.objects.exclude(id_prov__in=[p.id_prov for p in keep]).delete()[0]

    print({
        'proveedores_restantes': Proveedor.objects.count(),
        'proveedores_borrados': borrados,
        'lotes_conservados': Lote.objects.count(),
        'proveedores': [proveedor.nombre for proveedor in keep],
    })


if __name__ == '__main__':
    main()
