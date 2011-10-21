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

 * `python-dateutil <http://labix.org/python-dateutil>`_
 * `django-ajax-selects <http://pypi.python.org/pypi/django-ajax-selects>`_
 * `django-pagination <http://pypi.python.org/pypi/django-pagination>`_
 * `textile <http://pypi.python.org/pypi/textile>`_

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

History
-------

0.3.1
*****

* Moved to GitHub (and git)
* Add hourly summary page to report daily, weekly, and monthly hours
* Refactored weekly overtime calculations to use ISO 8601

0.3.0
*****

* Removed ability to maintain multiple active entries
* Enhanced logic on clock in and add entry pages to check for overlapping entries
* Fixed date redirect when marking projects as invoiced
* Fixed issues related to the "Approve Timesheet" link missing
* Include billable, non-billable, uninvoiced, and invoiced summaries on person timesheet
* Use select_related in a few places to optimize page loads

0.2.0
*****

* First official release

Development sponsored by `Caktus Consulting Group, LLC
<http://www.caktusgroup.com/services>`_.
