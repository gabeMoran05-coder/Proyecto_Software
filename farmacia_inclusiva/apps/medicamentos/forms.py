from django import forms
from .models import Medicamento, Lote


class MedicamentoForm(forms.ModelForm):
    class Meta:
        model  = Medicamento
        fields = ['nombre', 'presentacion', 'concentracion', 'requiere_receta']
        widgets = {
            'nombre':          forms.TextInput(attrs={'class': 'form-control'}),
            'presentacion':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tableta, Cápsula, Jarabe...'}),
            'concentracion':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': '500mg, 10mg/5ml...'}),
            'requiere_receta': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class LoteForm(forms.ModelForm):
    class Meta:
        model  = Lote
        fields = ['numero_lote', 'proveedor', 'fecha_fabricacion',
                  'fecha_caducidad', 'stock_actual', 'precio_compra', 'precio_venta']
        widgets = {
            'numero_lote':       forms.TextInput(attrs={'class': 'form-control'}),
            'proveedor':         forms.Select(attrs={'class': 'form-select'}),
            'fecha_fabricacion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_caducidad':   forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'stock_actual':      forms.NumberInput(attrs={'class': 'form-control'}),
            'precio_compra':     forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precio_venta':      forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.proveedores.models import Proveedor
        self.fields['proveedor'].queryset = Proveedor.objects.all()
        self.fields['proveedor'].empty_label = '— Sin proveedor —'
        self.fields['proveedor'].required = False
