# Generated by Django 4.2.4 on 2024-02-20 19:00

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pfc_app', '0049_validacao_ch_conhecimento_posterior_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='validacao_ch',
            name='responsavel_analise',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='responsavel_validacao', to=settings.AUTH_USER_MODEL),
        ),
    ]
