# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):
    depends_on = (
        ('contracts', '0001_initial'),
    )

    def forwards(self, orm):
        # Originally part of the initial migration, but separated out because
        # it depends on contracts.

        # Adding field 'Entry.entry_group'
        db.add_column('timepiece_entry', 'entry_group',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='entries', null=True, on_delete=models.SET_NULL, to=orm['contracts.EntryGroup']),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Entry.entry_group'
        db.delete_column('timepiece_entry', 'entry_group_id')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'contracts.entrygroup': {
            'Meta': {'object_name': 'EntryGroup', 'db_table': "'timepiece_entrygroup'"},
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entry_group'", 'to': "orm['crm.Project']"}),
            'start': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'invoiced'", 'max_length': '24'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entry_group'", 'to': "orm['auth.User']"})
        },
        'crm.attribute': {
            'Meta': {'ordering': "('sort_order',)", 'unique_together': "(('type', 'label'),)", 'object_name': 'Attribute', 'db_table': "'timepiece_attribute'"},
            'billable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'enable_timetracking': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sort_order': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'crm.business': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Business', 'db_table': "'timepiece_business'"},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'external_id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'crm.project': {
            'Meta': {'ordering': "('name', 'status', 'type')", 'object_name': 'Project', 'db_table': "'timepiece_project'"},
            'activity_group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'activity_group'", 'null': 'True', 'to': "orm['entries.ActivityGroup']"}),
            'business': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'new_business_projects'", 'to': "orm['crm.Business']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'point_person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects_with_status'", 'to': "orm['crm.Attribute']"}),
            'tracker_url': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects_with_type'", 'to': "orm['crm.Attribute']"}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'user_projects'", 'symmetrical': 'False', 'through': "orm['crm.ProjectRelationship']", 'to': "orm['auth.User']"})
        },
        'crm.projectrelationship': {
            'Meta': {'unique_together': "(('user', 'project'),)", 'object_name': 'ProjectRelationship', 'db_table': "'timepiece_projectrelationship'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project_relationships'", 'to': "orm['crm.Project']"}),
            'types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'project_relationships'", 'blank': 'True', 'to': "orm['crm.RelationshipType']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project_relationships'", 'to': "orm['auth.User']"})
        },
        'crm.relationshiptype': {
            'Meta': {'object_name': 'RelationshipType', 'db_table': "'timepiece_relationshiptype'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'})
        },
        'entries.activity': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Activity', 'db_table': "'timepiece_activity'"},
            'billable': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '5'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'entries.activitygroup': {
            'Meta': {'object_name': 'ActivityGroup', 'db_table': "'timepiece_activitygroup'"},
            'activities': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'activity_group'", 'symmetrical': 'False', 'to': "orm['entries.Activity']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'entries.entry': {
            'Meta': {'ordering': "('-start_time',)", 'object_name': 'Entry', 'db_table': "'timepiece_entry'"},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': "orm['entries.Activity']"}),
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'entry_group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['contracts.EntryGroup']"}),
            'hours': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '8', 'decimal_places': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': "orm['entries.Location']"}),
            'pause_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': "orm['crm.Project']"}),
            'seconds_paused': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'unverified'", 'max_length': '24'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'timepiece_entries'", 'to': "orm['auth.User']"})
        },
        'entries.location': {
            'Meta': {'object_name': 'Location', 'db_table': "'timepiece_location'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'entries.projecthours': {
            'Meta': {'unique_together': "(('week_start', 'project', 'user'),)", 'object_name': 'ProjectHours', 'db_table': "'timepiece_projecthours'"},
            'hours': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '8', 'decimal_places': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Project']"}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'week_start': ('django.db.models.fields.DateField', [], {})
        }
    }

    complete_apps = ['entries']
