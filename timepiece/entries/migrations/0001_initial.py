# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from decimal import Decimal
import django.db.models.deletion
from django.conf import settings
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('crm', '0001_initial'),
        ('contracts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(help_text=b'Enter a short code to describe the type of activity that took place.', unique=True, max_length=5)),
                ('name', models.CharField(help_text=b'Now enter a more meaningful name for the activity.', max_length=50)),
                ('billable', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ('name',),
                'db_table': 'timepiece_activity',
                'verbose_name_plural': 'activities',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ActivityGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('activities', models.ManyToManyField(related_name='activity_group', to='entries.Activity')),
            ],
            options={
                'db_table': 'timepiece_activitygroup',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Entry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(default=b'unverified', max_length=24, choices=[(b'not-invoiced', b'Not Invoiced'), (b'invoiced', b'Invoiced'), (b'verified', b'Verified'), (b'approved', b'Approved'), (b'unverified', b'Unverified')])),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField(db_index=True, null=True, blank=True)),
                ('seconds_paused', models.PositiveIntegerField(default=0)),
                ('pause_time', models.DateTimeField(null=True, blank=True)),
                ('comments', models.TextField(blank=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
                ('hours', models.DecimalField(default=0, max_digits=8, decimal_places=2)),
                ('activity', models.ForeignKey(related_name='entries', to='entries.Activity')),
                ('entry_group', models.ForeignKey(related_name='entries', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='contracts.EntryGroup', null=True)),
            ],
            options={
                'ordering': ('-start_time',),
                'db_table': 'timepiece_entry',
                'verbose_name_plural': 'entries',
                'permissions': (('can_clock_in', 'Can use Pendulum to clock in'), ('can_pause', 'Can pause and unpause log entries'), ('can_clock_out', 'Can use Pendulum to clock out'), ('view_entry_summary', 'Can view entry summary page'), ('view_payroll_summary', 'Can view payroll summary page'), ('approve_timesheet', 'Can approve a verified timesheet')),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Location',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('slug', models.CharField(unique=True, max_length=255)),
            ],
            options={
                'db_table': 'timepiece_location',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectHours',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('week_start', models.DateField(verbose_name=b'start of week')),
                ('hours', models.DecimalField(default=0, max_digits=8, decimal_places=2, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('published', models.BooleanField(default=False)),
                ('project', models.ForeignKey(to='crm.Project')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'timepiece_projecthours',
                'verbose_name': 'project hours entry',
                'verbose_name_plural': 'project hours entries',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='projecthours',
            unique_together=set([('week_start', 'project', 'user')]),
        ),
        migrations.AddField(
            model_name='entry',
            name='location',
            field=models.ForeignKey(related_name='entries', to='entries.Location'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='entry',
            name='project',
            field=models.ForeignKey(related_name='entries', to='crm.Project'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='entry',
            name='user',
            field=models.ForeignKey(related_name='timepiece_entries', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
