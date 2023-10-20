# Generated by Django 4.2.4 on 2023-09-28 23:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pfc_app', '0008_user_cargo_user_categoria_user_classificacao_lotacao_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='telefone',
            field=models.CharField(blank=True, max_length=40, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='cpf',
            field=models.CharField(max_length=11, unique=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(default='a@b.com', max_length=254, unique=True),
        ),
    ]