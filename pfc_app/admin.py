from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Curso
from .models import User
from .models import Inscricao

class InscricaoInline(admin.TabularInline):
    model = Inscricao
    extra = 0
    fields = ['curso', 'participante', 'condicao_na_acao', 'status']
    list_display = ('curso', 'participante', 'ch_valida', 'condicao_na_acao', 'status')

class CursoAdmin(admin.ModelAdmin):
    inlines = [ InscricaoInline ]
    list_display = ('nome_curso', 'data_inicio', 'data_termino', 'vagas', 'status')
    fields = ['nome_curso', 'modalidade', 'tipo_reconhecimento', 'ch_curso', 'vagas',
               'categoria', 'competencia', ('data_inicio', 'data_termino'), 
               'inst_certificadora', 'inst_promotora', 'coordenador', 'status']
    class Meta:
        model = Curso

class CustomUserAdmin(UserAdmin):
    #add_form = UserCreationForm
    #form = UserChangeForm
    model = User
    list_display = ('username', 'nome', 'cpf', 'email')
    #fieldsets = (
    #    (None, {'fields': ('username', 'email', 'password', 'first_name', 'last_name', 'cpf', 'nome', 'lotacao', 'role')}),
    #    ('Permissions', {'fields': ('is_staff', 'is_active')}),
    #)
    #add_fieldsets = (
    #    (None, {
    #        'classes': ('wide',),
     #       'fields': ('username', 'email', 'password1', 'password2', 'first_name', 'last_name', 'cpf', 'nome', 'lotacao', 'role', 'is_staff', 'is_active')}
    #    ),
    #)

class IncricaoAdmin(admin.ModelAdmin):
    list_display = ('curso', 'participante', 'condicao_na_acao', 'ch_valida', 'status')

# Register your models here.
admin.site.register(Curso, CursoAdmin)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Inscricao, IncricaoAdmin)

admin.site.site_header = 'PFC'