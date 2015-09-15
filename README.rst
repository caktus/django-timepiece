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

NOTE from Chris: Branch Currently Under Development
---------------------------------------------------

This branch is undertaking an overhaul, and will be broken for a few days/weeks. It also means that once completed, this version will not be backwards compatible with previous timepiece releases.

Tasks being done:

 * I am removing the south migrations in favor of the Django built in, so that will end support for Django 1.6.
    - That means I'll need to figure out the dependencies & .travis files so that I can update them.
 * I am cleaning up the models and their relationships to each other, in favor of simpler database relations.
    - I'm still planning this part out, but I am considering removing the Attributes model in favor of selectable status and type fields.
    - There are also way too many FKs in some of the tables, so for example I am considering removing the point_person FK from the Project model, so that the Project is only a 1:many with the Business that the project is being done for.
 * I am adding a more complete sample project that is based on Django 1.8.4
    - I would also like to add more end user help because it has been a struggle for me to get this project up and running for myself. I'm fairly proficient in Python and DB modeling, but I am pretty new to Django.
    - I have added a Graphviz generated ERD of the current models, and will update it once I finish cleaning up the models.
    - I'm thinking that a few screenshots or some pre-loaded DB data would be nice to get a new user going.
 * More changes TBD as I continue poking through the code.
    - I am in favor of converting the less stuff back to standard css, as I don't see the need for this project to require node.js, npm, and less as dependencies. I'm not familiar with less, so I may or may not get to this.

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

django-timepiece is compatible with Django 1.6 (on Python 2.7 and Python 3.3), and Django 1.7 (on Python 2.7 and Python 3.4), and Django 1.8 (on Python 2.7 and Python 3.4). PostgreSQL is the only officially supported backend, however SQLite does work. For a full list of required libraries, see the `requirements/base.txt` from the project source on `GitHub`_.

We actively support desktop versions of Chrome and Firefox, as well as common mobile platforms. We do not support most versions of Internet Explorer. We welcome pull requests to fix bugs on unsupported browsers.

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

#. Ensure that `less`_ is installed on your machine::

    # Install node.js and npm:
    $ sudo apt-get install python-software-properties
    $ sudo add-apt-repository ppa:chris-lea/node.js
    $ sudo apt-get update
    $ sudo apt-get install nodejs npm

    # Use npm to install less:
    $ npm install less -g

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
        url(r'^selectable/', include('selectable.urls')),
        url(r'', include('timepiece.urls')),
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
            name='password_change'),
        url(r'^accounts/password-change/done/$',
            'django.contrib.auth.views.password_change_done',
            name='password_change_done'),
        url(r'^accounts/password-reset/$',
            'django.contrib.auth.views.password_reset',
            name='password_reset'),
        url(r'^accounts/password-reset/done/$',
            'django.contrib.auth.views.password_reset_done',
            name='password_reset_done'),
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

#. Add a login redirect URL to your settings.py file. This example redirects the user to the dashboard::

    LOGIN_REDIRECT_URL = '/dashboard'

Development sponsored by `Caktus Group`_.


.. _Caktus Group: https://www.caktusgroup.com/services
.. _GitHub: https://github.com/caktus/django-timepiece
.. _less: http://lesscss.org
.. _pip: http://pip.openplans.org/
.. _PyPI: http://pypi.python.org/pypi/django-timepiece
.. _Read The Docs: http://django-timepiece.readthedocs.org
