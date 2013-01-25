Release Notes
=============

0.8.2 (Unreleased)
------------------

Related issues are in the `0.8.2 milestone
<https://github.com/caktus/django-timepiece/issues?milestone=36&page=1&state=closed>`_.

* Added static files blocks to the base template

0.8.1 (Released 01-22-2013)
---------------------------

Related issues are in the `0.8.1 milestone
<https://github.com/caktus/django-timepiece/issues?milestone=35&page=1&state=closed>`_.

* Restored `slug` field on RelationshipType

0.8.0 (Released 01-21-2013)
---------------------------

Related issues are in the `0.8.0 milestone
<https://github.com/caktus/django-timepiece/issues?milestone=31&page=1&state=closed>`_.

*Features*

* Cleaned up the URL and template structure (This will break many existing bookmarks!)
* Removed the General Ledger report in favor of adding a summary by project on the Hourly Report page
* Default to showing entries from the previous week grouped by day on the Hourly Report
* Fall back to displaying username when a user's first & last name are unavailable
* Added name field to ProjectContract model
* Made ProjectContract <-> Project a many-to-many relationship
* Added additional information on ProjectContract detail page
* Added list of contracts on Project detail page
* Allow running a subset of tests through `runtests.py` (now in accordance with existing documentation)
* Created a `get_active_entry` utility which raises `ActiveEntryError` if a user has more than one active entry
* Permanent tabs for user time sheet tabs
* Upgrade less from 1.3.0 -> 1.3.3
* New model ContractHours allows tracking whether specific blocks of hours on
  a contract have been approved.

*Bugfixes*

* Prevent "None" from appearing under date headers on dashboard's All Entries tab
* Save Auth groups when adding/editing a user
* Include current GET parameters when using 'next' in a URL

*Other Changes*

* Removed unused methods from ProjectContract and ContractAssignment models
* Removed unused ContractMilestone model
* Removed unused AssignmentManager class
* Removed unused `slug` fields from Business & RelationshipType models
* Removed ProjectContract from Project admin
* Improved test coverage of template tags
* Changed references to person/people to user/users for consistency with data model
* Removed unused `clear_form.js`
* Used slightly darker highlight color for active project on dashboard's Progress tab
* Removed paste styles from `styles.less`
* Updated contributing docs to indicate that pull requests should be made to `caktus:develop`
* Removed some unused images, renamed a couple of others.

0.7.3 (Released 01-07-2013)
---------------------------

Related issues are in the `0.7.3 milestone
<https://github.com/caktus/django-timepiece/issues?milestone=30&page=1&state=closed>`_.

*Features*

* Row and column highlighting on weekly schedule
* Redirect regular users to schedule view from schedule edit (rather than redirecting to login)
* Use checkbox select multiple for editing groups on person add/edit forms
* Added "active" column to front-end user list & detail views
* Permanent links to dashboard tabs
* Dashboard project progress table

  - Highlight row of active project
  - Made width of bars relative to maximum worked or assigned hours
  - Show overtime bar for work on unassigned projects

* Dashboard "All Entries" tab

  - Moved "Add Entry" button to top right of page, and clock in dropdown
  - Split entries by day into separate tables, with a summary row
  - Added comment column, and included comment in row tooltip
  - Hide pause time unless it is greater than 0

*Bugfixes*

* Fixed bugs in handling filters on the hourly report
* Only summarize entries in the time period requested on hourly & billable
  reports (previously, entries for the entire week which includes the from
  date were included)
* Fixed bug which prevented projects being removed from the hourly report filter
* Keep GET parameters when deleting entry (allows proper redirection)
* Use ``history.back()`` on cancel buttons on clock in, clock out, and add
  entry pages
* Fixed floating point errors that caused project progress bars to display
  over two lines
* Prevent negative worked/assigned time on project progress bars
* Fix project progress bar behavior when worked = 0 and assigned = 0 (e.g.,
  just after clocking into an unassigned project)
