# Django settings for example_project project.

import os


PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'timepiece',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    },
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',

    # Timepiece apps must be listed before third-party apps in order
    # for template overrides to work.
    'timepiece',
    'timepiece.contracts',
    'timepiece.crm',
    'timepiece.entries',
    'timepiece.reports',

    'bootstrap3',
    'compressor',
    'selectable',
]

LANGUAGE_CODE = 'en-us'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

MEDIA_ROOT = os.path.join(PROJECT_PATH, 'public', 'media')

MEDIA_URL = '/media/'

MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'example_project.urls'

SECRET_KEY = 'oap0ahyb%_iitq1un(4j!#v81_%6jl$wefeh@$^=metg6w8pr^'

SITE_ID = 1

STATIC_ROOT = os.path.join(PROJECT_PATH, 'public', 'static')

STATIC_URL = '/static/'

STATICFILES_DIRS = []

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(PROJECT_PATH, 'templates')],
        #"APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.contrib.messages.context_processors.messages',
                'timepiece.context_processors.quick_search',
                'timepiece.context_processors.quick_clock_in',
                'timepiece.context_processors.extra_settings',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
        }
    }
]

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_L10N = True

USE_TZ = False  # NOTE: django-timepiece does not currently support timezones.

WSGI_APPLICATION = 'example_project.wsgi.application'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# === Third-party app settings. === #

COMPRESS_PRECOMPILERS = [
    ('text/less', 'lessc {infile} {outfile}'),
]

COMPRESS_ROOT = '%s/static/' % PROJECT_PATH


# === Timepiece settings. === #

TIMEPIECE_DEFAULT_LOCATION_SLUG = None

TIMEPIECE_PAID_LEAVE_PROJECTS = {}
