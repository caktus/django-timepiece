django-timepiece
================

django-timepiece is a multi-user application for tracking people's time on
projects. Documentation is available on `Read The Docs`_.

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

django-timepiece is compatible with Django 4.2 (on Python 3.9+) and
Django 5.x (Python 3.10+). PostgreSQL is the only
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

#. Ensure that `less`_ is installed on your machine and the version is 1.4.0::

    # Install node.js and npm:
    $ sudo apt-get install python-software-properties
    $ sudo add-apt-repository ppa:chris-lea/node.js
    $ sudo apt-get update
    $ sudo apt-get install nodejs npm
    $ npm install less@1.4.0

    # Use npm to install less from package.json:
    $ npm install

#. If you are starting from the included example project, copy the example
   local settings file at `example_project/settings/local.py.example` to
   `example_project/settings/local.py`.

   If you are using an existing project, you will need to make the following
   changes to your settings:

   - Add `timepiece` and its dependencies to ``INSTALLED_APPS``::

        INSTALLED_APPS = [
            ...
            'bootstrap3',
            'compressor',
            'selectable',

            # Must come last.
            'timepiece',
            'timepiece.contracts',
            'timepiece.crm',
            'timepiece.entries',
            'timepiece.reports',
        ]

   - Configure your middleware::

        MIDDLEWARE = [
            'django.middleware.common.CommonMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
        ]

   - Add `django.core.context_processors.request` and django-timepiece context
     processors to the ``context_processors`` in the ``TEMPLATES`` config::

        TEMPLATES = [
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'APP_DIRS': True,
                'OPTIONS': {
                    'context_processors': [
                        "django.contrib.auth.context_processors.auth",
                        "django.template.context_processors.debug",
                        "django.template.context_processors.i18n",
                        "django.template.context_processors.media",
                        "django.contrib.messages.context_processors.messages",
                        "django.template.context_processors.request",           # <----
                        "timepiece.context_processors.quick_clock_in",      # <----
                        "timepiece.context_processors.quick_search",        # <----
                        "timepiece.context_processors.extra_settings",      # <----
                    ],
                },
            },
        ]

   - Configure compressor settings::

        COMPRESS_PRECOMPILERS = [
            ('text/less', 'lessc {infile} {outfile}'),
        ]
        COMPRESS_ROOT = f"{PROJECT_PATH}/static/"
        INTERNAL_IPS = ('127.0.0.1',)
        COMPRESS_OFFLINE = 1

   - Set ``USE_TZ`` to ``False``. django-timepiece does not currently support
     timezones.

#. Run ``migrate``.

#. Run ``./manage.py compress`` to compress less css

#. Add URLs for django-timepiece and selectable to `urls.py`, e.g.::

    urlpatterns = [
        ...
        re_path(r'^selectable/', include('selectable.urls')),
        path(r'', include('timepiece.urls')),
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
            auth_views.PasswordChangeView.as_view(),
            name='change_password'),
        url(r'^accounts/password-change/done/$',
            auth_views.PasswordChangeDoneView.as_view()),
        url(r'^accounts/password-reset/$',
            auth_views.PasswordResetView.as_view(),
            name='reset_password'),
        url(r'^accounts/password-reset/done/$',
            auth_views.PasswordResetDoneView.as_view()),
        url(r'^accounts/reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
            auth_views.PasswordResetConfirmView.as_view()),
        url(r'^accounts/reset/done/$',
            auth_views.PasswordResetCompleteView.as_view()),
        ...
    ]

#. Create registration templates. For examples, see the registration templates
   in `example_project/templates/registration`. Ensure that your project's
   template directory is added to ``DIRS`` in the ``TEMPLATES`` config::

    TEMPLATES = [
        {
            ...
            'DIRS': [os.path.join(BASE_DIR, 'templates')],
            ...
        }
    ]

Development sponsored by `Caktus Group`_.


.. _Caktus Group: https://www.caktusgroup.com/services
.. _GitHub: https://github.com/caktus/django-timepiece
.. _less: http://lesscss.org
.. _pip: http://pip.openplans.org/
.. _PyPI: http://pypi.python.org/pypi/django-timepiece3
.. _Read The Docs: http://django-timepiece3.readthedocs.io

