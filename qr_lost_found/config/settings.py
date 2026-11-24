from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'development-only-change-me'
)

DEBUG = (
    os.getenv('VERCEL') != '1'
    and os.getenv('DEBUG', 'True').lower() == 'true'
)

ALLOWED_HOSTS = [
    x.strip()
    for x in os.getenv(
        'ALLOWED_HOSTS',
        '127.0.0.1,localhost'
    ).split(',')
]

if os.getenv('VERCEL') == '1':
    ALLOWED_HOSTS.append('.vercel.app')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'core.apps.CoreConfig',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'config.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# Database Configuration
database_url = os.getenv('DATABASE_URL', '').strip()

if database_url:

    DATABASES = {
        'default': dj_database_url.parse(
            database_url,
            conn_max_age=600,
        )
    }

elif os.getenv('DB_ENGINE', 'sqlite').lower() == 'postgres':

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'lost_found'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', '127.0.0.1'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }

else:

    database_name = (
        Path('/tmp/lost_found.sqlite3')
        if os.getenv('VERCEL') == '1'
        else BASE_DIR / 'db.sqlite3'
    )

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': database_name,
        }
    }


# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Language and Time
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'
USE_I18N = True
USE_TZ = True


# Static Files
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = (
    Path('/tmp/returnloop-static')
    if os.getenv('VERCEL') == '1'
    else BASE_DIR / 'staticfiles'
)
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if DEBUG or os.getenv('VERCEL') == '1'
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
    },
}


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Authentication
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'home'


# Email Configuration
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')

EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))

EMAIL_USE_TLS = os.getenv(
    'EMAIL_USE_TLS',
    'True'
).lower() == 'true'

EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')

EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

if 'EMAIL_BACKEND' in os.environ:
    EMAIL_BACKEND = os.environ['EMAIL_BACKEND']
elif DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
elif EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.dummy.EmailBackend'

EMAIL_DELIVERY_CONFIGURED = (
    EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend'
    and bool(EMAIL_HOST_USER and EMAIL_HOST_PASSWORD)
)

DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    'ReturnLoop <no-reply@returnloop.local>'
)

EMAIL_TIMEOUT = 20


# Security
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SECURE_SSL_REDIRECT = os.getenv(
        'SECURE_SSL_REDIRECT',
        'False' if os.getenv('VERCEL') == '1' else 'True'
    ).lower() == 'true'
    SECURE_HSTS_SECONDS = int(os.getenv(
        'SECURE_HSTS_SECONDS',
        '31536000'
    ))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
