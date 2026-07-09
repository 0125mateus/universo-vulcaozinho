from rest_framework import serializers

from .documento_utils import documento_duplicado_ativo, formatar_documento
from .models import Atividade, Hospede, Hotel, Passeio, PassaporteHospede, PresencaRegistro, ProdutoLoja, ProgramacaoDiaria, VendaLoja


class HotelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hotel
        fields = [
            'id', 'nome', 'slug', 'rede_marca', 'slogan',
            'cor_primaria', 'cor_secundaria', 'cor_destaque', 'cor_terciaria',
            'cidade', 'estado', 'ativo',
        ]
        read_only_fields = ['id']


class HospedeSerializer(serializers.ModelSerializer):
    faixa_etaria = serializers.SerializerMethodField()
    faixa_etaria_label = serializers.SerializerMethodField()
    ativo = serializers.BooleanField(read_only=True)

    class Meta:
        model = Hospede
        fields = [
            'id', 'hotel', 'nome_completo', 'data_nascimento', 'documento',
            'apartamento', 'data_checkin', 'data_checkout', 'observacoes',
            'faixa_etaria', 'faixa_etaria_label', 'ativo',
            'criado_em', 'atualizado_em',
        ]
        read_only_fields = ['id', 'criado_em', 'atualizado_em']

    def get_faixa_etaria(self, obj) -> str:
        return obj.faixa_etaria

    def get_faixa_etaria_label(self, obj) -> str:
        return obj.get_faixa_etaria_display()

    def validate(self, attrs):
        hotel = attrs.get('hotel') or getattr(self.instance, 'hotel', None)
        documento = attrs.get('documento') or getattr(self.instance, 'documento', None)
        if documento:
            documento = formatar_documento(documento)
            attrs['documento'] = documento
        if hotel and documento:
            if documento_duplicado_ativo(
                hotel,
                documento,
                exclude_pk=self.instance.pk if self.instance else None,
            ):
                raise serializers.ValidationError(
                    {'documento': 'Já existe hóspede ativo com este documento neste hotel.'}
                )
        return attrs


class AtividadeSerializer(serializers.ModelSerializer):
    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True, default=None)
    local_padrao_nome = serializers.CharField(source='local_padrao.nome', read_only=True, default=None)

    class Meta:
        model = Atividade
        fields = [
            'id', 'hotel', 'nome', 'descricao', 'frase_chamada', 'icone',
            'categoria', 'categoria_nome', 'local_padrao', 'local_padrao_nome',
            'duracao_minutos', 'capacidade_maxima', 'ativo',
        ]
        read_only_fields = ['id']


class ProgramacaoDiariaSerializer(serializers.ModelSerializer):
    atividade_nome = serializers.CharField(source='atividade.nome', read_only=True)
    local_nome = serializers.CharField(source='local.nome', read_only=True)
    recreador_nome = serializers.CharField(source='recreador.nome', read_only=True, default=None)
    categoria_nome = serializers.CharField(source='categoria.nome', read_only=True, default=None)
    presentes_count = serializers.IntegerField(read_only=True)
    vagas_ocupadas = serializers.SerializerMethodField()
    lotado = serializers.SerializerMethodField()

    class Meta:
        model = ProgramacaoDiaria
        fields = [
            'id', 'hotel', 'data', 'hora_inicio', 'hora_fim',
            'atividade', 'atividade_nome', 'local', 'local_nome',
            'recreador', 'recreador_nome', 'categoria', 'categoria_nome',
            'vagas_total', 'vagas_ocupadas', 'presentes_count', 'lotado',
            'observacoes', 'criado_em',
        ]
        read_only_fields = ['id', 'criado_em']

    def get_vagas_ocupadas(self, obj) -> int:
        if hasattr(obj, 'inscritos_count'):
            return obj.inscritos_count
        return obj.vagas_ocupadas

    def get_lotado(self, obj) -> bool:
        ocupadas = self.get_vagas_ocupadas(obj)
        return ocupadas >= obj.vagas_total


class PresencaRegistroSerializer(serializers.ModelSerializer):
    hospede_nome = serializers.CharField(source='hospede.nome_completo', read_only=True)
    programacao_label = serializers.SerializerMethodField()

    class Meta:
        model = PresencaRegistro
        fields = [
            'id', 'programacao', 'programacao_label', 'hospede', 'hospede_nome',
            'presente', 'registrado_em', 'registrado_por',
        ]
        read_only_fields = ['id', 'registrado_em', 'registrado_por']

    def get_programacao_label(self, obj) -> str:
        return str(obj.programacao)


class ProdutoLojaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProdutoLoja
        fields = [
            'id', 'hotel', 'nome', 'descricao', 'categoria', 'cor_tema',
            'preco', 'estoque', 'codigo_qr', 'ativo', 'ordem', 'custo',
        ]
        read_only_fields = ['id', 'codigo_qr']


class PasseioSerializer(serializers.ModelSerializer):
    dia_semana_label = serializers.CharField(source='get_dia_semana_display', read_only=True)

    class Meta:
        model = Passeio
        fields = [
            'id', 'hotel', 'dia_semana', 'dia_semana_label',
            'titulo', 'descricao', 'hora_saida', 'hora_retorno',
            'ponto_encontro', 'vagas', 'preco', 'ordem', 'ativo',
        ]
        read_only_fields = ['id']


class PassaporteHospedeSerializer(serializers.ModelSerializer):
    hospede_nome = serializers.CharField(source='hospede.nome_completo', read_only=True)
    hospede_apartamento = serializers.CharField(source='hospede.apartamento', read_only=True)
    total_carimbos = serializers.SerializerMethodField()
    nivel = serializers.SerializerMethodField()
    completo = serializers.SerializerMethodField()
    progresso_pct = serializers.SerializerMethodField()

    class Meta:
        model = PassaporteHospede
        fields = [
            'id', 'hospede', 'hospede_nome', 'hospede_apartamento',
            'moedas', 'total_carimbos', 'nivel', 'completo', 'progresso_pct',
            'criado_em',
        ]
        read_only_fields = ['id', 'criado_em']

    def _carimbos(self, obj) -> int:
        if hasattr(obj, 'total_carimbos') and isinstance(obj.total_carimbos, int):
            return obj.total_carimbos
        return obj.carimbos.count()

    def get_total_carimbos(self, obj) -> int:
        return self._carimbos(obj)

    def get_nivel(self, obj) -> str:
        n = self._carimbos(obj)
        if n >= 7:
            return 'Mestre Vulcãozinho'
        if n >= 4:
            return 'Aventureiro'
        if n >= 1:
            return 'Explorador'
        return 'Iniciante'

    def get_completo(self, obj) -> bool:
        return self._carimbos(obj) >= 7

    def get_progresso_pct(self, obj) -> int:
        return min(100, round(self._carimbos(obj) / 7 * 100))


class VendaLojaSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source='produto.nome', read_only=True, default=None)
    forma_pagamento_label = serializers.CharField(source='get_forma_pagamento_display', read_only=True)
    margem_pct = serializers.FloatField(read_only=True)

    class Meta:
        model = VendaLoja
        fields = [
            'id', 'hotel', 'produto', 'produto_nome', 'descricao',
            'quantidade', 'valor_unitario', 'valor_total',
            'custo_unitario', 'custo_total', 'lucro_bruto', 'margem_pct',
            'forma_pagamento', 'forma_pagamento_label',
            'registrado_por', 'criado_em',
        ]
        read_only_fields = ['id', 'criado_em', 'valor_total', 'custo_total', 'lucro_bruto']
