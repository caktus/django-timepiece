django-timepiece
================

django-timepiece is a multi-user application for tracking people's time on projects.

Features
--------

 * A simple CRM with projects and businesses
 * User dashboards with budgeted hours based on project contracts
 * Time sheets with daily, weekly, and monthly summaries
 * Verified, approved, and invoiced time sheet workflows
 * Monthly payroll reporting with overtime, paid leave, and vacation summaries
 * Project invoicing with hourly summaries

Requirements
------------

django-timepiece is compatible with Python 2.{6,7} and Django 1.{3,4}. PostgreSQL is the only offically supported database backend and, therefore, requires `psycopg2 <http://initd.org/psycopg/>`_. django-timepiece also depends on the following Django apps:

 * `python-dateutil <http://labix.org/python-dateutil>`_
 * `django-selectable <http://pypi.python.org/pypi/django-selectable>`_
 * `django-pagination <http://pypi.python.org/pypi/django-pagination>`_
 * `django-compressor <https://github.com/jezdez/django_compressor>`_
 * `django-bootstrap-toolkit <https://github.com/dyve/django-bootstrap-toolkit>`_

django-timepiece uses Sphinx and RST for documentation. You can use Sphinx to build the documentation

 * `docutils <http://docutils.sourceforge.net/>`_
 * `Sphinx <http://sphinx.pocoo.org/>`_

A makefile is included with the documentation so you can run `make html` in the `doc/` directory to build the documentation

Installation
------------

#. django-timepiece is available on `PyPI <http://pypi.python.org/pypi/django-timepiece>`_, so the easiest way to install it is to use `pip <http://pip.openplans.org/>`_::

    pip install django-timepiece

#. Add `timepiece` to INSTALLED_APPS in settings.py and run syncdb::

    INSTALLED_APPS = (
        ...
        'timepiece',
        ...
    )

#. Add `django.core.context_processors.request` to TEMPLATE_CONTEXT_PROCESSORS::

    TEMPLATE_CONTEXT_PROCESSORS = (
        "django.contrib.auth.context_processors.auth",
        "django.core.context_processors.debug",
        "django.core.context_processors.i18n",
        "django.core.context_processors.media",
        "django.contrib.messages.context_processors.messages",
        "django.core.context_processors.request", # <----
    )

#. Add the timepiece URLs to urls.py, e.g.::

    urlpatterns = patterns('',
        ...
        (r'^timepiece/', include('timepiece.urls')),
        ...
    )

Testing
-------

django-timepiece includes several different alternatives for testing. Test can be run using the default django test runner, through `Tox <http://tox.testrun.org/latest/>`_, or with `django-jenkins <https://github.com/kmmbvnr/django-jenkins>`_. Tox and django-jenkins are not required to run the tests for django-timepiece, but it is possible to use them::

    pip install --upgrade tox django-jenkins

A Python module, ``run_tests.py``, is included if you do not want to run tests using Tox. This is the Python module used to run tests when executing ``python setup.py test``. The tests are run through Django, using Django's default test runner. It accepts an optional argument, ``run_tests.py jenkins``, that runs the tests using django-jenkins. Running the tests with django-jenkins also requires you to install `coverage <http://pypi.python.org/pypi/coverage>`_ and `pep8 <http://pypi.python.org/pypi/pep8/>`_.

django-timepiece inclues a Tox configuration file to run tests in a variety of environments:

 * `py26-1.3` - Test using Python 2.6 and Django 1.3.x
 * `py26-1.4` - Test using Python 2.6 and Django 1.4.x
 * `py27-1.3` - Test using Python 2.7 and Django 1.3.x
 * `py27-1.4` - Test using Python 2.7 and Django 1.4.x

You can run any of the environments listed above using: ``tox -e name``. The tests are run through Django's default test runner, but you can also run the tests using django-jenkins along with tox by providing an extra argument: ``tox -e name -- jenkins``.

Development sponsored by `Caktus Consulting Group, LLC
<http://www.caktusgroup.com/services>`_.
