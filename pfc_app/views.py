from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages, auth
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.urls import reverse
import random
import string
from django.utils.encoding import force_bytes
from django.contrib.auth import update_session_auth_hash
from django.db import IntegrityError
from django.http import HttpResponse
from django.template import loader
from .models import Curso, Inscricao, StatusInscricao, Avaliacao, Validacao_CH, StatusValidacao, User, Certificado
from .forms import AvaliacaoForm, DateFilterForm
from django.db.models import Count, Q, Sum, Case, When, BooleanField, Exists, OuterRef, Value
from django.db.models.functions import Concat
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

# Create your views here.

def login(request):
    if request.method != 'POST':
        return render(request, 'pfc_app/login.html')

    usuario = request.POST.get('usuario')
    senha = request.POST.get('senha')

    user = auth.authenticate(username=usuario, password=senha)

    if not user:
        messages.error(request, 'Usuário ou senha inválidos!')
        return render(request, 'pfc_app/login.html')
    else:
        auth.login(request, user)
        messages.success(request, 'Seja bem vindo!')
        return redirect('lista_cursos')

    return render(request, 'pfc_app/login.html')

def logout(request):
    auth.logout(request)
    return redirect('login')




@login_required
def cursos(request):
  lista_cursos = Curso.objects.all()
  data_atual = date.today()
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
  
  cursos_com_inscricoes = Curso.objects.annotate(
        num_inscricoes=Count('inscricao', 
                             filter=~Q(inscricao__condicao_na_acao='DOCENTE') & 
                             ~Q(inscricao__status__nome='CANCELADA') &
                             ~Q(inscricao__status__nome='EM FILA') 
                             ),
        usuario_inscrito=Exists(
           Inscricao.objects.filter(participante=request.user, curso=OuterRef('pk'))
                                ),
        lista_inscritos = subquery
        
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
  context = {
    'cursos': cursos_com_inscricoes,
  }
  #print(context['cursos'][1].inscricao_set.count())
  return render(request, 'pfc_app/lista_cursos.html' ,context)


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
  satus_validacao = StatusValidacao.objects.get(nome='APROVADA')
  validacoes = Validacao_CH.objects.filter(usuario=request.user, status=satus_validacao)
  
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
    
  # Calcula a soma da carga horária das inscrições do usuário
  carga_horaria_pfc = inscricoes_do_usuario.aggregate(Sum('ch_valida'))['ch_valida__sum'] or 0
  validacoes_ch = validacoes.aggregate(Sum('ch_confirmada'))['ch_confirmada__sum'] or 0
  carga_horaria_total = carga_horaria_pfc + validacoes_ch

  context = {
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

        # Verifique se há uma inscrição do tipo 'DOCENTE' relacionada a este curso
        inscricoes_docentes = Inscricao.objects.filter(curso=curso, condicao_na_acao='DOCENTE')

        usuarios_docentes = [inscricao.participante for inscricao in inscricoes_docentes]

        # Adicione o usuário docente ao contexto
        context['usuarios_docentes'] = usuarios_docentes

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
       return render(request, 'pfc_app/inscricoes.html')
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
      if curso.eh_evento:
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
        form = AvaliacaoForm(request.POST)
        if form.is_valid():
            # Faça o que for necessário com os dados da avaliação, como salvá-los no banco de dados
            usuario = request.user
            ja_avaliado=Avaliacao.objects.filter(participante=usuario, curso=curso)
            
            if ja_avaliado:
                messages.error(request, f"Avaliação já realizada!")
                return redirect('inscricoes')
            


            avaliacao = form.save(commit=False)
            avaliacao.participante = usuario
            
            avaliacao.curso = curso
            #form.save()
            avaliacao.save()
            # Redirecione para uma página de sucesso ou outra ação apropriada
            messages.success(request, 'Avaliação Realizada!')
            return redirect('inscricoes')
        messages.error(request, form.errors)
            #return render(request, 'sucesso.html')
       #else:
           #messages.error(request, 'Nenhum item pode ficar em branco')
           #return render(request, 'pfc_app/avaliacao.html', {'form': form})

    else:
        form = AvaliacaoForm()

    return render(request, 'pfc_app/avaliacao.html', {'form': form, 'curso':curso})


def enviar_pdf(request):
    if request.method == 'POST':
        status_validacao = StatusValidacao.objects.get(nome="PENDENTE")
        arquivo_pdf = request.FILES['arquivo_pdf']
        nome_curso = request.POST['nome_curso']
        ch_solicitada = request.POST['ch_solicitada']
        data_inicio = request.POST['data_inicio']
        data_termino = request.POST['data_termino']
        instituicao_promotora = request.POST['instituicao_promotora']
        ementa = request.POST['ementa']
        try:
            agenda_pfc_check = request.POST['agenda_pfc']
            agenda_pfc = True
        except:
            agenda_pfc = False
      
        try:
           ch_solicitada = int(ch_solicitada)
        except:
            messages.error(request, 'O campo carga horária precisa ser númerico!')
            return redirect('enviar_pdf')
        avaliacao = Validacao_CH(usuario=request.user, arquivo_pdf=arquivo_pdf, 
                                 nome_curso=nome_curso, ch_solicitada=ch_solicitada, 
                                 data_termino_curso=data_termino, data_inicio_curso = data_inicio,
                                 instituicao_promotora=instituicao_promotora, ementa=ementa, 
                                 agenda_pfc=agenda_pfc, status=status_validacao)
        avaliacao.save()
        # Redirecionar ou fazer algo após o envio bem-sucedido
        messages.success(request, 'Arquivo enviado com sucesso!')
        return redirect('enviar_pdf')

    return render(request, 'pfc_app/enviar_pdf.html')


def download_all_pdfs(request):
    return render(request, 'pfc_app/download_all_pdfs.html')


def generate_all_pdfs(request, curso_id):
    try:
      curso = Curso.objects.get(pk=curso_id)
    except:
       messages.error(request, f"Curso não encontrado!")
       return redirect('lista_cursos')
    

    certificado = Certificado.objects.get(codigo='conclusao')
    #texto_certificado = certificado.texto
    users = curso.participantes.all()

    output_folder = "pdf_output"  # Pasta onde os PDFs temporários serão salvos
    zip_filename = "all_pdfs.zip"

    # Crie a pasta de saída se ela não existir
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Crie o arquivo ZIP
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for user in users:
            # Verifica o status da incrição do usuário, 
            # se não estiver concluída pula esse usuário.
            try:
                inscricao = Inscricao.objects.get(participante=user, curso=curso, concluido=True)
            except:
                continue
            
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
            igpe_relative_path = 'Igpe.jpg'
            egape_relative_path = 'Egape.jpg'
            pfc_relative_path = 'PFC1.png'
            seplag_relative_path = 'seplag-transp-horizontal.png'


            # Construa o caminho absoluto usando 'settings.STATIC_ROOT'
            imagem_path = os.path.join(settings.MEDIA_ROOT, imagem_relative_path)
            assinatura_path = os.path.join(settings.MEDIA_ROOT, assinatura_relative_path)
            igpe_path = os.path.join(settings.MEDIA_ROOT, igpe_relative_path)
            egape_path = os.path.join(settings.MEDIA_ROOT, egape_relative_path)
            pfc_path = os.path.join(settings.MEDIA_ROOT, pfc_relative_path)
            seplag_path = os.path.join(settings.MEDIA_ROOT, seplag_relative_path)




            # Desenhe a imagem como fundo
            c.drawImage(imagem_path, 230, 0, width=width, height=height, preserveAspectRatio=True, mask='auto')
            c.drawImage(assinatura_path, 130, 100, width=196, height=63, preserveAspectRatio=True, mask='auto')
            c.drawImage(igpe_path, width-850, 20, width=196, height=63, preserveAspectRatio=True, mask='auto')
            c.drawImage(egape_path, width-650, 20, width=196, height=63, preserveAspectRatio=True, mask='auto')
            c.drawImage(pfc_path, width-450, 20, width=196, height=63, preserveAspectRatio=True, mask='auto')
            c.drawImage(seplag_path, width-250, 20, width=196, height=63, preserveAspectRatio=True, mask='auto')
            p_title.wrapOn(c, 500, 100)
            p_title.drawOn(c, width-800, height-100)
            p_subtitle.wrapOn(c, 500, 100)
            p_subtitle.drawOn(c, width-800, height-165)
            p_subtitle2.wrapOn(c, 500, 100)
            p_subtitle2.drawOn(c, width-800, height-190)
            p1.wrapOn(c, 500, 100)
            p1.drawOn(c, width-800, height-300)
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
    zip_filename = "all_pdfs.zip"

    # Crie a pasta de saída se ela não existir
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Crie o arquivo ZIP
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
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

        # Construa o caminho absoluto usando 'settings.STATIC_ROOT'
        imagem_path = os.path.join(settings.MEDIA_ROOT, imagem_relative_path)
        assinatura_path = os.path.join(settings.MEDIA_ROOT, assinatura_relative_path)




        # Desenhe a imagem como fundo
        c.drawImage(imagem_path, 230, 0, width=width, height=height, preserveAspectRatio=True, mask='auto')
        c.drawImage(assinatura_path, 130, 100, width=196, height=63, preserveAspectRatio=True, mask='auto')
        p_title.wrapOn(c, 500, 100)
        p_title.drawOn(c, width-800, height-100)
        p_subtitle.wrapOn(c, 500, 100)
        p_subtitle.drawOn(c, width-800, height-165)
        p_subtitle2.wrapOn(c, 500, 100)
        p_subtitle2.drawOn(c, width-800, height-190)
        p1.wrapOn(c, 500, 100)
        p1.drawOn(c, width-800, height-300)
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



def generate_all_reconhecimento(request, validacao_id):
    try:
      validacao = Validacao_CH.objects.get(pk=validacao_id)
    except:
       messages.error(request, f"Validação não encontrada!")
       return redirect('lista_cursos')
    
    try:
        requerimento = validacao.requerimento_ch.do_requerimento
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
            "[data_envio]": validacao.enviado_em,
            "[lotacao]": user.lotacao,
            "[nome_curso]": validacao.nome_curso,
            "[instituicao_promotora]": validacao.instituicao_promotora,
            "[data_inicio]": validacao.data_inicio_curso,
            "[data_termino]": validacao.data_termino_curso,
            "[ch_valida]": validacao.ch_confirmada,
        }

# Substitua as tags pelo valor correspondente no texto
        for tag, value in tag_mapping.items():
            requerimento = requerimento.replace(tag, str(value))

        texto_customizado = requerimento
        pdf_filename = os.path.join(output_folder, f"{user.username}-requerimento.pdf")
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
        
        width, height = A4
        print(width)
        print(height)
        c = canvas.Canvas(pdf_filename, pagesize=A4)
        p_title=Paragraph("Analise de Requerimento", style_title)
        p_subtitle=Paragraph("Do Requerimento", style_subtitle)
        #p_subtitle2=Paragraph(certificado.subcabecalho2, style_subtitle)
        p1=Paragraph(texto_customizado, style_body)
            # Caminho relativo para a imagem dentro do diretório 'static'
        
        assinatura_relative_path = 'assinatura.jpg'
        igpe_relative_path = 'Igpe.jpg'
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
        
        c.drawImage(assinatura_path, 130, 100, width=196, height=63, preserveAspectRatio=True, mask='auto')
        c.drawImage(igpe_path, width-850, 20, width=196, height=63, preserveAspectRatio=True, mask='auto')
        c.drawImage(egape_path, width-650, 20, width=196, height=63, preserveAspectRatio=True, mask='auto')
        c.drawImage(pfc_path, width-450, 20, width=196, height=63, preserveAspectRatio=True, mask='auto')
        c.drawImage(seplag_path, width-250, 20, width=196, height=63, preserveAspectRatio=True, mask='auto')
        p_title.wrapOn(c, 500, 100)
        p_title.drawOn(c, width-500, height-100)
        p_subtitle.wrapOn(c, 500, 100)
        p_subtitle.drawOn(c, width-800, height-165)
        #p_subtitle2.wrapOn(c, 500, 100)
        #p_subtitle2.drawOn(c, width-800, height-190)
        p1.wrapOn(c, 500, 100)
        p1.drawOn(c, width-550, height-300)
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
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, 'Senha alterada com sucesso!')
            return redirect('lista_cursos')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'pfc_app/change_password.html', {'form': form})