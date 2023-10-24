from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.cursos, name='lista_cursos'),
    path('accounts/login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('cursos/', views.cursos, name='lista_cursos'),
    path('ch/', views.carga_horaria, name='carga_horaria'),
    path('inscricoes/', views.inscricoes, name='inscricoes'),
    path('curso_detail/<int:pk>', views.CursoDetailView.as_view(), name='detail_curso'),
    path('sucesso_inscricao/', views.sucesso_inscricao, name='sucesso_inscricao'),
    path('inscricao_existente/', views.inscricao_existente, name='inscricao_existente'),
    path('inscrever/<int:curso_id>/', views.inscrever, name='inscrever_curso'),
    path('avaliacao/<int:curso_id>/', views.avaliacao, name='avaliacao'),
    path('inscricao_cancelar/<int:inscricao_id>/', views.cancelar_inscricao, name='cancelar_inscricao'),
    path('enviar_pdf/', views.enviar_pdf, name='enviar_pdf'),
    path('download_all_pdfs/', views.download_all_pdfs, name='download_all_pdfs'),
    path('generate_all_pdfs/<int:curso_id>/', views.generate_all_pdfs, name='generate_all_pdfs'),
    path('generate_single_pdf/<int:inscricao_id>/', views.generate_single_pdf, name='generate_single_pdf'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)