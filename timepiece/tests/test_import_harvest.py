"""Tests for the import_harvest management command."""

import csv
import os
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from timepiece.crm.models import Business, Project
from timepiece.entries.models import Activity, Entry, Location

User = get_user_model()

COLUMNS = [
    'Date', 'Client', 'Project', 'Project Code', 'Task', 'Notes', 'Hours',
    'Billable?', 'Invoiced?', 'Approved?', 'First Name', 'Last Name',
    'Employee Id', 'Roles', 'Teams', 'Employee?', 'Billable Rate',
    'Billable Amount', 'Cost Rate', 'Cost Amount', 'Currency',
    'External Reference URL',
]


def make_row(entry_date, client, project, task, hours, first, last,
             billable='Yes', invoiced='No', approved='No', notes=''):
    return [
        entry_date, client, project, '', task, notes, hours, billable,
        invoiced, approved, first, last, '', '', '', 'Yes', '0.0', '0.0',
        '0.0', '0.0', 'United States Dollar - USD', '',
    ]


def write_csv(rows):
    handle, path = tempfile.mkstemp(suffix='.csv')
    with os.fdopen(handle, 'w', newline='') as output:
        writer = csv.writer(output)
        writer.writerow(COLUMNS)
        writer.writerows(rows)
    return path


