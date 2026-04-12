from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Notificacion
from apps.ventas.models import Venta
from django.http import JsonResponse
import urllib.parse

@login_required
def enviar_whatsapp(request, venta_id):
    venta    = get_object_or_404(Venta, pk=venta_id)
    cliente  = venta.cliente
    if not cliente or not cliente.telefono:
        return JsonResponse({'ok': False, 'error': 'El cliente no tiene teléfono.'})

    detalles = venta.detalles.select_related('medicamento', 'lote').all()
    lineas   = []
    for d in detalles:
        cad = d.lote.fecha_caducidad.strftime('%d/%m/%Y') if d.lote else 'N/D'
        lineas.append(f"• {d.medicamento.nombre} x{d.cantidad} – Cad: {cad}")
    qr_url   = ''
    if hasattr(detalles.first().medicamento, 'codigo_qr'):
        qr = detalles.first().medicamento.codigo_qr
        qr_url = qr.url_qr

    mensaje = (
        f"*Farmacia Gi* – Gracias por su compra 🙏\n"
        f"Folio: #{venta.pk}\n"
        f"Fecha: {venta.fecha_venta.strftime('%d/%m/%Y %H:%M')}\n\n"
        f"*Productos:*\n" + "\n".join(lineas) + "\n\n"
        f"*Total: ${venta.total_venta}*\n"
    )
    if qr_url:
        mensaje += f"\nConsulta tu medicamento aquí:\n{qr_url}"

    Notificacion.objects.create(venta=venta, mensaje_enviado=mensaje, enviado=True)
    tel   = cliente.telefono.replace('+', '').replace('-', '').replace(' ', '')
    wa_url = f"https://wa.me/52{tel}?text={urllib.parse.quote(mensaje)}"
    return JsonResponse({'ok': True, 'wa_url': wa_url})
