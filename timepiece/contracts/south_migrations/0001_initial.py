# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (
        ('entries', '0001_initial'),
    )

    def forwards(self, orm):
        # Adding model 'ProjectContract'
        db.create_table('timepiece_projectcontract', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('end_date', self.gf('django.db.models.fields.DateField')()),
            ('status', self.gf('django.db.models.fields.CharField')(default='upcoming', max_length=32)),
            ('type', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('contracts', ['ProjectContract'])

        # Adding M2M table for field projects on 'ProjectContract'
        db.create_table('timepiece_projectcontract_projects', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('projectcontract', models.ForeignKey(orm['contracts.projectcontract'], null=False)),
            ('project', models.ForeignKey(orm['crm.project'], null=False))
        ))
        db.create_unique('timepiece_projectcontract_projects', ['projectcontract_id', 'project_id'])

        # Adding model 'ContractHour'
        db.create_table('timepiece_contracthour', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('hours', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=8, decimal_places=2)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(related_name='contract_hours', to=orm['contracts.ProjectContract'])),
            ('date_requested', self.gf('django.db.models.fields.DateField')()),
            ('date_approved', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('status', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('notes', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('contracts', ['ContractHour'])

        # Adding model 'ContractAssignment'
        db.create_table('timepiece_contractassignment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(related_name='assignments', to=orm['contracts.ProjectContract'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='assignments', to=orm['auth.User'])),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('end_date', self.gf('django.db.models.fields.DateField')()),
            ('num_hours', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=8, decimal_places=2)),
            ('min_hours_per_week', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('contracts', ['ContractAssignment'])

        # Adding unique constraint on 'ContractAssignment', fields ['contract', 'user']
        db.create_unique('timepiece_contractassignment', ['contract_id', 'user_id'])

        # Adding model 'HourGroup'
        db.create_table('contracts_hourgroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('order', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True, null=True, blank=True)),
        ))
        db.send_create_signal('contracts', ['HourGroup'])

        # Adding M2M table for field activities on 'HourGroup'
        db.create_table('contracts_hourgroup_activities', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('hourgroup', models.ForeignKey(orm['contracts.hourgroup'], null=False)),
            ('activity', models.ForeignKey(orm['entries.activity'], null=False))
        ))
        db.create_unique('contracts_hourgroup_activities', ['hourgroup_id', 'activity_id'])

        # Adding model 'EntryGroup'
        db.create_table('timepiece_entrygroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='entry_group', to=orm['auth.User'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(related_name='entry_group', to=orm['crm.Project'])),
            ('status', self.gf('django.db.models.fields.CharField')(default='invoiced', max_length=24)),
            ('number', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('comments', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('start', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('end', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('contracts', ['EntryGroup'])


    def backwards(self, orm):
        # Removing unique constraint on 'ContractAssignment', fields ['contract', 'user']
        db.delete_unique('timepiece_contractassignment', ['contract_id', 'user_id'])

        # Deleting model 'ProjectContract'
        db.delete_table('timepiece_projectcontract')

        # Removing M2M table for field projects on 'ProjectContract'
        db.delete_table('timepiece_projectcontract_projects')

        # Deleting model 'ContractHour'
        db.delete_table('timepiece_contracthour')

        # Deleting model 'ContractAssignment'
        db.delete_table('timepiece_contractassignment')

        # Deleting model 'HourGroup'
        db.delete_table('contracts_hourgroup')

        # Removing M2M table for field activities on 'HourGroup'
        db.delete_table('contracts_hourgroup_activities')

        # Deleting model 'EntryGroup'
        db.delete_table('timepiece_entrygroup')


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
        'contracts.contractassignment': {
            'Meta': {'unique_together': "(('contract', 'user'),)", 'object_name': 'ContractAssignment', 'db_table': "'timepiece_contractassignment'"},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'assignments'", 'to': "orm['contracts.ProjectContract']"}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'min_hours_per_week': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_hours': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '8', 'decimal_places': '2'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'assignments'", 'to': "orm['auth.User']"})
        },
        'contracts.contracthour': {
            'Meta': {'object_name': 'ContractHour', 'db_table': "'timepiece_contracthour'"},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'contract_hours'", 'to': "orm['contracts.ProjectContract']"}),
            'date_approved': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'date_requested': ('django.db.models.fields.DateField', [], {}),
            'hours': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '8', 'decimal_places': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'})
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
        'contracts.hourgroup': {
            'Meta': {'object_name': 'HourGroup'},
            'activities': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'activity_bundle'", 'symmetrical': 'False', 'to': "orm['entries.Activity']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        'contracts.projectcontract': {
            'Meta': {'ordering': "('-end_date',)", 'object_name': 'ProjectContract', 'db_table': "'timepiece_projectcontract'"},
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'projects': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'contracts'", 'symmetrical': 'False', 'to': "orm['crm.Project']"}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'upcoming'", 'max_length': '32'}),
            'type': ('django.db.models.fields.IntegerField', [], {})
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
        }
    }

    complete_apps = ['contracts']
