"""
Django settings for the LentenSermons project.

Generated by 'django-admin startproject' using Django 1.9.1.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os
import posixpath
import socket
import sys
from django.contrib import admin

hst = socket.gethostbyname(socket.gethostname())
bUseTunnel = False

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_NAME = os.path.basename(BASE_DIR)
WRITABLE_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../writable/database/"))

if "RU-lenten\\writable" in WRITABLE_DIR:
    # Need another string
    WRITABLE_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../../writable/database/"))
elif "/applejack" in BASE_DIR:
    WRITABLE_DIR = os.path.abspath(os.path.join(BASE_DIR, "../../writable/lenten/database/"))

MEDIA_DIR = os.path.abspath(os.path.join(WRITABLE_DIR, "../media/"))

APP_PREFIX = ""
ADMIN_SITE_URL = ""
if "d:" in WRITABLE_DIR or "D:" in WRITABLE_DIR or "c:" in WRITABLE_DIR or "C:" in WRITABLE_DIR or bUseTunnel:
    APP_PREFIX = ""
    ADMIN_SITE_URL = '/'
elif "131.174" in hst:
    # Configuration within the Radboud University environment (AppleJack)
    APP_PREFIX = ""
    ADMIN_SITE_URL = '/'
elif "/var/www" in WRITABLE_DIR:
    # New configuration 
    APP_PREFIX = "lentensermons/"
    ADMIN_SITE_URL = '/lentensermons'
else:
    APP_PREFIX = "dd/"
    ADMIN_SITE_URL = '/dd'

# FORCE_SCRIPT_NAME = admin.site.site_url

DATA_UPLOAD_MAX_NUMBER_FIELDS = None

BLOCKED_IPS = ['40.77.167.57',
               '45.146.165.123',
               '45.61.186.43',
               '46.229.168.133', 
               '88.198.17.136', 
               '157.55.39.235',
               '157.55.39.199',
               '54.36.148.', '54.36.149.'
               ]



# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '561c5400-4ebf-4e45-a2ec-12d856638e45'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', 'applejack.science.ru.nl', 'lentensermons.science.ru.nl', 'lentensermons.cls.ru.nl', 'testserver' ]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Add your apps here to enable them
    'django_select2',
    'lentensermons.basic',
    'lentensermons.tagtext',
    'lentensermons.seeker',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'lentensermons.utils.BlockedIpMiddleware'
]

ROOT_URLCONF = 'lentensermons.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'lentensermons/templates')],
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

WSGI_APPLICATION = 'lentensermons.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(WRITABLE_DIR, 'lenten.db'),
        'TEST': {
            'NAME': os.path.join(WRITABLE_DIR, 'lenten-test.db'),
            }
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Amsterdam'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_URL = '/static/'
if ("/var/www" in WRITABLE_DIR and not bUseTunnel):
    STATIC_URL = "/" + APP_PREFIX + "static/"

STATIC_ROOT = os.path.abspath(os.path.join("/", posixpath.join(*(BASE_DIR.split(os.path.sep) + ['static']))))
