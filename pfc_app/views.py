from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.template import loader
from .models import Curso, Inscricao
from django.db.models import Count, Q, Sum
from datetime import date

# Create your views here.
@login_required
def cursos(request):
  lista_cursos = Curso.objects.all()
  data_atual = date.today()
  cursos_com_inscricoes = Curso.objects.annotate(
        num_inscricoes=Count('inscricao', filter=~Q(inscricao__condicao_na_acao='DOCENTE') & ~Q(inscricao__status__nome='CANCELADA'))
    ).order_by('data_inicio').all()#.filter(data_inicio__gt=data_atual)
  #template = loader.get_template('base.html')
  context = {
    'cursos': cursos_com_inscricoes,
  }
  #print(context['cursos'][1].inscricao_set.count())
  return render(request, 'pfc_app/lista_cursos.html' ,context)


@login_required
def carga_horaria(request):
  inscricoes_do_usuario = Inscricao.objects.filter(participante=request.user)
    
  # Calcula a soma da carga horária das inscrições do usuário
  carga_horaria_total = inscricoes_do_usuario.aggregate(Sum('ch_valida'))['ch_valida__sum'] or 0
  
  context = {
      'carga_horaria_total': carga_horaria_total,
  }

  return render(request, 'pfc_app/carga_horaria.html' ,context)


@login_required
def inscricoes(request):
    inscricoes_do_usuario = Inscricao.objects.filter(participante=request.user)
    
    context = {
        'inscricoes': inscricoes_do_usuario,
    }
    
    return render(request, 'pfc_app/inscricoes.html', context)