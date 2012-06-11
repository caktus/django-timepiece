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

django-timepiece uses Python 2.6

 * `python-dateutil <http://labix.org/python-dateutil>`_
 * `django-selectable <http://pypi.python.org/pypi/django-selectable>`_
 * `django-pagination <http://pypi.python.org/pypi/django-pagination>`_

django-timepiece depends on PostgreSQL as the database backend

 * `psycopg2 <http://initd.org/psycopg/>`_

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

Testing
-------

django-timepiece inclues a [Tox](http://tox.testrun.org/latest/) configuration file to run tests. Several environments were added for testing:

 * `py26-jenkins` - Test using `django-jenkins <https://github.com/kmmbvnr/django-jenkins>`_, Python 2.6, and Django 1.3.1
 * `py27-jenkins` - Test using `django-jenkins <https://github.com/kmmbvnr/django-jenkins>`_, Python 2.7, and Django 1.3.1
 * `py26-1.2` - Test using Python 2.6 and Django 1.2.x
 * `py26-1.3` - Test using Python 2.6 and Django 1.3.x
 * `py26-1.4` - Test using Python 2.6 and Django 1.4.x
 * `py27-1.2` - Test using Python 2.7 and Django 1.2.x
 * `py27-1.3` - Test using Python 2.7 and Django 1.3.x
 * `py27-1.4` - Test using Python 2.7 and Django 1.4.x

You can run any of the environments listed above using: `tox -e name`

A python module, `run_tests.py`, is also included if you do not want to run tests using Tox. The tests are run using Django's default test runner. It accepts an optional argument, `run_tests.py jenkins`, that runs the tests using django-jenkins.

History
-------

0.4.2 (Work in Progress)
************************
* Fixed permissions for creating businesses.
* Hourly reports in "My Ledger" display previous weeks of the month if an overlapping entry exists.
* Fixed permissions for rejecting verifies entries.
* Fixed a bug where you could verify entries while still clocked in.
* Added user selection for payroll reviewers to switch between timesheets.
* Fixed bug for where the incorrect email was shown in the header

0.4.1 (06-04-2012)
******************
* Made projects' tracker URL's appear on the project detail view.
* Added reasonable limits to the total time and pause length of entries.
* Users can now comment on the active entry while clocking into a new one.
* Fixed a bug with entries overlapping when clocking in while another entry is active.
* Added the ability for payroll reviewers to reject an entry, which marks it as unverified.
* Added a weekly total on the dashboard for all hours worked.
* The hourly summary in "My Ledger" now shows the entire first week of the month.
* Made payroll links to timesheets maintain the proper month and year.
* Made URL's in entry comments display as HTML links
* Fixed permissions checking for payroll and entry summary views.
* Made project list page filterable by project status.
* Replaced django-ajax-select with latest version of django-selectable
* Added migration to remove tables related to django-crm

0.4.0 (04-27-2012)
******************
* Improved personnel timesheets with a simplified, tabbed layout.
* Improved efficency and consistency of entry queries
* Removed BillingWindow, RepeatPeriod, and PersonRepeatPeriod models, tables and related code.
* Removed the update billing windows management command as it is no longer needed.

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
