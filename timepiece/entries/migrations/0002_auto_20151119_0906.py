# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('entries', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='code',
            field=models.CharField(unique=True, max_length=5, help_text='Enter a short code to describe the type of activity that took place.'),
        ),
        migrations.AlterField(
            model_name='activity',
            name='name',
            field=models.CharField(max_length=50, help_text='Now enter a more meaningful name for the activity.'),
        ),
        migrations.AlterField(
            model_name='entry',
            name='status',
            field=models.CharField(default='unverified', choices=[('unverified', 'Unverified'), ('verified', 'Verified'), ('approved', 'Approved'), ('invoiced', 'Invoiced'), ('not-invoiced', 'Not Invoiced')], max_length=24),
        ),
        migrations.AlterField(
            model_name='projecthours',
            name='week_start',
            field=models.DateField(verbose_name='start of week'),
        ),
    ]
