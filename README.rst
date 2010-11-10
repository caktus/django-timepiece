django-timepiece: project management and time tracking
===============================================================

 * Project by: Caktus Consulting Group, LLC (http://www.caktusgroup.com/)
 * Development: http://bitbucket.org/copelco/django-timepiece/
 * License: MIT
 * based on django-pendulum (http://code.google.com/p/django-pendulum/)

timepiece adds project management and time tracking to django-crm

Features
------------------

 * Project management
 * Contact/project relationships
 * Project and user time sheets

Requirements
------------------

 * django-crm - http://code.google.com/p/django-crm/

Installation
------------------

First of all, you must add this project to your list of `INSTALLED_APPS` in `settings.py`:

{{{
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
}}}

Run `manage.py syncdb`.

Next, you should add an entry to your main `urls.py` file.  For example:

{{{
from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/(.*)', admin.site.root),
    (r'^timepiece/', include('timepiece.urls')),
)
}}}
