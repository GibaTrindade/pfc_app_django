from django.urls import path
from . import views

urlpatterns = [
    path('cursos/', views.cursos, name='lista_cursos'),
    path('ch/', views.carga_horaria, name='carga_horaria'),
    path('inscricoes/', views.inscricoes, name='inscricoes'),
    path('curso_detail/<int:pk>', views.CursoDetailView.as_view(), name='detail_curso'),
    path('sucesso_inscricao/', views.sucesso_inscricao, name='sucesso_inscricao'),
    path('inscricao_existente/', views.inscricao_existente, name='inscricao_existente'),
    path('inscrever/<int:curso_id>/', views.inscrever, name='inscrever_curso'),
    path('avaliacao/<int:curso_id>/', views.avaliacao, name='avaliacao'),
    path('inscricao_cancelar/<int:inscricao_id>/', views.cancelar_inscricao, name='cancelar_inscricao'),

]