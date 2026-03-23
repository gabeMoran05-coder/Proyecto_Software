#!/usr/bin/env python
"""
Script de configuración inicial del proyecto Farmacia Inclusiva.
Se ejecuta automáticamente desde entrypoint.sh en cada arranque.
Es seguro correrlo múltiples veces (idempotente).
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.ventas.models import MetodoPago
from apps.usuarios.models import Usuario

# ── Métodos de pago ───────────────────────────────────────────────────────────
metodos = [
    ('Efectivo',      'Pago en efectivo'),
    ('Tarjeta',       'Tarjeta de crédito o débito'),
    ('Transferencia', 'Transferencia bancaria / OXXO Pay'),
]
for nombre, desc in metodos:
    obj, created = MetodoPago.objects.get_or_create(
        nombre=nombre, defaults={'descripcion': desc}
    )
    if created:
        print(f"  ✅ Creado: Método de pago – {nombre}")

# ── Usuario administrador ─────────────────────────────────────────────────────
if not Usuario.objects.filter(username='admin').exists():
    Usuario.objects.create_superuser(
        username='admin',
        password='Admin123!',
        nombre='Administrador',
        ap_pat='Farmacia',
        rol='admin',
    )
    print("  ✅ Creado: Usuario admin  (contraseña: Admin123!)")
else:
    print("  ℹ️  Ya existe: Usuario admin")

# ── Usuario cajero de prueba ──────────────────────────────────────────────────
if not Usuario.objects.filter(username='cajero1').exists():
    Usuario.objects.create_user(
        username='cajero1',
        password='Cajero123!',
        nombre='Juan',
        ap_pat='Pérez',
        rol='cajero',
    )
    print("  ✅ Creado: Usuario cajero1 (contraseña: Cajero123!)")
else:
    print("  ℹ️  Ya existe: Usuario cajero1")

print()
print("  🌐 Sistema:    http://localhost:8000")
print("  🔑 Admin:      admin   / Admin123!")
print("  💼 Cajero:     cajero1 / Cajero123!")
print("  🔌 PostgREST:  http://localhost:3000")
print("  📚 Swagger:    http://localhost:8080")
