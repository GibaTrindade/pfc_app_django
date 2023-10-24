from django.db import models
from django import forms
import os
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import pre_save
from django.dispatch import receiver
import base64
from django.conf import settings
from django.utils import timezone

# Create your models here.

class User(AbstractUser):
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    cpf = models.CharField(max_length=11, blank=False, null=False, unique=True)
    nome = models.CharField(max_length=400, blank=False, null=False)
    email = models.EmailField(default='a@b.com', null=False, blank=False, unique=True)
    telefone = models.CharField(max_length=40, blank=True, null=True)
    cargo = models.CharField(max_length=400, blank=True, null=True)
    nome_cargo = models.CharField(max_length=400, blank=True, null=True)
    categoria = models.CharField(max_length=400, blank=True, null=True)
    grupo_ocupacional = models.CharField(max_length=400, blank=True, null=True)
    origem = models.CharField(max_length=400, blank=True, null=True)
    simbologia = models.CharField(max_length=400, blank=True, null=True)
    tipo_atuacao = models.CharField(max_length=400, blank=True, null=True)
    lotacao = models.CharField(max_length=400, blank=True, null=True)
    lotacao_especifica = models.CharField(max_length=400, blank=True, null=True)
    lotacao_especifica_2 = models.CharField(max_length=400, blank=True, null=True)
    classificacao_lotacao = models.CharField(max_length=400, blank=True, null=True)

    is_ativo = models.BooleanField(default=True)
    role = models.CharField(max_length=40, default="USER")
    is_externo = models.BooleanField(default=False)
    avatar = models.ImageField(null=True, blank=True)
    avatar_base64 = models.TextField(blank=True, null=True)
    
    def publish(self):
        self.published_date = timezone.now()
        self.save()

    def __str__(self):
        return self.nome
    
    def save(self, *args, **kwargs):
        self.nome = self.nome.upper()
        self.first_name = self.first_name.upper()
        self.last_name = self.last_name.upper()
        if self.avatar:
            # Leia a imagem em bytes
            image_data = self.avatar.read()
            # Converta a imagem em base64
            base64_data = base64.b64encode(image_data).decode('utf-8')
            # Salve a imagem em base64 no campo avatar_base64
            self.avatar_base64 = base64_data

        self.avatar = None
        super(User, self).save(*args, **kwargs)

        if self.avatar:
            os.remove(self.avatar.path)

            # Defina o campo avatar como vazio para garantir que o arquivo não seja salvo novamente
            


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
    ementa_curso =  models.TextField(max_length=4000, blank=False, null=False)
    modalidade = models.CharField(max_length=400, blank=False, null=False)
    tipo_reconhecimento = models.CharField(max_length=400, blank=True, null=True)
    ch_curso = models.IntegerField(blank=False, null=False)
    vagas = models.IntegerField(blank=False, null=False)
    categoria = models.CharField(max_length=400, default='')
    competencia = models.CharField(max_length=400, default='')
    descricao = models.TextField(max_length=4000, default='')
    data_inicio = models.DateField(blank=False, null=False)
    data_termino = models.DateField(blank=True, null=True)
    inst_certificadora = models.CharField(max_length=400, blank=False, null=False)
    inst_promotora = models.CharField(max_length=400, blank=False, null=False)
    participantes = models.ManyToManyField(User, through='Inscricao', related_name='curso_participante')
    avaliacoes = models.ManyToManyField(User, through='Avaliacao', related_name='curso_avaliacao')
    #acao = models.ForeignKey(Acao, on_delete=models.CASCADE)
    #gestor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coordenador = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    #history = HistoricalRecords()
    status = models.ForeignKey(StatusCurso, on_delete=models.PROTECT)
    periodo_avaliativo = models.BooleanField(default=False)

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


notas=((1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5'))

class Avaliacao(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    participante = models.ForeignKey(User, on_delete=models.CASCADE)
    nota_atributo1 = models.IntegerField(choices=notas, default=None, blank=False, null=False)
    nota_atributo2 = models.IntegerField(choices=notas, default=None, blank=False, null=False)
    nota_atributo3 = models.IntegerField(choices=notas, default=None, blank=False, null=False)
    nota_atributo4 = models.IntegerField(choices=notas, default=None, blank=False, null=False)
    nota_atributo5 = models.IntegerField(choices=notas, default=None, blank=False, null=False)
    
    def __str__(self):
        return self.curso.nome_curso + ' > '+ self.participante.username
    
    class Meta:
        verbose_name_plural = "avaliações"

def user_directory_path(instance, filename):
    # O "instance" é a instância do modelo Avaliacao e "filename" é o nome do arquivo original
    # Este exemplo adiciona o nome de usuário ao caminho de destino
    return f'uploads/{instance.usuario.username}/{filename}'

class StatusValidacao(models.Model):
    nome = models.CharField(max_length=50)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name_plural = "status validações"

class Validacao_CH(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    arquivo_pdf = models.FileField(upload_to=user_directory_path)
    enviado_em = models.DateTimeField(auto_now_add=True)
    nome_curso = models.CharField(max_length=100, default='')
    ch_solicitada = models.IntegerField(blank=True, null=True)
    ch_confirmada = models.IntegerField(blank=True, null=True)
    status = models.ForeignKey(StatusValidacao, on_delete=models.DO_NOTHING, default=1)

    def __str__(self):
        return self.usuario.username

    class Meta:
        verbose_name_plural = "validações de CH"


class Certificado(models.Model):
    codigo = models.CharField(max_length=40, default='')
    cabecalho = models.CharField(max_length=100, default='')
    subcabecalho1 = models.CharField(max_length=100, default='')
    subcabecalho2 = models.CharField(max_length=100, default='')
    texto = models.TextField(max_length=4000, default='')

    def __str__(self):
        return self.codigo

    class Meta:
        verbose_name_plural = "certificados"