# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-07-25 11:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oppia', '0023_auto_20160601_1155'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='imei',
            field=models.TextField(blank=True, default=None, null=True),
        ),
    ]
