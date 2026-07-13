from django import forms
from django.forms import inlineformset_factory

from .models import (
    ExtraRecreador,
    ItemCompraSemanal,
    PagamentoAtracao,
    PeriodoOperacional,
    StatusPagamentoOperacional,
)
from .termo_utils import normalizar_telefone_whatsapp


class PeriodoOperacionalForm(forms.ModelForm):
    class Meta:
        model = PeriodoOperacional
        fields = (
            'titulo', 'data_inicio', 'data_fim', 'ocupacao_pct', 'qtd_pax',
        )
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'rec-input', 'placeholder': 'Ex.: 23/02 a 01/03'}),
            'data_inicio': forms.DateInput(attrs={'type': 'date', 'class': 'rec-input'}),
            'data_fim': forms.DateInput(attrs={'type': 'date', 'class': 'rec-input'}),
            'ocupacao_pct': forms.NumberInput(attrs={'class': 'rec-input', 'step': '0.01'}),
            'qtd_pax': forms.NumberInput(attrs={'class': 'rec-input', 'min': 0}),
        }


class PagamentoAtracaoForm(forms.ModelForm):
    class Meta:
        model = PagamentoAtracao
        fields = (
            'data_label', 'data_evento', 'artista', 'atracao', 'valor', 'chave_pix',
            'evento', 'tipo_servico', 'responsavel', 'horario', 'local_dept',
            'status', 'autorizacao_diretoria', 'observacoes',
        )
        widgets = {
            'data_label': forms.TextInput(attrs={'class': 'rec-input'}),
            'data_evento': forms.DateInput(attrs={'type': 'date', 'class': 'rec-input'}),
            'artista': forms.TextInput(attrs={'class': 'rec-input'}),
            'atracao': forms.TextInput(attrs={'class': 'rec-input'}),
            'valor': forms.NumberInput(attrs={'class': 'rec-input', 'step': '0.01'}),
            'chave_pix': forms.TextInput(attrs={'class': 'rec-input'}),
            'evento': forms.TextInput(attrs={'class': 'rec-input'}),
            'tipo_servico': forms.TextInput(attrs={'class': 'rec-input'}),
            'responsavel': forms.TextInput(attrs={'class': 'rec-input'}),
            'horario': forms.TextInput(attrs={'class': 'rec-input'}),
            'local_dept': forms.TextInput(attrs={'class': 'rec-input'}),
            'status': forms.Select(attrs={'class': 'rec-input'}),
            'autorizacao_diretoria': forms.TextInput(attrs={'class': 'rec-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'rec-input', 'rows': 2}),
        }


class ItemCompraForm(forms.ModelForm):
    class Meta:
        model = ItemCompraSemanal
        fields = ('descricao', 'quantidade', 'link_fornecedor', 'preco_unitario')
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'rec-input'}),
            'quantidade': forms.NumberInput(attrs={'class': 'rec-input', 'min': 1}),
            'link_fornecedor': forms.TextInput(attrs={'class': 'rec-input', 'placeholder': 'https://… ou LINK'}),
            'preco_unitario': forms.NumberInput(attrs={'class': 'rec-input', 'step': '0.01'}),
        }


class ExtraRecreadorForm(forms.ModelForm):
    class Meta:
        model = ExtraRecreador
        fields = (
            'nome',
            'valor_seg', 'valor_ter', 'valor_qua', 'valor_qui',
            'valor_sex', 'valor_sab', 'valor_dom',
        )
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'rec-input fin-grid-nome'}),
            **{
                f'valor_{d}': forms.NumberInput(attrs={
                    'class': 'rec-input fin-grid-valor',
                    'step': '0.01',
                    'min': 0,
                    'inputmode': 'decimal',
                })
                for d in ('seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom')
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'DELETE' in self.fields:
            self.fields['DELETE'].widget = forms.HiddenInput()


ExtraRecreadorFormSet = inlineformset_factory(
    PeriodoOperacional,
    ExtraRecreador,
    form=ExtraRecreadorForm,
    extra=1,
    can_delete=True,
)


class ImportarXlsxForm(forms.Form):
    arquivo = forms.FileField(
        label='Planilha Excel (.xlsx)',
        widget=forms.ClearableFileInput(attrs={'class': 'rec-input', 'accept': '.xlsx'}),
    )
    substituir = forms.BooleanField(
        label='Substituir itens deste período',
        required=False,
        initial=False,
    )


class WhatsAppSetorPagamentosForm(forms.Form):
    whatsapp_setor_pagamentos = forms.CharField(
        label='WhatsApp do setor de pagamentos',
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'rec-input',
            'placeholder': '(35) 99999-8888',
            'inputmode': 'tel',
            'autocomplete': 'tel',
        }),
        help_text='Com DDD. Este número recebe as planilhas pelo botão Enviar no WhatsApp.',
    )

    def clean_whatsapp_setor_pagamentos(self):
        value = (self.cleaned_data.get('whatsapp_setor_pagamentos') or '').strip()
        if not value:
            return ''
        if not normalizar_telefone_whatsapp(value):
            raise forms.ValidationError('Informe um número válido com DDD (ex.: 35999998888).')
        return value
