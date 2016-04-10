# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


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
        ),
        migrations.CreateModel(
            name='ContractAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('bucket', models.CharField(max_length=64)),
                ('uuid', models.TextField()),
                ('filename', models.CharField(max_length=128)),
                ('upload_datetime', models.DateTimeField(auto_now_add=True)),
                ('description', models.TextField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='ContractBudget',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_requested', models.DateField()),
                ('date_approved', models.DateField(null=True, blank=True)),
                ('status', models.IntegerField(default=1, choices=[(1, b'Pending'), (2, b'Approved')])),
                ('notes', models.TextField(blank=True)),
                ('budget', models.DecimalField(default=0, max_digits=11, decimal_places=2)),
            ],
            options={
                'verbose_name': 'contracted budget',
                'verbose_name_plural': 'contracted budget',
            },
        ),
        migrations.CreateModel(
            name='ContractHour',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_requested', models.DateField()),
                ('date_approved', models.DateField(null=True, blank=True)),
                ('status', models.IntegerField(default=1, choices=[(1, b'Pending'), (2, b'Approved')])),
                ('notes', models.TextField(blank=True)),
                ('hours', models.DecimalField(default=0, max_digits=8, decimal_places=2)),
            ],
            options={
                'db_table': 'timepiece_contracthour',
                'verbose_name': 'contracted hours',
                'verbose_name_plural': 'contracted hours',
            },
        ),
        migrations.CreateModel(
            name='ContractNote',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('edited', models.BooleanField(default=False)),
                ('last_edited', models.DateTimeField(auto_now=True)),
                ('text', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='ContractRate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rate', models.DecimalField(default=0, verbose_name=b'Rate per Hour', max_digits=6, decimal_places=2)),
            ],
        ),
        migrations.CreateModel(
            name='EntryGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('single_project', models.BooleanField(default=True)),
                ('status', models.CharField(default=b'invoiced', max_length=24, choices=[(b'invoiced', b'Invoiced'), (b'not-invoiced', b'Not Invoiced')])),
                ('override_invoice_date', models.DateField(null=True, blank=True)),
                ('auto_number', models.CharField(help_text=b'Auto-generated number for tracking.', max_length=17, null=True, verbose_name=b'Project Code', blank=True)),
                ('number', models.CharField(max_length=50, null=True, verbose_name=b'Reference #', blank=True)),
                ('comments', models.TextField(null=True, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('start', models.DateField(null=True, blank=True)),
                ('end', models.DateField()),
                ('year', models.SmallIntegerField(null=True, blank=True)),
            ],
            options={
                'db_table': 'timepiece_entrygroup',
            },
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
        ),
        migrations.CreateModel(
            name='InvoiceAdjustment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_payment', models.BooleanField(help_text=b'By unchecking this box, the adjustment is added in with the rest of the time entries.', verbose_name=b'Is a Payment/Credit')),
                ('date', models.DateField(null=True, blank=True)),
                ('line_item', models.CharField(max_length=10, null=True, blank=True)),
                ('description', models.CharField(max_length=50, null=True, blank=True)),
                ('quantity', models.DecimalField(max_digits=10, decimal_places=2)),
                ('rate', models.DecimalField(help_text=b'Make negative to credit the client.', max_digits=10, decimal_places=2)),
            ],
        ),
        migrations.CreateModel(
            name='ProjectContract',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('status', models.CharField(default=b'upcoming', max_length=32, choices=[(b'upcoming', b'Upcoming'), (b'current', b'Current'), (b'complete', b'Complete')])),
                ('type', models.IntegerField(choices=[(1, b'Fixed'), (2, b'Pre-paid Hourly'), (3, b'Post-paid Hourly')])),
                ('payment_terms', models.CharField(default=b'net30', max_length=32, choices=[(b'net60', b'Net-60'), (b'net90', b'Net-90'), (b'net75', b'Net-75'), (b'net45', b'Net-45'), (b'net30', b'Net-30'), (b'net15', b'Net-15'), (b'net0', b'On receipt (Net-0)')])),
                ('ceiling_type', models.IntegerField(default=2, help_text=b'How is the ceiling value determined for the contract?', choices=[(1, b'Hours'), (2, b'Budget')])),
                ('client_expense_category', models.CharField(default=b'unknown', max_length=16, choices=[(b'unknown', b'Unknown'), (b'operational', b'Operational'), (b'capital', b'Capital')])),
                ('po_number', models.CharField(max_length=100, null=True, verbose_name=b'PO Number', blank=True)),
                ('po_line_item', models.CharField(max_length=10, null=True, verbose_name=b'PO Line Item', blank=True)),
            ],
            options={
                'ordering': ('name',),
                'db_table': 'timepiece_projectcontract',
                'verbose_name': 'contract',
                'permissions': (('view_contract', 'Can view contracts'),),
            },
        ),
    ]
