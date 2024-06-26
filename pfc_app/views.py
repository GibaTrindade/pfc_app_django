from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages, auth
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils import dateformat
from django.urls import reverse
import random
import string
from django.utils.encoding import force_bytes
from django.contrib.auth import update_session_auth_hash
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.template import loader
from .models import Curso, Inscricao, StatusInscricao, Avaliacao, \
                    Validacao_CH, StatusValidacao, User, Certificado,\
                    Tema, Subtema, Carreira, Modalidade, Categoria, ItemRelatorio,\
                    PlanoCurso, Trilha, Curadoria
from .forms import AvaliacaoForm, DateFilterForm, UserUpdateForm
from django.db.models import Count, Q, Sum, F, \
                                Avg, FloatField, When, BooleanField, \
                                Exists, OuterRef, Value, Subquery, Min, Max
from django.db.models.functions import Coalesce, Concat, Cast, ExtractYear
from django.contrib.postgres.aggregates import StringAgg
from django.contrib.postgres.expressions import ArraySubquery
from datetime import date, datetime
import calendar
from django.views.generic import DetailView
import os
import zipfile
from django.http import HttpResponse
from django.shortcuts import get_list_or_404
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, \
                                Spacer, Image, PageBreak, \
                                PageTemplate, SimpleDocTemplate, Table, TableStyle

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart                           
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.graphics.shapes import *
from io import BytesIO
from reportlab.lib.units import inch
from validate_docbr import CPF
from .filters import UserFilter
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import matplotlib.colors as mc
import colorsys
from matplotlib.colors import to_rgb
from pdf2docx import Converter
from PIL import Image
import shutil


MONTHS = [
    (1, "Janeiro"), (2, "Fevereiro"), (3, "Março"),
    (4, "Abril"), (5, "Maio"), (6, "Junho"),
    (7, "Julho"), (8, "Agosto"), (9, "Setembro"),
    (10, "Outubro"), (11, "Novembro"), (12, "Dezembro")
]



# Create your views here.
@login_required
def dashboard(request):
    return render(request, 'pfc_app/presentation.html')
    return render(request, 'pfc_app/dashboard.html')


def login(request):
    if request.method != 'POST':
        if request.user.is_authenticated:
            return redirect('lista_cursos')
        return render(request, 'pfc_app/login.html')

    usuario = request.POST.get('usuario')
    senha = request.POST.get('senha')

    user = auth.authenticate(username=usuario, password=senha)

    if not user:
        messages.error(request, 'Usuário ou senha inválidos!')
        return render(request, 'pfc_app/login.html')
    else:
        auth.login(request, user)
        messages.success(request, f'Oi, {user.nome.split(" ")[0].capitalize()}!')
        return redirect('home')

    return render(request, 'pfc_app/login.html')

def registrar(request):
    if request.method != 'POST':
        return render(request, 'pfc_app/registrar.html')

    nome = request.POST.get('nome')
    cpf = request.POST.get('cpf')
    username = request.POST.get('username')
    email = request.POST.get('email')
    telefone = request.POST.get('telefone')
    orgao_origem = request.POST.get('orgao_origem')

    
    # Contexto para manter os dados no formulário
    context = {
        'nome': nome,
        'cpf': cpf,
        'username': username,
        'email': email,
        'telefone': telefone,
        'orgao_origem': orgao_origem
    }
    
    if User.objects.filter(username=username).exists():
        return JsonResponse({'success': False, 'msg': 'Username já existe!'})
    if User.objects.filter(email=email).exists():
        return JsonResponse({'success': False, 'msg': 'Email já existe!'})
    if User.objects.filter(cpf=cpf).exists():
        return JsonResponse({'success': False, 'msg': 'CPF já existe!'})

    cpf_padrao = CPF()
    # Validar CPF
    if not cpf_padrao.validate(cpf):
        #messages.error(request, f'CPF digitado está errado!')
        return JsonResponse({'success': False, 'msg': 'CPF Inválido!'})
        #return render(request, 'pfc_app/registrar.html', context)

    if not re.match(r'^\d{11}$', cpf):
        return JsonResponse({'success': False, 'msg': 'Digite o CPF sem números e sem traços.'})

    send_mail('Solicitação de cadastro', 
              f'Nome:{nome}\n '
              f'CPF: {cpf}\n '
              f'Username: {username}\n '
              f'Email: {email}\n '
              f'Telefone: {telefone}\n '
              f'Órgão de origem: {orgao_origem}\n ', 
              'ncdseplag@gmail.com', 
              ['pfc.seplag@gmail.com', 'g.trindade@gmail.com'])

    
    messages.success(request, f'Solicitação enviada com sucesso. Aguarde suas credenciais!')
        
    return JsonResponse({'success': True})
    # return render(request, 'pfc_app/login.html')

def logout(request):
    auth.logout(request)
    return redirect('login')


