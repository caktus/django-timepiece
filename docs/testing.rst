Testing
=======

django-timepiece includes several different alternatives for testing. Test can be run using the default django test runner, through `Tox <http://tox.testrun.org/latest/>`_, or with `django-jenkins <https://github.com/kmmbvnr/django-jenkins>`_. Tox and django-jenkins are not required to run the tests for django-timepiece, but it is possible to use them::

    pip install --upgrade tox django-jenkins

A Python module, ``run_tests.py``, is included if you do not want to run tests using Tox. This is the Python module used to run tests when executing ``python setup.py test``. The tests are run through Django, using Django's default test runner. It accepts an optional argument, ``run_tests.py jenkins``, that runs the tests using django-jenkins. Running the tests with django-jenkins also requires you to install `coverage <http://pypi.python.org/pypi/coverage>`_ and `pep8 <http://pypi.python.org/pypi/pep8/>`_.

To run a subset of the Django tests for django-timepiece, you can pass their names to ``run_tests.py`` as you would for ``django-admin.py test``, e.g. ``run_tests.py timepiece.TestClassName [...]``.

django-timepiece inclues a Tox configuration file to run tests in a variety of environments:

 * `py26-1.4` - Test using Python 2.6 and Django 1.4.x
 * `py26-1.5` - Test using Python 2.6 and Django 1.5.x
 * `py26-1.6` - Test using Python 2.6 and Django 1.6.x
 * `py26-1.7` - Test using Python 2.6 and Django 1.7.x
 * `py27-1.4` - Test using Python 2.7 and Django 1.4.x
 * `py27-1.5` - Test using Python 2.7 and Django 1.5.x
 * `py27-1.6` - Test using Python 2.7 and Django 1.6.x
 * `py27-1.7` - Test using Python 2.7 and Django 1.7.x

You can run any of the environments listed above using: ``tox -e name``. The tests are run through Django's default test runner, but you can also run the tests using django-jenkins along with tox by providing an extra argument: ``tox -e name -- jenkins``.


