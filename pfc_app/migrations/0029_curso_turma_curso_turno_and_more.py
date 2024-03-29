# Generated by Django 4.2.4 on 2024-01-10 14:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pfc_app', '0028_validacao_ch_agenda_pfc_validacao_ch_ementa'),
    ]

    operations = [
        migrations.AddField(
            model_name='curso',
            name='turma',
            field=models.CharField(choices=[('TURMA1', 'TURMA 1'), ('TURMA2', 'TURMA 2'), ('TURMA3', 'TURMA 3'), ('TURMA4', 'TURMA 4'), ('TURMA5', 'TURMA 5')], default='TURMA1', max_length=10),
        ),
        migrations.AddField(
            model_name='curso',
            name='turno',
            field=models.CharField(choices=[('MANHA', 'MANHÃ'), ('TARDE', 'TARDE'), ('NOITE', 'NOITE')], default='TARDE', max_length=10),
        ),
        migrations.AlterField(
            model_name='user',
            name='lotacao_especifica_2',
            field=models.CharField(blank=True, max_length=400, null=True, verbose_name='Lotação sigla'),
        ),
        migrations.AlterField(
            model_name='validacao_ch',
            name='status',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='pfc_app.statusvalidacao'),
        ),
    ]
