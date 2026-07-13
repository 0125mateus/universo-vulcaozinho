from datetime import date, time
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class RedeMarca(models.TextChoices):
    NACIONAL_INN = 'nacional_inn', 'Nacional Inn'
    EURO_SUITE = 'euro_suite', 'Euro Suite'
    DAN_INN = 'dan_inn', 'Dan Inn'
    CASSINO_RESORT = 'cassino_resort', 'Cassino Resort'


class Hotel(models.Model):
    nome = models.CharField('nome', max_length=120)
    slug = models.SlugField('slug', max_length=60, unique=True)
    rede_marca = models.CharField(
        'rede / marca',
        max_length=20,
        choices=RedeMarca.choices,
        default=RedeMarca.NACIONAL_INN,
    )
    slogan = models.CharField('slogan', max_length=200, blank=True)
    cor_primaria = models.CharField('cor primária', max_length=7, default='#1E6B43')
    cor_secundaria = models.CharField('cor secundária', max_length=7, default='#2FAE63')
    cor_destaque = models.CharField('cor destaque', max_length=7, default='#FFD43D')
    cor_terciaria = models.CharField('cor terciária (splash)', max_length=7, default='#F7941D', blank=True)
    endereco = models.CharField('endereço', max_length=255, blank=True)
    cidade = models.CharField('cidade', max_length=80, default='Poços de Caldas')
    estado = models.CharField('UF', max_length=2, default='MG')
    telefone = models.CharField('telefone', max_length=20, blank=True)
    whatsapp_setor_pagamentos = models.CharField(
        'WhatsApp setor de pagamentos',
        max_length=30,
        blank=True,
        help_text='Número com DDD para enviar planilhas financeiras (ex.: 35999998888).',
    )
    pix_chave = models.CharField(
        'chave PIX',
        max_length=140,
        blank=True,
        help_text='CPF/CNPJ, e-mail, telefone ou chave aleatória para receber pagamentos de passeios.',
    )
    pix_beneficiario = models.CharField('nome do beneficiário PIX', max_length=80, blank=True)
    ativo = models.BooleanField('ativo', default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'hotel'
        verbose_name_plural = 'hotéis'

    def __str__(self):
        return self.nome

    @property
    def tema_css(self) -> dict:
        return {
            'primaria': self.cor_primaria,
            'secundaria': self.cor_secundaria,
            'destaque': self.cor_destaque,
            'terciaria': self.cor_terciaria,
        }

    @property
    def logo_static(self) -> str:
        from .hotel_brand import hotel_logo_static_path
        return hotel_logo_static_path(self.slug)


class FaixaEtaria(models.TextChoices):
    BEBE = 'bebe', 'Bebê (0-2 anos)'
    INFANTIL = 'infantil', 'Infantil (3-11 anos)'
    ADOLESCENTE = 'adolescente', 'Adolescente (12-17 anos)'
    ADULTO = 'adulto', 'Adulto (18-59 anos)'
    IDOSO = 'idoso', 'Terceira idade (60+ anos)'


def calcular_faixa_etaria(data_nascimento: date, referencia: date | None = None) -> str:
    """Calcula a faixa etária com base na data de nascimento."""
    referencia = referencia or timezone.localdate()
    idade = referencia.year - data_nascimento.year
    if (referencia.month, referencia.day) < (data_nascimento.month, data_nascimento.day):
        idade -= 1

    if idade <= 2:
        return FaixaEtaria.BEBE
    if idade <= 11:
        return FaixaEtaria.INFANTIL
    if idade <= 17:
        return FaixaEtaria.ADOLESCENTE
    if idade <= 59:
        return FaixaEtaria.ADULTO
    return FaixaEtaria.IDOSO


class Hospede(models.Model):
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.PROTECT,
        related_name='hospedes',
        verbose_name='hotel',
    )
    nome_completo = models.CharField('nome completo', max_length=200)
    data_nascimento = models.DateField('data de nascimento')
    documento = models.CharField('documento', max_length=30)
    apartamento = models.CharField('apartamento', max_length=20)
    data_checkin = models.DateField('data check-in', default=date.today)
    data_checkout = models.DateField('data check-out', null=True, blank=True)
    observacoes = models.TextField('observações', blank=True)
    responsavel_nome = models.CharField('nome do responsável', max_length=200, blank=True)
    responsavel_documento = models.CharField('documento do responsável', max_length=30, blank=True)
    responsavel_parentesco = models.CharField(
        'parentesco',
        max_length=40,
        blank=True,
        choices=[
            ('mae', 'Mãe'),
            ('pai', 'Pai'),
            ('avo', 'Avô/Avó'),
            ('tio', 'Tio/Tia'),
            ('responsavel_legal', 'Responsável legal'),
            ('outro', 'Outro'),
        ],
    )
    responsavel_telefone = models.CharField('telefone do responsável', max_length=30, blank=True)
    responsavel_assinatura = models.TextField(
        'assinatura do responsável',
        blank=True,
        help_text='Imagem da assinatura capturada no check-in (data URL PNG).',
    )
    responsavel_assinado_em = models.DateTimeField('assinado em', null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_checkin', 'nome_completo']
        verbose_name = 'hóspede'
        verbose_name_plural = 'hóspedes'
        indexes = [
            models.Index(fields=['hotel', 'documento']),
            models.Index(fields=['hotel', 'data_checkout']),
        ]

    def __str__(self):
        return f'{self.nome_completo} — apt. {self.apartamento}'

    @property
    def idade(self) -> int:
        hoje = timezone.localdate()
        anos = hoje.year - self.data_nascimento.year
        if (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day):
            anos -= 1
        return anos

    @property
    def is_menor_idade(self) -> bool:
        return self.idade < 18

    @property
    def tem_assinatura_responsavel(self) -> bool:
        return bool(self.responsavel_assinatura)

    @property
    def faixa_etaria(self) -> str:
        return calcular_faixa_etaria(self.data_nascimento)

    def get_faixa_etaria_display(self) -> str:
        return FaixaEtaria(self.faixa_etaria).label

    @property
    def categoria_recreacao(self):
        return CategoriaProgramacao.objects.filter(
            idade_min__lte=self.idade,
            idade_max__gte=self.idade,
        ).first()

    @property
    def ativo(self) -> bool:
        if self.data_checkout is None:
            return True
        return self.data_checkout >= timezone.localdate()

    def clean(self):
        super().clean()
        if self.data_checkout and self.data_checkout < self.data_checkin:
            raise ValidationError({'data_checkout': 'Check-out não pode ser anterior ao check-in.'})

        if not self.hotel_id:
            return

        from .documento_utils import documento_duplicado_ativo

        if documento_duplicado_ativo(self.hotel, self.documento, exclude_pk=self.pk):
            raise ValidationError(
                {'documento': 'Já existe hóspede ativo com este documento neste hotel.'}
            )


class Recreador(models.Model):
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.PROTECT,
        related_name='recreadores',
        verbose_name='hotel',
    )
    nome = models.CharField('nome', max_length=120)
    telefone = models.CharField('telefone', max_length=20, blank=True)
    ativo = models.BooleanField('ativo', default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'recreador'
        verbose_name_plural = 'recreadores'

    def __str__(self):
        return self.nome


class LocalAtividade(models.Model):
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.PROTECT,
        related_name='locais',
        verbose_name='hotel',
    )
    nome = models.CharField('nome', max_length=120)
    descricao = models.TextField('descrição', blank=True)
    capacidade_maxima = models.PositiveIntegerField('capacidade máxima', default=50)
    ativo = models.BooleanField('ativo', default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'local de atividade'
        verbose_name_plural = 'locais de atividade'
        unique_together = [('hotel', 'nome')]

    def __str__(self):
        return f'{self.nome} ({self.hotel.nome})'


class CategoriaProgramacao(models.Model):
    """Colunas da grade de programação diária (Vulcão Kids, Boys & Girls, etc.)."""

    codigo = models.SlugField('código', max_length=30, unique=True)
    nome = models.CharField('nome', max_length=80)
    idade_min = models.PositiveSmallIntegerField('idade mínima')
    idade_max = models.PositiveSmallIntegerField('idade máxima')
    cor = models.CharField('cor', max_length=7, default='#1E6B43')
    icone = models.CharField('ícone', max_length=8, default='🌋')
    descricao_atividades = models.TextField(
        'atividades típicas',
        blank=True,
        help_text='Tipos de atividades desta faixa (ex.: caça ao tesouro, gincanas).',
    )
    ordem = models.PositiveSmallIntegerField('ordem', default=0)

    class Meta:
        ordering = ['ordem']
        verbose_name = 'faixa etária / categoria'
        verbose_name_plural = 'faixas etárias / categorias'

    def __str__(self):
        return f'{self.nome} ({self.idade_min}–{self.idade_max} anos)'

    @property
    def faixa_label(self) -> str:
        return f'{self.idade_min} a {self.idade_max} anos'


def categoria_recreacao_por_idade(idade: int) -> str | None:
    """Retorna o código da categoria de recreação para uma idade."""
    cat = CategoriaProgramacao.objects.filter(
        idade_min__lte=idade,
        idade_max__gte=idade,
    ).order_by('ordem').first()
    return cat.codigo if cat else None


class Atividade(models.Model):
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.PROTECT,
        related_name='atividades',
        verbose_name='hotel',
    )
    nome = models.CharField('nome', max_length=120)
    descricao = models.TextField('descrição', blank=True)
    frase_chamada = models.CharField('frase de chamada', max_length=200, blank=True)
    icone = models.CharField('ícone', max_length=8, default='⭐')
    categoria = models.ForeignKey(
        CategoriaProgramacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='atividades',
        verbose_name='categoria',
    )
    local_padrao = models.ForeignKey(
        LocalAtividade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='atividades_padrao',
        verbose_name='local padrão',
    )
    duracao_minutos = models.PositiveIntegerField('duração (min)', default=60)
    capacidade_maxima = models.PositiveIntegerField(
        'capacidade máxima',
        null=True,
        blank=True,
        help_text='Se vazio, usa a capacidade do local.',
    )
    ativo = models.BooleanField('ativo', default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'atividade'
        verbose_name_plural = 'atividades'
        unique_together = [('hotel', 'nome')]

    def __str__(self):
        return self.nome

    def capacidade_efetiva(self, local: 'LocalAtividade | None' = None) -> int:
        if self.capacidade_maxima:
            return self.capacidade_maxima
        local = local or self.local_padrao
        if local:
            return local.capacidade_maxima
        return 0


class ProgramacaoDiaria(models.Model):
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.PROTECT,
        related_name='programacoes',
        verbose_name='hotel',
    )
    data = models.DateField('data')
    hora_inicio = models.TimeField('início')
    hora_fim = models.TimeField('término')
    atividade = models.ForeignKey(
        Atividade,
        on_delete=models.PROTECT,
        related_name='programacoes',
        verbose_name='atividade',
    )
    local = models.ForeignKey(
        LocalAtividade,
        on_delete=models.PROTECT,
        related_name='programacoes',
        verbose_name='local',
    )
    recreador = models.ForeignKey(
        Recreador,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='programacoes',
        verbose_name='recreador',
    )
    categoria = models.ForeignKey(
        CategoriaProgramacao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='programacoes',
        verbose_name='categoria / faixa',
    )
    vagas_total = models.PositiveIntegerField('vagas totais')
    observacoes = models.TextField('observações', blank=True)
    atividade_chuva = models.CharField('atividade (plano B chuva)', max_length=200, blank=True)
    local_chuva_nome = models.CharField('local chuva', max_length=200, blank=True)
    responsavel_nome = models.CharField('responsável', max_length=120, blank=True)
    coordenador_nome = models.CharField('coordenador', max_length=120, blank=True)
    musico_nome = models.CharField('músico', max_length=120, blank=True)
    realizado = models.BooleanField('realizado', default=False)
    auditado_por = models.CharField('auditado por', max_length=120, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['data', 'hora_inicio']
        verbose_name = 'programação diária'
        verbose_name_plural = 'programações diárias'
        unique_together = [('hotel', 'data', 'hora_inicio', 'local')]

    def __str__(self):
        return f'{self.data} {self.hora_inicio:%H:%M} — {self.atividade.nome}'

    def clean(self):
        super().clean()
        if self.hora_fim <= self.hora_inicio:
            raise ValidationError({'hora_fim': 'Horário de término deve ser após o início.'})
        if self.atividade.hotel_id != self.hotel_id:
            raise ValidationError({'atividade': 'Atividade deve pertencer ao mesmo hotel.'})
        if self.local.hotel_id != self.hotel_id:
            raise ValidationError({'local': 'Local deve pertencer ao mesmo hotel.'})
        if self.recreador and self.recreador.hotel_id != self.hotel_id:
            raise ValidationError({'recreador': 'Recreador deve pertencer ao mesmo hotel.'})

    @property
    def vagas_ocupadas(self) -> int:
        return self.inscricoes.count()

    @property
    def presentes(self) -> int:
        return self.presencas.filter(presente=True).count()

    def lotado(self) -> bool:
        return self.vagas_ocupadas >= self.vagas_total


class TelaoGradePublicada(models.Model):
    """Marca a grade do dia como publicada no telão da recreação."""

    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='grades_telao',
        verbose_name='hotel',
    )
    data = models.DateField('data da grade')
    total_atividades = models.PositiveIntegerField('total de atividades', default=0)
    ativo = models.BooleanField('ativa no telão', default=True)
    publicado_em = models.DateTimeField('publicado em', auto_now=True)
    publicado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='grades_telao_publicadas',
        verbose_name='publicado por',
    )

    class Meta:
        verbose_name = 'grade publicada no telão'
        verbose_name_plural = 'grades publicadas no telão'
        unique_together = [('hotel', 'data')]
        ordering = ['-publicado_em']

    def __str__(self):
        return f'{self.hotel.nome} — {self.data:%d/%m/%Y}'


