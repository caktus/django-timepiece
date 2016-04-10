# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('crm', '0002_auto_20160403_1925'),
    ]

    operations = [
        migrations.AlterField(
            model_name='businessattachment',
            name='file_id',
            field=models.CharField(help_text=b'DEPRECATED', max_length=24, blank=True),
        ),
        migrations.AlterField(
            model_name='leadattachment',
            name='file_id',
            field=models.CharField(help_text=b'DEPRECATED', max_length=24, blank=True),
        ),
        migrations.AlterField(
            model_name='projectattachment',
            name='file_id',
            field=models.CharField(help_text=b'DEPRECATED', max_length=24, blank=True),
        ),
    ]
