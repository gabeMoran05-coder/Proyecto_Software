from io import BytesIO

import qrcode
import requests
from django.conf import settings


class WhatsAppIntegrationError(Exception):
    pass


COUNTRY_CODES = [
    {'code': '52', 'name': 'Mexico', 'flag': 'MX', 'placeholder': '312 198 1722'},
    {'code': '1', 'name': 'Estados Unidos', 'flag': 'US', 'placeholder': '555 123 4567'},
    {'code': '57', 'name': 'Colombia', 'flag': 'CO', 'placeholder': '300 123 4567'},
    {'code': '54', 'name': 'Argentina', 'flag': 'AR', 'placeholder': '11 2345 6789'},
    {'code': '34', 'name': 'Espana', 'flag': 'ES', 'placeholder': '612 345 678'},
]

WHATSAPP_REQUEST_TIMEOUT = 20
OPENAI_TTS_TIMEOUT = 25


def enviar_paquete_qr_por_whatsapp(request, qr, telefono):
    _validar_configuracion()

    medicamento = qr.id_medicamento
    ficha_url = _absolute_url(request, qr.url_qr)
    qr_png = _generar_qr_png(ficha_url)
    qr_media_id = _subir_media(qr_png, 'image/png', f'qr-{qr.id_qr}.png')

    _enviar_texto(telefono, _texto_presentacion(medicamento, ficha_url))
    _enviar_imagen(telefono, qr_media_id, _caption_qr(medicamento))

    if settings.OPENAI_API_KEY:
        audio_texto = _texto_audio(medicamento)
        audio_mp3 = _generar_audio_ia(audio_texto)
        audio_media_id = _subir_media(audio_mp3, 'audio/mpeg', f'info-{qr.id_qr}.mp3')
        _enviar_audio(telefono, audio_media_id)


def construir_preview_whatsapp(request, qr):
    medicamento = qr.id_medicamento
    return {
        'texto': _texto_presentacion(medicamento, _absolute_url(request, qr.url_qr)),
        'audio': _texto_audio(medicamento),
    }


def normalizar_telefono(raw):
    telefono = ''.join(ch for ch in raw if ch.isdigit())
    if len(telefono) < 10:
        raise WhatsAppIntegrationError('Ingresa un teléfono con código de país. Ejemplo: 5213312345678.')
    return telefono


def normalizar_telefono_con_pais(country_code, local_number):
    codigo = ''.join(ch for ch in country_code if ch.isdigit())
    numero = ''.join(ch for ch in local_number if ch.isdigit())

    if not codigo:
        raise WhatsAppIntegrationError('Selecciona el país del numero de WhatsApp.')
    if len(numero) < 7:
        raise WhatsAppIntegrationError('Ingresa un numero de WhatsApp valido.')

    if numero.startswith(codigo):
        return numero
    return f'{codigo}{numero}'


def telefono_form_context(country_code='52', local_number=''):
    selected = next(
        (country for country in COUNTRY_CODES if country['code'] == country_code),
        COUNTRY_CODES[0],
    )
    return {
        'country_codes': COUNTRY_CODES,
        'country_code': selected['code'],
        'phone_placeholder': selected['placeholder'],
        'telefono_local': local_number,
    }


def _validar_configuracion():
    faltantes = []
    if not settings.WHATSAPP_PHONE_NUMBER_ID:
        faltantes.append('WHATSAPP_PHONE_NUMBER_ID')
    if not settings.WHATSAPP_ACCESS_TOKEN:
        faltantes.append('WHATSAPP_ACCESS_TOKEN')
    if faltantes:
        raise WhatsAppIntegrationError('Faltan variables de entorno: ' + ', '.join(faltantes))


def _absolute_url(request, path):
    if path.startswith(('http://', 'https://')):
        return path
    if settings.QR_PUBLIC_BASE_URL:
        return settings.QR_PUBLIC_BASE_URL + path
    if settings.SITE_PUBLIC_BASE_URL:
        return settings.SITE_PUBLIC_BASE_URL + path
    return request.build_absolute_uri(path)


def _generar_qr_png(target_url):
    img = qrcode.make(target_url).convert('RGB')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return buffer.getvalue()


