#!/usr/bin/env python
import os
import sys
import optparse

from django.conf import settings
from django.core.management import call_command, setup_environ


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
            'django.contrib.markup',
            'bootstrap_toolkit',
            'compressor',
            'pagination',
            'selectable',
            'timepiece',
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
        STATIC_URL='%s/example_project/static/' % directory,
        TEMPLATE_CONTEXT_PROCESSORS=(
            'django.contrib.auth.context_processors.auth',
            'django.core.context_processors.debug',
            'django.core.context_processors.i18n',
            'django.core.context_processors.media',
            'django.core.context_processors.static',
            'django.contrib.messages.context_processors.messages',
            'django.core.context_processors.request',
            'timepiece.context_processors.quick_search',
            'timepiece.context_processors.extra_nav',
        ),
        TEMPLATE_DIRS=(
            '%s/example_project/templates' % directory,
        ),

        # compress settings.
        COMPRESS_PRECOMPILERS=(
            ('text/less', 'lessc {infile} {outfile}'),
        ),
        COMPRESS_ROOT='%s/timepiece/static/' % directory,

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


def run_jenkins_tests():
    kwargs = {
        'pep8-exclude': 'migrations',
        'pep8-select': '',
        'pep8-ignore': '',
        'pep8-max-line-length': 80,
        'coverage-exclude': 'timepiece.migrations',
        'coverage_with_migrations': False,
        'coverage_html_report_dir': '',
        'coverage_excludes': [],
        'coverage_measure_branch': False,
        'coverage_rcfile': '',
        'output_dir': 'reports/',
    }
    call_command('jenkins', **kwargs)


def run_django_tests():
    from django.test.utils import get_runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, interactive=True, failfast=False)
    failures = test_runner.run_tests(['timepiece'])
    sys.exit(failures)


if __name__ == '__main__':
    if 'jenkins' in args:
        run_jenkins_tests()
    else:
        run_django_tests()
