from django.urls import path
from . import views

urlpatterns = [
    path('cursos/', views.cursos, name='lista_cursos'),
    path('ch/', views.carga_horaria, name='carga_horaria'),
    path('inscricoes/', views.inscricoes, name='inscricoes'),
]