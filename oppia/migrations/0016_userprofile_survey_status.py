# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-02-11 15:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oppia', '0015_auto_20160209_1647'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='survey_status',
            field=models.TextField(blank=True, default=b'', null=True),
        ),
    ]