class InscricaoAtividade(models.Model):
    """Pré-inscrição de hóspede em atividade do dia (antes da presença)."""

    programacao = models.ForeignKey(
        ProgramacaoDiaria,
        on_delete=models.CASCADE,
        related_name='inscricoes',
        verbose_name='programação',
    )
    hospede = models.ForeignKey(
        Hospede,
        on_delete=models.CASCADE,
        related_name='inscricoes',
        verbose_name='hóspede',
    )
    inscrito_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'inscrição em atividade'
        verbose_name_plural = 'inscrições em atividades'
        unique_together = [('programacao', 'hospede')]

    def __str__(self):
        return f'{self.hospede.nome_completo} → {self.programacao.atividade.nome}'

    def clean(self):
        super().clean()
        if self.hospede.hotel_id != self.programacao.hotel_id:
            raise ValidationError('Hóspede e programação devem ser do mesmo hotel.')
        if not self.hospede.ativo:
            raise ValidationError('Hóspede não está com check-in ativo.')


class PresencaRegistro(models.Model):
    programacao = models.ForeignKey(
        ProgramacaoDiaria,
        on_delete=models.CASCADE,
        related_name='presencas',
        verbose_name='programação',
    )
    hospede = models.ForeignKey(
        Hospede,
        on_delete=models.CASCADE,
        related_name='presencas',
        verbose_name='hóspede',
    )
    presente = models.BooleanField('presente', default=True)
    registrado_em = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='presencas_registradas',
        verbose_name='registrado por',
    )

    class Meta:
        verbose_name = 'registro de presença'
        verbose_name_plural = 'registros de presença'
        unique_together = [('programacao', 'hospede')]

    def __str__(self):
        status = 'presente' if self.presente else 'ausente'
        return f'{self.hospede.nome_completo} — {status}'

    def clean(self):
        super().clean()
        if self.hospede.hotel_id != self.programacao.hotel_id:
            raise ValidationError('Hóspede e programação devem ser do mesmo hotel.')


