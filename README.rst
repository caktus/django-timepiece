django-timepiece
================

django-timepiece is a multi-user application for tracking people's time on
projects. Documentation is available on `Read The Docs`_.

:master: |master-status|
:develop: |develop-status|

.. |master-status| image::
    https://api.travis-ci.org/caktus/django-timepiece.png?branch=master
    :alt: Build Status
    :target: https://travis-ci.org/caktus/django-timepiece

.. |develop-status| image::
    https://api.travis-ci.org/caktus/django-timepiece.png?branch=develop
    :alt: Build Status
    :target: https://travis-ci.org/caktus/django-timepiece

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

django-timepiece is compatible with Django 1.8 (on Python 2.7 and Python 3.4) and
Django 1.9 (on Python 2.7 and Python 3.4). PostgreSQL is the only
officially supported backend. For a full list of required libraries, see
the `requirements/base.txt` from the project source on `GitHub`_.

We actively support desktop versions of Chrome and Firefox, as well as common
mobile platforms. We do not support most versions of Internet Explorer. We
welcome pull requests to fix bugs on unsupported browsers.

Documentation
-------------

Documentation is hosted on `Read The Docs`_.

To build the documentation locally:

#. Download a copy of the `django-timepiece` source, either through
   use of `git clone` or by downloading a zipfile from `GitHub`_.

#. Make sure that the top-level directory is on your Python path. If you're
   using a virtual environment, this can be accomplished via::

        cd /path/to/django-timepiece/ && add2virtualenv .

#. Install the requirements in `requirements/docs.txt` from the project
   source on `GitHub`_.

#. Run ``make html`` from within the `docs/` directory. HTML files will be
   output in the `docs/_build/html/` directory.

Installation
------------

#. django-timepiece is available on `PyPI`_, so the easiest way to
   install it and its dependencies is to use `pip`_::

    $ pip install django-timepiece

#. Ensure that `less`_ is installed on your machine and the version is <=1.4.0::

    # Install node.js and npm:
    $ sudo apt-get install python-software-properties
    $ sudo add-apt-repository ppa:chris-lea/node.js
    $ sudo apt-get update
    $ sudo apt-get install nodejs npm

    # Use npm to install less from package.json:
    $ npm install

#. If you are starting from the included example project, copy the example
   local settings file at `example_project/settings/local.py.example` to
   `example_project/settings/local.py`.

   If you are using an existing project, you will need to make the following
   changes to your settings:

   - Add `timepiece` and its dependencies to ``INSTALLED_APPS``::

        INSTALLED_APPS = (
            ...
            'bootstrap_toolkit',
            'compressor',
            'selectable',

            # Must come last.
            'timepiece',
            'timepiece.contracts',
            'timepiece.crm',
            'timepiece.entries',
            'timepiece.reports',
        )

   - Configure your middleware::

        MIDDLEWARE_CLASSES = (
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        )

   - Add `django.core.context_processors.request` and django-timepiece context
     processors to ``TEMPLATE_CONTEXT_PROCESSORS``::

        TEMPLATE_CONTEXT_PROCESSORS = (
            "django.contrib.auth.context_processors.auth",
            "django.core.context_processors.debug",
            "django.core.context_processors.i18n",
            "django.core.context_processors.media",
            "django.contrib.messages.context_processors.messages",
            "django.core.context_processors.request",           # <----
            "timepiece.context_processors.quick_clock_in",      # <----
            "timepiece.context_processors.quick_search",        # <----
            "timepiece.context_processors.extra_settings",      # <----
        )

   - Configure compressor settings::

        COMPRESS_PRECOMPILERS = (
            ('text/less', 'lessc {infile} {outfile}'),
        )
        COMPRESS_ROOT = '%s/static/' % PROJECT_PATH
        INTERNAL_IPS = ('127.0.0.1',)

   - Set ``USE_TZ`` to ``False``. django-timepiece does not currently support
     timezones.

#. Run ``syncdb`` and ``migrate``.

#. Add URLs for django-timepiece and selectable to `urls.py`, e.g.::

    urlpatterns = [
        ...
        (r'^selectable/', include('selectable.urls')),
        (r'', include('timepiece.urls')),
        ...
    ]

#. Add the ``django.contrib.auth`` URLs to `urls.py`, e.g.::

    urlpatterns = [
        ...
        url(r'^accounts/login/$', 'django.contrib.auth.views.login',
            name='auth_login'),
        url(r'^accounts/logout/$', 'django.contrib.auth.views.logout_then_login',
            name='auth_logout'),
        url(r'^accounts/password-change/$',
            'django.contrib.auth.views.password_change',
            name='change_password'),
        url(r'^accounts/password-change/done/$',
            'django.contrib.auth.views.password_change_done'),
        url(r'^accounts/password-reset/$',
            'django.contrib.auth.views.password_reset',
            name='reset_password'),
        url(r'^accounts/password-reset/done/$',
            'django.contrib.auth.views.password_reset_done'),
        url(r'^accounts/reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
            'django.contrib.auth.views.password_reset_confirm'),
        url(r'^accounts/reset/done/$',
            'django.contrib.auth.views.password_reset_complete'),
        ...
    ]

#. Create registration templates. For examples, see the registration templates
   in `example_project/templates/registration`. Ensure that your project's
   template directory is added to ``TEMPLATE_DIRS``::

    TEMPLATE_DIRS = (
        ...
        '%s/templates' % PROJECT_PATH,
        ...
    )

Development sponsored by `Caktus Group`_.


.. _Caktus Group: https://www.caktusgroup.com/services
.. _GitHub: https://github.com/caktus/django-timepiece
.. _less: http://lesscss.org
.. _pip: http://pip.openplans.org/
.. _PyPI: http://pypi.python.org/pypi/django-timepiece
.. _Read The Docs: http://django-timepiece.readthedocs.org
