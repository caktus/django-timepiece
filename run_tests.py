import os
import optparse

from django.conf import settings
from django.core.management import call_command

parser = optparse.OptionParser()
opts, args = parser.parse_args()


class TestRunner(object):
    def __init__(self, *args, **kwargs):
        self.databases = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': 'django_timepiece',
                'USER': '',
                'PASSWORD': '',
                'HOST': '',
                'PORT': '',
            }
        }
        self.project_apps = ('timepiece',)
        self.jenkins_tasks = (
            'django_jenkins.tasks.with_coverage',
            'django_jenkins.tasks.django_tests',
            'django_jenkins.tasks.run_pep8',
        )

    def run_jenkins_tests(self):
        settings.DATABASES = self.databases
        settings.INSTALLED_APPS += ('django_jenkins',)
        settings.PROJECT_APPS = self.project_apps
        settings.JENKINS_TASKS = self.jenkins_tasks
        # import pdb; pdb.set_trace()
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
            'output_dir': '%s/reports' % os.getcwd(),
        }
        call_command('jenkins', **kwargs)

    def run_django_tests(self):
        settings.DATABASES = self.databases
        call_command('test', 'timepiece')

if __name__ == '__main__':
    runner = TestRunner()
    if 'jenkins' in args:
        runner.run_jenkins_tests()
    else:
        runner.run_django_tests()
