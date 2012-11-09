======================
Employee Time Tracking
======================

django-timepiece allows employees to keep track of their time on projects.

Entries
=======

Entries describe a period of work by a user on a particular project. Each user
may only have one active entry at a time; no entries can overlap.
Additionally, entries are limited to 12 hours in length.

user
    Foreign key to a User.

project
    Foreign key to a Project.

activity
    Foreign key to an Activity that describes the type of work that was done
    (e.g., development, estimation, planning)

location
    Foreign key to a Location that describes where the work was done (e.g.,
    home, office)

status
    Foreign key to a 'status' Attribute (e.g., tracking whether entries have
    been verified for payroll purposes)

start_time
    When the entry started.

end_time
    When the entry ended. If the entry has no end_time, it is an active entry.
    Each user may only have one active entry at any point in time.

seconds_paused
    How long the entry was paused.

pause_time
    If ``pause_time`` is not ``None``, then the entry is currently paused.

comments
    Optional description of this entry.

hours
    Total number of hours that this entry covers.

Clocking In and Out
===================

Users can track their time through the Clock In and Clock Out views. If the
user tries to clock in while another entry is active, the previous entry is
clocked out at the second before the new entry is clocked in.

Users may pause their active entry by using the "Pause" button on the weekly
dashboard. To resume the entry, the user must click the "Resume" button.

The user can clock into a specific project from anywhere on the site by
selecting the project from the "Clock" pulldown on the navbar. This links to
the Clock In view with that project and the most recent activity on that
project already filled in on the form.

Weekly Dashboard View
=====================

The dashboard gives an overview of the logged-in user's work this week.

Active Entry
------------

Each user may be clocked in to only one entry at a time. The user can view the
status of their current entry on the dashboard. From this section, the user
can clock out, pause/resume, or edit the current entry, or clock in or switch
to a new entry.

Overall Progress
----------------

The overall progress bar displays the number of hours that the user has worked
this week (including the time so far on the active entry), out of the number
of hours they are expected to work in a week (defined in the UserProfile
model). If the user has gone over the expected number of hours, the overtime
portion of the bar is displayed in red.

Project Progress
----------------

The project progress table shows how much the user has worked on each project,
out of the hours they were assigned to work this week (given by the
ProjectHours model). The name of the each project links to the Clock In view
with that project and the most recent activity on that project already filled
in on the form.

All Entries
-----------

The user can see a detailed view of all of their entries for the current week.
This list includes all entries that end in the current week, and does not
include the active entry. Each entry has links for editing and removal.

Online Users
------------

The online users tab lists the active entries of all other users.


Monthly Ledger View
===================

The ledger gives a summary of the user's work in a given month. At the end of
the month, the user can verify their entries for payroll purposes.