class ImportHarvestTest(TestCase):

    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_user(
            username='admin', email='admin@example.com', password='secret')

    def import_file(self, rows, **kwargs):
        path = write_csv(rows)
        try:
            call_command('import_harvest', path, **kwargs)
        finally:
            os.unlink(path)

    # ------------------------------------------------------------------
    # Basic import
    # ------------------------------------------------------------------

    def test_creates_entries_and_reference_data(self):
        self.import_file([
            make_row('2024-05-01', 'Acme', 'Website', 'Development', 1.5,
                     'Jane', 'Doe'),
            make_row('2024-05-01', 'Acme', 'Website', 'Development', 2.0,
                     'Jane', 'Doe', invoiced='Yes'),
            make_row('2024-05-02', 'Acme', 'Intranet', 'Design', 0.5,
                     'John', 'Smith', approved='Yes', billable='No',
                     notes='wireframes'),
            make_row('2024-05-02', 'Acme', 'Intranet', 'Design', 1.0,
                     'John', 'Smith', billable='No'),
        ])

        self.assertEqual(Entry.objects.count(), 4)

        jane = User.objects.get(first_name='Jane', last_name='Doe')
        self.assertEqual(jane.username, 'jane.doe'.lower())
        self.assertEqual(jane.email, 'jane.doe@example.com')
        john = User.objects.get(first_name='John', last_name='Smith')

        self.assertEqual(Business.objects.filter(name='Acme').count(), 1)
        projects = {p.name: p for p in Project.objects.all()}
        self.assertEqual(set(projects), {'Website', 'Intranet'})
        for project in projects.values():
            self.assertEqual(project.point_person, self.admin)
            self.assertTrue(project.type.enable_timetracking)
            self.assertTrue(project.status.enable_timetracking)
        self.assertEqual(
            Activity.objects.filter(name='Development').count(), 1)
        location = Location.objects.get(name='Harvest Import')
        self.assertEqual(location.entries.count(), 4)

        entry = Entry.objects.get(start_time=datetime(2024, 5, 1),
                                  hours=Decimal('1.50000'))
        self.assertEqual(entry.status, Entry.UNVERIFIED)
        self.assertEqual(entry.user, jane)
        self.assertEqual(entry.project, projects['Website'])
        self.assertEqual(entry.activity, Activity.objects.get(name='Development'))
        self.assertEqual(entry.location, location)
        self.assertEqual(entry.end_time - entry.start_time, timedelta(hours=1.5))

        entry = Entry.objects.get(hours=Decimal('2.00000'))
        self.assertEqual(entry.status, Entry.INVOICED)

        entry = Entry.objects.get(start_time=datetime(2024, 5, 2),
                                  hours=Decimal('0.50000'))
        self.assertEqual(entry.status, Entry.APPROVED)
        self.assertEqual(entry.comments, 'wireframes')
        self.assertEqual(entry.user, john)

        entry = Entry.objects.get(hours=Decimal('1.00000'))
        self.assertEqual(entry.status, Entry.NOT_INVOICED)
        self.assertFalse(entry.activity.billable)

    def test_matches_existing_users_case_insensitively(self):
        existing = User.objects.create_user(
            username='preexisting', first_name='jAnE',
            last_name='DOE', email='preexisting@example.com')
        self.import_file([
            make_row('2024-05-01', 'Acme', 'Website', 'Development', 1.0,
                     'Jane', 'Doe'),
        ])
        entry = Entry.objects.get()
        self.assertEqual(entry.user, existing)
        self.assertEqual(User.objects.count(), 2)  # admin + preexisting

    def test_duplicate_rows_are_all_imported(self):
        row = make_row('2024-05-01', 'Acme', 'Website', 'Development', 1.0,
                       'Jane', 'Doe')
        self.import_file([row, row])
        self.assertEqual(Entry.objects.count(), 2)

    # ------------------------------------------------------------------
    # Long and negative hours
    # ------------------------------------------------------------------

    def test_splits_long_entries_across_consecutive_days(self):
        self.import_file([
            make_row('2024-05-01', 'Acme', 'Website', 'Development', 18.5,
                     'Jane', 'Doe'),
        ])
        entries = list(Entry.objects.order_by('start_time'))
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].start_time, datetime(2024, 5, 1))
        self.assertEqual(entries[0].end_time,
                         datetime(2024, 5, 1) + timedelta(hours=12))
        self.assertEqual(entries[0].hours, Decimal('12.00000'))
        self.assertEqual(entries[1].start_time, datetime(2024, 5, 2))
        self.assertEqual(entries[1].end_time,
                         datetime(2024, 5, 2) + timedelta(hours=6.5))
        self.assertEqual(entries[1].hours, Decimal('6.50000'))

    def test_negative_hours_are_netted_against_same_day(self):
        self.import_file([
            make_row('2024-05-01', 'Acme', 'Website', 'Development', 2.0,
                     'Jane', 'Doe'),
            make_row('2024-05-01', 'Acme', 'Website', 'Development', -0.5,
                     'Jane', 'Doe'),
            # Different task: not netted with the group above.
            make_row('2024-05-01', 'Acme', 'Website', 'Design', 1.0,
                     'Jane', 'Doe'),
            # Group that nets to zero: skipped entirely.
            make_row('2024-05-02', 'Acme', 'Website', 'Design', 1.0,
                     'John', 'Smith'),
            make_row('2024-05-02', 'Acme', 'Website', 'Design', -1.0,
                     'John', 'Smith'),
        ])
        self.assertEqual(Entry.objects.count(), 2)
        entry = Entry.objects.get(project__name='Website',
                                  activity__name='Development')
        self.assertEqual(entry.hours, Decimal('1.50000'))
        self.assertFalse(
            Entry.objects.filter(
                user__last_name='Smith').exists())

    # ------------------------------------------------------------------
    # Overlap guard / --force
    # ------------------------------------------------------------------

    def test_refuses_to_import_over_existing_entries(self):
        self.import_file([
            make_row('2024-05-01', 'Acme', 'Website', 'Development', 1.0,
                     'Jane', 'Doe'),
        ])
        with self.assertRaises(CommandError):
            self.import_file([
                make_row('2024-05-01', 'Acme', 'Website', 'Development', 2.0,
                         'Jane', 'Doe'),
            ])
        # Nothing new was imported.
        self.assertEqual(Entry.objects.count(), 1)

    def test_force_deletes_overlapping_entries_and_reimports(self):
        self.import_file([
            make_row('2024-05-01', 'Acme', 'Website', 'Development', 1.0,
                     'Jane', 'Doe'),
        ])
        # New file covers the same day, so --force wipes the old entry.
        self.import_file(
            [make_row('2024-05-01', 'Acme', 'Website', 'Development', 3.0,
                      'Jane', 'Doe')],
            force=True)
        entries = list(Entry.objects.order_by('start_time'))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].hours, Decimal('3.00000'))

    def test_missing_file_raises_command_error(self):
        with self.assertRaises(CommandError):
            call_command('import_harvest', '/nonexistent/report.csv')
