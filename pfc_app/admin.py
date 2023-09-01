from django.contrib import admin
from .models import Curso
from .models import User
from .models import Inscricao

class InscricaoInline(admin.TabularInline):
    model = Inscricao
    extra = 0

class CursoAdmin(admin.ModelAdmin):
    inlines = [ InscricaoInline ]
    list_display = ('nome_curso', 'data_inicio', 'data_termino', 'vagas', 'status')
    fields = ['nome_curso', 'modalidade', 'tipo_reconhecimento', 'ch_curso', 'vagas',
               'categoria', 'competencia', ('data_inicio', 'data_termino'), 
               'inst_certificadora', 'inst_promotora', 'coordenador', 'status']
    
    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.coordenador != request.user:
            return False
        return True
    
    class Meta:
        model = Curso

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'nome', 'cpf', 'email')

class IncricaoAdmin(admin.ModelAdmin):
    list_display = ('curso', 'participante', 'condicao_na_acao', 'ch_valida', 'status')

# Register your models here.
admin.site.register(Curso, CursoAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Inscricao, IncricaoAdmin)

admin.site.site_header = 'PFC'