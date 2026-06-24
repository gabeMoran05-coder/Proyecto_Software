from pathlib import Path
import os

from celery.schedules import crontab
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=None, sep=','):
    raw = os.environ.get(name)
    if raw is None:
        raw = default or ''
    if isinstance(raw, (list, tuple)):
        return [str(item).strip() for item in raw if str(item).strip()]
    return [item.strip() for item in raw.split(sep) if item.strip()]


SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-farmacia-cambiar-en-produccion')
DEBUG = env_bool('DJANGO_DEBUG', True)
ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', ['localhost', '127.0.0.1'])
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')

TIME_ZONE = os.environ.get('TIME_ZONE', 'America/Mexico_City')
LANGUAGE_CODE = os.environ.get('LANGUAGE_CODE', 'es-mx')

# ─── Apps instaladas ────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Apps del proyecto
    'apps.medicamentos.apps.MedicamentosConfig',
    'apps.proveedores.apps.ProveedoresConfig',
    'apps.clientes.apps.ClientesConfig',
    'apps.usuarios.apps.UsuariosConfig',
    'apps.ventas.apps.VentasConfig',
    'apps.reportes.apps.ReportesConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.usuarios.security.UsuarioAccessMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'farmacia.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.usuarios.security.usuario_context',
                'apps.medicamentos.context_processors.notificaciones_caducidad',
            ],
        },
    },
]

WSGI_APPLICATION = 'farmacia.wsgi.application'

# ─── Base de datos ───────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     os.environ.get('POSTGRES_DB',       'farmacia_inclusiva'),
        'USER':     os.environ.get('POSTGRES_USER',     'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'Farmacia123!'),
        'HOST':     os.environ.get('POSTGRES_HOST',     'db'),
        'PORT':     os.environ.get('POSTGRES_PORT',     '5432'),
    }
}

# ─── Validadores de contraseña ───────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── Internacionalización ────────────────────────────────────────────────────
USE_I18N = True
USE_TZ = True

# ─── Archivos estáticos ──────────────────────────────────────────────────────
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_SECURE_HSTS_SECONDS', 3600))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
    SECURE_HSTS_PRELOAD = env_bool('DJANGO_SECURE_HSTS_PRELOAD', False)
    SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', False)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SITE_PUBLIC_BASE_URL = os.environ.get('SITE_PUBLIC_BASE_URL', '').rstrip('/')
QR_PUBLIC_BASE_URL = os.environ.get('QR_PUBLIC_BASE_URL', SITE_PUBLIC_BASE_URL).rstrip('/')

EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend',
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', False)
DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL',
    EMAIL_HOST_USER or 'Farmacia Inclusiva <notificaciones@farmacia.local>',
)

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/1')
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = False
CELERY_TASK_TIME_LIMIT = int(os.environ.get('CELERY_TASK_TIME_LIMIT', 300))
CELERY_TASK_SOFT_TIME_LIMIT = int(os.environ.get('CELERY_TASK_SOFT_TIME_LIMIT', 240))
CELERY_BEAT_SCHEDULE = {
    'actualizar-estados-inventario-diario-0705': {
        'task': 'apps.medicamentos.tasks.actualizar_estados_inventario_task',
        'schedule': crontab(hour=7, minute=5),
    },
    'revisar-y-ocultar-lotes-caducos-diario-0710': {
        'task': 'apps.medicamentos.tasks.retirar_lotes_caducos_task',
        'schedule': crontab(minute='*/5'),
    },
    'limpiar-notificaciones-descartadas-cada-hora': {
        'task': 'apps.medicamentos.tasks.limpiar_notificaciones_descartadas_task',
        'schedule': crontab(minute=15),
    },
    'ejecutar-automatizaciones-correo-cada-minuto': {
        'task': 'apps.ventas.tasks.ejecutar_automatizaciones_correo_task',
        'schedule': crontab(minute='*'),
    },
}

WHATSAPP_GRAPH_API_VERSION = os.environ.get('WHATSAPP_GRAPH_API_VERSION', 'v21.0')
WHATSAPP_BUSINESS_ACCOUNT_ID = os.environ.get('WHATSAPP_BUSINESS_ACCOUNT_ID', '')
WHATSAPP_PHONE_NUMBER_ID = os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '')
WHATSAPP_ACCESS_TOKEN = os.environ.get('WHATSAPP_ACCESS_TOKEN', '')
WHATSAPP_TICKET_TEMPLATE_NAME = os.environ.get('WHATSAPP_TICKET_TEMPLATE_NAME', 'ticket_compra_farmacia')
WHATSAPP_TICKET_TEMPLATE_LANGUAGE = os.environ.get('WHATSAPP_TICKET_TEMPLATE_LANGUAGE', 'es_MX')
WHATSAPP_RECALL_TEMPLATE_NAME = os.environ.get('WHATSAPP_RECALL_TEMPLATE_NAME', 'aviso_producto_defectuoso')
WHATSAPP_RECALL_TEMPLATE_LANGUAGE = os.environ.get('WHATSAPP_RECALL_TEMPLATE_LANGUAGE', 'es_MX')
WHATSAPP_WEBHOOK_VERIFY_TOKEN = os.environ.get('WHATSAPP_WEBHOOK_VERIFY_TOKEN', '')
WHATSAPP_TICKET_TEMPLATE_HEADER_IMAGE = os.environ.get(
    'WHATSAPP_TICKET_TEMPLATE_HEADER_IMAGE',
    'False',
).lower() in {'1', 'true', 'yes', 'on'}

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_TTS_MODEL = os.environ.get('OPENAI_TTS_MODEL', 'gpt-4o-mini-tts')
OPENAI_TTS_VOICE = os.environ.get('OPENAI_TTS_VOICE', 'coral')
