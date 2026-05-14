from pathlib import Path
import os
from django.contrib.messages import constants as messages
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-7xx+3%9o4ni5#7s$0)3lyjb8g4albmz533@^+3w)1hm$v$06^)'
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
    'admin_interface',
    'colorfield',
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary',
    'cloudinary_storage',
    'biblioartdis.apps.BiblioartdisConfig',
    
    # Aplicaciones adicionales
    'django_extensions',
    'django_filters',
    'django_cleanup.apps.CleanupConfig',
    'rest_framework',
    # 'auditlog',  # 🔥 DESACTIVADO - Causaba error __str__
    # 'reversion',  # 🔥 DESACTIVADO
    'widget_tweaks',
    'import_export',
    'django_session_timeout',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'auditlog.middleware.AuditlogMiddleware',  # 🔥 DESACTIVADO
    # 'reversion.middleware.RevisionMiddleware',  # 🔥 DESACTIVADO
    'django_session_timeout.middleware.SessionTimeoutMiddleware',
]

ROOT_URLCONF = 'arteydis.urls'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Primero el backend por defecto
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

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'chatbot_errors.log',
            'maxBytes': 5000000,
            'backupCount': 2,
            'formatter': 'default',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
    },
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
        'cloudinary': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
LOGIN_REDIRECT_URL = '/inicio/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/'

WSGI_APPLICATION = 'arteydis.wsgi.application'

# Database

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
    }
}
# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 9}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
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

# ============================================
# CONFIGURACIÓN DE CLOUDINARY (CORREGIDA)
# ============================================

# Configuración de Cloudinary
cloudinary.config(
    cloud_name='dnnl3rije',
    api_key='372388277625767',
    api_secret='1Gjjfdf968eIypjxyu_nr3fo2Mk',
    secure=True
)

# Configuración de Cloudinary Storage
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': 'dnnl3rije',
    'API_KEY': '372388277625767',
    'API_SECRET': '1Gjjfdf968eIypjxyu_nr3fo2Mk',
    'SECURE': True,
    'STATICFILES_MANIFEST_ROOT': os.path.join(BASE_DIR, 'staticfiles'),
}

# Usar Cloudinary para todos los archivos media
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# Cloudinary maneja las URLs de los archivos automáticamente
MEDIA_URL = '/media/'

# Para debugging de Cloudinary
import logging
logging.getLogger('cloudinary').setLevel(logging.INFO)

# ============================================
# CONFIGURACIÓN DE EMAIL (VERIFICACIÓN 2FA)
# ============================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'biblioteca.artesdis.umsa@gmail.com'
EMAIL_HOST_PASSWORD = 'chlbefsqxhtfclfp'
DEFAULT_FROM_EMAIL = 'Biblioteca ARTyDIS <biblioteca.artesdis.umsa@gmail.com>'

# ============================================
# CONFIGURACIONES ADICIONALES
# ============================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuración adicional para admin-interface
SILENCED_SYSTEM_CHECKS = ['security.W019']

IMPORT_EXPORT_USE_TRANSACTIONS = True
IMPORT_EXPORT_SKIP_ADMIN_LOG = False

# Configuración para django-reversion (desactivado)
# REVERSION_REGISTER_AUTO_ADD_TO_ADMIN = True