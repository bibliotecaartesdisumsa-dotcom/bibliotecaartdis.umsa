from pathlib import Path
import os
from django.contrib.messages import constants as messages
import cloudinary
import cloudinary.uploader
import cloudinary.api
import sys
import resend

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-7xx+3%9o4ni5#7s$0)3lyjb8g4albmz533@^+3w)1hm$v$06^)'

# Silenciar warnings específicos
import warnings
warnings.filterwarnings("ignore", module="admin_interface.templatetags")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    'bibliotecaartdisumsa-production.up.railway.app',
    '.up.railway.app',
    '127.0.0.1',
    'localhost',
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Cloudinary
    'cloudinary',
    'cloudinary_storage',
    
    # Apps propias
    'biblioartdis.apps.BiblioartdisConfig',
    
    # Aplicaciones adicionales
    'django_extensions',
    'django_filters',
    'django_cleanup.apps.CleanupConfig',
    'rest_framework',
    'widget_tweaks',
    'import_export',
    'django_session_timeout',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_session_timeout.middleware.SessionTimeoutMiddleware',
]

ROOT_URLCONF = 'arteydis.urls'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Logging mejorado para producción
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
        'file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django_errors.log'),
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'default',
        },
    },
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'biblioartdis': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'cloudinary': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}

# Crear directorio de logs si no existe
if not os.path.exists(os.path.join(BASE_DIR, 'logs')):
    os.makedirs(os.path.join(BASE_DIR, 'logs'))

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
LOGIN_REDIRECT_URL = '/inicio/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/'

WSGI_APPLICATION = 'arteydis.wsgi.application'

# ============================================
# BASE DE DATOS SUPABASE (POSTGRESQL)
# ============================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres.vmwkbkvsthswxshcwhmp',
        'PASSWORD': 'cnPd.fxp4x.5kMQ2',
        'HOST': 'aws-1-us-east-1.pooler.supabase.com',
        'PORT': '6543',
        'OPTIONS': {
            'sslmode': 'require',
        },
        'CONN_MAX_AGE': 60,
        'CONN_HEALTH_CHECKS': True,
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 9},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Configuración de timeout de sesión
SESSION_EXPIRE_SECONDS = 3600
SESSION_EXPIRE_AFTER_LAST_ACTIVITY = True
SESSION_TIMEOUT_REDIRECT = '/'

# Internationalization
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/La_Paz'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Configuración de mensajes
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

X_FRAME_OPTIONS = 'SAMEORIGIN'

# ============================================
# CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS
# ============================================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================================
# CONFIGURACIÓN DE CLOUDINARY
# ============================================

cloudinary.config(
    cloud_name='dnnl3rije',
    api_key='372388277625767',
    api_secret='1Gjjfdf968eIypjxyu_nr3fo2Mk',
    secure=True
)

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'dnnl3rije',
    'API_KEY': '372388277625767',
    'API_SECRET': '1Gjjfdf968eIypjxyu_nr3fo2Mk',
    'SECURE': True,
}

# Usar Cloudinary Storage
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
MEDIA_URL = '/media/'

# ============================================
# CONFIGURACIÓN DE EMAIL CON RESEND
# ============================================

# Configurar Resend con tu API Key
RESEND_API_KEY = 're_M9BFWHyM_3kioxxBxW55dJRa5PQFz7gZE'
resend.api_key = RESEND_API_KEY

# Email backend con Resend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.resend.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'resend'
EMAIL_HOST_PASSWORD = RESEND_API_KEY
DEFAULT_FROM_EMAIL = 'Biblioteca ARTyDIS <onboarding@resend.dev>'
EMAIL_TIMEOUT = 30

# ============================================
# CONFIGURACIONES DE SEGURIDAD PARA PRODUCCIÓN
# ============================================

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

CSRF_TRUSTED_ORIGINS = [
    'https://bibliotecaartdisumsa-production.up.railway.app',
]
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600

# ============================================
# CONFIGURACIONES ADICIONALES
# ============================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SILENCED_SYSTEM_CHECKS = ['security.W019']
IMPORT_EXPORT_USE_TRANSACTIONS = True
IMPORT_EXPORT_SKIP_ADMIN_LOG = False

# ============================================
# CONFIGURACIÓN PARA EVITAR SEÑALES DUPLICADAS
# ============================================

IS_MANAGEMENT_COMMAND = 'manage.py' in sys.argv[0] if sys.argv else False