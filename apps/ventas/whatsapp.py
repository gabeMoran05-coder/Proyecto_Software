from django.conf import settings
from django.urls import reverse

from apps.medicamentos.whatsapp import (
    WhatsAppIntegrationError,
    _absolute_url,
    _enviar_audio,
    _enviar_plantilla,
    _generar_audio_ia,
    _generar_qr_png,
    _subir_media,
    _validar_configuracion,
    normalizar_telefono_con_pais,
    telefono_form_context,
)


def enviar_aviso_producto_defectuoso(request, detalle):
    _validar_configuracion()

    venta = detalle.id_ventas
    cliente = venta.id_cliente
    if not cliente or not cliente.telefono:
        raise WhatsAppIntegrationError('La venta no tiene cliente con teléfono registrado.')

    telefono = normalizar_telefono_con_pais('52', cliente.telefono)
    medicamento = detalle.id_medicamento
    lote = medicamento.id_lote
    lote_numero = lote.numero_lote if lote else 'Sin lote'
    razon = _razon_contacto_lote(lote)

    _enviar_plantilla(
        telefono=telefono,
        template_name=settings.WHATSAPP_RECALL_TEMPLATE_NAME,
        language_code=settings.WHATSAPP_RECALL_TEMPLATE_LANGUAGE,
        body_params=[
            cliente.nombre_completo(),
            medicamento.nombre,
            lote_numero,
            venta.id_ventas,
            razon,
        ],
    )
    return telefono


def texto_aviso_producto_defectuoso(request, detalle):
    venta = detalle.id_ventas
    cliente = venta.id_cliente
    medicamento = detalle.id_medicamento
    lote = medicamento.id_lote
    lote_numero = lote.numero_lote if lote else 'Sin lote'
    razon = _razon_contacto_lote(lote)
    return (
        f'Hola {cliente.nombre_completo() if cliente else "cliente"}, te contactamos de Farmacia Inclusiva por un aviso importante sobre un producto adquirido.\n\n'
        f'Medicamento: {medicamento.nombre}\n'
        f'Lote: {lote_numero}\n'
        f'Venta: #{venta.id_ventas}\n'
        f'Razón del contacto: {razon}\n\n'
        'Por precaución, no consumas el producto y comunícate con la farmacia para recibir indicaciones.'
    )


def _razon_contacto_lote(lote):
    if not lote:
        return 'Revisión preventiva del producto'
    if lote.motivo_oculto:
        return lote.get_motivo_oculto_display()
    if not lote.activo or lote.oculto_por_caducidad:
        return 'Producto retirado del inventario operativo'
    return 'Revisión preventiva del producto'


def enviar_ticket_por_whatsapp(request, venta, telefono):
    _validar_configuracion()

    ticket_url = _ticket_url(request, venta)
    qr_media_id = None

    from django.conf import settings
    if settings.WHATSAPP_TICKET_TEMPLATE_HEADER_IMAGE:
        ticket_qr_png = _generar_qr_png(ticket_url)
        qr_media_id = _subir_media(
            ticket_qr_png,
            'image/png',
            f'ticket-venta-{venta.id_ventas}-qr.png',
        )

    _enviar_plantilla(
        telefono=telefono,
        template_name=settings.WHATSAPP_TICKET_TEMPLATE_NAME,
        language_code=settings.WHATSAPP_TICKET_TEMPLATE_LANGUAGE,
        header_image_id=qr_media_id,
        body_params=_ticket_template_params(request, venta, ticket_url),
        button_url_param=venta.ticket_token,
    )

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
    ticket_url = _ticket_url(request, venta)
    cliente, folio, fecha, productos_count, total, url = _ticket_template_params(request, venta, ticket_url)
    return (
        f'Hola {cliente}, gracias por tu compra en Farmacia Inclusiva.\n\n'
        f'Tu ticket #{folio} del {fecha} incluye {productos_count} producto(s).\n\n'
        f'Total: ${total}\n\n'
        f'Puedes consultar tu ticket y los QR de tus medicamentos aqui:\n'
        f'{url}\n\n'
        f'Gracias, buen dia'
    )


def texto_ticket_detallado(request, venta):
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
        f'Método de pago: {venta.id_metPag.nombre_metodo}\n\n'
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
        f'Método de pago: {venta.id_metPag.nombre_metodo}.',
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


def _ticket_template_params(request, venta, ticket_url=None):
    detalles = list(_detalles(venta))
    productos_count = sum(det.cantidad or 0 for det in detalles)
    fecha = venta.fecha_venta.strftime('%d/%m/%Y') if venta.fecha_venta else 'No registrada'
    total = f'{venta.total_venta:.2f}' if venta.total_venta is not None else '0.00'
    return [
        venta.cliente_display(),
        venta.id_ventas,
        fecha,
        productos_count,
        total,
        ticket_url or _ticket_url(request, venta),
    ]
