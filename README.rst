django-timepiece
================

An extension to `django-crm <http://code.google.com/p/django-crm/>`_ for time
tracking and basic project management, originally
forked from `django-pendulum <http://code.google.com/p/django-pendulum/>`_.

Features
--------

 * Project management
 * Contact/project relationships
 * Project and user time sheets

Requirements
------------

 * `django-crm <http://code.google.com/p/django-crm/>`_

Installation
------------

First of all, you must add this project to your list of `INSTALLED_APPS` in `settings.py`::

    INSTALLED_APPS = (
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
        ...
        'timepiece',
        ...
    )

Run `manage.py syncdb`.

Next, you should add an entry to your main `urls.py` file.  For example::

    from django.conf.urls.defaults import *

    from django.contrib import admin
    admin.autodiscover()

    urlpatterns = patterns('',
        (r'^admin/(.*)', admin.site.root),
        (r'^timepiece/', include('timepiece.urls')),
    )

Development sponsored by `Caktus Consulting Group, LLC.
<http://www.caktusgroup.com/services>`_.
