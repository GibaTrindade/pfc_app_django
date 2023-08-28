from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from .models import Curso

# Create your views here.

def cursos(request):
  lista_cursos = Curso.objects.all().values()
  template = loader.get_template('base.html')
  context = {
    'cursos': lista_cursos,
  }
  return HttpResponse(template.render(context, request))