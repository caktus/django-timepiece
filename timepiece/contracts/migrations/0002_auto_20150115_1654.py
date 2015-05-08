# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('crm', '0001_initial'),
        ('contracts', '0001_initial'),
        ('entries', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectcontract',
            name='projects',
            field=models.ManyToManyField(related_name='contracts', to='crm.Project'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='hourgroup',
            name='activities',
            field=models.ManyToManyField(related_name='activity_bundle', to='entries.Activity'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='entrygroup',
            name='project',
            field=models.ForeignKey(related_name='entry_group', to='crm.Project'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='entrygroup',
            name='user',
            field=models.ForeignKey(related_name='entry_group', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contracthour',
            name='contract',
            field=models.ForeignKey(related_name='contract_hours', to='contracts.ProjectContract'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contractassignment',
            name='contract',
            field=models.ForeignKey(related_name='assignments', to='contracts.ProjectContract'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contractassignment',
            name='user',
            field=models.ForeignKey(related_name='assignments', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='contractassignment',
            unique_together=set([('contract', 'user')]),
        ),
    ]
