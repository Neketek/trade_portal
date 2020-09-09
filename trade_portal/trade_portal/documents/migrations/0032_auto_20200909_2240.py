# Generated by Django 2.2.10 on 2020-09-09 12:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0031_documentfile_metadata'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='status',
            field=models.CharField(choices=[('not-sent', 'Not Sent'), ('pending', 'Pending'), ('failed', 'Failed'), ('validated', 'Validated'), ('incoming', 'Incoming')], default='pending', max_length=12, verbose_name='Message Status'),
        ),
        migrations.AlterField(
            model_name='document',
            name='workflow_status',
            field=models.CharField(choices=[('draft', 'Draft'), ('issued', 'Issued'), ('not-issued', 'Not issued')], default='draft', max_length=32, verbose_name='Workflow status'),
        ),
    ]
