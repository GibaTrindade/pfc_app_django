# Generated by Django 4.2.4 on 2023-10-24 13:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pfc_app', '0020_alter_curso_coordenador'),
    ]

    operations = [
        migrations.AlterField(
            model_name='validacao_ch',
            name='usuario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]