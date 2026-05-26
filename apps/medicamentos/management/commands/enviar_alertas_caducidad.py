from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils import timezone

from apps.medicamentos.context_processors import (
    lotes_con_alerta_caducidad,
    resumen_alertas_caducidad,
)
from apps.medicamentos.models import Lote
from apps.usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Envía un resumen de lotes caducos y próximos a caducar a administradores activos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra destinatarios y resumen sin enviar correos.',
        )

    def handle(self, *args, **options):
        admins = list(
            Usuario.objects.filter(
                activo=True,
                rol__in=[Usuario.ROL_ADMIN, Usuario.ROL_ADMINISTRADOR],
                email__isnull=False,
            )
            .exclude(email='')
            .order_by('nombre', 'ap_pat', 'usuario')
        )
        lotes = lotes_con_alerta_caducidad(incluir_descartadas=True)
        caducos, proximos = resumen_alertas_caducidad(lotes)
        total = caducos + proximos

        if not admins:
            self.stdout.write(self.style.WARNING('No hay administradores activos con correo registrado.'))
            return
        if total == 0:
            self.stdout.write('No hay alertas de caducidad para enviar.')
            return

        subject = f'Alertas de caducidad: {caducos} caducos, {proximos} próximos'
        text_body = self._text_body(lotes, caducos, proximos)
        html_body = self._html_body(lotes, caducos, proximos)

        if options['dry_run']:
            self.stdout.write('DRY RUN: no se enviaron correos.')
            self.stdout.write(f'Destinatarios: {", ".join(admin.email for admin in admins)}')
            self.stdout.write(subject)
            return

        sent = 0
        for admin in admins:
            message = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[admin.email],
            )
            message.attach_alternative(html_body, 'text/html')
            sent += message.send()

        self.stdout.write(self.style.SUCCESS(f'Correos enviados: {sent}'))

    def _text_body(self, lotes, caducos, proximos):
        lines = [
            'Farmacia Inclusiva',
            'Resumen de alertas de caducidad',
            '',
            f'Fecha: {timezone.localdate():%d/%m/%Y}',
            f'Caducos: {caducos}',
            f'Próximos a caducar: {proximos}',
            '',
        ]
        url = self._notificaciones_url()
        if url:
            lines.extend(['Ver detalle:', url, ''])

        for lote in lotes:
            medicamento = self._medicamento_nombre(lote)
            fecha = lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else '-'
            dias = lote.dias_para_caducar
            estado = 'Caduco' if lote.estado_caducidad == Lote.CADUCIDAD_ROJO else 'Próximo a caducar'
            lines.append(f'- {medicamento} | Lote {lote.numero_lote} | {fecha} | {estado} | {dias} días')
        return '\n'.join(lines)

    def _html_body(self, lotes, caducos, proximos):
        rows = []
        for lote in lotes:
            medicamento = self._medicamento_nombre(lote)
            fecha = lote.fecha_caducidad.strftime('%d/%m/%Y') if lote.fecha_caducidad else '-'
            dias = lote.dias_para_caducar
            estado = 'Caduco' if lote.estado_caducidad == Lote.CADUCIDAD_ROJO else 'Próximo a caducar'
            rows.append(
                '<tr>'
                f'<td>{medicamento}</td>'
                f'<td>{lote.numero_lote}</td>'
                f'<td>{fecha}</td>'
                f'<td>{estado}</td>'
                f'<td>{dias}</td>'
                '</tr>'
            )

        url = self._notificaciones_url()
        link = f'<p><a href="{url}">Ver detalle en el sistema</a></p>' if url else ''
        return (
            '<h2>Farmacia Inclusiva</h2>'
            '<h3>Resumen de alertas de caducidad</h3>'
            f'<p><strong>Fecha:</strong> {timezone.localdate():%d/%m/%Y}</p>'
            f'<p><strong>Caducos:</strong> {caducos}<br>'
            f'<strong>Próximos a caducar:</strong> {proximos}</p>'
            f'{link}'
            '<table border="1" cellpadding="6" cellspacing="0">'
            '<thead><tr><th>Medicamento</th><th>Lote</th><th>Caducidad</th><th>Estado</th><th>Días</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody>'
            '</table>'
        )

    def _medicamento_nombre(self, lote):
        medicamento = lote.medicamento_set.all()[0] if len(lote.medicamento_set.all()) else None
        return medicamento.nombre if medicamento else 'Lote sin medicamento'

    def _notificaciones_url(self):
        if not settings.SITE_PUBLIC_BASE_URL:
            return ''
        return settings.SITE_PUBLIC_BASE_URL + reverse('lote_notificaciones')
