# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'BusinessDepartment'
        db.create_table(u'crm_businessdepartment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('business', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Business'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('short_name', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
        ))
        db.send_create_signal(u'crm', ['BusinessDepartment'])

        # Adding model 'BusinessNote'
        db.create_table(u'crm_businessnote', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('business', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.Business'])),
            ('author', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('edited', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('last_edited', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.BusinessNote'], null=True, blank=True)),
            ('text', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'crm', ['BusinessNote'])

        # Deleting field 'Business.email'
        db.delete_column('timepiece_business', 'email')

        # Adding field 'Business.poc'
        db.add_column('timepiece_business', 'poc',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=5, related_name='business_poc', to=orm['auth.User']),
                      keep_default=False)

        # Adding field 'Business.classification'
        db.add_column('timepiece_business', 'classification',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=8, blank=True),
                      keep_default=False)

        # Adding field 'Business.active'
        db.add_column('timepiece_business', 'active',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Business.status'
        db.add_column('timepiece_business', 'status',
                      self.gf('django.db.models.fields.CharField')(max_length=16, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Business.account_owner'
        db.add_column('timepiece_business', 'account_owner',
                      self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='biz_account_holder', null=True, to=orm['auth.User']),
                      keep_default=False)

        # Adding field 'Business.billing_street'
        db.add_column('timepiece_business', 'billing_street',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                      keep_default=False)

        # Adding field 'Business.billing_postalcode'
        db.add_column('timepiece_business', 'billing_postalcode',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                      keep_default=False)

        # Adding field 'Business.billing_city'
        db.add_column('timepiece_business', 'billing_city',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                      keep_default=False)

        # Adding field 'Business.billing_state'
        db.add_column('timepiece_business', 'billing_state',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=2, blank=True),
                      keep_default=False)

        # Adding field 'Business.billing_zip'
        db.add_column('timepiece_business', 'billing_zip',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=32, blank=True),
                      keep_default=False)

        # Adding field 'Business.billing_country'
        db.add_column('timepiece_business', 'billing_country',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                      keep_default=False)

        # Adding field 'Business.billing_lat'
        db.add_column('timepiece_business', 'billing_lat',
                      self.gf('django.db.models.fields.FloatField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Business.billing_lon'
        db.add_column('timepiece_business', 'billing_lon',
                      self.gf('django.db.models.fields.FloatField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Business.shipping_street'
        db.add_column('timepiece_business', 'shipping_street',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                      keep_default=False)

        # Adding field 'Business.shipping_postalcode'
        db.add_column('timepiece_business', 'shipping_postalcode',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                      keep_default=False)

        # Adding field 'Business.shipping_city'
        db.add_column('timepiece_business', 'shipping_city',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                      keep_default=False)

        # Adding field 'Business.shipping_state'
        db.add_column('timepiece_business', 'shipping_state',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=2, blank=True),
                      keep_default=False)

        # Adding field 'Business.shipping_zip'
        db.add_column('timepiece_business', 'shipping_zip',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=32, blank=True),
                      keep_default=False)

        # Adding field 'Business.shipping_country'
        db.add_column('timepiece_business', 'shipping_country',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                      keep_default=False)

        # Adding field 'Business.shipping_lat'
        db.add_column('timepiece_business', 'shipping_lat',
                      self.gf('django.db.models.fields.FloatField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Business.shipping_lon'
        db.add_column('timepiece_business', 'shipping_lon',
                      self.gf('django.db.models.fields.FloatField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Business.phone'
        db.add_column('timepiece_business', 'phone',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=16, blank=True),
                      keep_default=False)

        # Adding field 'Business.fax'
        db.add_column('timepiece_business', 'fax',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=16, blank=True),
                      keep_default=False)

        # Adding field 'Business.website'
        db.add_column('timepiece_business', 'website',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                      keep_default=False)

        # Adding field 'Business.account_numer'
        db.add_column('timepiece_business', 'account_numer',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                      keep_default=False)

        # Adding field 'Business.industry'
        db.add_column('timepiece_business', 'industry',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=64, blank=True),
                      keep_default=False)

        # Adding field 'Business.ownership'
        db.add_column('timepiece_business', 'ownership',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                      keep_default=False)

        # Adding field 'Business.annual_revenue'
        db.add_column('timepiece_business', 'annual_revenue',
                      self.gf('django.db.models.fields.FloatField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Business.num_of_employees'
        db.add_column('timepiece_business', 'num_of_employees',
                      self.gf('django.db.models.fields.FloatField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'Business.ticker_symbol'
        db.add_column('timepiece_business', 'ticker_symbol',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=32, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting model 'BusinessDepartment'
        db.delete_table(u'crm_businessdepartment')

        # Deleting model 'BusinessNote'
        db.delete_table(u'crm_businessnote')

        # Adding field 'Business.email'
        db.add_column('timepiece_business', 'email',
                      self.gf('django.db.models.fields.EmailField')(default='', max_length=75, blank=True),
                      keep_default=False)

        # Deleting field 'Business.poc'
        db.delete_column('timepiece_business', 'poc_id')

        # Deleting field 'Business.classification'
        db.delete_column('timepiece_business', 'classification')

        # Deleting field 'Business.active'
        db.delete_column('timepiece_business', 'active')

        # Deleting field 'Business.status'
        db.delete_column('timepiece_business', 'status')

        # Deleting field 'Business.account_owner'
        db.delete_column('timepiece_business', 'account_owner_id')

        # Deleting field 'Business.billing_street'
        db.delete_column('timepiece_business', 'billing_street')

        # Deleting field 'Business.billing_postalcode'
        db.delete_column('timepiece_business', 'billing_postalcode')

        # Deleting field 'Business.billing_city'
        db.delete_column('timepiece_business', 'billing_city')

        # Deleting field 'Business.billing_state'
        db.delete_column('timepiece_business', 'billing_state')

        # Deleting field 'Business.billing_zip'
        db.delete_column('timepiece_business', 'billing_zip')

        # Deleting field 'Business.billing_country'
        db.delete_column('timepiece_business', 'billing_country')

        # Deleting field 'Business.billing_lat'
        db.delete_column('timepiece_business', 'billing_lat')

        # Deleting field 'Business.billing_lon'
        db.delete_column('timepiece_business', 'billing_lon')

        # Deleting field 'Business.shipping_street'
        db.delete_column('timepiece_business', 'shipping_street')

        # Deleting field 'Business.shipping_postalcode'
        db.delete_column('timepiece_business', 'shipping_postalcode')

        # Deleting field 'Business.shipping_city'
        db.delete_column('timepiece_business', 'shipping_city')

        # Deleting field 'Business.shipping_state'
        db.delete_column('timepiece_business', 'shipping_state')

        # Deleting field 'Business.shipping_zip'
        db.delete_column('timepiece_business', 'shipping_zip')

        # Deleting field 'Business.shipping_country'
        db.delete_column('timepiece_business', 'shipping_country')

        # Deleting field 'Business.shipping_lat'
        db.delete_column('timepiece_business', 'shipping_lat')

        # Deleting field 'Business.shipping_lon'
        db.delete_column('timepiece_business', 'shipping_lon')

        # Deleting field 'Business.phone'
        db.delete_column('timepiece_business', 'phone')

        # Deleting field 'Business.fax'
        db.delete_column('timepiece_business', 'fax')

        # Deleting field 'Business.website'
        db.delete_column('timepiece_business', 'website')

        # Deleting field 'Business.account_numer'
        db.delete_column('timepiece_business', 'account_numer')

        # Deleting field 'Business.industry'
        db.delete_column('timepiece_business', 'industry')

        # Deleting field 'Business.ownership'
        db.delete_column('timepiece_business', 'ownership')

        # Deleting field 'Business.annual_revenue'
        db.delete_column('timepiece_business', 'annual_revenue')

        # Deleting field 'Business.num_of_employees'
        db.delete_column('timepiece_business', 'num_of_employees')

        # Deleting field 'Business.ticker_symbol'
        db.delete_column('timepiece_business', 'ticker_symbol')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'crm.activitygoal': {
            'Meta': {'ordering': "('milestone', 'employee__last_name', 'goal_hours')", 'object_name': 'ActivityGoal'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['entries.Activity']", 'null': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'employee': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'activity_goals'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'goal_hours': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'milestone': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Milestone']"})
        },
        u'crm.attribute': {
            'Meta': {'ordering': "('sort_order',)", 'unique_together': "(('type', 'label'),)", 'object_name': 'Attribute', 'db_table': "'timepiece_attribute'"},
            'billable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'enable_timetracking': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'sort_order': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        u'crm.business': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Business', 'db_table': "'timepiece_business'"},
            'account_numer': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'account_owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'biz_account_holder'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'annual_revenue': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'billing_city': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'billing_country': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'billing_lat': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'billing_lon': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'billing_postalcode': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'billing_state': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'billing_street': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'billing_zip': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'classification': ('django.db.models.fields.CharField', [], {'max_length': '8', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'external_id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'fax': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'industry': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'num_of_employees': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'ownership': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'poc': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'business_poc'", 'to': u"orm['auth.User']"}),
            'shipping_city': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'shipping_country': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'shipping_lat': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'shipping_lon': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'shipping_postalcode': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'shipping_state': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'shipping_street': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'shipping_zip': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'ticker_symbol': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'website': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'crm.businessdepartment': {
            'Meta': {'object_name': 'BusinessDepartment'},
            'business': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Business']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'crm.businessnote': {
            'Meta': {'object_name': 'BusinessNote'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'business': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Business']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'edited': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_edited': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.BusinessNote']", 'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        u'crm.milestone': {
            'Meta': {'ordering': "('due_date',)", 'object_name': 'Milestone'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'due_date': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Project']"})
        },
        u'crm.paidtimeofflog': {
            'Meta': {'ordering': "('user_profile', '-date')", 'object_name': 'PaidTimeOffLog'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pto_request': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.PaidTimeOffRequest']", 'null': 'True', 'blank': 'True'}),
            'user_profile': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.UserProfile']"})
        },
        u'crm.paidtimeoffrequest': {
            'Meta': {'ordering': "('user_profile', '-pto_start_date')", 'object_name': 'PaidTimeOffRequest'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'approval_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'approver': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'pto_approver'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'approver_comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'process_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'processor': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'pto_processor'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'pto': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'pto_end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'pto_start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'request_date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '24'}),
            'user_profile': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.UserProfile']"})
        },
        u'crm.project': {
            'Meta': {'ordering': "('code', 'name', 'status', 'type')", 'object_name': 'Project', 'db_table': "'timepiece_project'"},
            'activity_group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'activity_group'", 'null': 'True', 'to': u"orm['entries.ActivityGroup']"}),
            'binder': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'binder'", 'to': u"orm['auth.User']"}),
            'business': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'new_business_projects'", 'to': u"orm['crm.Business']"}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '12', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'finder': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'finder'", 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'point_person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'minder'", 'to': u"orm['auth.User']"}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects_with_status'", 'to': u"orm['crm.Attribute']"}),
            'tracker_url': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'projects_with_type'", 'to': u"orm['crm.Attribute']"}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'user_projects'", 'symmetrical': 'False', 'through': u"orm['crm.ProjectRelationship']", 'to': u"orm['auth.User']"}),
            'year': ('django.db.models.fields.SmallIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'crm.projectrelationship': {
            'Meta': {'unique_together': "(('user', 'project'),)", 'object_name': 'ProjectRelationship', 'db_table': "'timepiece_projectrelationship'"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project_relationships'", 'to': u"orm['crm.Project']"}),
            'types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'project_relationships'", 'blank': 'True', 'to': u"orm['crm.RelationshipType']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'project_relationships'", 'to': u"orm['auth.User']"})
        },
        u'crm.relationshiptype': {
            'Meta': {'object_name': 'RelationshipType', 'db_table': "'timepiece_relationshiptype'"},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '255'})
        },
        u'crm.userprofile': {
            'Meta': {'object_name': 'UserProfile', 'db_table': "'timepiece_userprofile'"},
            'business': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Business']"}),
            'earns_pto': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'employee_type': ('django.db.models.fields.CharField', [], {'default': "'inactive'", 'max_length': '24'}),
            'hire_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'hours_per_week': ('django.db.models.fields.DecimalField', [], {'default': '40', 'max_digits': '8', 'decimal_places': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'profile'", 'unique': 'True', 'to': u"orm['auth.User']"})
        },
        u'entries.activity': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Activity', 'db_table': "'timepiece_activity'"},
            'billable': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '16'}),
            'examples': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'entries.activitygroup': {
            'Meta': {'object_name': 'ActivityGroup', 'db_table': "'timepiece_activitygroup'"},
            'activities': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'activity_group'", 'symmetrical': 'False', 'to': u"orm['entries.Activity']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        }
    }

    complete_apps = ['crm']