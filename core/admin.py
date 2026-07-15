from django.contrib import admin

from .models import (
    Atividade,
    CarimboPassaporte,
    CategoriaProgramacao,
    Hospede,
    Hotel,
    InscricaoAtividade,
    InscricaoPasseio,
    LocalAtividade,
    MensagemReuniao,
    NoiteTematica,
    Passeio,
    PassaporteHospede,
    PerfilUsuario,
    PontoBatida,
    PresencaRegistro,
    ProdutoLoja,
    EventoRecreacao,
    ProgramacaoDiaria,
    Recreador,
    SalaReuniao,
    VendaLoja,
)


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('nome', 'rede_marca', 'cidade', 'cor_primaria', 'pix_chave', 'ativo')
    list_filter = ('ativo', 'rede_marca', 'estado')
    search_fields = ('nome', 'slug', 'cidade')
    prepopulated_fields = {'slug': ('nome',)}
    fieldsets = (
        (None, {'fields': ('nome', 'slug', 'rede_marca', 'slogan', 'ativo')}),
        ('Localização e contato', {
            'fields': ('endereco', 'cidade', 'estado', 'telefone', 'whatsapp_setor_pagamentos'),
        }),
        ('Cores do tema', {'fields': ('cor_primaria', 'cor_secundaria', 'cor_destaque', 'cor_terciaria')}),
        ('Pagamento PIX (passeios)', {'fields': ('pix_chave', 'pix_beneficiario')}),
    )


@admin.register(CategoriaProgramacao)
class CategoriaProgramacaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'idade_min', 'idade_max', 'cor', 'ordem')
    ordering = ('ordem',)
    search_fields = ('nome', 'descricao_atividades')


@admin.register(Hospede)
class HospedeAdmin(admin.ModelAdmin):
    list_display = (
        'nome_completo', 'hotel', 'apartamento', 'documento',
        'data_checkin', 'data_checkout', 'faixa_etaria_display',
    )
    list_filter = ('hotel', 'data_checkin', 'data_checkout')
    search_fields = ('nome_completo', 'documento', 'apartamento')
    readonly_fields = ('faixa_etaria_display', 'idade_display')
    date_hierarchy = 'data_checkin'

    @admin.display(description='faixa etária')
    def faixa_etaria_display(self, obj):
        return obj.get_faixa_etaria_display()

    @admin.display(description='idade')
    def idade_display(self, obj):
        return obj.idade


@admin.register(Recreador)
class RecreadorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'hotel', 'telefone', 'tem_pin_display', 'ativo')
    list_filter = ('hotel', 'ativo')
    search_fields = ('nome',)
    readonly_fields = ('pin_hash', 'pin_atualizado_em')

    @admin.display(boolean=True, description='tem PIN')
    def tem_pin_display(self, obj):
        return obj.tem_pin


@admin.register(PontoBatida)
class PontoBatidaAdmin(admin.ModelAdmin):
    list_display = ('recreador', 'hotel', 'tipo', 'extra_plantao', 'registrado_em')
    list_filter = ('hotel', 'tipo', 'extra_plantao', 'registrado_em')
    search_fields = ('recreador__nome',)
    readonly_fields = ('hotel', 'recreador', 'tipo', 'extra_plantao', 'registrado_em', 'foto_auditoria', 'ip', 'user_agent', 'registrado_por')
    date_hierarchy = 'registrado_em'


@admin.register(LocalAtividade)
class LocalAtividadeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'hotel', 'capacidade_maxima', 'ativo')
    list_filter = ('hotel', 'ativo')
    search_fields = ('nome',)


@admin.register(Atividade)
class AtividadeAdmin(admin.ModelAdmin):
    list_display = ('nome', 'hotel', 'categoria', 'local_padrao', 'icone', 'ativo')
    list_filter = ('hotel', 'categoria', 'ativo')
    search_fields = ('nome',)


class InscricaoAtividadeInline(admin.TabularInline):
    model = InscricaoAtividade
    extra = 0


class PresencaRegistroInline(admin.TabularInline):
    model = PresencaRegistro
    extra = 0


