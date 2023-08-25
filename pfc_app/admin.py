from django.contrib import admin
from .models import Curso
from .models import Participante
from .models import CH_Valida

class CH_ValidaInline(admin.TabularInline):
    model = CH_Valida
    extra = 0

class CursoAdmin(admin.ModelAdmin):
    inlines = [ CH_ValidaInline ]
    list_display = ('nome_curso', 'data_inicio', 'data_termino', 'vagas', 'status')
    fields = ['nome_curso', 'modalidade', 'tipo_reconhecimento', 'ch_curso', 'vagas',
               'categoria', 'competencia', ('data_inicio', 'data_termino'), 
               'inst_certificadora', 'inst_promotora', 'gestor', 'status']
    class Meta:
        model = Curso

# Register your models here.
admin.site.register(Curso, CursoAdmin)
admin.site.register(Participante)
admin.site.register(CH_Valida)

admin.site.site_header = 'PFC'