@login_required
def update_profile(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Perfil atualizado com sucesso!')
            return redirect('update_profile')
        else:
            messages.error(request, f'Corrija os erros abaixo')
            #return redirect('update_profile')
    else:
        form = UserUpdateForm(instance=request.user)
    
    context = {
        'form': form,
        'user': request.user
    }
    return render(request, 'pfc_app/update_profile.html', context)


@login_required
def cursos(request):
  lista_cursos = Curso.objects.all()
  data_atual = date.today()
  status_inscricao=Subquery(
        Inscricao.objects.filter(
            curso=OuterRef('pk'), participante=request.user
        ).values('status__nome')[:1]
    )
  subquery = ArraySubquery(
    Inscricao.objects.filter(curso=OuterRef('pk'))
        .exclude(condicao_na_acao='DOCENTE')
        .exclude(status__nome='CANCELADA')
        .exclude(status__nome='EM FILA')
        .exclude(status__nome='PENDENTE')
        .order_by('participante__nome')
        .values('curso')
        .annotate(nomes_concatenados=StringAgg('participante__nome', delimiter=', '))
        .values('nomes_concatenados')
)
  subquery_docentes = ArraySubquery(
    Inscricao.objects.filter(curso=OuterRef('pk'))
        .exclude(condicao_na_acao='DISCENTE')
        .order_by('inscrito_em')
        .annotate(nome_completo=Concat('participante__first_name', Value(' '), 'participante__last_name'))
        .values('curso')
        .annotate(nomes_concatenados=StringAgg('nome_completo', delimiter=', '))
        .values('nomes_concatenados')
)
  
  cursos_com_inscricoes = Curso.objects.annotate(
        num_inscricoes=Count('inscricao', 
                             filter=~Q(inscricao__condicao_na_acao='DOCENTE') & 
                             ~Q(inscricao__status__nome='CANCELADA') &
                             ~Q(inscricao__status__nome='EM FILA') & 
                             ~Q(inscricao__status__nome='PENDENTE') 
                             ),
        usuario_inscrito=Exists(
           Inscricao.objects.filter(participante=request.user, curso=OuterRef('pk'))
                                ),
        lista_inscritos = subquery,
        lista_docentes = subquery_docentes,
        status_inscricao = status_inscricao
        
    ).order_by('data_inicio').all().filter(data_inicio__gte=data_atual).exclude(status__nome = 'CANCELADO')
  #template = loader.get_template('base.html')
  #cursos_nao_inscrito = cursos_com_inscricoes.exclude(inscricao__participante=request.user)
  #lista_inscritos=Inscricao.objects.filter(curso=OuterRef('pk'))
                        # .exclude(condicao_na_acao='DOCENTE')
                        # .exclude(status__nome='CANCELADA')
                        # .exclude(status__nome='EM FILA')
                        # .annotate(nome_com_virgula=Concat('participante__nome', Value(', ')))
                        # .values('nome_com_virgula')
                        # .order_by('participante__nome')
                        # .distinct('participante__nome')
                        # .values_list('participante__nome', flat=True)        

  context = {
    'cursos': cursos_com_inscricoes,
  }
  #print(context['cursos'][1].inscricao_set.count())
  return render(request, 'pfc_app/lista_cursos.html' ,context)

@login_required
def usuarios_sem_ch(request):
    inscricoes = Inscricao.objects.filter(
            participante=OuterRef('pk'),
            concluido=True,
            curso__status__nome='FINALIZADO'
        ).values('participante').annotate(
            total_ch=Sum('ch_valida')
        ).values('total_ch')[:1]
    
    validacoes = Validacao_CH.objects.filter(
            usuario=OuterRef('pk'),
            status__nome='DEFERIDA'
        ).values('usuario').annotate(
            total_ch=Sum('ch_confirmada')
        ).values('total_ch')[:1]
    
    # Filter users with a total load less than 60
    users = User.objects.annotate(
        total_ch_inscricao=Coalesce(Subquery(inscricoes), 0),
        total_ch_validacao=Coalesce(Subquery(validacoes), 0)
    ).annotate(
        total_ch=F('total_ch_inscricao') + F('total_ch_validacao')
    ).filter(grupo_ocupacional='GGOV').order_by('nome')

    # Calculate remaining load needed to reach 60
    users = users.annotate(ch_faltante=60 - F('total_ch')).filter(
                            total_ch__lt=60)

    # Select the fields you need for the table
    users = users.values('nome', 'email', 'lotacao', 'lotacao_especifica', 'total_ch', 'ch_faltante')

    filtro = UserFilter(request.GET, queryset=users)
    users = filtro.qs
    # lotacao_values = User.objects.values_list('lotacao', flat=True).distinct().order_by('lotacao')
    # lotacao_especifica = User.objects.values_list('lotacao_especifica', flat=True).distinct().order_by('lotacao_especifica')
    
    context = {
        'usuarios_sem_ch': users,
        'filtro': filtro,
    }
    return render(request, 'pfc_app/usuarios_sem_ch.html', context )

@login_required
def carga_horaria(request):
  form = DateFilterForm(request.GET)
  inscricoes_do_usuario = Inscricao.objects.filter(
     ~Q(status__nome='CANCELADA'),
     ~Q(status__nome='EM FILA'),
     Q(curso__status__nome='FINALIZADO'),
     Q(concluido=True),
     participante=request.user
     
     )
  try:
    status_validacao_deferida = StatusValidacao.objects.get(nome='DEFERIDA')
    status_validacao_deferida_parc = StatusValidacao.objects.get(nome='DEFERIDA PARCIALMENTE')
  except:
    novo_status_deferida = StatusValidacao(nome="DEFERIDA")
    novo_status_deferida_parc = StatusValidacao(nome="DEFERIDA PARCIALMENTE")
    novo_status_deferida.save()
    novo_status_deferida_parc.save()
    status_validacao_deferida = StatusValidacao.objects.get(nome='DEFERIDA')
    status_validacao_deferida_parc = StatusValidacao.objects.get(nome='DEFERIDA PARCIALMENTE')

  validacoes = Validacao_CH.objects.filter(usuario=request.user, 
                                           status__in=[status_validacao_deferida, 
                                                       status_validacao_deferida_parc])
  
  ## Calculo para verificar se o usuario ja está inscrito em um dado curso

  data_hoje = datetime.now()
  
  # Verificar se a data atual é anterior a "01/03" do ano atual
  if data_hoje.month < 3:
       ano_atual = data_hoje.year - 1
  else:
       ano_atual = data_hoje.year
  
  data_hoje = data_hoje.strftime("%Y-%m-%d")

  if form.is_valid():
        data_inicio = form.cleaned_data['data_inicio']
        data_fim = form.cleaned_data['data_fim']
        
        if data_inicio:
            inscricoes_do_usuario = inscricoes_do_usuario.filter(curso__data_termino__gte=data_inicio)
            validacoes = validacoes.filter(data_termino_curso__gte=data_inicio)
        else:# Se data_inicio não estiver preenchida filtra com a data 01/03/{ano_atual}
            inscricoes_do_usuario = inscricoes_do_usuario.filter(curso__data_termino__gte=f'{ano_atual}-03-01')
            validacoes = validacoes.filter(data_termino_curso__gte=f'{ano_atual}-03-01')
        if data_fim:
            inscricoes_do_usuario = inscricoes_do_usuario.filter(curso__data_termino__lte=data_fim)
            validacoes = validacoes.filter(data_termino_curso__lte=data_fim)
        else:
            inscricoes_do_usuario = inscricoes_do_usuario.filter(curso__data_termino__lte=data_hoje)
            validacoes = validacoes.filter(data_termino_curso__lte=data_hoje)
  
  cursos_feitos_pfc = inscricoes_do_usuario
  # Distinc para que so conte 1 curso por periodo
  inscricoes_do_usuario = inscricoes_do_usuario.values('curso__nome_curso').distinct()
  # Calcula a soma da carga horária das inscrições do usuário
  carga_horaria_pfc = inscricoes_do_usuario.aggregate(Sum('ch_valida'))['ch_valida__sum'] or 0
  validacoes_ch = validacoes.aggregate(Sum('ch_confirmada'))['ch_confirmada__sum'] or 0
  carga_horaria_total = carga_horaria_pfc + validacoes_ch


  context = {
      'inscricoes_pfc': cursos_feitos_pfc,
      'validacoes_externas': validacoes,
      'carga_horaria_pfc': carga_horaria_pfc,
      'carga_horaria_validada': validacoes_ch,
      'carga_horaria_total': carga_horaria_total,
      'form': form,
      'values': request.GET if request.GET else {'data_inicio': f'{ano_atual}-03-01', 'data_fim': data_hoje},
  }

  return render(request, 'pfc_app/carga_horaria.html' ,context)


@login_required
def inscricoes(request):
    #inscricoes_do_usuario = Inscricao.objects.filter(participante=request.user)

    inscricoes_do_usuario = Inscricao.objects.annotate(
        curso_avaliado=Exists(
           Avaliacao.objects.filter(participante=request.user, curso=OuterRef('curso'))
            
        )
    ).filter(participante=request.user)
    
    context = {
        'inscricoes': inscricoes_do_usuario,
    }
    
    return render(request, 'pfc_app/inscricoes.html', context)


class CursoDetailView(LoginRequiredMixin, DetailView):
   # model_detail.html
   model = Curso

   def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Recupere o usuário docente relacionado ao curso atual
        curso = self.get_object()
        usuario_docente = None

        lotado = self.kwargs.get('lotado', None)
        if lotado:
            lotado_bool = lotado.lower() == 'true'
            context['lotado'] = lotado_bool
        else:
            context['lotado'] = False

        # Verifique se há uma inscrição do tipo 'DOCENTE' relacionada a este curso
        inscricoes_docentes = Inscricao.objects.filter(curso=curso, condicao_na_acao='DOCENTE')

        usuarios_docentes = [inscricao.participante for inscricao in inscricoes_docentes]
        usuario_inscrito = Inscricao.objects.filter(curso=curso, participante=self.request.user).exists()
    
        # Adicione o usuário docente ao contexto
        context['usuarios_docentes'] = usuarios_docentes
        context['usuario_inscrito'] = usuario_inscrito

        return context


@login_required
def cancelar_inscricao(request, inscricao_id):
    try:
      inscricao = Inscricao.objects.get(pk=inscricao_id)
    except:
       messages.error(request, 'Inscrição não existe!')
       return render(request, 'pfc_app/inscricoes.html')
    
    if request.user == inscricao.participante:
       status_cancelado = StatusInscricao.objects.get(nome='CANCELADA')
       inscricao.status = status_cancelado
       inscricao.save()
       messages.success(request, 'Inscrição cancelada')
       return redirect('inscricoes')
    else:
       messages.error(request, 'Você não está inscrito nesse curso!')
       return render(request, 'pfc_app/inscricoes.html')
    
    #return render(request, 'pfc_app/inscricoes.html', context)

@login_required
def inscrever(request, curso_id):
    curso = Curso.objects.get(pk=curso_id)
    status_id_aprovada = StatusInscricao.objects.get(nome='APROVADA')
    status_id_pendente = StatusInscricao.objects.get(nome='PENDENTE')
    status_id_fila = StatusInscricao.objects.get(nome='EM FILA')
    
    # Conta quantas inscrições válidas há nesse curso
    inscricoes_validas = Inscricao.objects.filter(
        ~Q(status__nome='CANCELADA'),
        ~Q(status__nome='EM FILA'),
        ~Q(status__nome='PENDENTE'),
        ~Q(condicao_na_acao='DOCENTE'),
        curso=curso
    ).count()
    
    if curso.status.nome != 'A INICIAR' :
        messages.error(request, 'Curso não disponível!')
        return redirect('lista_cursos')

    # Compara com o número de vagas
    # Caso seja maior ou igual redireciona
    if inscricoes_validas >= curso.vagas:
        print(inscricoes_validas)
        # O curso está lotado
        try:
          inscricao, criada = Inscricao.objects.get_or_create(participante=request.user, curso=curso, status=status_id_fila)
          if criada:
            messages.success(request, 'Inscrição adicionada à fila')
            return render(request, 'pfc_app/curso_lotado.html')
          else:
            messages.error(request, 'Você já está inscrito')
            return redirect('lista_cursos')
        except IntegrityError:
          print("INTEGRITY ERROR 1")
          messages.error(request, 'Você já está inscrito')
          return redirect('detail_curso', pk=curso_id)
    
    try:
      if curso.eh_evento or not request.user.is_externo:
          inscricao, criada = Inscricao.objects.get_or_create(participante=request.user, curso=curso, status=status_id_aprovada)
      else:
          inscricao, criada = Inscricao.objects.get_or_create(participante=request.user, curso=curso, status=status_id_pendente)

      if criada:
          # A inscrição foi criada com sucesso
          messages.success(request, 'Inscrição realizada!')
          #send_mail('Teste', f'Follow this link to reset your password: ihaa', 'g.trindade@gmail.com', [request.user.email])
          return redirect('lista_cursos')
      else:
          # A inscrição já existe
          messages.error(request, 'Você já está inscrito')
          return redirect('lista_cursos')
    except IntegrityError:
       print("INTEGRITY ERROR")
       messages.error(request, 'Você já está inscrito')
       return redirect('detail_curso', pk=curso_id)
    
def sucesso_inscricao(request):
    return render(request, 'pfc_app/sucesso_inscricao.html')

def inscricao_existente(request):
    return render(request, 'pfc_app/inscricao_existente.html')

@login_required
def avaliacao(request, curso_id):
    # Checa se o curso existe
    temas = Tema.objects.all()
    try:
      curso = Curso.objects.get(pk=curso_id)
    except:
       messages.error(request, f"Curso não encontrado!")
       return redirect('lista_cursos')
    
    # Se existe, checa se o status está como "FINALIZADO"
    if curso.status.nome != "FINALIZADO":
       messages.error(request, f"Curso não finalizado!")
       return redirect('lista_cursos')
    
    try:
       inscricao = Inscricao.objects.get(participante=request.user, curso=curso)
    except:
       messages.error(request, f"Você não está inscrito neste curso!")
       return redirect('lista_cursos')
    
    if request.method == 'POST':
        #form = AvaliacaoForm(request.POST)
        #if form.is_valid():
            # Faça o que for necessário com os dados da avaliação, como salvá-los no banco de dados
        usuario = request.user
        ja_avaliado=Avaliacao.objects.filter(participante=usuario, curso=curso)
        
        if ja_avaliado:
            messages.error(request, f"Avaliação já realizada!")
            return redirect('inscricoes')
        
        subtemas = Subtema.objects.all()
        for subtema in subtemas:
            #print("id: "+subtema.id)
            avaliacao = Avaliacao(curso=curso, participante=request.user,
                                    subtema=subtema, nota=request.POST.get(subtema.nome))
            avaliacao.save()

        #avaliacao = form.save(commit=False)
        #avaliacao.participante = usuario
        
        #avaliacao.curso = curso
        #form.save()
        #avaliacao.save()
        # Redirecione para uma página de sucesso ou outra ação apropriada
        messages.success(request, 'Avaliação Realizada!')
        return redirect('inscricoes')
    #messages.error(request, form.errors)
        #return render(request, 'sucesso.html')
    #else:
        #messages.error(request, 'Nenhum item pode ficar em branco')
        #return render(request, 'pfc_app/avaliacao.html', {'form': form})

    
        
        

        #form = AvaliacaoForm()

    return render(request, 'pfc_app/avaliacao.html', {'temas': temas, 'curso':curso})


def validar_ch(request):
    if request.method == 'POST':
        status_validacao = StatusValidacao.objects.get(nome="EM ANÁLISE")
        arquivo_pdf = request.FILES['arquivo_pdf']
        nome_curso = request.POST['nome_curso']
        ch_solicitada = request.POST['ch_solicitada']
        data_inicio = request.POST['data_inicio']
        data_termino = request.POST['data_termino']
        instituicao_promotora = request.POST['instituicao_promotora']
        ementa = request.POST['ementa']
        condicao_na_acao = request.POST['condicao_acao']
        carreira_id = request.POST['carreira']
        conhecimento_previo = request.POST['conhecimento_previo']
        conhecimento_posterior = request.POST['conhecimento_posterior']
        voce_indicaria = request.POST['voce_indicaria']
        try:
            agenda_pfc_check = request.POST['agenda_pfc']
            agenda_pfc = True
        except:
            agenda_pfc = False
      
        try:
           ch_solicitada = int(ch_solicitada)
        except:
            messages.error(request, 'O campo carga horária precisa ser númerico!')
            return redirect('validar_ch')
        try:
            carreira = Carreira.objects.get(pk=carreira_id)
        except:
            messages.error(request, 'Carreira não encontrada')
            return redirect('validar_ch')
        
        avaliacao = Validacao_CH(usuario=request.user, arquivo_pdf=arquivo_pdf, 
                                 nome_curso=nome_curso, ch_solicitada=ch_solicitada, 
                                 data_termino_curso=data_termino, data_inicio_curso = data_inicio,
                                 instituicao_promotora=instituicao_promotora, ementa=ementa, 
                                 agenda_pfc=agenda_pfc, status=status_validacao,
                                 condicao_na_acao=condicao_na_acao, carreira=carreira,
                                 conhecimento_previo=conhecimento_previo, 
                                 conhecimento_posterior=conhecimento_posterior,
                                 voce_indicaria=voce_indicaria)
        avaliacao.save()
        # Redirecionar ou fazer algo após o envio bem-sucedido
        messages.success(request, 'Arquivo enviado com sucesso!')
        return redirect('validar_ch')

    validacoes_user = Validacao_CH.objects.filter(usuario=request.user)
    condica_acao = Validacao_CH.CONDICAO_ACAO_CHOICES
    carreiras = Carreira.objects.all()
    modalidades = Modalidade.objects.all()
    categorias = Categoria.objects.all()


    return render(request, 'pfc_app/validar_ch.html', 
                  {'validacoes': validacoes_user, 
                   'opcoes': condica_acao, 
                   'carreiras': carreiras,
                   'modalidades': modalidades,
                   'categorias': categorias
                   })


def download_all_pdfs(request):
    return render(request, 'pfc_app/download_all_pdfs.html')


def generate_all_pdfs(request, curso_id, unico=0):
    try:
      curso = Curso.objects.get(pk=curso_id)
    except:
       messages.error(request, f"Curso não encontrado!")
       return redirect('lista_cursos')
    

    certificado = Certificado.objects.get(codigo='conclusao')
    #texto_certificado = certificado.texto
    if unico:
        users=[]
        users.append(request.user)
    else:
        users = curso.participantes.all()

    #output_folder = "pdf_output"  # Pasta onde os PDFs temporários serão salvos
    zip_filename = "all_pdfs.zip"

    # Crie a pasta de saída se ela não existir
    #if not os.path.exists(output_folder):
    #    os.makedirs(output_folder)

    # Crie o arquivo ZIP
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for user in users:
            # Verifica o status da incrição do usuário, 
            # se não estiver concluída pula esse usuário.
            try:
                inscricao = Inscricao.objects.get(participante=user, curso=curso, concluido=True)
            except:
                continue
            
            pdf_filename = generate_single_pdf(request, inscricao.id)
    #         texto_certificado = certificado.texto
    #         data_inicio = str(curso.data_inicio)
    #         data_termino = str(curso.data_termino)
    #         # Converte a string para um objeto datetime
    #         data_inicio_formatada = datetime.strptime(data_inicio, "%Y-%m-%d")
    #         data_termino_formatada = datetime.strptime(data_termino, "%Y-%m-%d")
    #         # Formata a data no formato "DD/MM/YYYY"
    #         data_inicio_formatada_str = data_inicio_formatada.strftime("%d/%m/%Y")
    #         data_termino_formatada_str = data_termino_formatada.strftime("%d/%m/%Y")

    #         try:
                
    #             cpf = CPF()
    #             # Validar CPF
    #             if not cpf.validate(user.cpf):
    #                 messages.error(request, f'CPF de {user.nome} está errado! ({user.cpf})')
    #                 return redirect('lista_cursos')
                
    #             # Formata o CPF no formato "000.000.000-00"
    #             cpf_formatado = f"{user.cpf[:3]}.{user.cpf[3:6]}.{user.cpf[6:9]}-{user.cpf[9:]}"
    #         except:
    #             messages.error(request, f'CPF de {user.nome} está com número de caracteres errado!')
    #             return redirect('lista_cursos')

    #         tag_mapping = {
    #             "[nome_completo]": user.nome,
    #             "[cpf]": cpf_formatado,
    #             "[nome_curso]": curso.nome_curso,
    #             "[data_inicio]": data_inicio_formatada_str,
    #             "[data_termino]": data_termino_formatada_str,
    #             "[curso_carga_horaria]": curso.ch_curso,
    #         }
    
    # # Substitua as tags pelo valor correspondente no texto
    #         for tag, value in tag_mapping.items():
    #             texto_certificado = texto_certificado.replace(tag, str(value))

    #         texto_customizado = texto_certificado
    #         pdf_filename = os.path.join(output_folder, f"{user.username}-{curso.nome_curso}.pdf")
    #         # Crie o PDF usando ReportLab

    #         style_body = ParagraphStyle('body',
    #                                     fontName = 'Helvetica',
    #                                     fontSize=13,
    #                                     leading=17,
    #                                     alignment=TA_JUSTIFY)
    #         style_title = ParagraphStyle('title',
    #                                     fontName = 'Helvetica',
    #                                     fontSize=36)
    #         style_subtitle = ParagraphStyle('subtitle',
    #                                     fontName = 'Helvetica',
    #                                     fontSize=24)
            
    #         width, height = landscape(A4)
    #         c = canvas.Canvas(pdf_filename, pagesize=landscape(A4))
    #         p_title=Paragraph(certificado.cabecalho, style_title)
    #         p_subtitle=Paragraph(certificado.subcabecalho1, style_subtitle)
    #         p_subtitle2=Paragraph(certificado.subcabecalho2, style_subtitle)
    #         p1=Paragraph(texto_customizado, style_body)
    #          # Caminho relativo para a imagem dentro do diretório 'static'
    #         imagem_relative_path = 'Certificado-FUNDO.png'
    #         assinatura_relative_path = 'assinatura.jpg'
    #         igpe_relative_path = 'Igpe.jpg'
    #         egape_relative_path = 'Egape.jpg'
    #         pfc_relative_path = 'PFC1.png'
    #         seplag_relative_path = 'seplag-transp-horizontal.png'


    #         # Construa o caminho absoluto usando 'settings.STATIC_ROOT'
    #         imagem_path = os.path.join(settings.MEDIA_ROOT, imagem_relative_path)
    #         assinatura_path = os.path.join(settings.MEDIA_ROOT, assinatura_relative_path)
    #         igpe_path = os.path.join(settings.MEDIA_ROOT, igpe_relative_path)
    #         egape_path = os.path.join(settings.MEDIA_ROOT, egape_relative_path)
    #         pfc_path = os.path.join(settings.MEDIA_ROOT, pfc_relative_path)
    #         seplag_path = os.path.join(settings.MEDIA_ROOT, seplag_relative_path)




    #         # Desenhe a imagem como fundo
    #         c.drawImage(imagem_path, 230, 0, width=width, height=height, preserveAspectRatio=True, mask='auto')
    #         c.drawImage(assinatura_path, 130, 100, width=196, height=63, preserveAspectRatio=True, mask='auto')
    #         c.drawImage(igpe_path, width-850, 20, width=196, height=63, preserveAspectRatio=True, mask='auto')
    #         c.drawImage(egape_path, width-650, 20, width=196, height=63, preserveAspectRatio=True, mask='auto')
    #         c.drawImage(pfc_path, width-450, 20, width=196, height=63, preserveAspectRatio=True, mask='auto')
    #         c.drawImage(seplag_path, width-250, 20, width=196, height=63, preserveAspectRatio=True, mask='auto')
    #         p_title.wrapOn(c, 500, 100)
    #         p_title.drawOn(c, width-800, height-100)
    #         p_subtitle.wrapOn(c, 500, 100)
    #         p_subtitle.drawOn(c, width-800, height-165)
    #         p_subtitle2.wrapOn(c, 500, 100)
    #         p_subtitle2.drawOn(c, width-800, height-190)
    #         p1.wrapOn(c, 500, 100)
    #         p1.drawOn(c, width-800, height-300)
    #         c.save()
           
            
            zipf.write(pdf_filename, os.path.basename(pdf_filename))
            os.remove(pdf_filename)

    # Configure a resposta HTTP para o arquivo ZIP
    response = HttpResponse(content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'

    # Abra o arquivo ZIP e envie seu conteúdo como resposta
    with open(zip_filename, 'rb') as zip_file:
        response.write(zip_file.read())

    os.remove(zip_filename)

    return response


def generate_single_pdf(request, inscricao_id):
    try:
      inscricao = Inscricao.objects.get(pk=inscricao_id)
    except:
       messages.error(request, f"Inscrição não encontrada!")
       return redirect('lista_cursos')
    
    certificado = Certificado.objects.get(codigo='conclusao')
    #texto_certificado = certificado.texto
    user = inscricao.participante
    curso = inscricao.curso

    output_folder = "pdf_output"  # Pasta onde os PDFs temporários serão salvos
    #zip_filename = "all_pdfs.zip"

    # Crie a pasta de saída se ela não existir
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Crie o arquivo ZIP
    #with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        #for user in users:
    texto_certificado = certificado.texto
    data_inicio = str(curso.data_inicio)
    data_termino = str(curso.data_termino)
    # Converte a string para um objeto datetime
    data_inicio_formatada = datetime.strptime(data_inicio, "%Y-%m-%d")
    data_termino_formatada = datetime.strptime(data_termino, "%Y-%m-%d")
    # Formata a data no formato "DD/MM/YYYY"
    data_inicio_formatada_str = data_inicio_formatada.strftime("%d/%m/%Y")
    data_termino_formatada_str = data_termino_formatada.strftime("%d/%m/%Y")

    try:
        
        cpf = CPF()
        # Validar CPF
        if not cpf.validate(user.cpf):
            messages.error(request, f'CPF de {user.nome} está errado! ({user.cpf})')
            return redirect('lista_cursos')
        
        # Formata o CPF no formato "000.000.000-00"
        cpf_formatado = f"{user.cpf[:3]}.{user.cpf[3:6]}.{user.cpf[6:9]}-{user.cpf[9:]}"
    except:
        messages.error(request, f'CPF de {user.nome} está com número de caracteres errado!')
        return redirect('lista_cursos')

    tag_mapping = {
        "[nome_completo]": user.nome,
        "[cpf]": cpf_formatado,
        "[nome_curso]": curso.nome_curso,
        "[data_inicio]": data_inicio_formatada_str,
        "[data_termino]": data_termino_formatada_str,
        "[curso_carga_horaria]": curso.ch_curso,
        "[condicao_na_acao]": str(inscricao.condicao_na_acao).lower(),
    }

# Substitua as tags pelo valor correspondente no texto
    for tag, value in tag_mapping.items():
        texto_certificado = texto_certificado.replace(tag, str(value))

    texto_customizado = texto_certificado
    pdf_filename = os.path.join(output_folder, f"{user.username}-{curso.nome_curso}.pdf")
    # Crie o PDF usando ReportLab

    pdf_filename = os.path.join(output_folder, f"{user.username}-{curso.nome_curso}.pdf")
        # Crie o PDF usando ReportLab

    style_body = ParagraphStyle('body',
                                fontName = 'Helvetica',
                                fontSize=13,
                                leading=17,
                                alignment=TA_JUSTIFY)
    style_title = ParagraphStyle('title',
                                fontName = 'Helvetica',
                                fontSize=36)
    style_subtitle = ParagraphStyle('subtitle',
                                fontName = 'Helvetica',
                                fontSize=24)
    
    width, height = landscape(A4)
    c = canvas.Canvas(pdf_filename, pagesize=landscape(A4))
    p_title=Paragraph(certificado.cabecalho, style_title)
    p_subtitle=Paragraph(certificado.subcabecalho1, style_subtitle)
    p_subtitle2=Paragraph(certificado.subcabecalho2, style_subtitle)
    p1=Paragraph(texto_customizado, style_body)
        # Caminho relativo para a imagem dentro do diretório 'static'
    imagem_relative_path = 'Certificado-FUNDO.png'
    assinatura_relative_path = 'assinatura.jpg'
    igpe_relative_path = 'igpe.png'
    egape_relative_path = 'Egape.png'
    pfc_relative_path = 'retangulartransp.png'
    seplag_relative_path = 'seplagtransparente.png'

    # Construa o caminho absoluto usando 'settings.STATIC_ROOT'
    imagem_path = os.path.join(settings.MEDIA_ROOT, imagem_relative_path)
    assinatura_path = os.path.join(settings.MEDIA_ROOT, assinatura_relative_path)
    igpe_path = os.path.join(settings.MEDIA_ROOT, igpe_relative_path)
    egape_path = os.path.join(settings.MEDIA_ROOT, egape_relative_path)
    pfc_path = os.path.join(settings.MEDIA_ROOT, pfc_relative_path)
    seplag_path = os.path.join(settings.MEDIA_ROOT, seplag_relative_path)




    # Desenhe a imagem como fundo
    c.drawImage(imagem_path, 230, 0, width=width, height=height, preserveAspectRatio=True, mask='auto')
    c.drawImage(assinatura_path, 130, 100, width=196, height=50, preserveAspectRatio=True, mask='auto')
    c.drawImage(igpe_path, 50, 20, width=63, height=50, preserveAspectRatio=True, mask='auto')
    c.drawImage(seplag_path, 63+50+30, 20, width=196, height=50, preserveAspectRatio=True, mask='auto')
    c.drawImage(pfc_path, 63+30+50+196, 20, width=196, height=50, preserveAspectRatio=True, mask='auto')
    c.drawImage(egape_path, 63+50+30+196+196, 20, width=196, height=50, preserveAspectRatio=True, mask='auto')
    
    p_title.wrapOn(c, 500, 100)
    p_title.drawOn(c, width-800, height-100)
    p_subtitle.wrapOn(c, 500, 100)
    p_subtitle.drawOn(c, width-800, height-165)
    p_subtitle2.wrapOn(c, 500, 100)
    p_subtitle2.drawOn(c, width-800, height-190)
    p1.wrapOn(c, 500, 100)
    p1.drawOn(c, width-800, height-300)
    c.setTitle("Certificado PFC")
    c.save()
        
        #zipf.write(pdf_filename, os.path.basename(pdf_filename))
        #os.remove(pdf_filename)

    # Configure a resposta HTTP para o arquivo ZIP
    #response = HttpResponse(content_type='application/zip')
    #response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'

    # Abra o arquivo ZIP e envie seu conteúdo como resposta
    #with open(zip_filename, 'rb') as zip_file:
    #    response.write(zip_file.read())

    #os.remove(zip_filename)

    return pdf_filename



def generate_all_reconhecimento(request, validacao_id):
    try:
      validacao = Validacao_CH.objects.get(pk=validacao_id)
    except:
       messages.error(request, f"Validação não encontrada!")
       return redirect('lista_cursos')
    
    try:
        requerimento = validacao.requerimento_ch.do_requerimento
        fundamentacao = validacao.requerimento_ch.da_fundamentacao
        conclusao = validacao.requerimento_ch.da_conclusao
        local_data = validacao.requerimento_ch.local_data
        rodape = validacao.requerimento_ch.rodape
        rodape2 = validacao.requerimento_ch.rodape2
        
        #responsavel = validacao.responsavel_analise
    except:
        messages.error(request, f'Erro ao gerar reconhecimento')
        # Redireciona para a página de lista do modelo Validacao no app pfc_app
        return redirect(reverse('admin:pfc_app_validacao_ch_changelist'))

    #texto_certificado = certificado.texto
    user = validacao.usuario

    output_folder = "req_output"  # Pasta onde os PDFs temporários serão salvos
    zip_filename = "requerimento_ch.zip"

    # Crie a pasta de saída se ela não existir
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Crie o arquivo ZIP
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:

        try:
            cpf = CPF()
            # Validar CPF
            if not cpf.validate(user.cpf):
                messages.error(request, f'CPF de {user.nome} está errado! ({user.cpf})')
                return redirect('lista_cursos')
            
            # Formata o CPF no formato "000.000.000-00"
            cpf_formatado = f"{user.cpf[:3]}.{user.cpf[3:6]}.{user.cpf[6:9]}-{user.cpf[9:]}"
        except:
            messages.error(request, f'CPF de {user.nome} está com número de caracteres errado!')
            return redirect('lista_cursos')

        competencias = [competencia.nome for competencia in validacao.competencia.all()]
        if competencias:  # Verifica se a lista não está vazia
            # Caso haja mais de uma competência, substitui a última vírgula por " e "
            texto_competencia = ", ".join(competencias[:-1]) + " e " + competencias[-1] if len(competencias) > 1 else competencias[0]
        else:
            texto_competencia = ""


        tag_mapping = {
            "[nome_completo]": validacao.usuario.nome,
            "[cpf]": cpf_formatado,
            "[origem]": user.origem,
            "[data_envio]": validacao.enviado_em.strftime("%d/%m/%Y"),
            "[lotacao]": user.lotacao,
            "[nome_curso]": validacao.nome_curso,
            "[instituicao_promotora]": validacao.instituicao_promotora,
            "[data_inicio]": validacao.data_inicio_curso.strftime("%d/%m/%Y"),
            "[data_termino]": validacao.data_termino_curso.strftime("%d/%m/%Y"),
            "[ch_valida]": validacao.ch_confirmada,
            "[ch_solicitada]": validacao.ch_solicitada,
            "[data_analise]": dateformat.format(datetime.now(), 'd \d\e F \d\e Y'),
            "[responsavel_analise]": validacao.responsavel_analise,
            "[competencias]": texto_competencia
        }

# Substitua as tags pelo valor correspondente no texto
        for tag, value in tag_mapping.items():
            requerimento = requerimento.replace(tag, str(value))
            fundamentacao = fundamentacao.replace(tag, str(value))
            conclusao = conclusao.replace(tag, str(value))
            local_data = local_data.replace(tag, str(value))
            rodape = rodape.replace(tag, str(value))


        requerimento_custom = requerimento
        fundamentacao_custom = fundamentacao
        conclusao_custom = conclusao
        rodape_custom = rodape
        local_data_custom = local_data
        rodape2_custom = rodape2
        pdf_filename = os.path.join(output_folder, f"{user.username}-requerimento.pdf")
        # Crie o PDF usando ReportLab

        style_body = ParagraphStyle('body',
                                    fontName = 'Helvetica',
                                    fontSize=12,
                                    leading=17,
                                    alignment=TA_JUSTIFY)
        style_rodape = ParagraphStyle('rodape',
                                    fontName = 'Helvetica',
                                    fontSize=12,
                                    leading=17,
                                    alignment=TA_CENTER)
        style_title = ParagraphStyle('title',
                                    fontName = 'Helvetica',
                                    fontSize=16,
                                    alignment=TA_CENTER)
        style_subtitle = ParagraphStyle('subtitle',
                                    fontName = 'Helvetica',
                                    fontSize=14)
        style_numero = ParagraphStyle('numero',
                                    fontName = 'Helvetica',
                                    fontSize=12,
                                    leading=17,
                                    alignment=TA_RIGHT)
        
        width, height = A4
        print(width)
        print(height)
        numero_doc = 'N° ' + str(validacao_id)+'/'+str(validacao.analisado_em.year)
        c = canvas.Canvas(pdf_filename, pagesize=A4)
        p_title=Paragraph("ANÁLISE PARA RECONHECIMENTO DE CARGA HORÁRIA", style_title)
        p_numero = Paragraph(numero_doc, style_numero)
        p_subtitle=Paragraph("I - DO REQUERIMENTO", style_subtitle)
        p_subtitle_f=Paragraph("II - DA FUNDAMENTAÇÃO", style_subtitle)
        p_subtitle_c=Paragraph("III - DA CONCLUSÃO", style_subtitle)
        #p_subtitle2=Paragraph(certificado.subcabecalho2, style_subtitle)
        p1=Paragraph(requerimento_custom, style_body)
        p2=Paragraph(fundamentacao_custom, style_body)
        p3=Paragraph(conclusao_custom, style_body)
        p4=Paragraph(local_data_custom, style_rodape)
        p5=Paragraph(rodape_custom, style_rodape)
        p6=Paragraph(rodape2_custom, style_rodape)
        
            # Caminho relativo para a imagem dentro do diretório 'static'
        
        assinatura_relative_path = 'assinatura.jpg'
        igpe_relative_path = 'igpe.png'
        egape_relative_path = 'Egape.jpg'
        pfc_relative_path = 'retangulartransp.png'
        seplag_relative_path = 'seplag-transp-horizontal.png'


        # Construa o caminho absoluto usando 'settings.STATIC_ROOT'
       
        #assinatura_path = os.path.join(settings.MEDIA_ROOT, assinatura_relative_path)
        igpe_path = os.path.join(settings.MEDIA_ROOT, igpe_relative_path)
        egape_path = os.path.join(settings.MEDIA_ROOT, egape_relative_path)
        pfc_path = os.path.join(settings.MEDIA_ROOT, pfc_relative_path)
        seplag_path = os.path.join(settings.MEDIA_ROOT, seplag_relative_path)




        # Desenhe a imagem como fundo
        
        #c.drawImage(assinatura_path, 200, 80, width=196, height=63, preserveAspectRatio=True, mask='auto')
        c.drawImage(igpe_path, 32 + 20, height-35, width=32, height=32, preserveAspectRatio=True, mask='auto')
        #c.drawImage(egape_path, width-650, 20, width=196, height=63, preserveAspectRatio=True, mask='auto')
        c.drawImage(pfc_path, width-100, height-35, width=98, height=32, preserveAspectRatio=True, mask='auto')
        #c.drawImage(seplag_path, width-250, 20, width=196, height=63, preserveAspectRatio=True, mask='auto')
        off_set = height
        espaco_entre_paragrafos = 35

        # REQUERIMENTO
        off_set = off_set - 120
        p_subtitle.wrapOn(c, 300, 100)
        p_subtitle.drawOn(c, width-550, off_set)
         
        p1.wrapOn(c, 500, 400)
        off_set = off_set - 30 - p1.height
        p1.drawOn(c, width-550, off_set)
        
        # FUNDAMENTAÇÃO
        p_subtitle_f.wrapOn(c, 300, 100)
        off_set = off_set - p_subtitle_f.height - espaco_entre_paragrafos
        p_subtitle_f.drawOn(c, width-550, off_set)
        p2.wrapOn(c, 500, 100)
        off_set = off_set - 30 - p2.height
        p2.drawOn(c, width-550, off_set)
        
        # CONCLUSÃO
        p_subtitle_c.wrapOn(c, 300, 100)
        off_set = off_set - p_subtitle_c.height - espaco_entre_paragrafos
        p_subtitle_c.drawOn(c, width-550, off_set)
        p3.wrapOn(c, 500, 100)
        off_set = off_set - 30 - p3.height
        p3.drawOn(c, width-550, off_set)
        
        # DATA
        p4.wrapOn(c, 500, 100)
        meio = (width/2)-(p4.width/2)
        off_set = off_set - p4.height - espaco_entre_paragrafos
        p4.drawOn(c, meio, off_set)
        
        # RODAPÉ
        p5.wrapOn(c, 500, 100)
        meio = (width/2)-(p5.width/2)
        off_set = off_set - p4.height - espaco_entre_paragrafos
        p5.drawOn(c, meio, off_set)

        # RODAPÉ 2
        p6.wrapOn(c, 500, 100)
        meio = (width/2)-(p5.width/2)
        off_set = off_set - p4.height - 20
        p6.drawOn(c, meio, off_set)

        p_title.wrapOn(c, 500, 100)
        meio = (width/2)-(p_title.width/2)
        p_title.drawOn(c, meio, height-50)

        p_numero.wrapOn(c, 500, 30)
        right = (width/2) - (p_numero.width/2)
        p_numero.drawOn(c, width-550, height-100)
        
        c.setTitle("Requerimento de Carga Horária")
        
        
        #p_subtitle2.wrapOn(c, 500, 100)
        #p_subtitle2.drawOn(c, width-800, height-190)
        
        c.save()
        
        # Caminho para o arquivo DOCX que será criado
        docx_filename = pdf_filename.replace('.pdf', '.docx')

        # Converte o PDF em DOCX
        cv = Converter(pdf_filename)
        cv.convert(docx_filename)
        cv.close()

        # Adiciona o PDF ao arquivo ZIP
        zipf.write(pdf_filename, os.path.basename(pdf_filename))
        
        # Adiciona o DOCX ao arquivo ZIP
        zipf.write(docx_filename, os.path.basename(docx_filename))

        os.remove(pdf_filename)
        os.remove(docx_filename)

    # Configure a resposta HTTP para o arquivo ZIP
    response = HttpResponse(content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'

    # Abra o arquivo ZIP e envie seu conteúdo como resposta
    with open(zip_filename, 'rb') as zip_file:
        response.write(zip_file.read())

    os.remove(zip_filename)

    return response


def reset_password_request(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            #user = form.get_users(request.POST['email']).first()
            users = form.get_users(request.POST['email'])
            user = next(users, None) 
            if user:
                senha_aleatoria = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                try:
                    user.set_password(senha_aleatoria)
                    user.save()
                except:
                    messages.error(request, 'Erro no BD inesperado, entre em contato com o IG!')
                    return redirect('reset_password_request')
                
                try:
                    send_mail('Senha Nova - AppPFC', f'Sua nova senha é: {senha_aleatoria}', 'ncdseplag@gmail.com', [user.email])
                except:
                    user.set_password("12345678")
                    user.save()
                    messages.error(request, 'Erro no envio de email. Sua nova senha é: 12345678')
                    return redirect('lista_cursos')
            else:
                messages.error(request, 'Email não encontrado em nosso sistema!')
                return redirect('reset_password_request')

            messages.success(request, 'Email enviado com sua nova senha. Aproveite!')
            return redirect('lista_cursos')
    else:
        form = PasswordResetForm()
    return render(request, 'pfc_app/reset_password_request.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Senha alterada com sucesso!')
            return redirect('lista_cursos')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    # A mensagem de erro é adicionada para cada erro encontrado.
                    # Você pode personalizar esta parte para melhor atender às suas necessidades.
                    messages.error(request, f"Erro: {error}")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'pfc_app/change_password.html', {'form': form})

def draw_logos_infos(curso, canvas, doc):
    draw_logos(curso, canvas, doc)
        # Coordenadas para o logo (ajuste conforme necessário)
    logo_width = 50
    logo_height = 50
    x_ig = doc.width + doc.leftMargin +doc.rightMargin - 27.5 - logo_width  # Alinhamento à direita
    y_ig = doc.height + doc.bottomMargin + doc.topMargin - logo_height -20 # No topo
        # Posição e texto do parágrafo
    x_text = 27.5
    y_text = y_ig + 30  # Ajuste conforme necessário
    text = f"Curso: {curso.nome_curso}<br/>Data:<br/>Horário:<br/>Local:"

    # Definir o estilo do texto
    styles = getSampleStyleSheet()
    style = styles['Normal']
    style.fontSize = 10
    style.leading = 12  # Espaçamento entre linhas

     # Criando o objeto Paragraph para o texto do curso
    paragraph = Paragraph(text, style)

    # Determina a largura máxima para o texto
    max_width = doc.width / 2  # Metade da largura da página

    # Calcula a altura necessária para o texto
    required_height = paragraph.wrap(max_width, 40)[1]  # Retorna uma tupla (width, height)
    # Desenha o parágrafo no canvas
    paragraph.drawOn(canvas, x_text, y_text - required_height)

def draw_logos(curso, canvas, doc):
    # Coordenadas para o logo (ajuste conforme necessário)
    logo_width = 50
    logo_height = 50
    x_ig = doc.width + doc.leftMargin +doc.rightMargin - 27.5 - logo_width  # Alinhamento à direita
    y_ig = doc.height + doc.bottomMargin + doc.topMargin - logo_height -20 # No topo

    x_pfc = x_ig - logo_width - 10
    y_pfc = y_ig

    igpe_relative_path = 'igpe.png'
    pfc_relative_path = 'PFC-NOVO-180x180.png'
    igpe_path = os.path.join(settings.MEDIA_ROOT, igpe_relative_path)
    pfc_path = os.path.join(settings.MEDIA_ROOT, pfc_relative_path)
    
    # Substitua 'path/to/your/logo.png' pelo caminho do seu logo
    canvas.drawImage(igpe_path, x_ig, y_ig, width=logo_width, height=logo_height, mask='auto')
    canvas.drawImage(pfc_path, x_pfc, y_pfc, width=logo_width, height=logo_height, mask='auto')

def docentes_curso(curso):

    # Obtém as inscrições que são de 'DOCENTE' para este curso específico
    inscricoes_docentes = Inscricao.objects.filter(curso=curso, condicao_na_acao='DOCENTE')

    # Extrai os participantes (Users) dessas inscrições
    participantes_docentes = [inscricao.participante for inscricao in inscricoes_docentes]

    return participantes_docentes

def create_signature_line(width=200, height=1):
    """
    Cria uma linha para a área de assinatura.

    :param width: Largura da linha.
    :param height: Altura (espessura) da linha.
    :return: Objeto Drawing contendo a linha.
    """
    d = Drawing(width, height)
    d.add(Line(0, 0, width, 0))
    return d

def assinatura_ata(curso):
    # Obtém a folha de estilos padrão do ReportLab
    styles = getSampleStyleSheet()

    # Obtém um estilo existente da folha de estilos e o personaliza para as assinaturas
    signature_style = styles['Normal'].clone('SignatureStyle')
    signature_style.fontSize = 7  # Define o tamanho da fonte
    signature_style.alignment = 1  # Centraliza o texto (0 = esquerda, 1 = centro, 2 = direita)
    # Elementos para a primeira assinatura
    coordinator_elements = [
        [Paragraph(curso.coordenador.nome, signature_style)],
        [Spacer(1, 15)],
        [create_signature_line()],
        [Paragraph("Assinatura da Coordenação", signature_style)]
    ]

    coordinator_table = Table(coordinator_elements, colWidths=[400])
    coordinator_table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))

    if not curso.eh_evento:  
        # Assinaturas dos instrutores
        docentes = docentes_curso(curso)
        instrutor_elements = []
        for i, docente in enumerate(docentes):
            instrutor_elements.append([
            Paragraph(docente.nome, signature_style),
            Spacer(1, 20),
            create_signature_line(),
            Paragraph("Assinatura Instrutoria", signature_style)
            ])
            # Adiciona o separador apenas entre os instrutores, não após o último
            if i < len(docentes) - 1:  # Verifica se não é o último instrutor
                instrutor_elements.append([
                    Paragraph("", signature_style)            
                ] * 4)

        if len(docentes) > 1:
            # Inserir uma coluna de separação entre as assinaturas dos instrutores
            col_widths = [200,50,200]
            instrutor_elements = [instrutor_elements[:4],  instrutor_elements[4:]]
        else:
            col_widths = [400]
            instrutor_elements = [instrutor_elements]
        
        instrutor_table = Table(instrutor_elements, colWidths=col_widths)
        instrutor_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))
        # Combinar as tabelas de assinaturas verticalmente
        elements = [Spacer(1, 20), coordinator_table, Spacer(1, 40), instrutor_table]
    else:
        elements = [Spacer(1, 20), coordinator_table, Spacer(1, 40)]
    return (
        elements
    )


