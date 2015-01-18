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


def run_django_tests(options):
    # Use the example project settings, which are intentionally bare-bones.
    os.environ['DJANGO_SETTINGS_MODULE'] = options.settings

    import django
    if hasattr(django, 'setup'):  # Django 1.7
        django.setup()

    from django.test.runner import DiscoverRunner
    runner = DiscoverRunner(verbosity=1, interactive=True, failfast=False)
    failures = runner.run_tests(options.apps or DEFAULT_APPS)
    sys.exit(failures)


if __name__ == '__main__':
    options = parser.parse_args()
    run_django_tests(options)
