from datetime import datetime, timedelta

from django import forms
from django.core.exceptions import ValidationError

from .documento_utils import documento_duplicado_ativo, formatar_documento
from .models import Atividade, CategoriaProgramacao, DiaSemana, Hospede, LocalAtividade, NoiteTematica, Passeio, ProdutoLoja, ProgramacaoDiaria, Recreador


PARENTESCO_CHOICES = [
    ('', 'Selecione…'),
    ('mae', 'Mãe'),
    ('pai', 'Pai'),
    ('avo', 'Avô/Avó'),
    ('tio', 'Tio/Tia'),
    ('responsavel_legal', 'Responsável legal'),
    ('outro', 'Outro'),
]


def _calcular_idade(data_nascimento, referencia=None):
    from django.utils import timezone
    ref = referencia or timezone.localdate()
    anos = ref.year - data_nascimento.year
    if (ref.month, ref.day) < (data_nascimento.month, data_nascimento.day):
        anos -= 1
    return anos


class HospedeForm(forms.ModelForm):
    responsavel_parentesco = forms.ChoiceField(
        label='Parentesco',
        choices=PARENTESCO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'rec-input rec-select'}),
    )
    responsavel_assinatura = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_responsavel_assinatura'}),
    )

    class Meta:
        model = Hospede
        fields = [
            'nome_completo',
            'data_nascimento',
            'documento',
            'apartamento',
            'data_checkin',
            'data_checkout',
            'observacoes',
            'responsavel_nome',
            'responsavel_documento',
            'responsavel_parentesco',
            'responsavel_telefone',
            'responsavel_assinatura',
        ]
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'rec-input', 'placeholder': 'Nome completo'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'rec-input', 'type': 'date', 'id': 'id_data_nascimento'}),
            'documento': forms.TextInput(attrs={
                'class': 'rec-input doc-input',
                'placeholder': '000.000.000-00',
                'id': 'id_documento',
                'autocomplete': 'off',
                'spellcheck': 'false',
            }),
            'apartamento': forms.TextInput(attrs={'class': 'rec-input', 'placeholder': 'Ex.: 302'}),
            'data_checkin': forms.DateInput(attrs={'class': 'rec-input', 'type': 'date'}),
            'data_checkout': forms.DateInput(attrs={'class': 'rec-input', 'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'class': 'rec-input rec-textarea', 'rows': 3, 'placeholder': 'Observações opcionais'}),
            'responsavel_nome': forms.TextInput(attrs={'class': 'rec-input', 'placeholder': 'Nome do responsável legal'}),
            'responsavel_documento': forms.TextInput(attrs={
                'class': 'rec-input doc-input',
                'placeholder': '000.000.000-00',
                'id': 'id_responsavel_documento',
                'autocomplete': 'off',
                'spellcheck': 'false',
            }),
            'responsavel_telefone': forms.TextInput(attrs={'class': 'rec-input', 'placeholder': '(00) 00000-0000'}),
        }

    def __init__(self, *args, hotel=None, **kwargs):
        self.hotel = hotel
        super().__init__(*args, **kwargs)
        self.fields['data_checkout'].required = False
        for campo in ('responsavel_nome', 'responsavel_documento', 'responsavel_telefone'):
            self.fields[campo].required = False
        if hotel and not self.instance.pk:
            self.instance.hotel = hotel
        if self.instance.documento:
            self.initial.setdefault(
                'documento',
                formatar_documento(self.instance.documento),
            )
        if self.instance.responsavel_documento:
            self.initial.setdefault(
                'responsavel_documento',
                formatar_documento(self.instance.responsavel_documento),
            )

    def clean(self):
        cleaned = super().clean()
        if not self.hotel:
            raise ValidationError('Hotel não definido para o check-in.')

        documento = cleaned.get('documento')
        if documento:
            documento = formatar_documento(documento)
            cleaned['documento'] = documento
        if documento and self.hotel:
            if documento_duplicado_ativo(
                self.hotel,
                documento,
                exclude_pk=self.instance.pk if self.instance else None,
            ):
                raise ValidationError(
                    {'documento': 'Já existe hóspede ativo com este documento neste hotel.'}
                )

        data_checkin = cleaned.get('data_checkin')
        data_checkout = cleaned.get('data_checkout')
        if data_checkin and data_checkout and data_checkout < data_checkin:
            raise ValidationError({'data_checkout': 'Check-out não pode ser anterior ao check-in.'})

        resp_doc = cleaned.get('responsavel_documento')
        if resp_doc:
            cleaned['responsavel_documento'] = formatar_documento(resp_doc)

        data_nascimento = cleaned.get('data_nascimento')
        if data_nascimento and _calcular_idade(data_nascimento) < 18:
            erros_menor = {}
            if not cleaned.get('responsavel_nome'):
                erros_menor['responsavel_nome'] = 'Obrigatório para hóspede menor de idade.'
            if not cleaned.get('responsavel_documento'):
                erros_menor['responsavel_documento'] = 'Obrigatório para hóspede menor de idade.'
            if not cleaned.get('responsavel_parentesco'):
                erros_menor['responsavel_parentesco'] = 'Informe o parentesco do responsável.'
            if not cleaned.get('responsavel_assinatura'):
                erros_menor['responsavel_assinatura'] = (
                    'A assinatura do responsável legal é obrigatória para menores de idade.'
                )
            if erros_menor:
                raise ValidationError(erros_menor)

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.hotel:
            instance.hotel = self.hotel
        if instance.responsavel_assinatura and not instance.responsavel_assinado_em:
            from django.utils import timezone
            instance.responsavel_assinado_em = timezone.now()
        if commit:
            instance.save()
        return instance


class PasseioForm(forms.ModelForm):
    class Meta:
        model = Passeio
        fields = [
            'dia_semana', 'titulo', 'descricao', 'hora_saida', 'hora_retorno',
            'ponto_encontro', 'vagas', 'preco', 'pix_chave', 'pix_beneficiario',
            'ordem', 'ativo',
        ]
        widgets = {
            'dia_semana': forms.Select(attrs={'class': 'rec-input rec-select'}),
            'titulo': forms.TextInput(attrs={'class': 'rec-input', 'placeholder': 'Ex.: City Tour Poços'}),
            'descricao': forms.Textarea(attrs={'class': 'rec-input rec-textarea', 'rows': 3}),
            'hora_saida': forms.TimeInput(attrs={'class': 'rec-input', 'type': 'time'}),
            'hora_retorno': forms.TimeInput(attrs={'class': 'rec-input', 'type': 'time'}),
            'ponto_encontro': forms.TextInput(attrs={'class': 'rec-input', 'placeholder': 'Ex.: Recepção / Lobby'}),
            'vagas': forms.NumberInput(attrs={'class': 'rec-input', 'min': 0}),
            'preco': forms.NumberInput(attrs={'class': 'rec-input', 'step': '0.01', 'min': 0, 'id': 'id_preco'}),
            'pix_chave': forms.TextInput(attrs={'class': 'rec-input', 'id': 'id_pix_chave', 'placeholder': 'CPF/CNPJ, e-mail, telefone ou chave aleatória'}),
            'pix_beneficiario': forms.TextInput(attrs={'class': 'rec-input', 'id': 'id_pix_beneficiario', 'placeholder': 'Nome de quem recebe'}),
            'ordem': forms.NumberInput(attrs={'class': 'rec-input', 'min': 0}),
        }

    def __init__(self, *args, hotel=None, **kwargs):
        self.hotel = hotel
        super().__init__(*args, **kwargs)
        self.fields['dia_semana'].choices = DiaSemana.choices
        if hotel and not self.instance.pk:
            self.instance.hotel = hotel

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.hotel:
            instance.hotel = self.hotel
        if commit:
            instance.save()
        return instance


class ProdutoLojaForm(forms.ModelForm):
    class Meta:
        model = ProdutoLoja
        fields = [
            'nome', 'descricao', 'categoria', 'cor_tema', 'preco', 'custo',
            'estoque', 'ativo', 'ordem',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'rec-input'}),
            'descricao': forms.Textarea(attrs={'class': 'rec-input rec-textarea', 'rows': 2}),
            'categoria': forms.Select(attrs={'class': 'rec-input rec-select'}),
            'cor_tema': forms.TextInput(attrs={'class': 'rec-input'}),
            'preco': forms.NumberInput(attrs={'class': 'rec-input', 'step': '0.01'}),
            'custo': forms.NumberInput(attrs={'class': 'rec-input', 'step': '0.01'}),
            'estoque': forms.NumberInput(attrs={'class': 'rec-input', 'min': 0}),
            'ordem': forms.NumberInput(attrs={'class': 'rec-input', 'min': 0}),
        }


