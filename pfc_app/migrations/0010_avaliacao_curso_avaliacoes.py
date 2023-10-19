# Generated by Django 4.2.4 on 2023-10-18 21:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pfc_app', '0009_user_telefone_alter_user_cpf_alter_user_email'),
    ]

    operations = [
        migrations.CreateModel(
            name='Avaliacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nota_atributo1', models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=None)),
                ('nota_atributo2', models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=None)),
                ('nota_atributo3', models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=None)),
                ('nota_atributo4', models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=None)),
                ('nota_atributo5', models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=None)),
                ('curso', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pfc_app.curso')),
                ('participante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='curso',
            name='avaliacoes',
            field=models.ManyToManyField(related_name='curso_avaliacao', through='pfc_app.Avaliacao', to=settings.AUTH_USER_MODEL),
        ),
    ]