class DiaSemana(models.IntegerChoices):
    DOMINGO = 0, 'Domingo'
    SEGUNDA = 1, 'Segunda-feira'
    TERCA = 2, 'Terça-feira'
    QUARTA = 3, 'Quarta-feira'
    QUINTA = 4, 'Quinta-feira'
    SEXTA = 5, 'Sexta-feira'
    SABADO = 6, 'Sábado'


class NoiteTematica(models.Model):
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='noites_tematicas',
        verbose_name='hotel',
    )
    dia_semana = models.IntegerField('dia da semana', choices=DiaSemana.choices)
    tema = models.CharField('tema da noite', max_length=120)
    cor_dominante = models.CharField('cor dominante', max_length=40, blank=True)
    cores_do_dia = models.CharField('cores do dia', max_length=200, blank=True)
    atracao_musical = models.CharField('atração musical', max_length=200)
    vista_se = models.CharField('vista-se', max_length=200, blank=True)
    descricao_gastronomia = models.TextField('gastronomia')
    manha_tema = models.CharField('tema da manhã', max_length=200, blank=True)
    manha_genero_musical = models.CharField('música da manhã', max_length=200, blank=True)
    manha_atividades = models.TextField('atividades da manhã', blank=True)
    horario_noite_inicio = models.TimeField('início noite', default=time(19, 0))
    horario_noite_fim = models.TimeField('término noite', default=time(23, 0))
    horario_manha_inicio = models.TimeField('início manhã', default=time(8, 0))
    horario_manha_fim = models.TimeField('término manhã', default=time(10, 0))

    class Meta:
        ordering = ['dia_semana']
        verbose_name = 'noite temática'
        verbose_name_plural = 'noites temáticas'
        unique_together = [('hotel', 'dia_semana')]

    def __str__(self):
        return f'{self.get_dia_semana_display()} — {self.tema} ({self.hotel.nome})'


