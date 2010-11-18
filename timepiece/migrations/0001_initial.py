# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Attribute'
        db.create_table('timepiece_attribute', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('sort_order', self.gf('django.db.models.fields.SmallIntegerField')(null=True, blank=True)),
            ('enable_timetracking', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('timepiece', ['Attribute'])

        # Adding unique constraint on 'Attribute', fields ['type', 'label']
        db.create_unique('timepiece_attribute', ['type', 'label'])

        # Adding model 'Project'
        db.create_table('timepiece_project', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('trac_environment', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('business', self.gf('django.db.models.fields.related.ForeignKey')(related_name='business_projects', to=orm['crm.Contact'])),
            ('point_person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='projects_with_type', to=orm['timepiece.Attribute'])),
            ('status', self.gf('django.db.models.fields.related.ForeignKey')(related_name='projects_with_status', to=orm['timepiece.Attribute'])),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('billing_period', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='projects', null=True, to=orm['timepiece.RepeatPeriod'])),
        ))
        db.send_create_signal('timepiece', ['Project'])

        # Adding M2M table for field interactions on 'Project'
        db.create_table('timepiece_project_interactions', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('project', models.ForeignKey(orm['timepiece.project'], null=False)),
            ('interaction', models.ForeignKey(orm['crm.interaction'], null=False))
        ))
        db.create_unique('timepiece_project_interactions', ['project_id', 'interaction_id'])

        # Adding model 'ProjectRelationship'
        db.create_table('timepiece_projectrelationship', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contact', self.gf('django.db.models.fields.related.ForeignKey')(related_name='project_relationships', to=orm['crm.Contact'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(related_name='project_relationships', to=orm['timepiece.Project'])),
        ))
        db.send_create_signal('timepiece', ['ProjectRelationship'])

        # Adding unique constraint on 'ProjectRelationship', fields ['contact', 'project']
        db.create_unique('timepiece_projectrelationship', ['contact_id', 'project_id'])

        # Adding M2M table for field types on 'ProjectRelationship'
        db.create_table('timepiece_projectrelationship_types', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('projectrelationship', models.ForeignKey(orm['timepiece.projectrelationship'], null=False)),
            ('relationshiptype', models.ForeignKey(orm['crm.relationshiptype'], null=False))
        ))
        db.create_unique('timepiece_projectrelationship_types', ['projectrelationship_id', 'relationshiptype_id'])

        # Adding model 'Activity'
        db.create_table('timepiece_activity', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=5)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('timepiece', ['Activity'])

        # Adding model 'Location'
        db.create_table('timepiece_location', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('slug', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
        ))
        db.send_create_signal('timepiece', ['Location'])

        # Adding model 'Entry'
        db.create_table('timepiece_entry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='timepiece_entries', to=orm['auth.User'])),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(related_name='entries', to=orm['timepiece.Project'])),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='entries', null=True, to=orm['timepiece.Activity'])),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(related_name='entries', to=orm['timepiece.Location'])),
            ('start_time', self.gf('django.db.models.fields.DateTimeField')()),
            ('end_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('seconds_paused', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('pause_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('comments', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('date_updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('hours', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=8, decimal_places=2)),
        ))
        db.send_create_signal('timepiece', ['Entry'])

        # Adding model 'RepeatPeriod'
        db.create_table('timepiece_repeatperiod', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('count', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('interval', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('timepiece', ['RepeatPeriod'])

        # Adding model 'BillingWindow'
        db.create_table('timepiece_billingwindow', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('period', self.gf('django.db.models.fields.related.ForeignKey')(related_name='billing_windows', to=orm['timepiece.RepeatPeriod'])),
            ('date', self.gf('django.db.models.fields.DateField')()),
            ('end_date', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('timepiece', ['BillingWindow'])

        # Adding model 'PersonRepeatPeriod'
        db.create_table('timepiece_personrepeatperiod', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contact', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Contact'], unique=True)),
            ('repeat_period', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['timepiece.RepeatPeriod'], unique=True)),
        ))
        db.send_create_signal('timepiece', ['PersonRepeatPeriod'])

        # Adding model 'ProjectContract'
        db.create_table('timepiece_projectcontract', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(related_name='contracts', to=orm['timepiece.Project'])),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('end_date', self.gf('django.db.models.fields.DateField')()),
            ('num_hours', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=8, decimal_places=2)),
        ))
        db.send_create_signal('timepiece', ['ProjectContract'])

        # Adding model 'ContractAssignment'
        db.create_table('timepiece_contractassignment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contract', self.gf('django.db.models.fields.related.ForeignKey')(related_name='assignments', to=orm['timepiece.ProjectContract'])),
            ('contact', self.gf('django.db.models.fields.related.ForeignKey')(related_name='assignments', to=orm['crm.Contact'])),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('end_date', self.gf('django.db.models.fields.DateField')()),
            ('num_hours', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=8, decimal_places=2)),
        ))
        db.send_create_signal('timepiece', ['ContractAssignment'])

        # Adding unique constraint on 'ContractAssignment', fields ['contract', 'contact']
        db.create_unique('timepiece_contractassignment', ['contract_id', 'contact_id'])

        # Adding model 'PersonSchedule'
        db.create_table('timepiece_personschedule', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contact', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Contact'], unique=True)),
            ('hours_per_week', self.gf('django.db.models.fields.DecimalField')(default=0, max_digits=8, decimal_places=2)),
            ('end_date', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('timepiece', ['PersonSchedule'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'ContractAssignment', fields ['contract', 'contact']
        db.delete_unique('timepiece_contractassignment', ['contract_id', 'contact_id'])

        # Removing unique constraint on 'ProjectRelationship', fields ['contact', 'project']
        db.delete_unique('timepiece_projectrelationship', ['contact_id', 'project_id'])

        # Removing unique constraint on 'Attribute', fields ['type', 'label']
        db.delete_unique('timepiece_attribute', ['type', 'label'])

        # Deleting model 'Attribute'
        db.delete_table('timepiece_attribute')

        # Deleting model 'Project'
        db.delete_table('timepiece_project')

        # Removing M2M table for field interactions on 'Project'
        db.delete_table('timepiece_project_interactions')

        # Deleting model 'ProjectRelationship'
        db.delete_table('timepiece_projectrelationship')

        # Removing M2M table for field types on 'ProjectRelationship'
        db.delete_table('timepiece_projectrelationship_types')

        # Deleting model 'Activity'
        db.delete_table('timepiece_activity')

        # Deleting model 'Location'
        db.delete_table('timepiece_location')

        # Deleting model 'Entry'
        db.delete_table('timepiece_entry')

        # Deleting model 'RepeatPeriod'
        db.delete_table('timepiece_repeatperiod')

        # Deleting model 'BillingWindow'
        db.delete_table('timepiece_billingwindow')

        # Deleting model 'PersonRepeatPeriod'
        db.delete_table('timepiece_personrepeatperiod')

        # Deleting model 'ProjectContract'
        db.delete_table('timepiece_projectcontract')

        # Deleting model 'ContractAssignment'
        db.delete_table('timepiece_contractassignment')

        # Deleting model 'PersonSchedule'
        db.delete_table('timepiece_personschedule')


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
        'contactinfo.location': {
            'Meta': {'object_name': 'Location'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'default': "u'US'", 'to': "orm['countries.Country']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'default': '2', 'to': "orm['contactinfo.LocationType']"})
        },
        'contactinfo.locationtype': {
            'Meta': {'object_name': 'LocationType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'slug': ('django.db.models.fields.CharField', [], {'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'countries.country': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Country', 'db_table': "'country'"},
            'iso': ('django.db.models.fields.CharField', [], {'max_length': '2', 'primary_key': 'True'}),
            'iso3': ('django.db.models.fields.CharField', [], {'max_length': '3', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'numcode': ('django.db.models.fields.PositiveSmallIntegerField', [], {'null': 'True'}),
            'printable_name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'crm.businesstype': {
            'Meta': {'object_name': 'BusinessType'},
            'can_view_all_projects': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'crm.contact': {
            'Meta': {'object_name': 'Contact'},
            'business_types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'businesses'", 'blank': 'True', 'to': "orm['crm.BusinessType']"}),
            'contacts': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'related_contacts+'", 'symmetrical': 'False', 'through': "orm['crm.ContactRelationship']", 'to': "orm['crm.Contact']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'external_id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'locations': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['contactinfo.Location']", 'symmetrical': 'False', 'blank': 'True'}),
            'middle_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'picture': ('django.db.models.fields.files.ImageField', [], {'max_length': '1048576', 'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'sort_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'contacts'", 'unique': 'True', 'null': 'True', 'to': "orm['auth.User']"})
        },
        'crm.contactrelationship': {
            'Meta': {'unique_together': "(('from_contact', 'to_contact'),)", 'object_name': 'ContactRelationship'},
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'from_contact': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'from_contacts'", 'to': "orm['crm.Contact']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'to_contact': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'to_contacts'", 'to': "orm['crm.Contact']"}),
            'types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'contact_relationships'", 'blank': 'True', 'to': "orm['crm.RelationshipType']"})
        },
        'crm.interaction': {
            'Meta': {'ordering': "['-date']", 'object_name': 'Interaction'},
            'cdr_id': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'completed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'contacts': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'interactions'", 'symmetrical': 'False', 'to': "orm['crm.Contact']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'memo': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '15'})
        },
        'crm.relationshiptype': {
            'Meta': {'object_name': 'RelationshipType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'timepiece.activity': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Activity'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '5'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'timepiece.attribute': {
            'Meta': {'ordering': "('sort_order',)", 'unique_together': "(('type', 'label'),)", 'object_name': 'Attribute'},
            'enable_timetracking': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sort_order': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'timepiece.billingwindow': {
            'Meta': {'object_name': 'BillingWindow'},
            'date': ('django.db.models.fields.DateField', [], {}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'period': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'billing_windows'", 'to': "orm['timepiece.RepeatPeriod']"})
        },
        'timepiece.contractassignment': {
            'Meta': {'unique_together': "(('contract', 'contact'),)", 'object_name': 'ContractAssignment'},
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'assignments'", 'to': "orm['crm.Contact']"}),
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'assignments'", 'to': "orm['timepiece.ProjectContract']"}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_hours': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '8', 'decimal_places': '2'}),
            'start_date': ('django.db.models.fields.DateField', [], {})
        },
        'timepiece.entry': {
            'Meta': {'object_name': 'Entry'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'entries'", 'null': 'True', 'to': "orm['timepiece.Activity']"}),
            'comments': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'hours': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '8', 'decimal_places': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': "orm['timepiece.Location']"}),
            'pause_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entries'", 'to': "orm['timepiece.Project']"}),
            'seconds_paused': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'timepiece_entries'", 'to': "orm['auth.User']"})
        },
        'timepiece.location': {
            'Meta': {'object_name': 'Location'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'slug': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'timepiece.personrepeatperiod': {
            'Meta': {'object_name': 'PersonRepeatPeriod'},
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Contact']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'repeat_period': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['timepiece.RepeatPeriod']", 'unique': 'True'})
        },
        'timepiece.personschedule': {
            'Meta': {'object_name': 'PersonSchedule'},
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['crm.Contact']", 'unique': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'hours_per_week': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '8', 'decimal_places': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'timepiece.project': {
            'Meta': {'ordering': "('name', 'status', 'type')", 'object_name': 'Project'},
            'billing_period': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'projects'", 'null': 'True', 'to': "orm['timepiece.RepeatPeriod']"}),
            'business': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'business_projects'", 'to': "orm['crm.Contact']"}),
            'contacts': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'contact_projects'", 'symmetrical': 'False', 'through': "orm['timepiece.ProjectRelationship']", 'to': "orm['crm.Contact']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interactions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['crm.Interaction']", 'symmetrical': 'False', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'point_person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects_with_status'", 'to': "orm['timepiece.Attribute']"}),
            'trac_environment': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects_with_type'", 'to': "orm['timepiece.Attribute']"})
        },
        'timepiece.projectcontract': {
            'Meta': {'object_name': 'ProjectContract'},
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_hours': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '8', 'decimal_places': '2'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'contracts'", 'to': "orm['timepiece.Project']"}),
            'start_date': ('django.db.models.fields.DateField', [], {})
        },
        'timepiece.projectrelationship': {
            'Meta': {'unique_together': "(('contact', 'project'),)", 'object_name': 'ProjectRelationship'},
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project_relationships'", 'to': "orm['crm.Contact']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project_relationships'", 'to': "orm['timepiece.Project']"}),
            'types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'project_relationships'", 'blank': 'True', 'to': "orm['crm.RelationshipType']"})
        },
        'timepiece.repeatperiod': {
            'Meta': {'object_name': 'RepeatPeriod'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'contacts': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'repeat_periods'", 'blank': 'True', 'through': "orm['timepiece.PersonRepeatPeriod']", 'to': "orm['crm.Contact']"}),
            'count': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interval': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        }
    }

    complete_apps = ['timepiece']