@login_required
def gerar_ata(request, curso_id):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Ata.pdf"'
    curso = Curso.objects.get(pk=curso_id)
    doc = SimpleDocTemplate(response, pagesize=A4)
    
    styles = getSampleStyleSheet()
    header_style = styles['Heading1']  # Pode ajustar o estilo conforme necessário
    header_style.alignment = 1  # 1 para centralizar
    info_style = styles['Normal']  # Usando o estilo Normal como base
    info_style.fontSize = 10

    header = Paragraph("FREQUÊNCIA", header_style)
    # Assume que a largura da página seja dividida igualmente pelas colunas
    column_widths = [30, 270, 240]  # A largura total é 595, ajuste conforme necessário
    # lista_inscritos = curso.inscricoes.filter(
    #     condicao_na_acao='DISCENTE',
    #     status__nome='APROVADA'
    # ).order_by('participante__nome')
    
    lista_inscritos = curso.participantes.filter(
        inscricao__condicao_na_acao='DISCENTE', inscricao__status__nome='APROVADA').order_by('nome')
    # Cabeçalho da tabela
    data = [['ORD', 'NOME', 'ASSINATURA']]
    ordem = 0

    # Adicionando algumas linhas de exemplo. Você pode ajustar isso conforme necessário
    # Por exemplo, você pode querer calcular o número de linhas que cabem em uma página
    for i, participante in enumerate(lista_inscritos, start=1):
        data.append([str(i), participante.nome, ''])
        ordem = i

    # for j in range(1, 6):
    #     data.append([str(ordem + j), '', ''])  # Adiciona 5 linhas em branco.

    table = Table(data, colWidths=column_widths)

    # Estilizando a tabela
    table.setStyle(TableStyle([
                       ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
                       ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                       ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                       ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                       ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                       ('TOPPADDING', (0, 0), (-1, 0), 6),
                       ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                       ('FONTSIZE', (0, 1), (-1, -1), 8),
                       ('GRID', (0, 0), (-1, -1), 1, colors.black),
                   ]))
    table.repeatRows = 1

    espaco_altura = 20
    spacer = Spacer(1, espaco_altura)

    assinatura = assinatura_ata(curso)

    elements = [header, spacer, table]  # Adicione o header antes da tabela
    elements += assinatura
    doc.build(
        elements, 
        onFirstPage=lambda canvas, doc: draw_logos_infos(curso, canvas, doc),
        onLaterPages=lambda canvas, doc: draw_logos(curso, canvas, doc)
        )
    return response