* Allow editing groups on person edit page
* Fixed subnav rendering on invoice pages

0.7.2 (Released 11-28-2012)
---------------------------

* Fixed test failures that resulted from changes to the display of project
  names when clocking time.

0.7.1 (Released 11-28-2012)
---------------------------

Related issues are in the `0.7.1 milestone
<https://github.com/caktus/django-timepiece/issues?milestone=29&page=1&state=closed>`_.

* Fixed path to white Glyphicons
* Fixed duplicates in unverified list on Payroll Summary report
* Removed unused ``timepiece/time-sheet/_entry_list.html`` template
* Made ``Business.name`` field required
* Schema migration to add ``Business.short_name`` field
* Add ``Business.get_display_name()`` to retrieve first of ``short_name`` or
  ``name``
* Show business short name with project name on the dashboard, clock in,
  clock out, and outstanding invoices pages
* Added ``Entry.get_paused_seconds()`` - gets total time paused on any entry,
  regardless of whether it is currently active or paused
* Removed ``Entry.get_active_seconds()``
* Moved ``Entry.get_seconds()`` to ``Entry.get_total_seconds()`` - updated to
  get total worked seconds for any entry, regardless of whether it is
  currently active or paused, also taking into account the amount of time
  paused
* Dashboard tweaks and bug fixes

  - Fixed pause time bug
  - Fixed incorrect link name in mobile navbar
  - Fixed floating point errors in progress bar width calculations
  - Fixed overall progress bar styling when worked width = 0%
  - Fixed project progress bar responsiveness when resizing or zooming the
    page
  - Show overtime on project progress bars
  - Use dark green instead of red on overtime bars
  - Separated the "Project" and "Activity" columns in the all entries list
  - Include active entry in the all entries list
  - Increased the prominence of the active entry section
  - Show the current activity name in the active entry section
  - Removed link to the active project from the active entry section
  - Use "for" instead of "on" when describing entries

0.7.0 (Released 11-16-2012)
---------------------------

*Features*

* Added search to Project list view in admin
* Added project relationship information on Person detail view
* Updated the navigation bar

  - Added "Quick Clock In" pulldown to allow link to project-specific clock
    in form from anywhere on the site
  - Replaced "Dashboard" pulldown with a link to the user's monthly time
    sheet. The dashboard is accessible via the "Timepiece" link in the top
    left corner.
  - Renamed "Reports" dropdown to "Management", and moved link to the admin
    from the user pulldown
  - Moved "Online Users" info to weekly dashboard view & removed the
    ``active_entries`` context processor
  - Made search box smaller unless it is the focused element
  - Use user's first name instead of email address on user pulldown

* Redesigned the weekly dashboard view

  - Active entry section allows convenient summary & manipulation of the
    current entry
  - Visualization of overall progress (out of hours set in
    ``UserProfile.hours_per_week``)
  - Visualization of hours worked on each project (out of ProjectHours
    assigned this week)
  - Use "humanized" hours display (1:30) rather than decimal (1.5)

* Added productivity report, which compares the hours worked on a project to
  the hours that were assigned to it

*Bug Fixes*

* Updated to latest version of Bootstrap
* Updated django-compressor from 1.1.2 -> 1.2 & updated run_tests settings to
  avoid masking primary errors in tests
* Set ``USE_TZ = False`` in example_project settings because we don't
  currently support use of timezones
* Added missing app and context processors to settings in example_project and
  run_tests
* Updated example_project settings & README to reflect that INTERNAL_IPS must
  be set in order to ensure that Bootstrap Glyphicons can be found
* Fixed bug when copying the previous week's ProjectHours entries to
  current week when entries for the current week already exist.
* Fixed bug when removing ProjectRelationship through the front end

*Code Quality*

