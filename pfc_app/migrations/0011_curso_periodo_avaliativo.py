# Generated by Django 4.2.4 on 2023-10-19 00:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pfc_app', '0010_avaliacao_curso_avaliacoes'),
    ]

    operations = [
        migrations.AddField(
            model_name='curso',
            name='periodo_avaliativo',
            field=models.BooleanField(default=False),
        ),
    ]
