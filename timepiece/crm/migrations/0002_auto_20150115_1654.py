# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('entries', '0001_initial'),
        ('crm', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='activity_group',
            field=models.ForeignKey(related_name='activity_group', verbose_name=b'restrict activities to', blank=True, to='entries.ActivityGroup', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='project',
            name='business',
            field=models.ForeignKey(related_name='new_business_projects', to='crm.Business'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='project',
            name='point_person',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='project',
            name='status',
            field=models.ForeignKey(related_name='projects_with_status', to='crm.Attribute'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='project',
            name='type',
            field=models.ForeignKey(related_name='projects_with_type', to='crm.Attribute'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='project',
            name='users',
            field=models.ManyToManyField(related_name='user_projects', through='crm.ProjectRelationship', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='attribute',
            unique_together=set([('type', 'label')]),
        ),
    ]