* Renamed the 'timepiece-entries' URL to 'dashboard'
* Removed unnecessary settings from example_project and run_tests
* Split up settings files in example project to use base and local settings
* Removed unused jqplot library
* Moved ``multiply`` template tag to timepiece_tags and removed math_tags file
* Removed most of custom icon set in favor of Bootstrap's Glyphicons

0.6.0 (Released 10-04-2012)
---------------------------

* Updated version requirement for South to 0.7.6
* Updated version requirement for django-bootstrap-toolkit to 2.5.6
* Use Javascript to manage date filter links on Reports pages
* Use "empty" text when there is no Billable Report data to visualize
* Include auth groups select to Person creation form
* Added pagination and search to Previous Invoices page
* Show current project name and activity on Clock Out page
* Maintain selected month on link to Person time sheet from Payroll Report page
* Maintain selected month on link to Project time sheet from Outstanding Hours page
* Fixed division-by-0 bug on ContractAssignment admin page
* Fixed infinite loop when ordering by Project on ProjectContract admin page
* Prevent admin from requiring that all ProjectContract inlines be completed on Project creation
* Use default options for the filter form on the Hourly Report page

We also completed a full audit of the code, in which we deleted stale parts, removed unmaintained features, and made some simple cleanups:

* Migrated the ``PersonSchedule.hours_per_week`` field to the UserProfile model
* Deleted the AssignmentAllocation and PersonSchedule models
* Removed all projection-related code, including admin and model hooks, forms, views, templates, and `projection.py`
* Deleted `widgets.py`
* Removed unused fields from DateForm
* Removed unused templates and static files
* Removed unused utilities, template tags, and forms
* Cleaned up imports, used the ``render`` shortcut in all views, and used the new-style url in all templates
* Refreshed the example project and added missing templates and JavaScript files

0.5.4 (Released 09-13-2012)
---------------------------

* Projects on Invoices/Outstanding Hours page are sorted by status and then by name
* Weekly Project Hours chart uses horizontal zebra striping
* New permission added for approving timesheets
* Fixed a bug in Project Hours edit view that prevented deletion of multiple entries at once
* Added links to Person timesheet from Payroll Report page
* Added links to Project timesheet on Invoice page

0.5.3 (Released 08-10-2012)
---------------------------

* Added a "Billable Hours" report, which displays a chart of billable and non-billable hours for a selected group of people, activities, project types and date range.
* Improved usability of the payroll report
* Made forms with date ranges more consistent and DRY
* Added a restriction that prevents users from adding entries to months with approved or invoiced entries.
* Removed the link to edit weekly project hours for users without that permission
* Improved readability of report tables by changing the hover color to something more distinctive.

0.5.2 (Released 08-01-2012)
---------------------------

* Added "Project Hours" views, which allow managers to assign project hours to users in a spreadsheet-like interface.
* Simplified implementation of timezone support.
* Fixed a bug that was preventing the weekly totals in "Hourly Summary" of "My Ledger" from being displayed.
* Removed the display of "hours out of" in the "billable time" section of "My Work This Week" and added it to the "total time this week" section.

0.5.1 (Released 07-20-2012)
---------------------------

* Added compatability with Django 1.4 and timezone support
* Added mobile support for the dashboard (clocking in/out, ledger, etc.)
* Fixed a bug where the last billable day was calculated incorrectly
* Payroll report now lists types of projects under billable and non-billable columns
* Moved the "Others Are Working On" table to a popover in the navigation
* Work total table now includes the active entry
* Comment field available when clocking in to a project
* Added support for custom navigation through EXTRA_NAV setting
* Across the board styling changes

0.5.0 (Released 07-12-2012)
---------------------------

* Complete styling upgrade using `Twitter Bootstrap <http://twitter.github.com/bootstrap/>`_
* Fixed permissions for client users that can't clock in
* Replaced deprecated message_set calls with new messages API calls
* Added django-bootstrap-toolkit requirement
* Included the top navigation bar inside of the app's templates.
* Made the project edit form use selectables for searching for businesses.
* Improved tox configuration of test database names
* Added a makefile and /docs for building documentation with Sphinx

