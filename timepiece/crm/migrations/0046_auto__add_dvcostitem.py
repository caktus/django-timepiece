# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'DVCostItem'
        db.create_table(u'crm_dvcostitem', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('dv', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['crm.DistinguishingValueChallenge'])),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('details', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('cost', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=11, decimal_places=2, blank=True)),
            ('man_hours', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=11, decimal_places=2, blank=True)),
            ('rate', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=6, decimal_places=2, blank=True)),
        ))
        db.send_create_signal(u'crm', ['DVCostItem'])


    def backwards(self, orm):
        # Deleting model 'DVCostItem'
        db.delete_table(u'crm_dvcostitem')


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
            'Meta': {'ordering': "('project__code', 'employee__last_name', 'employee__first_name', 'goal_hours')", 'object_name': 'ActivityGoal'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['entries.Activity']", 'null': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'employee': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'activity_goals'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'goal_hours': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'milestone': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Milestone']", 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Project']", 'null': 'True', 'blank': 'True'})
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
            'account_number': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'account_owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'biz_account_holder'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'annual_revenue': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'billing_city': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'billing_country': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'billing_lat': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'billing_lon': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'billing_mailstop': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'billing_postalcode': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'billing_state': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'billing_street': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'classification': ('django.db.models.fields.CharField', [], {'max_length': '8', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'external_id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'fax': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'industry': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'num_of_employees': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'ownership': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'poc': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'business_poc_old'", 'null': 'True', 'to': u"orm['auth.User']"}),
            'primary_contact': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'business_poc'", 'null': 'True', 'to': u"orm['crm.Contact']"}),
            'shipping_city': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'shipping_country': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'shipping_lat': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'shipping_lon': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'shipping_mailstop': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'shipping_postalcode': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'shipping_state': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'shipping_street': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '3', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'ticker_symbol': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'website': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'crm.businessattachment': {
            'Meta': {'object_name': 'BusinessAttachment'},
            'business': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Business']"}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'file_id': ('django.db.models.fields.CharField', [], {'max_length': '24'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'upload_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'uploader': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'crm.businessdepartment': {
            'Meta': {'object_name': 'BusinessDepartment'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'bd_billing_city': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'bd_billing_country': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'bd_billing_lat': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'bd_billing_lon': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'bd_billing_mailstop': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'bd_billing_postalcode': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'bd_billing_state': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'bd_billing_street': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'bd_shipping_city': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'bd_shipping_country': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'bd_shipping_lat': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'bd_shipping_lon': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'bd_shipping_mailstop': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'bd_shipping_postalcode': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'bd_shipping_state': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'bd_shipping_street': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'business': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Business']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'poc': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'business_department_poc'", 'null': 'True', 'to': u"orm['crm.Contact']"}),
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
        u'crm.contact': {
            'Meta': {'ordering': "('last_name', 'first_name')", 'object_name': 'Contact'},
            'assistant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Contact']", 'null': 'True', 'blank': 'True'}),
            'assistant_email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'assistant_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'assistant_phone': ('django.db.models.fields.CharField', [], {'max_length': '24', 'blank': 'True'}),
            'birthday': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'business': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Business']", 'null': 'True', 'blank': 'True'}),
            'business_department': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.BusinessDepartment']", 'null': 'True', 'blank': 'True'}),
            'do_not_call': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'fax': ('django.db.models.fields.CharField', [], {'max_length': '24', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'has_opted_out_of_email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'has_opted_out_of_fax': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'home_phone': ('django.db.models.fields.CharField', [], {'max_length': '24', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'lead_source': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'contact_lead_source'", 'to': u"orm['auth.User']"}),
            'mailing_city': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'mailing_country': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'mailing_lat': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'mailing_lon': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'mailing_mailstop': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'mailing_postalcode': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'mailing_state': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'mailing_street': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'mobile_phone': ('django.db.models.fields.CharField', [], {'max_length': '24', 'blank': 'True'}),
            'office_phone': ('django.db.models.fields.CharField', [], {'max_length': '24', 'blank': 'True'}),
            'other_city': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'other_country': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'other_lat': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'other_lon': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'other_mailstop': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'other_phone': ('django.db.models.fields.CharField', [], {'max_length': '24', 'blank': 'True'}),
            'other_postalcode': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'other_state': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'other_street': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'salutation': ('django.db.models.fields.CharField', [], {'max_length': '8', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'blank': 'True', 'related_name': "'contact'", 'unique': 'True', 'null': 'True', 'to': u"orm['auth.User']"})
        },
        u'crm.contactnote': {
            'Meta': {'object_name': 'ContactNote'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Contact']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'edited': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_edited': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.ContactNote']", 'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        u'crm.distinguishingvaluechallenge': {
            'Meta': {'ordering': "['order', '-due_date']", 'object_name': 'DistinguishingValueChallenge'},
            'benefits_begin': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'business': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Business']", 'null': 'True', 'blank': 'True'}),
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'commitment': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'commitment_notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'confirm': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'confirm_notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'confirm_resources': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'cost': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'date_benefits_begin': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'due': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'due_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'lead': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Lead']", 'null': 'True', 'blank': 'True'}),
            'longevity': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'order': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'probing_question': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'resources_notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'results': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'steps': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'crm.dvcostitem': {
            'Meta': {'ordering': "['description']", 'object_name': 'DVCostItem'},
            'cost': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '11', 'decimal_places': '2', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'details': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'dv': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.DistinguishingValueChallenge']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'man_hours': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '11', 'decimal_places': '2', 'blank': 'True'}),
            'rate': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '6', 'decimal_places': '2', 'blank': 'True'})
        },
        u'crm.lead': {
            'Meta': {'object_name': 'Lead'},
            'aac_poc': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'lead_poc'", 'to': u"orm['auth.User']"}),
            'business_placeholder': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Business']", 'null': 'True', 'blank': 'True'}),
            'contacts': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'lead_contacts'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['crm.Contact']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'lead_created_by'", 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_activity': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'last_editor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'lead_edited_by'", 'to': u"orm['auth.User']"}),
            'lead_source': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'lead_source'", 'to': u"orm['auth.User']"}),
            'primary_contact': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Contact']", 'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'open'", 'max_length': '16'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        u'crm.leadattachment': {
            'Meta': {'object_name': 'LeadAttachment'},
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'file_id': ('django.db.models.fields.CharField', [], {'max_length': '24'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lead': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Lead']"}),
            'upload_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'uploader': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'crm.leadnote': {
            'Meta': {'object_name': 'LeadNote'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'edited': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_edited': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'lead': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Lead']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.LeadNote']", 'null': 'True', 'blank': 'True'}),
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
            'pto': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
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
            'business_department': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'new_business_department_projects'", 'null': 'True', 'to': u"orm['crm.BusinessDepartment']"}),
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
        u'crm.templatedifferentiatingvalue': {
            'Meta': {'ordering': "['short_name']", 'object_name': 'TemplateDifferentiatingValue'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'probing_question': ('django.db.models.fields.TextField', [], {}),
            'short_name': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        u'crm.userprofile': {
            'Meta': {'object_name': 'UserProfile', 'db_table': "'timepiece_userprofile'"},
            'business': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Business']"}),
            'earns_holiday_pay': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'earns_pto': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'employee_type': ('django.db.models.fields.CharField', [], {'default': "'inactive'", 'max_length': '24'}),
            'hire_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'hours_per_week': ('django.db.models.fields.DecimalField', [], {'default': '40', 'max_digits': '8', 'decimal_places': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pto_accrual': ('django.db.models.fields.FloatField', [], {'default': '0.0'}),
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
        },
        u'taggit.tag': {
            'Meta': {'object_name': 'Tag'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'taggit.taggeditem': {
            'Meta': {'object_name': 'TaggedItem'},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'taggit_taggeditem_tagged_items'", 'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'tag': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'taggit_taggeditem_items'", 'to': u"orm['taggit.Tag']"})
        }
    }

    complete_apps = ['crm']