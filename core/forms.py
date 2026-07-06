from django import forms
from django.core.exceptions import ValidationError

from .models import Hospede, NoiteTematica, ProdutoLoja, NoiteTematica, ProdutoLoja


class HospedeForm(forms.ModelForm):
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
        ]
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'rec-input', 'placeholder': 'Nome completo'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'rec-input', 'type': 'date', 'id': 'id_data_nascimento'}),
            'documento': forms.TextInput(attrs={'class': 'rec-input', 'placeholder': 'RG, CPF ou passaporte'}),
            'apartamento': forms.TextInput(attrs={'class': 'rec-input', 'placeholder': 'Ex.: 302'}),
            'data_checkin': forms.DateInput(attrs={'class': 'rec-input', 'type': 'date'}),
            'data_checkout': forms.DateInput(attrs={'class': 'rec-input', 'type': 'date'}),
            'observacoes': forms.Textarea(attrs={'class': 'rec-input rec-textarea', 'rows': 3, 'placeholder': 'Observações opcionais'}),
        }

    def __init__(self, *args, hotel=None, **kwargs):
        self.hotel = hotel
        super().__init__(*args, **kwargs)
        self.fields['data_checkout'].required = False

    def clean(self):
        cleaned = super().clean()
        if not self.hotel:
            raise ValidationError('Hotel não definido para o check-in.')

        documento = cleaned.get('documento')
        if documento and self.hotel:
            duplicado = (
                Hospede.objects.filter(
                    hotel=self.hotel,
                    documento=documento,
                    data_checkout__isnull=True,
                )
                .exclude(pk=self.instance.pk if self.instance else None)
                .exists()
            )
            if duplicado:
                raise ValidationError(
                    {'documento': 'Já existe hóspede ativo com este documento neste hotel.'}
                )

        data_checkin = cleaned.get('data_checkin')
        data_checkout = cleaned.get('data_checkout')
        if data_checkin and data_checkout and data_checkout < data_checkin:
            raise ValidationError({'data_checkout': 'Check-out não pode ser anterior ao check-in.'})

        return cleaned


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
