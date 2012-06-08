from django.conf import settings
from django.core.management import call_command

databases = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'caktus',
        'USER': 'omarestrella',
        'PASSWORD': 'nothing',
        'HOST': '',
        'PORT': '',
    }
}
project_apps = ('timepiece',)
jenkins_tasks = (
    'django_jenkins.tasks.with_coverage',
    'django_jenkins.tasks.django_tests',
    'django_jenkins.tasks.run_pep8',
)

settings.DATABASES = databases
settings.INSTALLED_APPS += ('django_jenkins',)
settings.PROJECT_APPS = project_apps
settings.JENKINS_TASKS = jenkins_tasks


def runtests():
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
    }
    call_command('jenkins', **kwargs)

if __name__ == '__main__':
    runtests()
