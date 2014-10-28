#!/usr/bin/env python
import os
import sys
import optparse
import django

from django.conf import settings
from django import VERSION as DJANGO_VERSION


parser = optparse.OptionParser()
opts, args = parser.parse_args()

if not settings.configured:
    directory = os.path.abspath('%s' % os.path.dirname(__file__))
    jenkins = ()
    db_name = 'test_django_timepiece'
    if 'jenkins' in args:
        jenkins = ('django_jenkins',)
        db_name = 'timepiece_%s' % os.environ.get('TESTENV', db_name)

    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': 'django_timepiece',
                'TEST_NAME': db_name,
            }
        },
        INSTALLED_APPS=(
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.sites',
            'bootstrap_toolkit',
            'compressor',
            'pagination',
            'selectable',
            'timepiece',
            'timepiece.contracts',
            'timepiece.crm',
            'timepiece.entries',
            'timepiece.reports',
        ) + jenkins,
        MIDDLEWARE_CLASSES=(
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'pagination.middleware.PaginationMiddleware',
        ),
        ROOT_URLCONF='example_project.urls',
        SITE_ID=1,
        STATIC_URL='%s/timepiece/static/' % directory,
        TEMPLATE_CONTEXT_PROCESSORS=(
            'django.contrib.auth.context_processors.auth',
            'django.core.context_processors.debug',
            'django.core.context_processors.i18n',
            'django.core.context_processors.media',
            'django.core.context_processors.static',
            'django.contrib.messages.context_processors.messages',
            'django.core.context_processors.request',
            'timepiece.context_processors.quick_search',
            'timepiece.context_processors.quick_clock_in',
            'timepiece.context_processors.extra_settings',
        ),
        TEMPLATE_DIRS=(
            '%s/example_project/templates' % directory,
        ),

        # In tests, compressor has a habit of choking on failing tests & masking the real error.
        COMPRESS_ENABLED=False,
        STATIC_ROOT='static/',

        # jenkins settings.
        PROJECT_APPS=('timepiece',),
        JENKINS_TASKS=(
            'django_jenkins.tasks.with_coverage',
            'django_jenkins.tasks.django_tests',
            'django_jenkins.tasks.run_pep8',
        ),

        # Increase speed in 1.4.
        PASSWORD_HASHERS=('django.contrib.auth.hashers.MD5PasswordHasher',),
    )


def run_django_tests():
    from django.test.utils import get_runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, interactive=True, failfast=False)
    apps = ['timepiece', 'contracts', 'crm', 'entries', 'reports']
    if DJANGO_VERSION[0] == 1 and DJANGO_VERSION[1] >= 6:
        apps = ['timepiece', 'timepiece.contracts', 'timepiece.crm',
                'timepiece.entries', 'timepiece.reports']
    if DJANGO_VERSION[0] == 1 and DJANGO_VERSION[1] >= 7:
        django.setup()
    failures = test_runner.run_tests(args or apps)
    sys.exit(failures)


if __name__ == '__main__':
    run_django_tests()
