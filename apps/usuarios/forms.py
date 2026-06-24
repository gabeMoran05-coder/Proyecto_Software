from django import forms

from django.utils import timezone

from .models import Usuario
from apps.text_utils import first_upper, first_upper_or_none


class LoginForm(forms.Form):
    usuario = forms.CharField(
        label='Usuario',
        max_length=60,
        widget=forms.TextInput(attrs={'autofocus': True, 'placeholder': 'usuario'}),
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'placeholder': 'contraseña'}),
    )


class UsuarioForm(forms.ModelForm):
    password = forms.CharField(
        label='Contraseña',
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
            'email',
            'puesto',
            'fecha_contratacion',
            'fecha_baja',
            'activo',
            'password',
        ]
        widgets = {
            'fecha_contratacion': forms.DateInput(attrs={'type': 'date'}),
            'fecha_baja': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.localdate().isoformat()
        self.fields['rol'].choices = Usuario.ROL_PUBLIC_CHOICES
        self.fields['fecha_contratacion'].widget.attrs['max'] = today
        if self.instance.pk and self.instance.rol == Usuario.ROL_ADMINISTRADOR:
            self.initial['rol'] = Usuario.ROL_ADMIN
        for field_name in ('nombre', 'ap_pat', 'ap_mat', 'puesto'):
            self.fields[field_name].widget.attrs['data-capitalize-first'] = ''
        if not self.instance.pk:
            self.fields['password'].required = True
            self.fields['password'].widget.attrs['placeholder'] = 'Contraseña inicial'

    def clean(self):
        cleaned_data = super().clean()
        fecha_contratacion = cleaned_data.get('fecha_contratacion')
        fecha_baja = cleaned_data.get('fecha_baja')
        hoy = timezone.localdate()

        if fecha_contratacion and fecha_contratacion > hoy:
            self.add_error(
                'fecha_contratacion',
                'La fecha de contratación no puede ser posterior a la fecha actual.',
            )
        if fecha_contratacion and fecha_baja and fecha_contratacion > fecha_baja:
            self.add_error(
                'fecha_contratacion',
                'La fecha de contratación no puede ser posterior al último día laboral.',
            )
            self.add_error(
                'fecha_baja',
                'El último día laboral debe ser igual o posterior a la fecha de contratación.',
            )
        return cleaned_data

    def save(self, commit=True):
        password = self.cleaned_data.pop('password', '')
        usuario = super().save(commit=False)
        usuario.nombre = first_upper(usuario.nombre)
        usuario.ap_pat = first_upper_or_none(usuario.ap_pat)
        usuario.ap_mat = first_upper_or_none(usuario.ap_mat)
        usuario.puesto = first_upper_or_none(usuario.puesto)
        if usuario.rol == Usuario.ROL_ADMINISTRADOR:
            usuario.rol = Usuario.ROL_ADMIN
        if password:
            usuario.set_password(password)
        if commit:
            usuario.save()
        return usuario
