# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Attribute',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=32, choices=[(b'project-status', b'Project Status'), (b'project-type', b'Project Type')])),
                ('label', models.CharField(max_length=255)),
                ('sort_order', models.SmallIntegerField(blank=True, null=True, choices=[(-20, -20), (-19, -19), (-18, -18), (-17, -17), (-16, -16), (-15, -15), (-14, -14), (-13, -13), (-12, -12), (-11, -11), (-10, -10), (-9, -9), (-8, -8), (-7, -7), (-6, -6), (-5, -5), (-4, -4), (-3, -3), (-2, -2), (-1, -1), (0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, 10), (11, 11), (12, 12), (13, 13), (14, 14), (15, 15), (16, 16), (17, 17), (18, 18), (19, 19), (20, 20)])),
                ('enable_timetracking', models.BooleanField(default=False, help_text=b'Enable time tracking functionality for projects with this type or status.')),
                ('billable', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ('sort_order',),
                'db_table': 'timepiece_attribute',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Business',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('short_name', models.CharField(max_length=255, blank=True)),
                ('email', models.EmailField(max_length=75, blank=True)),
                ('description', models.TextField(blank=True)),
                ('notes', models.TextField(blank=True)),
                ('external_id', models.CharField(max_length=32, blank=True)),
            ],
            options={
                'ordering': ('name',),
                'db_table': 'timepiece_business',
                'verbose_name_plural': 'Businesses',
                'permissions': (('view_business', 'Can view businesses'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('tracker_url', models.CharField(default=b'', max_length=255, blank=True)),
                ('description', models.TextField()),
            ],
            options={
                'ordering': ('name', 'status', 'type'),
                'db_table': 'timepiece_project',
                'permissions': (('view_project', 'Can view project'), ('email_project_report', 'Can email project report'), ('view_project_time_sheet', 'Can view project time sheet'), ('export_project_time_sheet', 'Can export project time sheet'), ('generate_project_invoice', 'Can generate project invoice')),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectRelationship',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('project', models.ForeignKey(related_name='project_relationships', to='crm.Project')),
            ],
            options={
                'db_table': 'timepiece_projectrelationship',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RelationshipType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('slug', models.SlugField(max_length=255)),
            ],
            options={
                'db_table': 'timepiece_relationshiptype',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('hours_per_week', models.DecimalField(default=40, max_digits=8, decimal_places=2)),
                ('user', models.OneToOneField(related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'timepiece_userprofile',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='projectrelationship',
            name='types',
            field=models.ManyToManyField(related_name='project_relationships', to='crm.RelationshipType', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='projectrelationship',
            name='user',
            field=models.ForeignKey(related_name='project_relationships', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='projectrelationship',
            unique_together=set([('user', 'project')]),
        ),
    ]