def _generar_audio_ia(texto):
    try:
        response = requests.post(
            'https://api.openai.com/v1/audio/speech',
            headers={
                'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'model': settings.OPENAI_TTS_MODEL,
                'voice': settings.OPENAI_TTS_VOICE,
                'input': texto,
                'instructions': 'Habla en espanol de Mexico, con tono claro, amable y profesional para un paciente.',
            },
            timeout=OPENAI_TTS_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise WhatsAppIntegrationError(f'No se pudo conectar con OpenAI TTS: {exc}') from exc
    if response.status_code >= 400:
        raise WhatsAppIntegrationError(_api_error('OpenAI TTS', response))
    return response.content


def _subir_media(contenido, mime_type, filename):
    try:
        response = requests.post(
            _graph_url('media'),
            headers={'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}'},
            data={'messaging_product': 'whatsapp', 'type': mime_type},
            files={'file': (filename, contenido, mime_type)},
            timeout=WHATSAPP_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise WhatsAppIntegrationError(f'No se pudo conectar con WhatsApp media: {exc}') from exc
    if response.status_code >= 400:
        raise WhatsAppIntegrationError(_api_error('WhatsApp media', response))
    return response.json()['id']


def _enviar_texto(telefono, texto):
    _enviar_mensaje({
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': telefono,
        'type': 'text',
        'text': {
            'preview_url': True,
            'body': texto,
        },
    })


def _enviar_imagen(telefono, media_id, caption):
    _enviar_mensaje({
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': telefono,
        'type': 'image',
        'image': {
            'id': media_id,
            'caption': caption,
        },
    })


def _enviar_audio(telefono, media_id):
    _enviar_mensaje({
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': telefono,
        'type': 'audio',
        'audio': {'id': media_id},
    })


def _enviar_plantilla(
    telefono,
    template_name,
    language_code,
    body_params,
    header_image_id=None,
    button_url_param=None,
):
    components = []
    if header_image_id:
        components.append({
            'type': 'header',
            'parameters': [
                {
                    'type': 'image',
                    'image': {'id': header_image_id},
                },
            ],
        })

    components.append({
        'type': 'body',
        'parameters': [
            {'type': 'text', 'text': str(param)}
            for param in body_params
        ],
    })

    if button_url_param:
        components.append({
            'type': 'button',
            'sub_type': 'url',
            'index': '0',
            'parameters': [
                {'type': 'text', 'text': str(button_url_param)},
            ],
        })

    _enviar_mensaje({
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': telefono,
        'type': 'template',
        'template': {
            'name': template_name,
            'language': {'code': language_code},
            'components': components,
        },
    })


def _enviar_mensaje(payload):
    try:
        response = requests.post(
            _graph_url('messages'),
            headers={
                'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=WHATSAPP_REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise WhatsAppIntegrationError(f'No se pudo conectar con WhatsApp messages: {exc}') from exc
    if response.status_code >= 400:
        raise WhatsAppIntegrationError(_api_error('WhatsApp messages', response))


def _graph_url(resource):
    version = settings.WHATSAPP_GRAPH_API_VERSION
    phone_id = settings.WHATSAPP_PHONE_NUMBER_ID
    return f'https://graph.facebook.com/{version}/{phone_id}/{resource}'


def _texto_presentacion(medicamento, ficha_url):
    lote = medicamento.id_lote
    caducidad = lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else 'No registrada'
    receta = 'Requiere receta medica' if medicamento.requiere_receta else 'No requiere receta medica'
    precio = f'${lote.precio_venta:.2f}' if lote.precio_venta is not None else 'No registrado'
    return (
        f'Información de medicamento\n\n'
        f'{medicamento.nombre}\n'
        f'Presentación: {medicamento.presentacion_completa or "No registrada"}\n'
        f'Concentracion: {medicamento.concentracion or "No registrada"}\n'
        f'{receta}\n'
        f'Caducidad: {caducidad}\n'
        f'Proveedor: {lote.id_prov.nombre}\n'
        f'Precio: {precio}\n\n'
        f'Ficha QR: {ficha_url}\n\n'
        f'Audio generado por IA para accesibilidad.'
    )


def _caption_qr(medicamento):
    return (
        f'QR de consulta para {medicamento.nombre}. '
        f'Escanealo para ver la ficha pública del medicamento.'
    )


def _texto_audio(medicamento):
    lote = medicamento.id_lote
    caducidad = lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else 'no tiene fecha de caducidad registrada'
    receta = 'requiere receta medica' if medicamento.requiere_receta else 'no requiere receta medica'
    return (
        f'Aviso: este audio fue generado por inteligencia artificial. '
        f'El medicamento {medicamento.nombre}, presentacion {medicamento.presentacion_completa or "no registrada"}, '
        f'con concentracion {medicamento.concentracion or "no registrada"}, {receta}. '
        f'La fecha de caducidad es {caducidad}. '
        f'Proveedor: {lote.id_prov.nombre}. '
        f'Consulta a un profesional de salud si tienes dudas sobre su uso.'
    )


def _api_error(nombre, response):
    try:
        detalle = response.json()
    except ValueError:
        detalle = response.text[:500]

    if nombre.startswith('WhatsApp') and response.status_code == 401:
        return (
            'WhatsApp rechazó la autenticación. Revisa que las credenciales '
            'estén vigentes y pertenezcan al mismo número configurado en Meta.'
        )

    error = detalle.get('error', {}) if isinstance(detalle, dict) else {}
    if nombre.startswith('WhatsApp') and error.get('code') == 132001:
        return (
            'WhatsApp no puede enviar esta plantilla todavía. Revisa en Meta '
            'que la plantilla del ticket esté aprobada y en el mismo idioma '
            'configurado para el sistema.'
        )

    return f'{nombre} respondió con error {response.status_code}: {detalle}'