class NoiteTematicaForm(forms.ModelForm):
    class Meta:
        model = NoiteTematica
        fields = [
            'tema', 'cor_dominante', 'cores_do_dia', 'atracao_musical', 'vista_se',
            'descricao_gastronomia', 'manha_tema', 'manha_genero_musical', 'manha_atividades',
            'horario_noite_inicio', 'horario_noite_fim',
            'horario_manha_inicio', 'horario_manha_fim',
        ]
        widgets = {
            'tema': forms.TextInput(attrs={'class': 'rec-input'}),
            'cor_dominante': forms.TextInput(attrs={'class': 'rec-input'}),
            'cores_do_dia': forms.TextInput(attrs={'class': 'rec-input'}),
            'atracao_musical': forms.TextInput(attrs={'class': 'rec-input'}),
            'vista_se': forms.TextInput(attrs={'class': 'rec-input'}),
            'descricao_gastronomia': forms.Textarea(attrs={'class': 'rec-input rec-textarea', 'rows': 3}),
            'manha_tema': forms.TextInput(attrs={'class': 'rec-input'}),
            'manha_genero_musical': forms.TextInput(attrs={'class': 'rec-input'}),
            'manha_atividades': forms.Textarea(attrs={'class': 'rec-input rec-textarea', 'rows': 2}),
            'horario_noite_inicio': forms.TimeInput(attrs={'class': 'rec-input', 'type': 'time'}),
            'horario_noite_fim': forms.TimeInput(attrs={'class': 'rec-input', 'type': 'time'}),
            'horario_manha_inicio': forms.TimeInput(attrs={'class': 'rec-input', 'type': 'time'}),
            'horario_manha_fim': forms.TimeInput(attrs={'class': 'rec-input', 'type': 'time'}),
        }


