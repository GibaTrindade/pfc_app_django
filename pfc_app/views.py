from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
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
                    Tema, Subtema, Carreira, Modalidade, Categoria
from .forms import AvaliacaoForm, DateFilterForm
from django.db.models import Count, Q, Sum, F, When, BooleanField, Exists, OuterRef, Value, Subquery
from django.db.models.functions import Coalesce, Concat
from django.contrib.postgres.aggregates import StringAgg
from django.contrib.postgres.expressions import ArraySubquery
from datetime import date, datetime
from django.views.generic import DetailView
import os
import zipfile
from django.http import HttpResponse
from django.shortcuts import get_list_or_404
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, PageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from io import BytesIO
from reportlab.lib.units import inch
from validate_docbr import CPF
from .filters import UserFilter

# Create your views here.
def dashboard(request):
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
        return redirect('lista_cursos')

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
                             ~Q(inscricao__status__nome='EM FILA') 
                             ),
        usuario_inscrito=Exists(
           Inscricao.objects.filter(participante=request.user, curso=OuterRef('pk'))
                                ),
        lista_inscritos = subquery,
        lista_docentes = subquery_docentes,
        status_inscricao = status_inscricao
        
    ).order_by('data_inicio').all().filter(data_inicio__gt=data_atual)
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
  for curso in cursos_com_inscricoes:
      print(curso.lista_docentes)

  context = {
    'cursos': cursos_com_inscricoes,
  }
  #print(context['cursos'][1].inscricao_set.count())
  return render(request, 'pfc_app/lista_cursos.html' ,context)

@login_required
def usuarios_sem_ch(request):

    # Filter users with a total load less than 60
    users = User.objects.annotate(
        total_ch_inscricao=Coalesce(Sum('inscricao__ch_valida', filter=Q(inscricao__concluido=True, inscricao__curso__status__nome='FINALIZADO'), distinct=True), 0),
        total_ch_validacao=Coalesce(Sum('requerente_validacao__ch_confirmada', filter=Q(requerente_validacao__status__nome='DEFERIDA'), distinct=True), 0)
    ).annotate(
        total_ch=F('total_ch_inscricao') + F('total_ch_validacao')
    ).filter(grupo_ocupacional='GGOV').order_by('nome')

    # Calculate remaining load needed to reach 60
    users = users.annotate(ch_faltante=60 - F('total_ch'))

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


class CursoDetailView(DetailView):
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
        ~Q(condicao_na_acao='DOCENTE'),
        curso=curso
    ).count()
    
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
    pfc_relative_path = 'PFC1.png'
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

        tag_mapping = {
            "[cpf]": cpf_formatado,
            "[data_envio]": validacao.enviado_em.strftime("%d/%m/%Y"),
            "[lotacao]": user.lotacao,
            "[nome_curso]": validacao.nome_curso,
            "[instituicao_promotora]": validacao.instituicao_promotora,
            "[data_inicio]": validacao.data_inicio_curso.strftime("%d/%m/%Y"),
            "[data_termino]": validacao.data_termino_curso.strftime("%d/%m/%Y"),
            "[ch_valida]": validacao.ch_confirmada,
            "[data_analise]": dateformat.format(datetime.now(), 'd \d\e F \d\e Y'),
            "[responsavel_analise]": validacao.responsavel_analise
        }

# Substitua as tags pelo valor correspondente no texto
        for tag, value in tag_mapping.items():
            requerimento = requerimento.replace(tag, str(value))
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
        
        width, height = A4
        print(width)
        print(height)
        c = canvas.Canvas(pdf_filename, pagesize=A4)
        p_title=Paragraph("ANÁLISE PARA RECONHECIMENTO DE CARGA HORÁRIA", style_title)
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
        pfc_relative_path = 'PFC1.png'
        seplag_relative_path = 'seplag-transp-horizontal.png'


        # Construa o caminho absoluto usando 'settings.STATIC_ROOT'
       
        assinatura_path = os.path.join(settings.MEDIA_ROOT, assinatura_relative_path)
        igpe_path = os.path.join(settings.MEDIA_ROOT, igpe_relative_path)
        egape_path = os.path.join(settings.MEDIA_ROOT, egape_relative_path)
        pfc_path = os.path.join(settings.MEDIA_ROOT, pfc_relative_path)
        seplag_path = os.path.join(settings.MEDIA_ROOT, seplag_relative_path)




        # Desenhe a imagem como fundo
        
        c.drawImage(assinatura_path, 200, 80, width=196, height=63, preserveAspectRatio=True, mask='auto')
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
        
        
        print(p_subtitle.height)
        
        
        #p_subtitle2.wrapOn(c, 500, 100)
        #p_subtitle2.drawOn(c, width-800, height-190)
        
        c.save()
        
        
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