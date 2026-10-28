"""
Import time entries from a Harvest "time report" CSV into timepiece.

Usage:
    python manage.py import_harvest [file] [--force]

The CSV must contain (at least) these columns:
    Date, Client, Project, Task, Notes, Hours,
    Billable?, Invoiced?, Approved?, First Name, Last Name

Behaviour:
  * Users, businesses, projects and activities are created as needed.
    Users are matched case-insensitively on first + last name; missing
    users are created with an example.com address.
  * Each row becomes one or more entries on the given date, starting at
    midnight. Entries longer than 12 hours are split across consecutive
    days (Timepiece's per-entry maximum).
  * Negative hours (Harvest corrections) are netted against the positive
    rows of the same user, date, project and task. Groups whose net total
    is zero or negative are skipped and reported.
  * The command refuses to run if the database already contains entries
    overlapping the file's date span. Pass --force to delete the
    overlapping entries first.

Dependencies: polars (see requirements/base.txt).
"""

import hashlib
import math
import re
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

import polars as pl

from timepiece.crm.models import Attribute, Business, Project
from timepiece.entries.models import Activity, Entry, Location


class Command(BaseCommand):
    help = 'Import time entries from a Harvest time report CSV.'

    REQUIRED_COLUMNS = [
        'Date', 'Client', 'Project', 'Task', 'Notes', 'Hours',
        'Billable?', 'Invoiced?', 'Approved?', 'First Name', 'Last Name',
    ]
    # Harvest formats money with thousands separators ("1,317.5"); we do
    # not store rates, so read these as strings to keep parsing clean.
    STRING_COLUMNS = (
        'Billable Rate', 'Billable Amount', 'Cost Rate', 'Cost Amount'
    )
    YES = 'Yes'
    MAX_HOURS_PER_ENTRY = Decimal('12')
    LOCATION_NAME = 'Harvest Import'
    IMPORTED_TYPE_LABEL = 'Imported'
    IMPORTED_STATUS_LABEL = 'Active'
    POINT_PERSON_USERNAME = 'admin'
    BATCH_SIZE = 1000

    def add_arguments(self, parser):
        parser.add_argument(
            'file',
            nargs='?',
            default='harvest_time_report.csv',
            help='Path to the Harvest time report CSV (default: %(default)s).')
        parser.add_argument(
            '--force',
            action='store_true',
            help='Delete existing entries overlapping the file\'s date span '
                 'before importing.')

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def handle(self, file, force, **options):
        frame = self._read_csv(file)
        min_date, max_date = frame['Date'].min(), frame['Date'].max()
        max_hours = frame['Hours'].abs().max()
        extra_days = int(math.ceil(max_hours / float(self.MAX_HOURS_PER_ENTRY)))

        self._handle_overlap(min_date, max_date + timedelta(days=extra_days), force)

        with transaction.atomic():
            users = self._prepare_users(frame)
            businesses = self._prepare_businesses(frame)
            activities = self._prepare_activities(frame)
            projects = self._prepare_projects(frame, businesses)
            location = self._prepare_location()

            entries, skipped_groups, zero_rows = self._build_entries(frame, {
                'users': users,
                'projects': projects,
                'activities': activities,
                'location': location,
            })

            self._bulk_create(entries)
            self._report(frame.height, zero_rows, skipped_groups, len(entries))

    # ------------------------------------------------------------------
    # CSV reading
    # ------------------------------------------------------------------

    def _read_csv(self, path):
        try:
            frame = pl.read_csv(
                path,
                schema_overrides={c: pl.String for c in self.STRING_COLUMNS},
            )
        except FileNotFoundError:
            raise CommandError('File not found: %s' % path)
        missing = [c for c in self.REQUIRED_COLUMNS if c not in frame.columns]
        if missing:
            raise CommandError(
                'Missing required CSV column(s): %s' % ', '.join(missing))
        try:
            frame = frame.with_columns(
                pl.col('Date').str.to_date('%Y-%m-%d').alias('Date'))
        except Exception as exc:
            raise CommandError('Could not parse Date column: %s' % exc)
        return frame

    # ------------------------------------------------------------------
    # Overlap guard
    # ------------------------------------------------------------------

    def _overlapping_entries(self, min_date, max_date):
        span_start = datetime.combine(min_date, time.min)
        span_end = datetime.combine(max_date, time.max)
        return Entry.objects.filter(
            Q(start_time__lte=span_end)
            & (Q(end_time__isnull=True) | Q(end_time__gte=span_start)))

    def _handle_overlap(self, min_date, max_date, force):
        overlapping = self._overlapping_entries(min_date, max_date)
        count = overlapping.count()
        if not count:
            return
        span = '%s to %s' % (min_date, max_date)
        if not force:
            raise CommandError(
                'The database contains %s existing time entries overlapping '
                'the file\'s date span (%s). Re-run with --force to delete '
                'them first.' % (count, span))
        self.stdout.write('Deleting %s overlapping entries (%s) with --force'
                          % (count, span))
        pks = list(overlapping.values_list('pk', flat=True))
        for start in range(0, len(pks), self.BATCH_SIZE):
            Entry.objects.filter(
                pk__in=pks[start:start + self.BATCH_SIZE]).delete()

    # ------------------------------------------------------------------
    # Reference data
    # ------------------------------------------------------------------

    def _unique_name(self, base, taken):
        name = base
        suffix = 2
        while name in taken:
            name = '%s%d' % (base, suffix)
            suffix += 1
        taken.add(name)
        return name

    def _prepare_users(self, frame):
        """Match users on (first, last) name; create the missing ones."""
        User = get_user_model()
        names = sorted({(row['First Name'].strip(), row['Last Name'].strip())
                        for row in frame.select('First Name', 'Last Name')
                        .unique().to_dicts()})
        existing = {
            (u.first_name.strip().lower(), u.last_name.strip().lower()): u.pk
            for u in User.objects.filter(
                first_name__isnull=False, last_name__isnull=False)
        }
        taken_usernames = set(
            User.objects.values_list('username', flat=True))
        taken_emails = set(User.objects.values_list('email', flat=True))

        mapping = {}
        to_create = []
        for first, last in names:
            key = (first.lower(), last.lower())
            if key in existing:
                mapping[key] = existing[key]
                continue
            base = re.sub(r'[^a-z0-9]+', '.', '%s.%s' % (first.lower(), last.lower())).strip('.')
            username = self._unique_name(base, taken_usernames)
            email = self._unique_name('%s@example.com' % username, taken_emails)
            to_create.append(User(
                username=username, first_name=first, last_name=last, email=email))
        if to_create:
            User.objects.bulk_create(to_create)
            self.stdout.write('Created %d users' % len(to_create))
        for user in to_create:
            key = (user.first_name.lower(), user.last_name.lower())
            mapping[key] = user.pk
        return mapping

    def _prepare_businesses(self, frame):
        clients = frame['Client'].unique(maintain_order=True).to_list()
        existing = {
            name: pk for pk, name in Business.objects.values_list('pk', 'name')}
        to_create = [Business(name=c) for c in clients if c not in existing]
        if to_create:
            Business.objects.bulk_create(to_create)
            self.stdout.write('Created %d businesses' % len(to_create))
        for business in to_create:
            existing[business.name] = business.pk
        return existing

    def _prepare_activities(self, frame):
        taken_codes = set(Activity.objects.values_list('code', flat=True))
        existing = {
            name: pk for pk, name in Activity.objects.values_list('pk', 'name')}
        # Billable flag: first occurrence of each task in the file wins.
        billable_by_task = {
            task: flag
            for task, flag in frame.select('Task', 'Billable?')
            .unique(subset='Task', keep='first').iter_rows()
        }
        to_create = []
        for task in frame['Task'].unique(maintain_order=True).to_list():
            if task not in existing:
                to_create.append(Activity(
                    name=task,
                    code=self._activity_code(task, taken_codes),
                    billable=billable_by_task.get(task) == self.YES,
                ))
        if to_create:
            Activity.objects.bulk_create(to_create)
            self.stdout.write('Created %d activities' % len(to_create))
        for activity in to_create:
            existing[activity.name] = activity.pk
        return existing

    @staticmethod
    def _base36(value, width):
        digits = '0123456789abcdefghijklmnopqrstuvwxyz'
        text = ''
        while value:
            value, remainder = divmod(value, 36)
            text = digits[remainder] + text
        return text.zfill(width)[-width:]

    def _activity_code(self, name, taken):
        """Deterministic unique code (<=5 chars) derived from the task name."""
        for salt in range(1000):
            digest = hashlib.md5(
                ('%s:%d' % (name, salt)).encode('utf-8')).hexdigest()
            code = self._base36(int(digest[:8], 16), 5)
            if code not in taken:
                taken.add(code)
                return code
        raise CommandError('Could not allocate an activity code for %r' % name)

    def _prepare_projects(self, frame, businesses):
        point_person = get_user_model().objects.filter(
            username=self.POINT_PERSON_USERNAME).first()
        if point_person is None:
            raise CommandError(
                'No user named %r exists to serve as project point person. '
                'Create one (e.g. `createsuperuser`) and re-run.'
                % self.POINT_PERSON_USERNAME)
        project_type, _ = Attribute.objects.get_or_create(
            type=Attribute.PROJECT_TYPE, label=self.IMPORTED_TYPE_LABEL,
            defaults={'enable_timetracking': True, 'billable': True})
        project_status, _ = Attribute.objects.get_or_create(
            type=Attribute.PROJECT_STATUS, label=self.IMPORTED_STATUS_LABEL,
            defaults={'enable_timetracking': True})

        pairs = {
            (row['Client'], row['Project'])
            for row in frame.select('Client', 'Project').unique().to_dicts()}
        used_businesses = {businesses[client] for client, _ in pairs}
        existing = {
            (project['business_id'], project['name']): project['pk']
            for project in Project.objects
            .filter(business_id__in=used_businesses)
            .values('pk', 'name', 'business_id')}
        to_create = [
            Project(
                name=project_name,
                business_id=businesses[client],
                point_person=point_person,
                type=project_type,
                status=project_status,
                description='Imported from Harvest time report',
            )
            for client, project_name in sorted(pairs)
            if (businesses[client], project_name) not in existing
        ]
        if to_create:
            Project.objects.bulk_create(to_create)
            self.stdout.write('Created %d projects' % len(to_create))
        for project in to_create:
            existing[(project.business_id, project.name)] = project.pk
        return {(client, project_name):
                existing[(businesses[client], project_name)]
                for client, project_name in pairs}

    def _prepare_location(self):
        location = Location.objects.filter(name=self.LOCATION_NAME).first()
        if location is None:
            slug = 'harvest-import'
            while Location.objects.filter(slug=slug).exists():
                slug += '-x'
            location = Location.objects.create(
                name=self.LOCATION_NAME, slug=slug)
            self.stdout.write('Created location %r' % self.LOCATION_NAME)
        return location

    # ------------------------------------------------------------------
    # Entry construction
    # ------------------------------------------------------------------

    @staticmethod
    def _entry_status(invoiced, approved, billable):
        if invoiced == Command.YES:
            return Entry.INVOICED
        if approved == Command.YES:
            return Entry.APPROVED
        if billable != Command.YES:
            return Entry.NOT_INVOICED
        return Entry.UNVERIFIED

    def _build_entries(self, frame, refs):
        """
        Turn CSV rows into Entry objects.

        Negative hours are netted per (user, date, project, task) group;
        entries longer than MAX_HOURS_PER_ENTRY are split across
        consecutive days.
        """
        users = refs['users']
        projects = refs['projects']
        activities = refs['activities']
        location = refs['location']

        columns = [
            'Date', 'Client', 'Project', 'Task', 'Notes', 'Hours',
            'Billable?', 'Invoiced?', 'Approved?', 'First Name', 'Last Name',
        ]
        zero_rows = 0
        groups = {}
        for (entry_date, client, project, task, notes, hours,
             billable, invoiced, approved, first, last) in \
                frame.select(columns).iter_rows():
            user_id = users[(first.strip().lower(), last.strip().lower())]
            project_id = projects[(client, project)]
            activity_id = activities[task]
            hours = Decimal(str(hours))
            if hours == 0:
                zero_rows += 1
                continue
            status = self._entry_status(invoiced, approved, billable)
            key = (user_id, project_id, activity_id, entry_date)
            groups.setdefault(key, []).append(
                (hours, status, notes or ''))

        positive = []
        skipped_groups = []
        for key, items in groups.items():
            user_id, project_id, activity_id, entry_date = key
            if any(hours < 0 for hours, _, _ in items):
                # Adjustment group: net the whole day/project/task together.
                net = sum(hours for hours, _, _ in items)
                if net <= 0:
                    skipped_groups.append(
                        (key, net, [hours for hours, _, _ in items]))
                    continue
                status = next(status for hours, status, _ in items if hours > 0)
                positive.append(
                    (entry_date, net, user_id, project_id, activity_id,
                     status, ''))
            else:
                for hours, status, notes in items:
                    positive.append(
                        (entry_date, hours, user_id, project_id,
                         activity_id, status, notes))

        entries = []
        for entry_date, hours, user_id, project_id, activity_id, status, notes in positive:
            day = entry_date
            remaining = hours
            while True:
                chunk = min(remaining, self.MAX_HOURS_PER_ENTRY)
                start = datetime.combine(day, time.min)
                entries.append(Entry(
                    user_id=user_id,
                    project_id=project_id,
                    activity_id=activity_id,
                    location=location,
                    status=status,
                    start_time=start,
                    end_time=start + timedelta(hours=float(chunk)),
                    comments=notes,
                    hours=chunk.quantize(Decimal('0.00001')),
                ))
                if chunk >= remaining:
                    break
                remaining -= chunk
                day = day + timedelta(days=1)
        return entries, skipped_groups, zero_rows

    def _bulk_create(self, entries):
        for start in range(0, len(entries), self.BATCH_SIZE):
            Entry.objects.bulk_create(entries[start:start + self.BATCH_SIZE])
            done = min(start + self.BATCH_SIZE, len(entries))
            self.stdout.write('%s of %s entries imported'
                              % (format(done, ','), format(len(entries), ',')))

    def _report(self, rows, zero_rows, skipped_groups, entry_count):
        self.stdout.write('')
        self.stdout.write('Imported %s entries from %s CSV rows'
                          % (format(entry_count, ','), format(rows, ',')))
        if zero_rows:
            self.stdout.write('Skipped %d zero-hour rows' % zero_rows)
        if skipped_groups:
            self.stdout.write(
                'Skipped %d adjustment group(s) with net zero or negative '
                'hours:' % len(skipped_groups))
            for (user_id, project_id, activity_id, entry_date), net, hours in skipped_groups:
                self.stdout.write(
                    '  %s  user=%s project=%s activity=%s  rows=%s net=%s'
                    % (entry_date, user_id, project_id, activity_id,
                       hours, net))
