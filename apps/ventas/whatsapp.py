from django.urls import reverse

from apps.medicamentos.whatsapp import (
    WhatsAppIntegrationError,
    _absolute_url,
    _enviar_audio,
    _enviar_imagen,
    _enviar_texto,
    _generar_audio_ia,
    _generar_qr_png,
    _subir_media,
    _validar_configuracion,
    normalizar_telefono_con_pais,
    telefono_form_context,
)


def enviar_ticket_por_whatsapp(request, venta, telefono):
    _validar_configuracion()

    ticket_url = _ticket_url(request, venta)
    ticket_qr_png = _generar_qr_png(ticket_url)
    qr_media_id = _subir_media(
        ticket_qr_png,
        'image/png',
        f'ticket-venta-{venta.id_ventas}-qr.png',
    )

    _enviar_texto(telefono, texto_ticket(request, venta))
    _enviar_imagen(telefono, qr_media_id, f'QR del ticket de compra #{venta.id_ventas}.')

    from django.conf import settings
    if settings.OPENAI_API_KEY:
        audio_texto = texto_audio_ticket(venta)
        audio_mp3 = _generar_audio_ia(audio_texto)
        audio_media_id = _subir_media(
            audio_mp3,
            'audio/mpeg',
            f'ticket-venta-{venta.id_ventas}.mp3',
        )
        _enviar_audio(telefono, audio_media_id)


def construir_preview_ticket(request, venta):
    return {
        'texto': texto_ticket(request, venta),
        'audio': texto_audio_ticket(venta),
    }


def texto_ticket(request, venta):
    detalles = _detalles(venta)
    productos = '\n'.join(
        f'- {det.cantidad} x {det.id_medicamento.nombre}: ${det.subtotal:.2f}'
        for det in detalles
    )
    return (
        f'Ticket de compra #{venta.id_ventas}\n\n'
        f'Farmacia Inclusiva\n'
        f'Fecha: {venta.fecha_venta.strftime("%d/%m/%Y %H:%M") if venta.fecha_venta else "No registrada"}\n'
        f'Cliente: {venta.cliente_display()}\n'
        f'Metodo de pago: {venta.id_metPag.nombre_metodo}\n\n'
        f'Productos:\n{productos}\n\n'
        f'Total: ${venta.total_venta:.2f}\n'
        f'Consulta tu ticket y los QR de tus medicamentos aqui:\n{_ticket_url(request, venta)}\n\n'
        f'Audio generado por IA para accesibilidad.'
    )


def texto_audio_ticket(venta):
    partes = [
        'Aviso: este audio fue generado por inteligencia artificial.',
        f'Ticket de compra numero {venta.id_ventas}.',
        f'Cliente: {venta.cliente_display()}.',
        f'Metodo de pago: {venta.id_metPag.nombre_metodo}.',
        'Productos comprados:',
    ]

    for det in _detalles(venta):
        med = det.id_medicamento
        lote = med.id_lote
        caducidad = (
            lote.fecha_caducidad.strftime('%d/%m/%Y')
            if lote.fecha_caducidad
            else 'no registrada'
        )
        receta = 'requiere receta medica' if med.requiere_receta else 'no requiere receta medica'
        partes.append(
            f'{det.cantidad} unidad o unidades de {med.nombre}, '
            f'presentacion {med.presentacion or "no registrada"}, '
            f'concentracion {med.concentracion or "no registrada"}, '
            f'{receta}, caducidad {caducidad}, '
            f'precio unitario {det.precio_unitario:.2f} pesos, '
            f'subtotal {det.subtotal:.2f} pesos.'
        )

    partes.append(f'Total de la compra: {venta.total_venta:.2f} pesos.')
    partes.append('Conserva tu ticket y consulta a un profesional de salud si tienes dudas sobre algun medicamento.')
    return ' '.join(partes)


def _ticket_url(request, venta):
    venta.ensure_ticket_token()
    return _absolute_url(
        request,
        reverse('venta_ticket_public', kwargs={'token': venta.ticket_token}),
    )


def _detalles(venta):
    return venta.detalleventa_set.select_related(
        'id_medicamento__id_lote__id_prov'
    ).all()
