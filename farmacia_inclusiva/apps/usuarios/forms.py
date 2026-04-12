from django import forms
from .models import Usuario


class LoginForm(forms.Form):
    username = forms.CharField(label='Usuario', max_length=150,
                               widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Usuario'}))
    password = forms.CharField(label='Contraseña',
                               widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}))


class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        label='Contraseña', required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Dejar vacío para no cambiar'})
    )

    class Meta:
        model = Usuario
        fields = ['username', 'nombre', 'ap_pat', 'ap_mat', 'telefono', 'rol', 'is_active']
        widgets = {
            'username':  forms.TextInput(attrs={'class': 'form-control'}),
            'nombre':    forms.TextInput(attrs={'class': 'form-control'}),
            'ap_pat':    forms.TextInput(attrs={'class': 'form-control'}),
            'ap_mat':    forms.TextInput(attrs={'class': 'form-control'}),
            'telefono':  forms.TextInput(attrs={'class': 'form-control'}),
            'rol':       forms.Select(attrs={'class': 'form-select'}),
        }
