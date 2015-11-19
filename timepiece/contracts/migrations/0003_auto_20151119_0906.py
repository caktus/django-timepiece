# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0002_auto_20150115_1654'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contracthour',
            name='status',
            field=models.IntegerField(default=1, choices=[(1, 'Pending'), (2, 'Approved')]),
        ),
        migrations.AlterField(
            model_name='entrygroup',
            name='number',
            field=models.CharField(verbose_name='Reference #', blank=True, null=True, max_length=50),
        ),
        migrations.AlterField(
            model_name='entrygroup',
            name='status',
            field=models.CharField(default='invoiced', choices=[('invoiced', 'Invoiced'), ('not-invoiced', 'Not Invoiced')], max_length=24),
        ),
        migrations.AlterField(
            model_name='projectcontract',
            name='status',
            field=models.CharField(default='upcoming', choices=[('upcoming', 'Upcoming'), ('current', 'Current'), ('complete', 'Complete')], max_length=32),
        ),
        migrations.AlterField(
            model_name='projectcontract',
            name='type',
            field=models.IntegerField(choices=[(1, 'Fixed'), (2, 'Pre-paid Hourly'), (3, 'Post-paid Hourly')]),
        ),
    ]
