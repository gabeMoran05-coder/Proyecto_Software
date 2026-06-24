import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Crea en Meta la plantilla de WhatsApp para aviso de producto defectuoso.'

    def handle(self, *args, **options):
        if not settings.WHATSAPP_BUSINESS_ACCOUNT_ID:
            raise CommandError('Falta WHATSAPP_BUSINESS_ACCOUNT_ID en .env.')
        if not settings.WHATSAPP_ACCESS_TOKEN:
            raise CommandError('Falta WHATSAPP_ACCESS_TOKEN en .env.')

        url = (
            f'https://graph.facebook.com/{settings.WHATSAPP_GRAPH_API_VERSION}/'
            f'{settings.WHATSAPP_BUSINESS_ACCOUNT_ID}/message_templates'
        )
        payload = {
            'name': settings.WHATSAPP_RECALL_TEMPLATE_NAME,
            'language': settings.WHATSAPP_RECALL_TEMPLATE_LANGUAGE,
            'category': 'UTILITY',
            'components': [
                {
                    'type': 'BODY',
                    'text': (
                        'Hola {{1}}, te contactamos de Farmacia Inclusiva por un aviso importante '
                        'sobre un producto adquirido.\n\n'
                        'Medicamento: {{2}}\n'
                        'Lote: {{3}}\n'
                        'Venta: #{{4}}\n\n'
                        'Razón del contacto: {{5}}\n\n'
                        'Por precaución, no consumas el producto y comunícate con la farmacia '
                        'para recibir indicaciones.'
                    ),
                    'example': {
                        'body_text': [[
                            'Alejandro Medina Carrillo',
                            'Cetirizina 10 mg',
                            'DEMO-059-021',
                            '188',
                            'Defectuoso',
                        ]],
                    },
                },
                {
                    'type': 'FOOTER',
                    'text': 'Farmacia Inclusiva',
                },
            ],
        }
        response = requests.post(
            url,
            headers={
                'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=60,
        )
        if response.status_code >= 400:
            raise CommandError(response.text)

        self.stdout.write(self.style.SUCCESS(response.text))
