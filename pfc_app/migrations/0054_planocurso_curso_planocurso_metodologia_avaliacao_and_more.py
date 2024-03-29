# Generated by Django 4.2.4 on 2024-03-08 19:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pfc_app', '0053_planocurso'),
    ]

    operations = [
        migrations.AddField(
            model_name='planocurso',
            name='curso',
            field=models.OneToOneField(default=13, on_delete=django.db.models.deletion.CASCADE, to='pfc_app.curso'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='planocurso',
            name='metodologia_avaliacao',
            field=models.TextField(blank=True, max_length=4000, null=True, verbose_name='Metodologia de avaliação'),
        ),
        migrations.AddField(
            model_name='planocurso',
            name='metodologia_ensino',
            field=models.TextField(blank=True, max_length=4000, null=True, verbose_name='Metodologia de ensino'),
        ),
        migrations.AddField(
            model_name='planocurso',
            name='objetivo_especifico',
            field=models.TextField(blank=True, max_length=4000, null=True, verbose_name='Objetivo específico'),
        ),
        migrations.AddField(
            model_name='planocurso',
            name='objetivo_geral',
            field=models.TextField(blank=True, max_length=4000, null=True, verbose_name='Objetivo geral'),
        ),
        migrations.AddField(
            model_name='planocurso',
            name='pre_requisitos',
            field=models.TextField(blank=True, max_length=4000, null=True, verbose_name='Pré-requisitos'),
        ),
        migrations.AddField(
            model_name='planocurso',
            name='publico_alvo',
            field=models.TextField(blank=True, max_length=4000, null=True, verbose_name='Público-alvo'),
        ),
        migrations.AddField(
            model_name='planocurso',
            name='quantidade_turma',
            field=models.SmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='planocurso',
            name='recursos_aluno',
            field=models.TextField(blank=True, max_length=4000, null=True, verbose_name='Recursos aluno'),
        ),
        migrations.AddField(
            model_name='planocurso',
            name='recursos_professor',
            field=models.TextField(blank=True, max_length=4000, null=True, verbose_name='Recursos professor'),
        ),
        migrations.AddField(
            model_name='planocurso',
            name='referencia_bibliografica',
            field=models.TextField(blank=True, max_length=4000, null=True, verbose_name='Referências bibliográficas'),
        ),
        migrations.CreateModel(
            name='CronogramaExecucao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('aula', models.SmallIntegerField(blank=True, null=True)),
                ('turno', models.CharField(blank=True, choices=[('MANHÃ', 'MANHÃ'), ('TARDE', 'TARDE')], max_length=10, null=True)),
                ('conteudo', models.TextField(blank=True, max_length=4000, null=True, verbose_name='Conteúdo')),
                ('atividade', models.TextField(blank=True, max_length=4000, null=True, verbose_name='Atividades')),
                ('plano', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='pfc_app.planocurso')),
            ],
        ),
    ]