0.4.2 (Released 06-15-2012)
---------------------------

* Fixed permissions for creating businesses.
* Hourly reports in "My Ledger" display previous weeks of the month if an overlapping entry exists.
* Fixed permissions for rejecting verified entries.
* Fixed a bug where you could verify entries while still clocked in.
* Added user selection for payroll reviewers to switch between timesheets.
* Fixed bug where the incorrect email was shown in the header.

0.4.1 (Released 06-04-2012)
---------------------------

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

0.4.0 (Released 04-27-2012)
---------------------------

* Improved personnel timesheets with a simplified, tabbed layout.
* Improved efficency and consistency of entry queries
* Removed BillingWindow, RepeatPeriod, and PersonRepeatPeriod models, tables and related code.
* Removed the update billing windows management command as it is no longer needed.

0.3.8 (Released 02-16-2012)
---------------------------

* Converted invoice reference to a CharField for more flexibility
* Added list and detail views for project contracts
* Hour groups now show totals for each activity nested within them
* Moved unapproved and unverified entry warnings to the payroll summary page.


0.3.7 (Released 02-01-2012)
---------------------------

* Make create invoice page inclusive of date

0.3.6 (Released 02-01-2012)
---------------------------

* Allowed entries to be added in the future.
* Added per project activity restrictions.
* Allowed marking entries as 'not invoiced' and grouped entries together after clicking on "Mark as invoiced"
* Added the ability to view previous invoices and export them as csv's
* Added the ability to group different activities together into Hour Groups for summarizing in invoices.

0.3.5 (Released 12-09-2011)
---------------------------

* Optimized Payroll Summary with reusable code from Hourly Reports.
* Removed use of Textile and used the linebreaks filter tag in its place.

0.3.4 (Released 11-14-2011)
---------------------------

* Added a new Hourly Reports view with project hours filtered and grouped by user specified criteria.
* Hourly Reports, General Ledger and Payroll Summary are now subheadings under Reports.
* Improved My Ledger with row highlighting, better CSS and a title attribute.
* Fixed Invoice projects to return the date range with m/d/Y.

0.3.3 (Released 10-31-2011)
---------------------------

* Fixed Time Detail This Week on Dashboard to show correct totals
* Fixed Billable Summary on My Ledger to show totals for unverified hours

0.3.2 (Released 10-28-2011)
---------------------------

* My Active Entries on Dashboard now shows the hours worked thus far
* Improved My Ledger by adding a comments column and a redirect from the edit entry link
* Fixed issues related to the hourly summary option not appearing for some users
* Fixed issues with date accuracy in weekly headings on ledger pages
* General ledger now sorts users by last name
* Enhanced project time sheets with an activity column and a summary of hours spent on each activity.
* Invoice projects page now shows project status
* Activity on clock in page now defaults to the last activity clocked on that project
* Payroll report only shows users that have clocked hours for the period.

0.3.1 (Released 10-20-2011)
---------------------------

* Moved to GitHub (and git)
* Add hourly summary page to report daily, weekly, and monthly hours
* Refactored weekly overtime calculations to use ISO 8601

0.3.0 (Released 10-03-2011)
---------------------------

* Removed ability to maintain multiple active entries
* Enhanced logic on clock in and add entry pages to check for overlapping entries
* Fixed date redirect when marking projects as invoiced
* Fixed issues related to the "Approve Timesheet" link missing
* Include billable, non-billable, uninvoiced, and invoiced summaries on person timesheet
* Use select_related in a few places to optimize page loads

0.2.0 (Released 09-01-2011)
---------------------------

* First official release

Development sponsored by `Caktus Consulting Group, LLC
<http://www.caktusgroup.com/services>`_.
