# Generated by Django 4.2.4 on 2024-05-17 16:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pfc_app', '0067_trilha_fundo_tabela'),
    ]

    operations = [
        migrations.AlterField(
            model_name='validacao_ch',
            name='nome_curso',
            field=models.CharField(default='', max_length=400),
        ),
    ]
