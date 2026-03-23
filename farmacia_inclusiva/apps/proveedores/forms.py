from django import forms
from .models import Proveedor

class ProveedorForm(forms.ModelForm):
    class Meta:
        model  = Proveedor
        fields = ['nombre', 'telefono', 'correo', 'direccion']
        widgets = {
            'nombre':    forms.TextInput(attrs={'class': 'form-control'}),
            'telefono':  forms.TextInput(attrs={'class': 'form-control'}),
            'correo':    forms.EmailInput(attrs={'class': 'form-control'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
