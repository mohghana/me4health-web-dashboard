# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-06-01 11:55
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oppia', '0022_cohort_school'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cohort',
            name='description',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
