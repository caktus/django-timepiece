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
 * `django-selectable <http://pypi.python.org/pypi/django-selectable>`_
 * `django-ajax-selects <http://pypi.python.org/pypi/django-ajax-selects>`_
 * `django-pagination <http://pypi.python.org/pypi/django-pagination>`_

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

0.3.8 (02-16-2012)
******************
* Converted invoice reference to a CharField for more flexibility
* Added list and detail views for project contracts
* Hour groups now show totals for each activity nested within them
* Moved unapproved and unverified entry warnings to the payroll summary page.


0.3.7 (02-01-2012)
******************
* Make create invoice page inclusive of date

0.3.6 (02-01-2012)
******************
* Allowed entries to be added in the future.
* Added per project activity restrictions.
* Allowed marking entries as 'not invoiced' and grouped entries together after clicking on "Mark as invoiced"
* Added the ability to view previous invoices and export them as csv's
* Added the ability to group different activities together into Hour Groups for summarizing in invoices.

0.3.5 (12-09-2011)
******************
* Optimized Payroll Summary with reusable code from Hourly Reports.
* Removed use of Textile and used the linebreaks filter tag in its place.

0.3.4 (11-14-2011)
******************
* Added a new Hourly Reports view with project hours filtered and grouped by user specified criteria.
* Hourly Reports, General Ledger and Payroll Summary are now subheadings under Reports.
* Improved My Ledger with row highlighting, better CSS and a title attribute.
* Fixed Invoice projects to return the date range with m/d/Y.

0.3.3 (10-31-2011)
******************

* Fixed Time Detail This Week on Dashboard to show correct totals
* Fixed Billable Summary on My Ledger to show totals for unverified hours

0.3.2 (10-28-2011)
******************

* My Active Entries on Dashboard now shows the hours worked thus far
* Improved My Ledger by adding a comments column and a redirect from the edit entry link
* Fixed issues related to the hourly summary option not appearing for some users
* Fixed issues with date accuracy in weekly headings on ledger pages
* General ledger now sorts users by last name
* Enhanced project time sheets with an activity column and a summary of hours spent on each activity.
* Invoice projects page now shows project status
* Activity on clock in page now defaults to the last activity clocked on that project
* Payroll report only shows users that have clocked hours for the period.

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
