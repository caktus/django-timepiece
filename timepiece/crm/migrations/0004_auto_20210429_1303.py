# Generated by Django 3.2 on 2021-04-29 13:03

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('crm', '0003_auto_20151119_0906'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='business',
            options={'ordering': ('name',), 'verbose_name_plural': 'Businesses'},
        ),
        migrations.AlterModelOptions(
            name='project',
            options={'ordering': ('name', 'status', 'type'), 'permissions': (('email_project_report', 'Can email project report'), ('view_project_time_sheet', 'Can view project time sheet'), ('export_project_time_sheet', 'Can export project time sheet'), ('generate_project_invoice', 'Can generate project invoice'))},
        ),
        migrations.AlterField(
            model_name='project',
            name='point_person',
            field=models.ForeignKey(limit_choices_to={'is_staff': True}, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='project',
            name='status',
            field=models.ForeignKey(limit_choices_to={'type': 'project-status'}, on_delete=django.db.models.deletion.CASCADE, related_name='projects_with_status', to='crm.attribute'),
        ),
        migrations.AlterField(
            model_name='project',
            name='type',
            field=models.ForeignKey(limit_choices_to={'type': 'project-type'}, on_delete=django.db.models.deletion.CASCADE, related_name='projects_with_type', to='crm.attribute'),
        ),
    ]