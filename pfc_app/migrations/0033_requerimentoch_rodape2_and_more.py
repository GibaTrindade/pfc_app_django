# Generated by Django 4.2.4 on 2024-01-15 17:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pfc_app', '0032_alter_requerimentoch_local_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='requerimentoch',
            name='rodape2',
            field=models.CharField(default='', max_length=400),
        ),
        migrations.AlterField(
            model_name='requerimentoch',
            name='local_data',
            field=models.CharField(default='', max_length=50),
        ),
        migrations.AlterField(
            model_name='requerimentoch',
            name='rodape',
            field=models.CharField(default='', max_length=400),
        ),
    ]