from django import forms

from .models import Usuario


class LoginForm(forms.Form):
    usuario = forms.CharField(
        label='Usuario',
        max_length=60,
        widget=forms.TextInput(attrs={'autofocus': True, 'placeholder': 'usuario'}),
    )
    password = forms.CharField(
        label='Contrasena',
        widget=forms.PasswordInput(attrs={'placeholder': 'contrasena'}),
    )


class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        label='Contrasena',
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Dejar vacio para no cambiar'}),
    )

    class Meta:
        model = Usuario
        fields = [
            'usuario',
            'rol',
            'nombre',
            'ap_pat',
            'ap_mat',
            'telefono',
            'puesto',
            'fecha_contratacion',
            'fecha_baja',
            'activo',
            'fecha_creacion',
            'password',
        ]
        widgets = {
            'fecha_creacion': forms.DateInput(attrs={'type': 'date'}),
            'fecha_contratacion': forms.DateInput(attrs={'type': 'date'}),
            'fecha_baja': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['password'].required = True
            self.fields['password'].widget.attrs['placeholder'] = 'Contrasena inicial'

    def save(self, commit=True):
        password = self.cleaned_data.pop('password', '')
        usuario = super().save(commit=False)
        if password:
            usuario.set_password(password)
        if commit:
            usuario.save()
        return usuario