class Passeio(models.Model):
    """Passeios do dia — coluna lateral da programação semanal."""

    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='passeios',
        verbose_name='hotel',
    )
    dia_semana = models.IntegerField('dia da semana', choices=DiaSemana.choices)
    titulo = models.CharField('título', max_length=120)
    descricao = models.TextField('descrição')
    hora_saida = models.TimeField('horário de saída', null=True, blank=True)
    hora_retorno = models.TimeField('horário de retorno', null=True, blank=True)
    ponto_encontro = models.CharField('ponto de encontro', max_length=160, blank=True)
    vagas = models.PositiveSmallIntegerField(
        'vagas',
        default=0,
        help_text='0 = sem limite de vagas.',
    )
    preco = models.DecimalField(
        'preço (R$)',
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Deixe em branco para passeio gratuito / incluso.',
    )
    pix_chave = models.CharField(
        'chave PIX do passeio',
        max_length=140,
        blank=True,
        help_text='Opcional. Se vazio, usa a chave PIX do hotel.',
    )
    pix_beneficiario = models.CharField(
        'beneficiário PIX do passeio',
        max_length=80,
        blank=True,
    )
    ordem = models.PositiveSmallIntegerField('ordem', default=0)
    ativo = models.BooleanField('ativo', default=True)

    class Meta:
        ordering = ['dia_semana', 'ordem']
        verbose_name = 'passeio'
        verbose_name_plural = 'passeios'
        unique_together = [('hotel', 'dia_semana', 'titulo')]

    def __str__(self):
        return f'{self.get_dia_semana_display()} — {self.titulo}'

    def vagas_ocupadas(self, data=None) -> int:
        qs = self.inscricoes.all()
        if data is not None:
            qs = qs.filter(data=data)
        return qs.count()

    def vagas_restantes(self, data=None):
        if not self.vagas:
            return None
        return max(self.vagas - self.vagas_ocupadas(data), 0)

    def lotado(self, data=None) -> bool:
        if not self.vagas:
            return False
        return self.vagas_ocupadas(data) >= self.vagas

    @property
    def is_gratuito(self) -> bool:
        return self.preco is None or self.preco == 0

    @property
    def pix_chave_efetiva(self) -> str:
        return self.pix_chave or (self.hotel.pix_chave if self.hotel_id else '')

    @property
    def pix_beneficiario_efetivo(self) -> str:
        if self.pix_beneficiario:
            return self.pix_beneficiario
        if self.hotel_id:
            return self.hotel.pix_beneficiario or self.hotel.nome
        return ''


class StatusPagamentoPasseio(models.TextChoices):
    ISENTO = 'isento', 'Incluso / gratuito'
    PENDENTE = 'pendente', 'Aguardando pagamento'
    COMPROVANTE_ENVIADO = 'comprovante_enviado', 'Comprovante enviado'
    CONFIRMADO = 'confirmado', 'Pagamento confirmado'
    REJEITADO = 'rejeitado', 'Comprovante rejeitado'


def comprovante_upload_path(instance, filename):
    import os
    ext = os.path.splitext(filename)[1].lower()
    return f'comprovantes_passeio/{instance.data:%Y/%m}/insc_{instance.pk or "novo"}{ext}'


class InscricaoPasseio(models.Model):
    """Inscrição de um hóspede em um passeio para uma data específica."""

    passeio = models.ForeignKey(
        Passeio,
        on_delete=models.CASCADE,
        related_name='inscricoes',
        verbose_name='passeio',
    )
    hospede = models.ForeignKey(
        'Hospede',
        on_delete=models.CASCADE,
        related_name='inscricoes_passeio',
        verbose_name='hóspede',
    )
    data = models.DateField('data do passeio')
    valor = models.DecimalField(
        'valor (R$)',
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    status_pagamento = models.CharField(
        'status do pagamento',
        max_length=25,
        choices=StatusPagamentoPasseio.choices,
        default=StatusPagamentoPasseio.PENDENTE,
    )
    comprovante = models.FileField(
        'comprovante de pagamento',
        upload_to=comprovante_upload_path,
        blank=True,
        null=True,
    )
    comprovante_enviado_em = models.DateTimeField('comprovante enviado em', null=True, blank=True)
    pagamento_confirmado_em = models.DateTimeField('pagamento confirmado em', null=True, blank=True)
    pagamento_confirmado_por = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagamentos_passeio_confirmados',
        verbose_name='confirmado por',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', 'passeio__ordem']
        verbose_name = 'inscrição em passeio'
        verbose_name_plural = 'inscrições em passeios'
        unique_together = [('passeio', 'hospede', 'data')]
        indexes = [
            models.Index(fields=['passeio', 'data']),
            models.Index(fields=['status_pagamento']),
        ]

    def __str__(self):
        return f'{self.hospede.nome_completo} → {self.passeio.titulo} ({self.data:%d/%m})'

    @property
    def pago(self) -> bool:
        return self.status_pagamento in (
            StatusPagamentoPasseio.CONFIRMADO,
            StatusPagamentoPasseio.ISENTO,
        )

    @property
    def aguardando_analise(self) -> bool:
        return self.status_pagamento == StatusPagamentoPasseio.COMPROVANTE_ENVIADO


class CategoriaProduto(models.TextChoices):
    ACESSORIO = 'acessorio', 'Acessório'
    NOITE_TEMATICA = 'noite_tematica', 'Noite Temática'
    SOUVENIR = 'souvenir', 'Souvenir'


class ProdutoLoja(models.Model):
    """Loja Oficial Vulcãozinho Inn."""

    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='produtos',
        verbose_name='hotel',
        help_text='Vazio = disponível em toda a rede.',
    )
    nome = models.CharField('nome', max_length=120)
    descricao = models.TextField('descrição', blank=True)
    categoria = models.CharField(
        'categoria',
        max_length=20,
        choices=CategoriaProduto.choices,
        default=CategoriaProduto.ACESSORIO,
    )
    cor_tema = models.CharField('cor / tema', max_length=40, blank=True)
    preco = models.DecimalField('preço', max_digits=8, decimal_places=2, null=True, blank=True)
    custo = models.DecimalField(
        'custo unitário',
        max_digits=8,
        decimal_places=2,
        default=Decimal('0'),
        help_text='Custo de aquisição — usado para calcular margem.',
    )
    estoque = models.PositiveIntegerField('estoque', default=0)
    codigo_qr = models.SlugField(
        'código QR',
        max_length=40,
        unique=True,
        blank=True,
        null=True,
        help_text='Gerado automaticamente se vazio.',
    )
    ativo = models.BooleanField('ativo', default=True)
    ordem = models.PositiveSmallIntegerField('ordem', default=0)

    class Meta:
        ordering = ['ordem', 'nome']
        verbose_name = 'produto da loja'
        verbose_name_plural = 'produtos da loja'

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.codigo_qr:
            import uuid
            base = uuid.uuid4().hex[:8]
            self.codigo_qr = f'VUL-{base}'
        super().save(*args, **kwargs)


