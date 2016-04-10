# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0002_auto_20150616_2121'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('crm', '0001_initial'),
        ('contracts', '0001_initial'),
        ('entries', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectcontract',
            name='primary_contact',
            field=models.ForeignKey(to='crm.Contact'),
        ),
        migrations.AddField(
            model_name='projectcontract',
            name='projects',
            field=models.ManyToManyField(related_name='contracts', to='crm.Project'),
        ),
        migrations.AddField(
            model_name='projectcontract',
            name='tags',
            field=taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', help_text='A comma-separated list of tags.', verbose_name='Tags'),
        ),
        migrations.AddField(
            model_name='invoiceadjustment',
            name='invoice',
            field=models.ForeignKey(to='contracts.EntryGroup'),
        ),
        migrations.AddField(
            model_name='hourgroup',
            name='activities',
            field=models.ManyToManyField(related_name='activity_bundle', to='entries.Activity'),
        ),
        migrations.AddField(
            model_name='entrygroup',
            name='contract',
            field=models.ForeignKey(blank=True, to='contracts.ProjectContract', null=True),
        ),
        migrations.AddField(
            model_name='entrygroup',
            name='project',
            field=models.ForeignKey(related_name='entry_group', blank=True, to='crm.Project', null=True),
        ),
        migrations.AddField(
            model_name='entrygroup',
            name='user',
            field=models.ForeignKey(related_name='entry_group', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='contractrate',
            name='activity',
            field=models.ForeignKey(to='entries.Activity'),
        ),
        migrations.AddField(
            model_name='contractrate',
            name='contract',
            field=models.ForeignKey(to='contracts.ProjectContract'),
        ),
        migrations.AddField(
            model_name='contractnote',
            name='author',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='contractnote',
            name='contract',
            field=models.ForeignKey(to='contracts.ProjectContract'),
        ),
        migrations.AddField(
            model_name='contractnote',
            name='parent',
            field=models.ForeignKey(blank=True, to='contracts.ContractNote', null=True),
        ),
        migrations.AddField(
            model_name='contracthour',
            name='contract',
            field=models.ForeignKey(to='contracts.ProjectContract'),
        ),
        migrations.AddField(
            model_name='contractbudget',
            name='contract',
            field=models.ForeignKey(to='contracts.ProjectContract'),
        ),
        migrations.AddField(
            model_name='contractattachment',
            name='contract',
            field=models.ForeignKey(to='contracts.ProjectContract'),
        ),
        migrations.AddField(
            model_name='contractattachment',
            name='uploader',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='contractassignment',
            name='contract',
            field=models.ForeignKey(related_name='assignments', to='contracts.ProjectContract'),
        ),
        migrations.AddField(
            model_name='contractassignment',
            name='user',
            field=models.ForeignKey(related_name='assignments', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='contractrate',
            unique_together=set([('contract', 'activity')]),
        ),
        migrations.AlterUniqueTogether(
            name='contractassignment',
            unique_together=set([('contract', 'user')]),
        ),
    ]
