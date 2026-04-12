from django import forms
from apps.ventas.models import Cliente

class ClienteForm(forms.ModelForm):
    class Meta:
        model  = Cliente
        fields = ['nombre', 'ap_pat', 'ap_mat', 'telefono']
        widgets = {
            'nombre':   forms.TextInput(attrs={'class': 'form-control'}),
            'ap_pat':   forms.TextInput(attrs={'class': 'form-control'}),
            'ap_mat':   forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }
