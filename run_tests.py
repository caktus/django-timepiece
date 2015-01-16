#!/usr/bin/env python
import os
import sys
import optparse


parser = optparse.OptionParser()
_, args = parser.parse_args()


DEFAULT_APPS = [
    'timepiece',
    'timepiece.contracts',
    'timepiece.crm',
    'timepiece.entries',
    'timepiece.reports',
]


def run_django_tests():
    # Use the example project settings, which are intentionally bare-bones.
    os.environ['DJANGO_SETTINGS_MODULE'] = 'example_project.settings.tests'

    import django
    if hasattr(django, 'setup'):  # Django 1.7
        django.setup()

    from django.test.runner import DiscoverRunner
    runner = DiscoverRunner(verbosity=1, interactive=True, failfast=False)
    failures = runner.run_tests(args or DEFAULT_APPS)
    sys.exit(failures)


if __name__ == '__main__':
    run_django_tests()
