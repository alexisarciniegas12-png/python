from pathlib import Path
import os
import sys
import dj_database_url  # <-- IMPORTANTE: Librería para leer la URL de Supabase

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
SECRET_KEY = 'django-insecure-lp%h@y-1b8t8xim)2+p7p(z4lc2m@8pi1a8+j6y7^g31a8vo1z'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Permitir que Railway y tu localhost puedan acceder
ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'usuarios',
    'reservas',
    'pedidos',
    'mesas',
    'menu',
    'eventos',
    'ventas',
    'django.contrib.humanize',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # <-- REQUISITO PRODUCCIÓN: Para servir CSS y JS en Railway
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'proyecto.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'proyecto.wsgi.application'


# =====================================================================
# CONFIGURACIÓN DE BASE DE DATOS (HÍBRIDA LOCAL/PRODUCCIÓN)
# =====================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'restaurante',
        'USER': 'root',
        'PASSWORD': '12345',
        'HOST': 'localhost',
        'PORT': '3307',
        'TEST': {
            'NAME': 'test_restaurante',
            'MIGRATE': True,
        },
    }
}

# Si Railway nos inyecta la variable de entorno, sobreescribimos la conexión usando Supabase
if os.environ.get('DATABASE_URL'):
    DATABASES['default'] = dj_database_url.config(
        conn_max_age=600,
        ssl_require=True  # Supabase exige SSL obligatorio por seguridad
    )


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Almacenamiento optimizado para producción con WhiteNoise
if not DEBUG:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Carpeta física donde se guardarán las fotos
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# =====================================================================
# CONFIGURACIÓN EXCLUSIVA PARA ENTORNO DE PRUEBAS (SALTAR MIGRACIONES)
# =====================================================================
if 'test' in sys.argv:
    from django.test.runner import DiscoverRunner
    
    class FastTestRunner(DiscoverRunner):
        def setup_databases(self, **kwargs):
            from django.conf import settings
            from django.db import connections
            
            # 1. Ignorar por completo el historial de la carpeta 'migrations'
            settings.MIGRATION_MODULES = {
                app.split('.')[-1]: None 
                for app in settings.INSTALLED_APPS
            }
            
            # 2. Forzar a la base de datos a ignorar restricciones de FK en pruebas
            connections['default'].settings_dict['OPTIONS'] = {
                'init_command': "SET FOREIGN_KEY_CHECKS=0;"
            }
            
            return super().setup_databases(**kwargs)

    TEST_RUNNER = f"{__name__}.FastTestRunner"