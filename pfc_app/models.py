from django.db import models
from django.contrib.auth.models import AbstractUser

from django.conf import settings
from django.utils import timezone

# Create your models here.

class User(AbstractUser):
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    cpf = models.CharField(max_length=11, blank=False, null=False)
    nome = models.CharField(max_length=400, blank=False, null=False)
    email = models.EmailField(default='a@b.com', null=False, blank=False)
    lotacao = models.CharField(max_length=400, blank=False, null=False)
    is_ativo = models.BooleanField(default=True)
    role = models.CharField(max_length=40, default="USER")
    
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
    participantes = models.ManyToManyField(User, through='Inscricao', related_name='curso_participante')
    #acao = models.ForeignKey(Acao, on_delete=models.CASCADE)
    #gestor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coordenador = models.ForeignKey(User, on_delete=models.CASCADE)
    #history = HistoricalRecords()
    status = models.CharField(max_length=40, default='PENDENTE')

    def publish(self):
        self.published_date = timezone.now()
        self.save()

    def __str__(self):
        return self.nome_curso
    

class Inscricao(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    participante = models.ForeignKey(User, on_delete=models.CASCADE)
    ch_valida = models.IntegerField()
    condicao_na_acao = models.CharField(max_length=400, blank=False, null=False)
    status = models.CharField(max_length=40)
    conluido = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "inscrições"

    def __str__(self):
        return f'Curso: {self.curso.nome_curso} >> Participante: {self.participante.nome}'
    