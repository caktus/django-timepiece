# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'UserProfile'
        db.create_table('timepiece_userprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='profile', unique=True, to=orm['auth.User'])),
            ('hours_per_week', self.gf('django.db.models.fields.DecimalField')(default=40, max_digits=8, decimal_places=2)),
        ))
        db.send_create_signal('crm', ['UserProfile'])

        # Adding model 'Attribute'
        db.create_table('timepiece_attribute', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('sort_order', self.gf('django.db.models.fields.SmallIntegerField')(null=True, blank=True)),
            ('enable_timetracking', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('billable', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('crm', ['Attribute'])

        # Adding unique constraint on 'Attribute', fields ['type', 'label']
        db.create_unique('timepiece_attribute', ['type', 'label'])

        # Adding model 'Business'
        db.create_table('timepiece_business', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('short_name', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('notes', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('external_id', self.gf('django.db.models.fields.CharField')(max_length=32, blank=True)),
        ))
        db.send_create_signal('crm', ['Business'])

        # Adding model 'Project'
        db.create_table('timepiece_project', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('tracker_url', self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True)),
            ('business', self.gf('django.db.models.fields.related.ForeignKey')(related_name='new_business_projects', to=orm['crm.Business'])),
            ('point_person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('activity_group', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='activity_group', null=True, to=orm['entries.ActivityGroup'])),
            ('type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='projects_with_type', to=orm['crm.Attribute'])),
            ('status', self.gf('django.db.models.fields.related.ForeignKey')(related_name='projects_with_status', to=orm['crm.Attribute'])),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('crm', ['Project'])

        # Adding model 'RelationshipType'
        db.create_table('timepiece_relationshiptype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=255)),
        ))
        db.send_create_signal('crm', ['RelationshipType'])

        # Adding model 'ProjectRelationship'
        db.create_table('timepiece_projectrelationship', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='project_relationships', to=orm['auth.User'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(related_name='project_relationships', to=orm['crm.Project'])),
        ))
        db.send_create_signal('crm', ['ProjectRelationship'])

        # Adding unique constraint on 'ProjectRelationship', fields ['user', 'project']
        db.create_unique('timepiece_projectrelationship', ['user_id', 'project_id'])

        # Adding M2M table for field types on 'ProjectRelationship'
        db.create_table('timepiece_projectrelationship_types', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('projectrelationship', models.ForeignKey(orm['crm.projectrelationship'], null=False)),
            ('relationshiptype', models.ForeignKey(orm['crm.relationshiptype'], null=False))
        ))
        db.create_unique('timepiece_projectrelationship_types', ['projectrelationship_id', 'relationshiptype_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'ProjectRelationship', fields ['user', 'project']
        db.delete_unique('timepiece_projectrelationship', ['user_id', 'project_id'])

        # Removing unique constraint on 'Attribute', fields ['type', 'label']
        db.delete_unique('timepiece_attribute', ['type', 'label'])

        # Deleting model 'UserProfile'
        db.delete_table('timepiece_userprofile')

        # Deleting model 'Attribute'
        db.delete_table('timepiece_attribute')

        # Deleting model 'Business'
        db.delete_table('timepiece_business')

        # Deleting model 'Project'
        db.delete_table('timepiece_project')

        # Deleting model 'RelationshipType'
        db.delete_table('timepiece_relationshiptype')

        # Deleting model 'ProjectRelationship'
        db.delete_table('timepiece_projectrelationship')

        # Removing M2M table for field types on 'ProjectRelationship'
        db.delete_table('timepiece_projectrelationship_types')


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
        'crm.userprofile': {
            'Meta': {'object_name': 'UserProfile', 'db_table': "'timepiece_userprofile'"},
            'hours_per_week': ('django.db.models.fields.DecimalField', [], {'default': '40', 'max_digits': '8', 'decimal_places': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'profile'", 'unique': 'True', 'to': "orm['auth.User']"})
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
        }
    }

    complete_apps = ['crm']
