from django import forms


class ImportacaoProgramacaoForm(forms.Form):
    arquivo = forms.FileField(
        label='Planilha de programação (.xlsx)',
        help_text='Padrão Nacional: abas por faixa etária (Adultos, Kids, Boys & Girls…)',
    )
    substituir_datas = forms.BooleanField(
        label='Substituir programação das datas importadas',
        required=False,
        initial=False,
        help_text='Remove registros existentes nas mesmas datas antes de importar.',
    )


class ImportacaoEventosForm(forms.Form):
    arquivo = forms.FileField(
        label='Planilha de eventos (.xlsx)',
        help_text='Padrão Nacional: abas por mês com EVENTO, fornecedor, orçamento e data.',
    )


class AnaliseFaixasForm(forms.Form):
    FONTE_PLANILHA = 'planilha'
    FONTE_BANCO = 'banco'

    fonte = forms.ChoiceField(
        label='Fonte dos dados',
        choices=[
            (FONTE_PLANILHA, 'Planilha Excel selecionada'),
            (FONTE_BANCO, 'Dados já importados no sistema'),
        ],
        initial=FONTE_PLANILHA,
        widget=forms.RadioSelect,
    )
    arquivo = forms.FileField(
        label='Planilha de programação (.xlsx)',
        required=False,
        help_text='Obrigatório se fonte = planilha.',
    )
    dias = forms.IntegerField(
        label='Período (dias)',
        min_value=7,
        max_value=365,
        initial=90,
        required=False,
        help_text='Para dados do banco: últimos N dias.',
    )
