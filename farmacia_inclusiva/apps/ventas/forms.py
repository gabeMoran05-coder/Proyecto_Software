from django import forms
from .models import Venta, DetalleVenta, MetodoPago
from django.forms import inlineformset_factory

class VentaForm(forms.ModelForm):
    class Meta:
        model  = Venta
        fields = ['metodo_pago', 'cliente']
        widgets = {
            'metodo_pago': forms.Select(attrs={'class': 'form-select'}),
            'cliente':     forms.Select(attrs={'class': 'form-select'}),
        }

DetalleVentaFormSet = inlineformset_factory(
    Venta, DetalleVenta,
    fields=['medicamento', 'cantidad', 'precio_unitario'],
    extra=1, can_delete=True
)