def adjust_lightness(color, amount):
    try:
        c = mc.cnames[color]
    except:
        c = color
    c = colorsys.rgb_to_hls(*mc.to_rgb(c))
    return colorsys.hls_to_rgb(c[0], max(0, min(1, amount * c[1])), c[2])

def draw_logos_relatorio(c: canvas.Canvas, width, height):
    # Coordenadas para o logo (ajuste conforme necessário)
    logo_width = 50
    logo_width_seplag = 150
    logo_height_seplag = 30
    logo_height = 50
    x_ig = width  - 40 - logo_width  # Alinhamento à direita
    y_ig = height - logo_height -20 # No topo

    x_seplag =(width/2) - (logo_width_seplag/2)  # Alinhamento à direita
    y_seplag = y_ig # No topo
    
    x_pfc = 40
    y_pfc = y_ig

    igpe_relative_path = 'igpe.png'
    pfc_relative_path = 'PFC-NOVO-180x180.png'
    seplag_relative_path = 'seplagtransparente.png'
    igpe_path = os.path.join(settings.MEDIA_ROOT, igpe_relative_path)
    pfc_path = os.path.join(settings.MEDIA_ROOT, pfc_relative_path)
    seplag_path = os.path.join(settings.MEDIA_ROOT, seplag_relative_path)
    
    # Substitua 'path/to/your/logo.png' pelo caminho do seu logo
    c.drawImage(igpe_path, x_ig, y_ig, width=logo_width, height=logo_height, mask='auto')
    c.drawImage(seplag_path, x_seplag, y_seplag, width=logo_width_seplag, height=logo_height_seplag, mask='auto')
    c.drawImage(pfc_path, x_pfc, y_pfc, width=logo_width, height=logo_height, mask='auto')


