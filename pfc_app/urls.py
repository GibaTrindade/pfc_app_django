from django.urls import path, re_path, include
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('accounts/login/', views.login, name='login'),
    path('registrar/', views.registrar, name='registrar'),
    path('logout/', views.logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('cursos/', views.cursos, name='lista_cursos'),
    path('ch/', views.carga_horaria, name='carga_horaria'),
    path('inscricoes/', views.inscricoes, name='inscricoes'),
    path('curso_detail/<int:pk>', views.CursoDetailView.as_view(), name='detail_curso'),
    path('curso_detail/<int:pk>/<str:lotado>', views.CursoDetailView.as_view(), name='detail_curso'),
    path('sucesso_inscricao/', views.sucesso_inscricao, name='sucesso_inscricao'),
    path('inscricao_existente/', views.inscricao_existente, name='inscricao_existente'),
    path('inscrever/<int:curso_id>/', views.inscrever, name='inscrever_curso'),
    path('avaliacao/<int:curso_id>/', views.avaliacao, name='avaliacao'),
    path('inscricao_cancelar/<int:inscricao_id>/', views.cancelar_inscricao, name='cancelar_inscricao'),
    path('validar_ch/', views.validar_ch, name='validar_ch'),
    path('download_all_pdfs/', views.download_all_pdfs, name='download_all_pdfs'),
    path('generate_all_pdfs/<int:curso_id>/', views.generate_all_pdfs, name='generate_all_pdfs'),
    path('generate_all_pdfs/<int:curso_id>/<int:unico>/', views.generate_all_pdfs, name='generate_all_pdfs'),
    path('generate_single_pdf/<int:inscricao_id>/', views.generate_single_pdf, name='generate_single_pdf'),
    path('reset-password/', views.reset_password_request, name='reset_password_request'),
    path('change-password/', views.change_password, name='change_password'),
    path('generate_reconhecimento/<int:validacao_id>/', views.generate_all_reconhecimento, name='generate_reconhecimento'),
    path('explorer/', include('explorer.urls')),
    path('usuarios_sem_ch/', views.usuarios_sem_ch, name='usuarios_sem_ch'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)