class ProgramacaoDiariaForm(forms.ModelForm):
    class Meta:
        model = ProgramacaoDiaria
        fields = [
            'data',
            'hora_inicio',
            'hora_fim',
            'atividade',
            'local',
            'categoria',
            'recreador',
            'vagas_total',
            'observacoes',
        ]
        widgets = {
            'data': forms.DateInput(attrs={'class': 'rec-input', 'type': 'date'}),
            'hora_inicio': forms.TimeInput(attrs={'class': 'rec-input', 'type': 'time'}),
            'hora_fim': forms.TimeInput(attrs={'class': 'rec-input', 'type': 'time'}),
            'atividade': forms.Select(attrs={'class': 'rec-input rec-select'}),
            'local': forms.Select(attrs={'class': 'rec-input rec-select'}),
            'categoria': forms.Select(attrs={'class': 'rec-input rec-select'}),
            'recreador': forms.Select(attrs={'class': 'rec-input rec-select'}),
            'vagas_total': forms.NumberInput(attrs={'class': 'rec-input', 'min': 1}),
            'observacoes': forms.Textarea(attrs={
                'class': 'rec-input rec-textarea',
                'rows': 2,
                'placeholder': 'Observações opcionais',
            }),
        }

    def __init__(self, *args, hotel=None, **kwargs):
        self.hotel = hotel
        super().__init__(*args, **kwargs)
        self.fields['recreador'].required = False
        self.fields['categoria'].required = False
        self.fields['observacoes'].required = False
        self.fields['categoria'].label = 'Faixa etária'
        self.fields['categoria'].queryset = CategoriaProgramacao.objects.all()

        if hotel:
            self.fields['atividade'].queryset = Atividade.objects.filter(hotel=hotel).order_by('nome')
            self.fields['local'].queryset = LocalAtividade.objects.filter(hotel=hotel, ativo=True).order_by('nome')
            self.fields['recreador'].queryset = Recreador.objects.filter(hotel=hotel, ativo=True).order_by('nome')
            if not self.instance.pk:
                self.instance.hotel = hotel

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.hotel:
            instance.hotel = self.hotel
        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned = super().clean()
        if not self.hotel:
            raise ValidationError('Hotel não definido.')

        atividade = cleaned.get('atividade')
        categoria = cleaned.get('categoria')
        if atividade and not categoria and atividade.categoria_id:
            cleaned['categoria'] = atividade.categoria

        hora_inicio = cleaned.get('hora_inicio')
        hora_fim = cleaned.get('hora_fim')
        if hora_inicio and hora_fim and hora_fim <= hora_inicio:
            raise ValidationError({'hora_fim': 'Horário de término deve ser após o início.'})

        return cleaned


