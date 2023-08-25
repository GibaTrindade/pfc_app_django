from django.db import models

from django.conf import settings
from django.utils import timezone

# Create your models here.

class Participante(models.Model):
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    cpf = models.CharField(max_length=11, blank=False, null=False)
    nome = models.CharField(max_length=400, blank=False, null=False)
    lotacao = models.CharField(max_length=400, blank=False, null=False)
    is_ativo = models.BooleanField()
    role = models.CharField(max_length=40)
    
    def publish(self):
        self.published_date = timezone.now()
        self.save()

    def __str__(self):
        return self.nome


class Curso(models.Model):
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    nome_curso =  models.CharField(max_length=400, blank=False, null=False)
    modalidade = models.CharField(max_length=400, blank=False, null=False)
    tipo_reconhecimento = models.CharField(max_length=400, blank=True, null=True)
    ch_curso = models.IntegerField(blank=False, null=False)
    vagas = models.IntegerField(blank=False, null=False)
    categoria = models.CharField(max_length=400, default='')
    competencia = models.CharField(max_length=400, default='')
    data_inicio = models.DateTimeField(blank=False, null=False)
    data_termino = models.DateTimeField(blank=True, null=True)
    inst_certificadora = models.CharField(max_length=400, blank=False, null=False)
    inst_promotora = models.CharField(max_length=400, blank=False, null=False)
    participantes = models.ManyToManyField(Participante, through='CH_Valida', related_name='curso_participante')
    #acao = models.ForeignKey(Acao, on_delete=models.CASCADE)
    gestor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    #history = HistoricalRecords()
    status = models.CharField(max_length=40, default='PENDENTE')

    def publish(self):
        self.published_date = timezone.now()
        self.save()

    def __str__(self):
        return self.nome_curso
    

class CH_Valida(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    participante = models.ForeignKey(Participante, on_delete=models.CASCADE)
    ch_valida = models.IntegerField()
    condicao_na_acao = models.CharField(max_length=400, blank=False, null=False)
    status = models.CharField(max_length=40)
    inscricao = models.BooleanField()

    def __str__(self):
        return f'Curso: {self.curso.nome_curso} >> Participante: {self.participante.nome}'