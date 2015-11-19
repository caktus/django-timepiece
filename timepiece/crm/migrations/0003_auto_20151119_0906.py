# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0002_auto_20150115_1654'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attribute',
            name='enable_timetracking',
            field=models.BooleanField(default=False, help_text='Enable time tracking functionality for projects with this type or status.'),
        ),
        migrations.AlterField(
            model_name='attribute',
            name='type',
            field=models.CharField(choices=[('project-type', 'Project Type'), ('project-status', 'Project Status')], max_length=32),
        ),
        migrations.AlterField(
            model_name='business',
            name='email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AlterField(
            model_name='project',
            name='activity_group',
            field=models.ForeignKey(verbose_name='restrict activities to', null=True, blank=True, to='entries.ActivityGroup', related_name='activity_group'),
        ),
        migrations.AlterField(
            model_name='project',
            name='tracker_url',
            field=models.CharField(default='', blank=True, max_length=255),
        ),
    ]