def capa_relatorio(c: canvas.Canvas, width, height, plano_curso: PlanoCurso):
    draw_logos_relatorio(c, width, height)
    x_position = (width) / 2
    y_position = (height) / 2
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor('#4472C4')
    text_width = c.stringWidth('Relatório Geral', "Helvetica-Bold", 16)
    c.drawString(x_position-(text_width/2), y_position, 'Relatório Geral')
    c.setFont("Helvetica", 12)
    text_width = c.stringWidth(plano_curso.curso.nome_curso, "Helvetica-Bold", 11)
    c.drawString(x_position-(text_width/2), y_position-40, plano_curso.curso.nome_curso)

    c.showPage()


def pagina_dados_curso(c: canvas.Canvas, width, height, curso_id):
    
    plano_curso = PlanoCurso.objects.get(curso_id = curso_id)
    capa_relatorio(c, width, height, plano_curso)
    inscricoes_validas = Inscricao.objects.filter(
        ~Q(status__nome='CANCELADA'),
        ~Q(status__nome='EM FILA'),
        ~Q(condicao_na_acao='DOCENTE'),
        curso=plano_curso.curso
    ).count()
    concluintes = Inscricao.objects.filter(
        ~Q(status__nome='CANCELADA'),
        ~Q(status__nome='EM FILA'),
        ~Q(condicao_na_acao='DOCENTE'),
        Q(concluido=True),
        curso=plano_curso.curso
    ).count()
    instrutores = Inscricao.objects.filter(
        ~Q(status__nome='CANCELADA'),
        ~Q(status__nome='EM FILA'),
        Q(condicao_na_acao='DOCENTE'),
        curso=plano_curso.curso
    ).order_by('inscrito_em')
    # c.setFont("Helvetica-Bold", 14)
    # c.drawAlignedString(100, height - 100, 'Dados do curso')
    style_body = ParagraphStyle('title',
                                    fontName = 'Helvetica-Bold',
                                    fontSize=12,
                                    leading=17,
                                    textColor=HexColor('#4472C4'),
                                    alignment=TA_JUSTIFY)
    style_body_sub = ParagraphStyle('subtitle',
                                    fontName = 'Helvetica-Bold',
                                    fontSize=11,
                                    leading=17,
                                    textColor=HexColor('#4472C4'),
                                    alignment=TA_JUSTIFY)
    style_body_center = ParagraphStyle('body-center',
                                    fontName = 'Helvetica',
                                    fontSize=11,
                                    leading=17,
                                    textColor=HexColor('#4472C4'),
                                    alignment=TA_CENTER)
    style_body_justify = ParagraphStyle('body-center',
                                    fontName = 'Helvetica',
                                    fontSize=10,
                                    leading=17,
                                    textColor=HexColor('#4472C4'),
                                    alignment=TA_JUSTIFY)
    
    
    draw_logos_relatorio(c, width, height)
    p1=Paragraph('Dados do curso', style_body)
    text_width, text_height = p1.wrapOn(c, 500, 20)
    x_position = (width - text_width) / 2
    p1.drawOn(c, x_position, height-100)

    # Define a cor da linha usando um código hexadecimal
    cor_linha = HexColor("#4472C4")

    # Define a cor e desenha uma linha horizontal
    c.setStrokeColor(cor_linha)
    c.line(50, height-100-text_height , width - 50, height-100-text_height)

    nome_curso = plano_curso.curso.nome_curso
    obj_geral = plano_curso.objetivo_geral
    metodologia = plano_curso.metodologia_ensino
    ch = plano_curso.curso.ch_curso
    data_inicio = plano_curso.curso.data_inicio
    data_termino = plano_curso.curso.data_termino
    inst_promotora = plano_curso.curso.inst_promotora.nome
    #ch, data_inicio, data_termino, inst_promotora, 
    #total_inscritos, total_Certificados, instrutor_princ, instrutor_sec

    p2=Paragraph('Nome da ação de capacitação: '+nome_curso, style_body_center)
    text_width, text_height = p2.wrapOn(c, 500, 40)
    x_position = (width - text_width) / 2
    p2.drawOn(c, x_position, height-150)

    # OBJETIVO GERAL #
    p3=Paragraph('Objetivo geral', style_body_sub)
    text_width, text_height = p3.wrapOn(c, 500, 40)
    x_position = (width - text_width) / 2
    p3.drawOn(c, x_position, height-200)
    p4=Paragraph(obj_geral, style_body_justify)
    text_width, text_height = p4.wrapOn(c, 500, 400)
    x_position = (width - text_width) / 2
    y_position = height-text_height-220
    p4.drawOn(c, x_position, y_position)

    # # METODOLOGIA #
    p5=Paragraph('Metodologia', style_body_sub)
    text_width, text_height = p5.wrapOn(c, 500, 40)
    x_position = (width - text_width) / 2
    y_position = y_position - 30
    p5.drawOn(c, x_position, y_position)
    p6=Paragraph(metodologia, style_body_justify)
    text_width, text_height = p6.wrapOn(c, 500, 400)
    x_position = (width - text_width) / 2
    y_position = y_position - 20
    p6.drawOn(c, x_position, y_position-text_height)

    # INFOS #
    
    c.setFont("Helvetica", 10)
    c.setFillColor('#4472C4')
    y_position = y_position-text_height - 30
    c.drawString(x_position, y_position, 'Carga-horária: '+str(ch)+' horas-aula')
    y_position = y_position - 20
    c.drawString(x_position, y_position, 'Data de início: '+str(data_inicio.strftime('%d/%m/%Y')))
    y_position = y_position - 20
    c.drawString(x_position, y_position, 'Data de término: '+str(data_termino.strftime('%d/%m/%Y')))
    y_position = y_position - 20
    c.drawString(x_position, y_position, 'Instituição promotora: '+inst_promotora)
    y_position = y_position - 20
    c.drawString(x_position, y_position, 'Total inscritos: '+str(inscricoes_validas))
    y_position = y_position - 20
    c.drawString(x_position, y_position, 'Total concluintes: '+str(concluintes))

    for index, instrutor in enumerate(instrutores):
        if index == 0:
            label = 'Instrutor principal: '
        else:
            label = 'Instrutor secundário: '
        y_position = y_position - 20
        c.drawString(x_position, y_position, label+instrutor.participante.nome)

    c.showPage()