class PassaporteHospede(models.Model):
    """Passaporte da Diversão — 7 carimbos das noites temáticas."""

    hospede = models.OneToOneField(
        Hospede,
        on_delete=models.CASCADE,
        related_name='passaporte',
        verbose_name='hóspede',
    )
    moedas = models.PositiveIntegerField('moedas Vulcãozinho', default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'passaporte do hóspede'
        verbose_name_plural = 'passaportes dos hóspedes'

    def __str__(self):
        return f'Passaporte — {self.hospede.nome_completo}'

    @property
    def total_carimbos(self) -> int:
        return self.carimbos.count()

    @property
    def completo(self) -> bool:
        return self.total_carimbos >= 7

    @property
    def nivel(self) -> str:
        n = self.total_carimbos
        if n >= 7:
            return 'Mestre Vulcãozinho'
        if n >= 4:
            return 'Aventureiro'
        if n >= 1:
            return 'Explorador'
        return 'Iniciante'

    @property
    def progresso_pct(self) -> int:
        return min(100, round(self.total_carimbos / 7 * 100))


class CarimboPassaporte(models.Model):
    passaporte = models.ForeignKey(
        PassaporteHospede,
        on_delete=models.CASCADE,
        related_name='carimbos',
        verbose_name='passaporte',
    )
    noite_tematica = models.ForeignKey(
        NoiteTematica,
        on_delete=models.PROTECT,
        related_name='carimbos',
        verbose_name='noite temática',
    )
    data_conquista = models.DateField('data da conquista', default=date.today)
    concedido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'carimbo do passaporte'
        verbose_name_plural = 'carimbos do passaporte'
        unique_together = [('passaporte', 'noite_tematica')]

    def __str__(self):
        return f'{self.noite_tematica.tema} — {self.passaporte.hospede.nome_completo}'


class FormaPagamento(models.TextChoices):
    DINHEIRO = 'dinheiro', 'Dinheiro'
    CARTAO = 'cartao', 'Cartão'
    PIX = 'pix', 'PIX'
    HOSPEDE = 'hospede', 'Conta hóspede'


class VendaLoja(models.Model):
    """Registro financeiro de venda na loja oficial."""

    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='vendas_loja',
        verbose_name='hotel',
    )
    produto = models.ForeignKey(
        ProdutoLoja,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendas',
        verbose_name='produto',
    )
    descricao = models.CharField('descrição', max_length=160)
    quantidade = models.PositiveIntegerField('quantidade', default=1)
    valor_unitario = models.DecimalField('valor unitário', max_digits=10, decimal_places=2)
    valor_total = models.DecimalField('valor total', max_digits=10, decimal_places=2)
    custo_unitario = models.DecimalField('custo unitário', max_digits=10, decimal_places=2, default=0)
    custo_total = models.DecimalField('custo total', max_digits=10, decimal_places=2, default=0)
    lucro_bruto = models.DecimalField('lucro bruto', max_digits=10, decimal_places=2, default=0)
    forma_pagamento = models.CharField(
        'forma de pagamento',
        max_length=20,
        choices=FormaPagamento.choices,
        default=FormaPagamento.PIX,
    )
    registrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendas_loja_registradas',
        verbose_name='registrado por',
    )
    criado_em = models.DateTimeField('data da venda', auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'venda da loja'
        verbose_name_plural = 'vendas da loja'

    def __str__(self):
        return f'{self.descricao} — R$ {self.valor_total}'

    def save(self, *args, **kwargs):
        from decimal import Decimal as D
        if not self.valor_total:
            self.valor_total = self.valor_unitario * self.quantidade
        if not self.custo_total:
            self.custo_total = (self.custo_unitario or D('0')) * self.quantidade
        self.lucro_bruto = self.valor_total - self.custo_total
        super().save(*args, **kwargs)

    @property
    def margem_pct(self) -> float:
        if not self.valor_total:
            return 0.0
        return round(float(self.lucro_bruto / self.valor_total * 100), 1)


class StatusEventoRecreacao(models.TextChoices):
    PENDENTE = 'pendente', 'Pendente'
    AGENDADO = 'agendado', 'Agendado'
    REALIZADO = 'realizado', 'Realizado'
    CANCELADO = 'cancelado', 'Cancelado'
    NAO_AUTORIZADO = 'nao_autorizado', 'Não autorizado'


class EventoRecreacao(models.Model):
    """Eventos especiais importados da planilha de eventos (shows, passeios, fornecedores)."""

    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.PROTECT,
        related_name='eventos_recreacao',
        verbose_name='hotel',
    )
    pacote = models.CharField('pacote / tema', max_length=80, blank=True)
    mes_referencia = models.CharField('mês referência', max_length=40, blank=True)
    nome = models.CharField('evento', max_length=200)
    descricao = models.TextField('descrição', blank=True)
    tipo_servico = models.CharField('tipo serviço / fornecedor', max_length=80, blank=True)
    nivel_atracao = models.CharField('nível atração', max_length=60, blank=True)
    contrato_assinado = models.CharField('contrato assinado', max_length=40, blank=True)
    prestador = models.CharField('prestador / fornecedor', max_length=120, blank=True)
    responsavel = models.CharField('responsável', max_length=120, blank=True)
    dia_semana = models.CharField('dia da semana', max_length=20, blank=True)
    data_inicio = models.DateField('data inicial')
    data_fim = models.DateField('data final', null=True, blank=True)
    orcamento = models.DecimalField(
        'orçamento (R$)',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    status = models.CharField(
        'status',
        max_length=20,
        choices=StatusEventoRecreacao.choices,
        default=StatusEventoRecreacao.AGENDADO,
    )
    importado_em = models.DateTimeField('importado em', auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['data_inicio', 'nome']
        verbose_name = 'evento de recreação'
        verbose_name_plural = 'eventos de recreação'
        indexes = [
            models.Index(fields=['hotel', 'data_inicio']),
        ]

    def __str__(self):
        return f'{self.data_inicio:%d/%m/%Y} — {self.nome}'


class SalaReuniao(models.Model):
    """Salas de reunião em tempo real para diretoria e gestores."""

    nome = models.CharField('nome da sala', max_length=120)
    slug = models.SlugField('slug', max_length=80, unique=True)
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='salas_reuniao',
        verbose_name='hotel',
        help_text='Vazio = sala da rede (todos os diretores).',
    )
    descricao = models.TextField('descrição', blank=True)
    jitsi_room = models.CharField('sala Jitsi', max_length=120, blank=True)
    ativa = models.BooleanField('ativa', default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'sala de reunião'
        verbose_name_plural = 'salas de reunião'

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.jitsi_room:
            self.jitsi_room = f'VulcaozinhoInn-{self.slug}'
        super().save(*args, **kwargs)

    @property
    def jitsi_url(self) -> str:
        room = self.jitsi_room or f'VulcaozinhoInn-{self.slug}'
        params = 'config.prejoinPageEnabled=false&config.startWithAudioMuted=true'
        return f'https://meet.jit.si/{room}#{params}'


class MensagemReuniao(models.Model):
    sala = models.ForeignKey(
        SalaReuniao,
        on_delete=models.CASCADE,
        related_name='mensagens',
        verbose_name='sala',
    )
    autor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mensagens_reuniao',
        verbose_name='autor',
    )
    texto = models.TextField('mensagem', max_length=2000)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['criado_em']
        verbose_name = 'mensagem da reunião'
        verbose_name_plural = 'mensagens da reunião'

    def __str__(self):
        autor = self.autor.username if self.autor else 'Anônimo'
        return f'{autor}: {self.texto[:40]}'


class PapelUsuario(models.TextChoices):
    ADMIN = 'ADMIN', 'Administrador'
    DIRETOR = 'DIRETOR', 'Diretor'
    GERENTE = 'GERENTE', 'Gerente'
    SUPERVISOR = 'SUPERVISOR', 'Supervisor'
    RECREADOR = 'RECREADOR', 'Recreador'
    RECEPCAO = 'RECEPCAO', 'Recepção'
    RESTAURANTE = 'RESTAURANTE', 'Restaurante'
    LOJA = 'LOJA', 'Loja'


PAPEIS_ACESSO_GLOBAL = {PapelUsuario.ADMIN, PapelUsuario.DIRETOR}


class PerfilUsuario(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='perfil',
        verbose_name='usuário',
    )
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='perfis',
        verbose_name='hotel',
        help_text='Vazio = acesso a todos os hotéis (Administrador/Diretor).',
    )
    papel = models.CharField(
        'papel',
        max_length=20,
        choices=PapelUsuario.choices,
        default=PapelUsuario.RECEPCAO,
    )
    ativo = models.BooleanField('ativo', default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'perfil de usuário'
        verbose_name_plural = 'perfis de usuário'

    def __str__(self):
        hotel = self.hotel.nome if self.hotel else 'Rede (global)'
        return f'{self.user.username} — {self.get_papel_display()} ({hotel})'

    @property
    def acesso_global(self) -> bool:
        return self.papel in PAPEIS_ACESSO_GLOBAL and self.hotel_id is None


class TipoPeriodoOperacional(models.TextChoices):
    EXTRAS_RECREADORES = 'extras_recreadores', 'Extras de recreadores'
    ATRACOES = 'atracoes', 'Atrações / artistas'
    COMPRAS = 'compras', 'Compras semanais'


class StatusPagamentoOperacional(models.TextChoices):
    PENDENTE = 'pendente', 'Pendente'
    AUTORIZADO = 'autorizado', 'Autorizado'
    PAGO = 'pago', 'Pago'
    CANCELADO = 'cancelado', 'Cancelado'


class PeriodoOperacional(models.Model):
    """Semana ou período de controle (extras, atrações ou compras)."""
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='periodos_operacionais',
        verbose_name='hotel',
    )
    tipo = models.CharField(
        'tipo',
        max_length=30,
        choices=TipoPeriodoOperacional.choices,
    )
    titulo = models.CharField('título', max_length=120)
    data_inicio = models.DateField('data início')
    data_fim = models.DateField('data fim')
    ocupacao_pct = models.DecimalField(
        'ocupação %',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    qtd_pax = models.PositiveIntegerField('qtd. hóspedes', null=True, blank=True)
    criado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='periodos_operacionais_criados',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_inicio', 'titulo']
        verbose_name = 'período operacional'
        verbose_name_plural = 'períodos operacionais'

    def __str__(self):
        return f'{self.titulo} ({self.get_tipo_display()})'


class PagamentoAtracao(models.Model):
    """Pagamentos de artistas, bandas e entretenimento."""
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='pagamentos_atracoes',
    )
    periodo = models.ForeignKey(
        PeriodoOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagamentos',
    )
    data_label = models.CharField('dia / referência', max_length=80, blank=True)
    data_evento = models.DateField('data do evento', null=True, blank=True)
    artista = models.CharField('artista / prestador', max_length=200)
    atracao = models.CharField('atração / tipo', max_length=200, blank=True)
    valor = models.DecimalField('valor (R$)', max_digits=10, decimal_places=2, default=Decimal('0'))
    chave_pix = models.CharField('chave PIX', max_length=200, blank=True)
    evento = models.CharField('evento', max_length=200, blank=True)
    pacote = models.CharField('pacote', max_length=120, blank=True)
    tipo_servico = models.CharField('tipo de serviço', max_length=120, blank=True)
    responsavel = models.CharField('responsável', max_length=120, blank=True)
    horario = models.CharField('horário', max_length=40, blank=True)
    local_dept = models.CharField('local / dept.', max_length=120, blank=True)
    status = models.CharField(
        'status',
        max_length=20,
        choices=StatusPagamentoOperacional.choices,
        default=StatusPagamentoOperacional.PENDENTE,
    )
    autorizacao_diretoria = models.CharField('autorização diretoria', max_length=80, blank=True)
    observacoes = models.TextField('observações', blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['data_evento', 'artista']
        verbose_name = 'pagamento de atração'
        verbose_name_plural = 'pagamentos de atrações'

    def __str__(self):
        return f'{self.artista} — R$ {self.valor}'


class ExtraRecreador(models.Model):
    """Extras semanais por recreador (grade Seg–Dom)."""
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='extras_recreadores',
    )
    periodo = models.ForeignKey(
        PeriodoOperacional,
        on_delete=models.CASCADE,
        related_name='extras_recreadores',
    )
    nome = models.CharField('recreador', max_length=120)
    valor_seg = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    valor_ter = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    valor_qua = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    valor_qui = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    valor_sex = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    valor_sab = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    valor_dom = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['ordem', 'nome']
        verbose_name = 'extra de recreador'
        verbose_name_plural = 'extras de recreadores'

    def __str__(self):
        return self.nome

    @property
    def total(self) -> Decimal:
        return (
            self.valor_seg + self.valor_ter + self.valor_qua + self.valor_qui
            + self.valor_sex + self.valor_sab + self.valor_dom
        )


class ItemCompraSemanal(models.Model):
    """Itens da planilha de compras de materiais."""
    hotel = models.ForeignKey(
        Hotel,
        on_delete=models.CASCADE,
        related_name='compras_semanais',
    )
    periodo = models.ForeignKey(
        PeriodoOperacional,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_compra',
    )
    descricao = models.CharField('material / item', max_length=300)
    quantidade = models.PositiveIntegerField('quantidade', default=1)
    link_fornecedor = models.CharField('link fornecedor', max_length=500, blank=True)
    preco_unitario = models.DecimalField('preço unitário', max_digits=10, decimal_places=2, default=Decimal('0'))
    ordem = models.PositiveSmallIntegerField(default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordem', 'descricao']
        verbose_name = 'item de compra'
        verbose_name_plural = 'itens de compra'

    def __str__(self):
        return self.descricao[:60]

    @property
    def preco_total(self) -> Decimal:
        return self.preco_unitario * self.quantidade

