# Generated by Django 4.2.4 on 2023-09-27 01:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pfc_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='inscricao',
            unique_together={('curso', 'participante')},
        ),
    ]