def pagina_fotos(c: canvas.Canvas, width, height):
    style_body = ParagraphStyle('body',
                                    fontName = 'Helvetica-Bold',
                                    fontSize=12,
                                    leading=17,
                                    textColor=HexColor('#4472C4'),
                                    alignment=TA_JUSTIFY)
    
    # Definir o diretório onde as imagens estão armazenadas
    upload_dir = os.path.join(settings.BASE_DIR, 'tmp')

    # Calcular a posição inicial para colocar as imagens
    y_position = height - 330  # Deixar uma margem no topo
    print(height)
    # Listar todos os arquivos no diretório de upload
    draw_logos_relatorio(c, width, height)
    p_titulo_tema=Paragraph('Fotos do curso', style_body)
    text_width, text_height = p_titulo_tema.wrapOn(c, 500, 20)
    x_position = (width - text_width) / 2
    p_titulo_tema.drawOn(c, x_position, height-100)

    # Define a cor da linha usando um código hexadecimal
    cor_linha = HexColor("#4472C4")

    # Define a cor e desenha uma linha horizontal
    c.setStrokeColor(cor_linha)
    c.line(50, height-100-text_height , width - 50, height-100-text_height)

    for filename in os.listdir(upload_dir):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):  # Aceitar formatos de imagem comuns
            path = os.path.join(upload_dir, filename)
            img = Image.open(path)
            img_width, img_height = img.size
            scale_factor = 300 / img_width
            scaled_height = img_height * scale_factor
            

            # Desenhar a imagem no canvas do PDF
            c.drawImage(path, 50, y_position, width=267, height=200, mask='auto')
            y_position -= 230 
            

    c.showPage()