class ProgramacaoBulkCreateForm(forms.Form):
    """Adiciona várias atividades na mesma data, em sequência de horários."""

    data = forms.DateField(
        label='Data',
        widget=forms.DateInput(attrs={'class': 'rec-input', 'type': 'date'}),
    )
    hora_inicio = forms.TimeField(
        label='Horário da primeira',
        widget=forms.TimeInput(attrs={'class': 'rec-input', 'type': 'time'}),
    )
    duracao_minutos = forms.IntegerField(
        label='Duração de cada (min)',
        min_value=10,
        max_value=240,
        initial=50,
        widget=forms.NumberInput(attrs={'class': 'rec-input', 'min': 10, 'step': 5}),
    )
    local = forms.ModelChoiceField(
        label='Local',
        queryset=LocalAtividade.objects.none(),
        widget=forms.Select(attrs={'class': 'rec-input rec-select'}),
    )
    categoria = forms.ModelChoiceField(
        label='Faixa etária (opcional)',
        queryset=CategoriaProgramacao.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'rec-input rec-select'}),
    )
    recreador = forms.ModelChoiceField(
        label='Recreador',
        queryset=Recreador.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'rec-input rec-select'}),
    )
    vagas_total = forms.IntegerField(
        label='Vagas por atividade',
        min_value=1,
        initial=30,
        widget=forms.NumberInput(attrs={'class': 'rec-input', 'min': 1}),
    )
    atividades = forms.ModelMultipleChoiceField(
        label='Atividades',
        queryset=Atividade.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'prog-bulk-checklist'}),
    )

    def __init__(self, *args, hotel=None, **kwargs):
        self.hotel = hotel
        super().__init__(*args, **kwargs)
        if hotel:
            self.fields['local'].queryset = LocalAtividade.objects.filter(
                hotel=hotel, ativo=True,
            ).order_by('nome')
            self.fields['recreador'].queryset = Recreador.objects.filter(
                hotel=hotel, ativo=True,
            ).order_by('nome')
            self.fields['atividades'].queryset = (
                Atividade.objects.filter(hotel=hotel)
                .select_related('categoria')
                .order_by('categoria__ordem', 'nome')
            )

    def clean_atividades(self):
        atividades = self.cleaned_data.get('atividades')
        if not atividades:
            raise ValidationError('Selecione ao menos uma atividade.')
        return atividades

    def criar_programacoes(self):
        if not self.hotel:
            raise ValidationError('Hotel não definido.')
        data = self.cleaned_data['data']
        inicio = self.cleaned_data['hora_inicio']
        duracao = self.cleaned_data['duracao_minutos']
        local = self.cleaned_data['local']
        categoria = self.cleaned_data.get('categoria')
        recreador = self.cleaned_data.get('recreador')
        vagas = self.cleaned_data['vagas_total']
        atividades = list(self.cleaned_data['atividades'])

        criadas = []
        erros = []
        for i, ativ in enumerate(atividades):
            hi = _somar_minutos(inicio, i * duracao)
            hf = _somar_minutos(inicio, (i + 1) * duracao)
            cat = categoria or ativ.categoria
            try:
                prog = ProgramacaoDiaria(
                    hotel=self.hotel,
                    data=data,
                    hora_inicio=hi,
                    hora_fim=hf,
                    atividade=ativ,
                    local=local,
                    categoria=cat,
                    recreador=recreador,
                    vagas_total=vagas,
                )
                prog.full_clean()
                prog.save()
                criadas.append(prog)
            except ValidationError as exc:
                msg = exc.message_dict if hasattr(exc, 'message_dict') else str(exc)
                erros.append(f'{ativ.nome} ({hi:%H:%M}): {msg}')

        return criadas, erros


def _somar_minutos(hora, minutos):
    base = datetime.combine(datetime.today(), hora)
    return (base + timedelta(minutes=minutos)).time()
