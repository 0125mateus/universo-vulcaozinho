from django import forms


class HospedeAppLoginForm(forms.Form):
    apartamento = forms.CharField(
        label='Apartamento',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'app-input',
            'placeholder': 'Ex.: 302',
            'autocomplete': 'off',
            'inputmode': 'numeric',
        }),
    )
    documento = forms.CharField(
        label='CPF / documento',
        max_length=30,
        help_text='Informe o documento completo ou os 4 últimos dígitos.',
        widget=forms.TextInput(attrs={
            'class': 'app-input',
            'placeholder': '000.000.000-00 ou 4 últimos dígitos',
            'autocomplete': 'off',
        }),
    )
