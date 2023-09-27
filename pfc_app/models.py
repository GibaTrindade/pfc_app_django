from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import pre_save
from django.dispatch import receiver

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
    
    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        self.first_name = self.first_name.upper()
        self.last_name = self.last_name.upper()
        super(User, self).save(*args, **kwargs)


class StatusCurso(models.Model):
    nome = models.CharField(max_length=50)
    
    def __str__(self):
        return self.nome

class StatusInscricao(models.Model):
    nome = models.CharField(max_length=50)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name_plural = "status inscrições"
    

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
    data_inicio = models.DateField(blank=False, null=False)
    data_termino = models.DateField(blank=True, null=True)
    inst_certificadora = models.CharField(max_length=400, blank=False, null=False)
    inst_promotora = models.CharField(max_length=400, blank=False, null=False)
    participantes = models.ManyToManyField(User, through='Inscricao', related_name='curso_participante')
    #acao = models.ForeignKey(Acao, on_delete=models.CASCADE)
    #gestor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coordenador = models.ForeignKey(User, on_delete=models.CASCADE)
    #history = HistoricalRecords()
    status = models.ForeignKey(StatusCurso, on_delete=models.PROTECT)

    def publish(self):
        self.published_date = timezone.now()
        self.save()

    def __str__(self):
        return self.nome_curso
    

class Inscricao(models.Model):
    CONDICAO_ACAO_CHOICES = [
        ('DISCENTE', 'DISCENTE'),
        ('DOCENTE', 'DOCENTE'),
    ]
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    participante = models.ForeignKey(User, on_delete=models.CASCADE)
    ch_valida = models.IntegerField(blank=True, null=True)
    condicao_na_acao = models.CharField(max_length=400, choices=CONDICAO_ACAO_CHOICES, blank=False, null=False, default="DISCENTE")
    status = models.ForeignKey(StatusInscricao, on_delete=models.PROTECT)
    concluido = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "inscrições"
        unique_together = ('curso', 'participante')

    def __str__(self):
        return f'Curso: {self.curso.nome_curso} >> Participante: {self.participante.nome}'

@receiver(pre_save, sender=Inscricao)
def calcular_carga_horaria(sender, instance, **kwargs):
    instance.ch_valida = instance.curso.ch_curso