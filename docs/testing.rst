Testing
=======

Test requirements are listed in `requirements/tests.txt` file in the `project
source <https://github.com/caktus/django-timepiece>`_. These requirements are
in addition to the main project requirements in `requirements/base.html`.

After you have installed `django-timepiece` in your project, you can use the
Django test runner to run tests against your installation::

    python manage.py test timepiece timepiece.contracts timepiece.crm timepiece.entries timepiece.reports

Tests in Development
====================

To easily run tests against different environments that `django-timepiece`
supports, download the source and navigate to the `django-timepiece`
directory. From there, you can use tox to run tests against a specific
environment::

    tox -e python3.8-django3.2

Or omit the `-e` argument to run tests against all combinations of Python
and Django that `django-timepiece` supports. By default tox uses the example
project test settings, but you can specify different test settings using the
``--settings`` flag. You can also specify a subset of apps to test against.