def gerar_relatorio(request, curso_id):
    avaliacoes = Avaliacao.objects.filter(curso_id=curso_id).select_related('subtema', 'subtema__tema')
    medias_notas_por_tema = Avaliacao.objects.filter(~Q(nota='0'), curso_id=curso_id ).annotate(
    nota_numerica=Cast('nota', FloatField())
        ).values('subtema__tema__id', 'subtema__tema__nome') \
        .annotate(media_notas=Avg('nota_numerica'))
    medias_notas_dict = {item['subtema__tema__id']: item['media_notas'] for item in medias_notas_por_tema}
    temas = Tema.objects.filter(subtema__avaliacao__curso_id=curso_id).distinct()

    # Conta o número de participantes distintos que avaliaram o curso
    quantidade_avaliadores = Avaliacao.objects.filter(curso_id=curso_id).values('participante').distinct().count()


    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="relatorio.pdf"'
    c = canvas.Canvas(response, pagesize=A4)

    # Gerar cores para cada nota
    base_rgb = to_rgb('#668923')
    # colors = [adjust_lightness('#4D6CFA', 1 - 0.15 * i) for i in range(5)]

    colors = [
        '#F8D9A3',
        '#FFD559',
        '#DDDDDD',
        '#B7E6E1',
        '#86D4CD',
        '#76C2AA'

    ]
    width, height = A4
    pagina_dados_curso(c, width, height, curso_id)

    # http://127.0.0.1:8000/gerar_relatorio/13
    for tema in temas:

        total_avaliacoes_tema = Avaliacao.objects.filter(subtema__tema_id=tema.id).count()
        avaliacoes_baixas_tema = Avaliacao.objects.filter(subtema__tema_id=tema.id, nota__in=['1', '2']).count()
        percentual_baixas_tema = (avaliacoes_baixas_tema / total_avaliacoes_tema) * 100 if total_avaliacoes_tema > 0 else 0
        percentual_baixas_tema = round(percentual_baixas_tema, 2)
        
        total_avaliacoes_zero = Avaliacao.objects.filter(subtema__tema_id=tema.id, nota='0').count()

        avaliacoes_altas_tema = Avaliacao.objects.filter(subtema__tema_id=tema.id, nota__in=['4', '5']).count()
        percentual_altas_tema = (avaliacoes_altas_tema / (total_avaliacoes_tema-total_avaliacoes_zero)) * 100 if total_avaliacoes_tema > 0 else 0
        percentual_altas_tema = round(percentual_altas_tema, 2)




        media_notas = medias_notas_dict.get(tema.id, 0)  # Obtém a média das notas para o tema ou 0 se não houver avaliações
        media_notas = round(media_notas, 1)
        # print(f'B+MB para o tema {tema.id}: {percentual_altas_tema}')

        item_relatorio = ItemRelatorio.objects.get(tema=tema)
        texto_tema = item_relatorio.texto
        notas_por_subtema = {}  # Dicionário para contagem de notas por subtema
        cor_por_subtema = {}
        
        
        
        for avaliacao in avaliacoes.filter(subtema__tema=tema):
            subtema_nome = avaliacao.subtema.nome
            nota = avaliacao.nota
            cor = avaliacao.subtema.cor
            if nota=='0':
                continue

            if subtema_nome not in notas_por_subtema:
                notas_por_subtema[subtema_nome] = {str(i): 0 for i in range(0, 6)}
                
            notas_por_subtema[subtema_nome][nota] += 1

            if subtema_nome not in cor_por_subtema:
                cor_por_subtema[subtema_nome] = cor
            
        #print(cor_por_subtema)
        media_conhecimento_previo = 0
        media_conhecimento_posterior = 0
        # Calcular as proporções
        proporcoes_por_subtema = {}
        contagens_por_subtema = {}
        cor_subtema_dict = {}
        
        for subtema, notas in notas_por_subtema.items():
            total = sum(notas.values())
            cor_subtema = {cor: cor}
            proporcoes = {nota: (count / total if total else 0) for nota, count in notas.items()}
            proporcoes_por_subtema[subtema] = proporcoes
            cor_subtema_dict[subtema] = cor_subtema
            contagens_por_subtema[subtema] = notas
            
            # TODO IMPLEMENTAR CONHECIMENTO PRÉVIO E ANTERIOR
            if tema.nome == 'Conhecimento':
                if subtema == "Conhecimento Prévio":
                    soma_notas_vezes_count = 0
                    soma_counts = 0
                    for nota, count in notas.items():
                        # print('nota: '+str(nota))
                        # print('count: '+str(count))
                        soma_notas_vezes_count += int(nota) * int(count)
                        soma_counts += int(count)
                    #print('previo: '+ media_conhecimento_previo)
                    # print(soma_notas_vezes_count)
                    # print(soma_counts)
                    # print(soma_notas_vezes_count/soma_counts)
                    media_conhecimento_previo = round(soma_notas_vezes_count/soma_counts, 1)
                elif subtema == "Conhecimento Posterior":
                    soma_notas_vezes_count = 0
                    soma_counts = 0
                    for nota, count in notas.items():
                        # print('nota: '+str(nota))
                        # print('count: '+str(count))
                        soma_notas_vezes_count += int(nota) * int(count)
                        soma_counts += int(count)
                    #print('previo: '+ media_conhecimento_previo)
                    # print(soma_notas_vezes_count)
                    # print(soma_counts)
                    # print(soma_notas_vezes_count/soma_counts)
                    media_conhecimento_posterior = round(soma_notas_vezes_count/soma_counts, 1)
                    
        # Criar o gráfico de barras empilhadas com proporções
        fig, ax = plt.subplots(figsize=(8, 4))
        bottom = [0] * len(proporcoes_por_subtema)
        subtema_names = list(proporcoes_por_subtema.keys())
        bar_heights = []
        for i, nota in enumerate(range(0, 6)):
            valores = [proporcoes_por_subtema[subtema].get(str(nota), 0) for subtema in proporcoes_por_subtema]
            cores = [cor_por_subtema[subtema] for subtema in subtema_names]
            barras = ax.barh(subtema_names, valores, left=bottom, label=f'Nota {nota}', color=colors[i])
            bottom = [bottom[i] + valores[i] for i in range(len(bottom))]

            for bar, valor in zip(barras, valores):
                    if valor > 0.05:  # Apenas mostrar texto para valores significativos
                        # # Colocar o nome do subtema acima do conjunto de barras
                        # ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height() + 0.05,
                        #         subtema_names[i], ha='center', va='bottom', fontsize=10, color='black')
                        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height() / 2,
                                f'{valor:.1%}',  # Exibir a proporção como percentual
                                fontsize=12, ha='center', va='center')
                        # Mostrar a nota abaixo do valor da proporção
                        if nota==0:
                            nota = 'N/A'
                        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + 0.055,
                                f'Nota: {nota}', ha='center', va='center', fontsize=9, color='#222222')
                        max_width = max([bar.get_width() for bar in barras])
        # Definir o limite do eixo y para manter a altura das barras constante
        if len(subtema_names) == 1:
            ax.set_ylim(-1, 1)  # Ajuste estes valores conforme necessário para manter a altura das barras
        else:
            ax.set_ylim(-0.5, len(subtema_names))

        ax.set_yticks(range(len(subtema_names)), subtema_names)
        # Adicionar os nomes dos subtemas acima das barras
        # ax.get_yticks()[idx]
        background_color = (250/255, 250/255, 250/255, 0.5)
        for idx, subtema in enumerate(subtema_names):
            ax.text(0.5, ax.get_yticks()[idx]+0.35 , subtema, va='top', ha='center', fontsize=8, color='black', backgroundcolor=background_color)

        ax.set_xlim([0, 1])
        #ax.set_xlabel('Avaliações')
        ax.set_xticks([]) 
        ax.set_yticks([]) 
        plt.tight_layout()
        plt.title(f'{tema.nome}', fontsize=16)
        #plt.legend()

        # Salvar o gráfico como uma imagem
        fig.savefig(f'{tema.id}_proporcoes.png', bbox_inches='tight')
        plt.close(fig)

        # Adicionar a imagem do gráfico ao PDF
        #252423
        style_body = ParagraphStyle('body',
                                    fontName = 'Helvetica-Bold',
                                    fontSize=12,
                                    leading=17,
                                    textColor=HexColor('#4472C4'),
                                    alignment=TA_JUSTIFY)
        style_body_text = ParagraphStyle('body-text',
                                    fontName = 'Helvetica',
                                    fontSize=10,
                                    leading=17,
                                    textColor=HexColor('#4472C4'),
                                    alignment=TA_JUSTIFY)
        style_kpi = ParagraphStyle('body',
                                    fontName = 'Helvetica-Bold',
                                    fontSize=16,
                                    leading=17,
                                    textColor=HexColor('#4472C4'),
                                    alignment=TA_CENTER,
                                    )
        style_text_kpi = ParagraphStyle('body',
                                    fontName = 'Helvetica-Bold',
                                    fontSize=10,
                                    leading=12,
                                    textColor=HexColor('#bbbbbb'),
                                    alignment=TA_CENTER,
                                    )

        tag_mapping = {
            "[C_PREVIO]": media_conhecimento_previo,
            "[C_POST]": media_conhecimento_posterior,
            "[R+MR%]": str(percentual_baixas_tema)+'%',
            "[B+MB%]": str(percentual_altas_tema)+'%',
            "[media]": media_notas,
            "[num_resp]": quantidade_avaliadores
        }

        # Substitua as tags pelo valor correspondente no texto
        for tag, value in tag_mapping.items():
            texto_tema = texto_tema.replace(tag, str(value))
            
        draw_logos_relatorio(c, width, height)
        p_titulo_tema=Paragraph(tema.nome, style_body)
        text_width, text_height = p_titulo_tema.wrapOn(c, 500, 20)
        x_position = (width - text_width) / 2
        p_titulo_tema.drawOn(c, x_position, height-100)

        # Define a cor da linha usando um código hexadecimal
        cor_linha = HexColor("#4472C4")

        # Define a cor e desenha uma linha horizontal
        c.setStrokeColor(cor_linha)
        c.line(50, height-100-text_height , width - 50, height-100-text_height)

        texto = texto_tema

        p1=Paragraph(texto, style_body_text)
        text_width, text_height = p1.wrapOn(c, 500, 400)
        x_position = (width - text_width) / 2
        p1.drawOn(c, x_position, 700-text_height)
        c.setFont("Helvetica-Bold", 18)
        # c.drawCentredString(width / 2, height - 100, tema.nome)
        c.drawImage(f'{tema.id}_proporcoes.png', 50, 200, width=500, height=250)  # Ajuste as dimensões conforme necessário
# http://127.0.0.1:8000/gerar_relatorio/12
        width_rect = 100
        height_rect = 70
        c.roundRect((width / 2)+50, 470, width_rect, height_rect, 10, stroke=1, fill=0)
        c.roundRect((width / 2)-150, 470, width_rect, height_rect, 10, stroke=1, fill=0)
        media_text = 'Média Geral'
        if tema.nome == 'Conhecimento':
            media_conhecimento = round(media_conhecimento_posterior/media_conhecimento_previo, 1)
            media_notas = media_conhecimento
            media_text = 'Ganho de Conhecimento'
           
        kpi_media = Paragraph(str(media_notas), style_kpi)
        kpi_numero = Paragraph(str(quantidade_avaliadores), style_kpi)
        kpi_media_text = Paragraph(media_text, style_text_kpi)
        kpi_numero_text = Paragraph('N° de Respostas', style_text_kpi)
        kpi_media_width, kpi_media_height = kpi_media.wrapOn(c, 30, 20)
        kpi_numero_width, kpi_numero_height = kpi_numero.wrapOn(c, 30, 20)
        kpi_numero_text_width, kpi_numero_text_height = kpi_numero_text.wrapOn(c, 80, 40)
        kpi_media_text_width, kpi_media_text_height = kpi_media_text.wrapOn(c, 80, 40)
        texto_x = (width / 2) + 50 + (width_rect / 2) - (kpi_media_width / 2)
        texto_y = 470 + (height_rect / 2) - 6  # Ajuste o valor para centralizar verticalmente
        texto_x2 = (width / 2) - 150 + (width_rect / 2) - (kpi_numero_width / 2)
        texto_y2 = 470 + (height_rect / 2) - 6 
        kpi_text_numero_x = (width / 2) - 150 + (width_rect / 2) - (kpi_numero_text_width / 2)
        kpi_text_numero_y = 470 + height_rect - kpi_numero_text_height
        kpi_text_media_x = (width / 2) + 50 + (width_rect / 2) - (kpi_media_text_width / 2)
        kpi_text_media_y = 470 + height_rect - kpi_media_text_height
        # Desenha o texto da média no quadrado
        kpi_numero.drawOn(c, texto_x2, texto_y2)
        kpi_media.drawOn(c, texto_x, texto_y)
        kpi_media_text.drawOn(c, kpi_text_media_x, kpi_text_media_y)
        kpi_numero_text.drawOn(c, kpi_text_numero_x, kpi_text_numero_y)
        c.showPage()  # Cria uma nova página para cada tema
    pagina_fotos(c, width, height)    
    c.save()
    shutil.rmtree(os.path.join(settings.BASE_DIR, 'tmp'))
    return response


def salva_fotos(fotos):
    upload_dir = os.path.join(settings.BASE_DIR, 'tmp')
    # Verificar se o diretório existe, se não, criá-lo
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    for foto in fotos:
        if foto.content_type in ["image/jpeg", "image/png"]:
            # Salvar temporariamente o arquivo para leitura
            path = os.path.join(upload_dir, foto.name)
            with open(path, 'wb+') as f:
                for chunk in foto.chunks():
                    f.write(chunk)



def relatorio(request):
    cursos = Curso.objects.order_by('data_inicio').filter(
        status__nome = 'FINALIZADO', planocurso__isnull=False)
    
    
    context = {
        'cursos': cursos,
    }

    if request.method == 'POST':
    
        curso_id = request.POST.get('curso')
        fotos = request.FILES.getlist('fotos')  # Pega a lista de arquivos enviados
        salva_fotos(fotos)
        #gerar_relatorio(request, curso_id)
        return redirect('gerar_relatorio', curso_id)
    

    return render(request, 'pfc_app/relatorio.html' ,context)

def hex_to_rgb_normalizado(hex_color):
    # Remover o prefixo '#' se houver
    if hex_color.startswith('#'):
        hex_color = hex_color[1:]
    
    # Converter os componentes R, G, B de hexadecimal para decimal
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    # Normalizar os valores para o intervalo 0-1
    return (r / 255, g / 255, b / 255)

def draw_logos_curadoria(c: canvas.Canvas, width, height):
    # Coordenadas para o logo (ajuste conforme necessário)
    logo_width = 50
    logo_width_seplag = 150
    logo_height_seplag = 30
    logo_height = 50
    x_ig = width  - 50 - logo_width  # Alinhamento à direita
    y_ig = height - logo_height -20 # No topo

    x_seplag = width  - 50 - logo_width_seplag   # Alinhamento à direita
    y_seplag = 10 # No topo
    
    x_pfc = x_ig - logo_width - 10
    y_pfc = y_ig

    igpe_relative_path = 'igpe.png'
    pfc_relative_path = 'PFC-NOVO-180x180.png'
    seplag_relative_path = 'seplagtransparente.png'
    igpe_path = os.path.join(settings.MEDIA_ROOT, igpe_relative_path)
    pfc_path = os.path.join(settings.MEDIA_ROOT, pfc_relative_path)
    seplag_path = os.path.join(settings.MEDIA_ROOT, seplag_relative_path)
    
    # Substitua 'path/to/your/logo.png' pelo caminho do seu logo
    c.drawImage(igpe_path, x_ig, y_ig, width=logo_width, height=logo_height, mask='auto')
    c.drawImage(seplag_path, x_seplag, y_seplag, width=logo_width_seplag, height=logo_height_seplag, mask='auto')
    c.drawImage(pfc_path, x_pfc, y_pfc, width=logo_width, height=logo_height, mask='auto')


