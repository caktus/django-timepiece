Testing
=======

Test requirements are listed `here <../requirements/tests.txt>`_.

You can run tests against your installation of django-timepiece using the
Django test runner::

    python manage.py test

Or with specific apps::

    python manage.py test timepiece timepiece.crm timepiece.reports

You can also use tox to run tests against a specific environment::

    tox -e py3.4-django1.7

Or omit the `-e` argument to run tests against all combinations of Python
and Django that django-timepiece supports. By default tox uses the example
project test settings, but you can specify different test settings using the
``--settings`` flag. You can also specify which apps to test against.
