# Generated by Django 4.2.4 on 2024-02-20 19:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pfc_app', '0050_alter_validacao_ch_responsavel_analise'),
    ]

    operations = [
        migrations.AlterField(
            model_name='validacao_ch',
            name='responsavel_analise',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='responsavel_validacao', to=settings.AUTH_USER_MODEL),
        ),
    ]
