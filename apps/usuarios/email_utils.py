from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.usuarios.models import Usuario


def admin_emails():
    return list(
        Usuario.objects.filter(
            activo=True,
            rol__in=[Usuario.ROL_ADMIN, Usuario.ROL_ADMINISTRADOR],
            email__isnull=False,
        )
        .exclude(email='')
        .values_list('email', flat=True)
    )


def usuario_email(usuario):
    if usuario and usuario.activo and usuario.email:
        return usuario.email
    return ''


def public_url(path):
    base_url = getattr(settings, 'SITE_PUBLIC_BASE_URL', '').rstrip('/')
    if not base_url:
        return path
    return f'{base_url}{path}'


def send_admin_email(subject, text_body, html_body=None, attachments=None, recipients=None):
    recipients = admin_emails() if recipients is None else list(recipients)
    recipients = [email for email in recipients if email]
    if not recipients:
        return 0

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    if html_body:
        message.attach_alternative(html_body, 'text/html')

    for filename, content, mimetype in attachments or []:
        message.attach(filename, content, mimetype)

    message.send()
    return len(recipients)