def gerar_curadoria(request, ano, mes):
    # Ano e mês são presumivelmente passados como inteiros, se não, converta-os.
    ano = int(ano)
    mes = int(mes)

    # O primeiro dia do mês é sempre 1
    data_inicio = date(ano, mes, 1)

    # Último dia do mês - monthrange retorna o dia da semana do primeiro dia do mês e o número de dias no mês
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    data_fim = date(ano, mes, ultimo_dia)

    trilhas = Trilha.objects.all().order_by('ordem_relatorio')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="agenda_pfc.pdf"'

    # Cria um objeto Canvas diretamente
    p = canvas.Canvas(response, pagesize=A4)
    p.setTitle('Agenda PFC')
    width, height = A4
    
    # Estilo para o cabeçalho
    header_style = ParagraphStyle(
        name='HeaderStyle',
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=colors.white,
        alignment=1,  # Centro
        spaceAfter=5,
    )

    # Estilo para o corpo da tabela
    body_style = ParagraphStyle(
        name='BodyStyle',
        fontSize=8,
        fontName='Helvetica',
        textColor=colors.black,
        alignment=1,  # Centro
        spaceAfter=5,
    )

    link_style = ParagraphStyle(
        name='link_style',  # Nome do estilo
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.blue,  # Definindo a cor do texto para azul
        underline=True,  # Adicionando sublinhado
        alignment=1,  # Centro
        spaceAfter=5,
    )

    cabecalho = [Paragraph("Curadoria", header_style), 
                 Paragraph("Link", header_style), 
                 Paragraph("CH", header_style), 
                 Paragraph("Modalidade", header_style), 
                 Paragraph("Promotor", header_style)]
    cabecalho_pfc = [Paragraph("PFC", header_style), 
                 Paragraph("Link", header_style), 
                 Paragraph("CH", header_style), 
                 Paragraph("Modalidade", header_style), 
                 Paragraph("Período", header_style)]
    
    y_table = 730
    # http://127.0.0.1:8000/curadoria
    for trilha in trilhas:
        data_pfc = [
                cabecalho_pfc,
            ]
        for curso in trilha.cursos.filter(data_inicio__gte=data_inicio, data_inicio__lte=data_fim):
            url = f"https://www.pfc.seplag.pe.gov.br/curso_detail/{curso.id}"
            link_text = '<u><link href="' + url + '">' + 'Inscrição' + '</link></u>'
            data_pfc.append(
                [Paragraph(curso.nome_curso, body_style), 
                 Paragraph(link_text, link_style), 
                 Paragraph(str(curso.ch_curso), body_style), 
                 Paragraph(curso.modalidade.nome, body_style), 
                 Paragraph(f"de {curso.data_inicio.strftime('%d/%m/%Y')} a {curso.data_termino.strftime('%d/%m/%Y')}", body_style) ],
            )
        
        data = [
                cabecalho,
            ]
        
        curadorias = trilha.curadorias.filter(
            Q(mes_competencia__gte=data_inicio, mes_competencia__lte=data_fim) |
            Q(permanente=True)
        )
        for curadoria in curadorias:
            
            url = curadoria.link_inscricao
            link_text = '<u><link href="' + url + '">' + 'Inscrição' + '</link></u>'
            #link_text = Hyperlink(url, 'Inscrição', color=colors.blue)
            data.append(
                [Paragraph(curadoria.nome_curso, body_style), 
                 Paragraph(link_text, link_style), 
                 Paragraph(str(curadoria.carga_horaria_total), body_style), 
                 Paragraph(curadoria.modalidade.nome, body_style), 
                 Paragraph("" if curadoria.instituicao_promotora is None else curadoria.instituicao_promotora.nome, body_style)],
            )
    
        if (len(data_pfc) + len(data)) <= 2:
            continue

        if len(data_pfc) > 1:
            table_pfc = Table(data_pfc, colWidths=[215, 50, 30, 80, 120])

        if len(data) > 1:
            table = Table(data, colWidths=[215, 50, 30, 80, 120])

        hex_color = trilha.cor_circulo
        rgb_normalized = hex_to_rgb_normalizado(hex_color)
        hex_color_fundo = trilha.fundo_tabela
        rgb_fundo_normalized = hex_to_rgb_normalizado(hex_color_fundo)

        table_style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), rgb_normalized),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('TOPPADDING', (0,0), (-1,0), 6),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BACKGROUND', (0,1), (-1,-1), rgb_fundo_normalized),
            ('GRID', (0,0), (-1,-1), 1, colors.white),
            ('FONTSIZE', (0,0), (-1,-1), 8)
        ])
        
        h_pfc = 0
        h = 0 
        if len(data_pfc) > 1:
            table_pfc.setStyle(table_style)
            w_pfc, h_pfc = table_pfc.wrapOn(p, 0, 0)

        if len(data) > 1:
            table.setStyle(table_style)
            w, h = table.wrapOn(p, 0, 0) 

        
        
        if y_table-h_pfc > 40 and y_table-h > 40:
            p.setFillColorRGB(rgb_normalized[0], rgb_normalized[1], rgb_normalized[2])
            p.circle(60, y_table + 20, 10, stroke=0, fill=1)
            p.setFillColorRGB(0, 0, 0)
            p.drawString(75, y_table + 15, trilha.nome)

        if len(data_pfc) > 1:
            
            if y_table-h_pfc <= 40:
                draw_logos_curadoria(p, width, height)
                p.setFont("Helvetica", 26)
                mes_escolhido = MONTHS[int(mes)-1][1]
                text_title = f"Agenda de {mes_escolhido}"
                p.drawCentredString(width / 2, height - 50, text_title) 
                p.showPage()  # Cria uma nova página
                p.setFont("Helvetica", 26)  # Redefinindo a fonte para o título
                mes_escolhido = MONTHS[int(mes)-1][1]
                text_title = f"Agenda de {mes_escolhido}"
                p.drawCentredString(width / 2, height - 50, text_title)
                draw_logos_curadoria(p, width, height)
                y_table = 730 
                p.setFont("Helvetica", 13)
                p.setFillColorRGB(rgb_normalized[0], rgb_normalized[1], rgb_normalized[2])
                p.circle(60, y_table + 20, 10, stroke=0, fill=1)
                p.setFillColorRGB(0, 0, 0)
                p.drawString(75, y_table + 15, trilha.nome)
                 # Redefinir `y_table` para o topo da nova página  # Prepara a tabela para ser desenhada
            table_pfc.drawOn(p, 50, y_table-h_pfc)
            y_table -= h_pfc + 10
        if len(data) > 1:
            
            if y_table-h <= 40:
                draw_logos_curadoria(p, width, height)
                p.setFont("Helvetica", 26)
                mes_escolhido = MONTHS[int(mes)-1][1]
                text_title = f"Agenda de {mes_escolhido}"
                p.drawCentredString(width / 2, height - 50, text_title) 
                p.showPage()  # Cria uma nova página
                p.setFont("Helvetica", 26)  # Redefinindo a fonte para o título
                mes_escolhido = MONTHS[int(mes)-1][1]
                text_title = f"Agenda de {mes_escolhido}"
                p.drawCentredString(width / 2, height - 50, text_title)
                draw_logos_curadoria(p, width, height)
                y_table = 730
                p.setFont("Helvetica", 13)
                p.setFillColorRGB(rgb_normalized[0], rgb_normalized[1], rgb_normalized[2])
                p.circle(60, y_table + 20, 10, stroke=0, fill=1)
                p.setFillColorRGB(0, 0, 0)
                p.drawString(75, y_table + 15, trilha.nome)
                  # Redefinir `y_table` para o topo da nova página  # Prepara a tabela para ser desenhada
            table.drawOn(p, 50, y_table-h)
            y_table -= h + 60  # Desenha a tabela na posição x=50, y=500
        else:
            y_table -= 40
    draw_logos_curadoria(p, width, height)
    p.setFont("Helvetica", 26)
    mes_escolhido = MONTHS[int(mes)-1][1]
    text_title = f"Agenda de {mes_escolhido}"
    p.drawCentredString(width / 2, height - 50, text_title) 
    p.showPage()
    p.save()
    return response



def curadoria(request):
    year_range = Curadoria.objects.aggregate(
        min_year=Min(ExtractYear('mes_competencia')),
        max_year=Max(ExtractYear('mes_competencia'))
    )
    min_year = year_range['min_year']
    max_year = year_range['max_year']

    # Gera uma lista de anos desde o ano mínimo até o ano máximo
    available_years = list(range(min_year, max_year + 1))
    
    
    context = {
        'cursos': cursos,
        'anos': available_years,
        'meses': MONTHS,
    }

    if request.method == 'POST':
    
        ano = request.POST.get('ano')
        mes = request.POST.get('mes') 
        
        return redirect('gerar_curadoria', ano, mes)
    

    return render(request, 'pfc_app/curadoria.html' ,context)


def curadoria_html_show(request):
    year_range = Curadoria.objects.aggregate(
        min_year=Min(ExtractYear('mes_competencia')),
        max_year=Max(ExtractYear('mes_competencia'))
    )
    min_year = year_range['min_year']
    max_year = year_range['max_year']

    # Gera uma lista de anos desde o ano mínimo até o ano máximo
    available_years = list(range(min_year, max_year + 1))
    
    
    context = {
        'cursos': cursos,
        'anos': available_years,
        'meses': MONTHS,
    }

    if request.method == 'POST':
    
        ano = request.POST.get('ano')
        mes = request.POST.get('mes') 
        
        return redirect('curadoria_html', ano, mes)
    

    return render(request, 'pfc_app/curadoria_show.html' ,context)

def curadoria_html(request, ano, mes):

    ano = int(ano)
    mes = int(mes)

    data_inicio = date(ano, mes, 1)
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    data_fim = date(ano, mes, ultimo_dia)

    trilhas = Trilha.objects.all().order_by('ordem_relatorio')
    trilhas_com_cursos = {}
    for trilha in trilhas:
        curadorias = trilha.curadorias.filter(
            Q(mes_competencia__gte=data_inicio, mes_competencia__lte=data_fim) |
            Q(permanente=True)
        )
        cursos = trilha.cursos.filter(data_inicio__gte=data_inicio, data_inicio__lte=data_fim)
        
        trilhas_com_cursos[trilha] = {
            'curadorias': curadorias,
            'cursos': cursos,
            'cor_circulo': trilha.cor_circulo,
            'fundo_tabela': trilha.fundo_tabela
        }



    mes_escolhido = MONTHS[int(mes)-1][1].upper()

    context = {
        'trilhas_com_cursos': trilhas_com_cursos,
        # 'cursos': cursos,
        # 'curadorias': curadorias,
        'mes_escolhido': mes_escolhido
    }

    return render(request, 'pfc_app/agenda_pfc.html', context)
