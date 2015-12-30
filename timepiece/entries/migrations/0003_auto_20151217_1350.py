# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('entries', '0002_auto_20151119_0906'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entry',
            name='hours',
            field=models.DecimalField(default=0, max_digits=11, decimal_places=5),
        ),
        migrations.AlterField(
            model_name='projecthours',
            name='hours',
            field=models.DecimalField(default=0, max_digits=11, decimal_places=5, validators=[django.core.validators.MinValueValidator(Decimal('0.00001'))]),
        ),
    ]
