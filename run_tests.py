#!/usr/bin/env python
import os
import sys
import argparse


# By default, tests will be run for these apps.
# Other tests can be specified via command-line arguments.
DEFAULT_APPS = [
    'timepiece',
    'timepiece.contracts',
    'timepiece.crm',
    'timepiece.entries',
    'timepiece.reports',
]


parser = argparse.ArgumentParser(
    description="Run tests for the django-timepiece application.")
parser.add_argument(
    'apps',
    nargs="*",
)
parser.add_argument(
    '--settings',
    dest="settings",
    default="example_project.settings.tests",
    help="Django settings file to use.",
)


def run_django_tests(settings, apps):
    os.environ['DJANGO_SETTINGS_MODULE'] = settings

    import django
    if hasattr(django, 'setup'):  # Django 1.7+
        django.setup()

    from django.conf import settings
    from django.test.utils import get_runner
    runner = get_runner(settings)(verbosity=1, interactive=True, failfast=False)
    failures = runner.run_tests(apps or DEFAULT_APPS)
    sys.exit(failures)


if __name__ == '__main__':
    options = parser.parse_args()
    run_django_tests(options.settings, options.apps)