@admin.register(ProgramacaoDiaria)
class ProgramacaoDiariaAdmin(admin.ModelAdmin):
    list_display = (
        'data', 'hora_inicio', 'atividade', 'categoria', 'local',
        'recreador', 'hotel', 'realizado', 'vagas_total', 'vagas_ocupadas_display',
    )
    list_filter = ('hotel', 'data', 'categoria')
    search_fields = ('atividade__nome', 'local__nome')
    date_hierarchy = 'data'
    inlines = [InscricaoAtividadeInline, PresencaRegistroInline]

    @admin.display(description='inscritos')
    def vagas_ocupadas_display(self, obj):
        return obj.vagas_ocupadas


@admin.register(EventoRecreacao)
class EventoRecreacaoAdmin(admin.ModelAdmin):
    list_display = (
        'data_inicio', 'nome', 'hotel', 'prestador', 'orcamento', 'status', 'responsavel',
    )
    list_filter = ('hotel', 'status', 'mes_referencia')
    search_fields = ('nome', 'prestador', 'descricao')
    date_hierarchy = 'data_inicio'


@admin.register(PresencaRegistro)
class PresencaRegistroAdmin(admin.ModelAdmin):
    list_display = ('hospede', 'programacao', 'presente', 'registrado_em', 'registrado_por')
    list_filter = ('presente', 'programacao__hotel', 'programacao__data')
    search_fields = ('hospede__nome_completo',)


@admin.register(NoiteTematica)
class NoiteTematicaAdmin(admin.ModelAdmin):
    list_display = ('hotel', 'dia_semana', 'tema', 'atracao_musical', 'cor_dominante')
    list_filter = ('hotel', 'dia_semana')
    search_fields = ('tema', 'atracao_musical')


@admin.register(Passeio)
class PasseioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'hotel', 'dia_semana', 'hora_saida', 'vagas', 'preco', 'ativo')
    list_filter = ('hotel', 'dia_semana', 'ativo')
    search_fields = ('titulo',)
    fields = (
        'hotel', 'dia_semana', 'titulo', 'descricao', 'hora_saida', 'hora_retorno',
        'ponto_encontro', 'vagas', 'preco', 'pix_chave', 'pix_beneficiario', 'ordem', 'ativo',
    )


@admin.register(InscricaoPasseio)
class InscricaoPasseioAdmin(admin.ModelAdmin):
    list_display = ('hospede', 'passeio', 'data', 'status_pagamento', 'valor', 'criado_em')
    list_filter = ('status_pagamento', 'data', 'passeio__hotel')
    search_fields = ('hospede__nome_completo', 'passeio__titulo')


@admin.register(ProdutoLoja)
class ProdutoLojaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'cor_tema', 'hotel', 'ativo')
    list_filter = ('categoria', 'ativo')


@admin.register(VendaLoja)
class VendaLojaAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'hotel', 'quantidade', 'valor_total', 'forma_pagamento', 'criado_em')
    list_filter = ('hotel', 'forma_pagamento', 'criado_em')
    date_hierarchy = 'criado_em'


class CarimboPassaporteInline(admin.TabularInline):
    model = CarimboPassaporte
    extra = 0


@admin.register(PassaporteHospede)
class PassaporteHospedeAdmin(admin.ModelAdmin):
    list_display = ('hospede', 'total_carimbos_display', 'criado_em')
    inlines = [CarimboPassaporteInline]

    @admin.display(description='carimbos')
    def total_carimbos_display(self, obj):
        return obj.total_carimbos


@admin.register(SalaReuniao)
class SalaReuniaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'hotel', 'jitsi_room', 'ativa', 'criado_em')
    list_filter = ('ativa', 'hotel')
    prepopulated_fields = {'slug': ('nome',)}


@admin.register(MensagemReuniao)
class MensagemReuniaoAdmin(admin.ModelAdmin):
    list_display = ('sala', 'autor', 'texto_curto', 'criado_em')
    list_filter = ('sala',)

    @admin.display(description='mensagem')
    def texto_curto(self, obj):
        return obj.texto[:60]


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('user', 'papel', 'hotel', 'ativo', 'atualizado_em')
    list_filter = ('papel', 'ativo', 'hotel')
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user',)
