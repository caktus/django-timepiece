# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'InvoiceAdjustment.is_payment'
        db.add_column(u'contracts_invoiceadjustment', 'is_payment',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'InvoiceAdjustment.is_payment'
        db.delete_column(u'contracts_invoiceadjustment', 'is_payment')


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
        u'contracts.contractassignment': {
            'Meta': {'unique_together': "(('contract', 'user'),)", 'object_name': 'ContractAssignment', 'db_table': "'timepiece_contractassignment'"},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'assignments'", 'to': u"orm['contracts.ProjectContract']"}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'min_hours_per_week': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'num_hours': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '8', 'decimal_places': '2'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'assignments'", 'to': u"orm['auth.User']"})
        },
        u'contracts.contractattachment': {
            'Meta': {'object_name': 'ContractAttachment'},
            'bucket': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contracts.ProjectContract']"}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'filename': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'upload_datetime': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'uploader': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'uuid': ('django.db.models.fields.TextField', [], {})
        },
        u'contracts.contractbudget': {
            'Meta': {'object_name': 'ContractBudget'},
            'budget': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '11', 'decimal_places': '2'}),
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contracts.ProjectContract']"}),
            'date_approved': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'date_requested': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        u'contracts.contracthour': {
            'Meta': {'object_name': 'ContractHour', 'db_table': "'timepiece_contracthour'"},
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contracts.ProjectContract']"}),
            'date_approved': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'date_requested': ('django.db.models.fields.DateField', [], {}),
            'hours': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '8', 'decimal_places': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '1'})
        },
        u'contracts.contractnote': {
            'Meta': {'object_name': 'ContractNote'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contracts.ProjectContract']"}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'edited': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_edited': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contracts.ContractNote']", 'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        u'contracts.contractrate': {
            'Meta': {'unique_together': "(('contract', 'activity'),)", 'object_name': 'ContractRate'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['entries.Activity']"}),
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contracts.ProjectContract']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rate': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '6', 'decimal_places': '2'})
        },
        u'contracts.entrygroup': {
            'Meta': {'object_name': 'EntryGroup', 'db_table': "'timepiece_entrygroup'"},
            'auto_number': ('django.db.models.fields.CharField', [], {'max_length': '17', 'null': 'True', 'blank': 'True'}),
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'contract': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contracts.ProjectContract']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'end': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'number': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'override_invoice_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'entry_group'", 'null': 'True', 'to': u"orm['crm.Project']"}),
            'single_project': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'start': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'invoiced'", 'max_length': '24'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'entry_group'", 'to': u"orm['auth.User']"})
        },
        u'contracts.hourgroup': {
            'Meta': {'object_name': 'HourGroup', 'db_table': "'timepiece_hourgroup'"},
            'activities': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'activity_bundle'", 'symmetrical': 'False', 'to': u"orm['entries.Activity']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'order': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'contracts.invoiceadjustment': {
            'Meta': {'object_name': 'InvoiceAdjustment'},
            'date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contracts.EntryGroup']"}),
            'is_payment': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'line_item': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'quantity': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'rate': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'})
        },
        u'contracts.projectcontract': {
            'Meta': {'ordering': "('name',)", 'object_name': 'ProjectContract', 'db_table': "'timepiece_projectcontract'"},
            'ceiling_type': ('django.db.models.fields.IntegerField', [], {'default': '2'}),
            'client_expense_category': ('django.db.models.fields.CharField', [], {'default': "'unknown'", 'max_length': '16'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'payment_terms': ('django.db.models.fields.CharField', [], {'default': "'net30'", 'max_length': '32'}),
            'po_line_item': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'po_number': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'primary_contact': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Contact']"}),
            'projects': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'contracts'", 'symmetrical': 'False', 'to': u"orm['crm.Project']"}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'upcoming'", 'max_length': '32'}),
            'type': ('django.db.models.fields.IntegerField', [], {})
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
            'billing_street_2': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
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
            'shipping_street_2': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'short_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '3', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'ticker_symbol': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'website': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
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
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'contact'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['auth.User']", 'blank': 'True', 'unique': 'True'})
        },
        u'crm.project': {
            'Meta': {'ordering': "('code', 'name', 'status', 'type')", 'object_name': 'Project', 'db_table': "'timepiece_project'"},
            'activity_group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'activity_group'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['entries.ActivityGroup']"}),
            'binder': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'binder'", 'to': u"orm['auth.User']"}),
            'business': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'new_business_projects'", 'to': u"orm['crm.Business']"}),
            'business_department': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'new_business_department_projects'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['crm.BusinessDepartment']"}),
            'client_primary_poc': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['crm.Contact']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '12', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'ext_code': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'finder': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'finder'", 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'point_person': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'minder'", 'to': u"orm['auth.User']"}),
            'project_department': ('django.db.models.fields.CharField', [], {'default': "'other'", 'max_length': '16'}),
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

    complete_apps = ['contracts']