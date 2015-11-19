# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Migrations are in entries.0001_initial, to resolve circular
        # dependencies. See #787.
        pass

    def backwards(self, orm):
        pass

    models = {
    }

    complete_apps = ['crm']
