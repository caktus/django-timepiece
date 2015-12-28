# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ContractAssignment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('num_hours', models.DecimalField(default=0, max_digits=8, decimal_places=2)),
                ('min_hours_per_week', models.IntegerField(default=0)),
            ],
            options={
                'db_table': 'timepiece_contractassignment',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContractHour',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('hours', models.DecimalField(default=0, max_digits=8, decimal_places=2)),
                ('date_requested', models.DateField()),
                ('date_approved', models.DateField(null=True, blank=True)),
                ('status', models.IntegerField(default=1, choices=[(1, b'Pending'), (2, b'Approved')])),
                ('notes', models.TextField(blank=True)),
            ],
            options={
                'db_table': 'timepiece_contracthour',
                'verbose_name': 'contracted hours',
                'verbose_name_plural': 'contracted hours',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EntryGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(default=b'invoiced', max_length=24, choices=[(b'not-invoiced', b'Not Invoiced'), (b'invoiced', b'Invoiced')])),
                ('number', models.CharField(max_length=50, null=True, verbose_name=b'Reference #', blank=True)),
                ('comments', models.TextField(null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('start', models.DateField(null=True, blank=True)),
                ('end', models.DateField()),
            ],
            options={
                'db_table': 'timepiece_entrygroup',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='HourGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('order', models.PositiveIntegerField(unique=True, null=True, blank=True)),
            ],
            options={
                'db_table': 'timepiece_hourgroup',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectContract',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('status', models.CharField(default=b'upcoming', max_length=32, choices=[(b'current', b'Current'), (b'complete', b'Complete'), (b'upcoming', b'Upcoming')])),
                ('type', models.IntegerField(choices=[(1, b'Fixed'), (2, b'Pre-paid Hourly'), (3, b'Post-paid Hourly')])),
            ],
            options={
                'ordering': ('-end_date',),
                'db_table': 'timepiece_projectcontract',
                'verbose_name': 'contract',
            },
            bases=(models.Model,),
        ),
    ]
