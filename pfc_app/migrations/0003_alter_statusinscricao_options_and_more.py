# Generated by Django 4.2.4 on 2023-09-27 03:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pfc_app', '0002_alter_inscricao_unique_together'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='statusinscricao',
            options={'verbose_name_plural': 'status inscrições'},
        ),
        migrations.RenameField(
            model_name='inscricao',
            old_name='conluido',
            new_name='concluido',
        ),
    ]
