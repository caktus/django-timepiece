# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='projectattachment',
            old_name='upload_datetime',
            new_name='upload_time',
        ),
        migrations.AddField(
            model_name='businessattachment',
            name='bucket',
            field=models.CharField(default=b'aaceng-firmbase', max_length=64),
        ),
        migrations.AddField(
            model_name='businessattachment',
            name='uuid',
            field=models.TextField(default='DNE'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='leadattachment',
            name='bucket',
            field=models.CharField(default=b'aaceng-firmbase', max_length=64),
        ),
        migrations.AddField(
            model_name='leadattachment',
            name='uuid',
            field=models.TextField(default='DNE'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='projectattachment',
            name='deleted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='projectattachment',
            name='file_id',
            field=models.CharField(default='DNE', max_length=24),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='businessattachment',
            name='description',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='lead',
            name='contacts',
            field=models.ManyToManyField(related_name='lead_contacts', verbose_name=b'Other Contacts', to='crm.Contact', blank=True),
        ),
        migrations.AlterField(
            model_name='leadattachment',
            name='description',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='opportunity',
            name='project',
            field=models.ManyToManyField(help_text=b'If this Opportunity results in a project, identify the project(s) here.', to='crm.Project', blank=True),
        ),
        migrations.AlterField(
            model_name='projectattachment',
            name='bucket',
            field=models.CharField(default=b'aaceng-firmbase', max_length=64),
        ),
    ]
