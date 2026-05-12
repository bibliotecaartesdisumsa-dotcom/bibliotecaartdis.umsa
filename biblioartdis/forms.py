# forms.py
from django import forms
import locale
from datetime import datetime
from .models import Autor,Imagen,Usuario,Coleccion,Revista

locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')  # Para sistemas Unix
# locale.setlocale(locale.LC_TIME, 'es_ES')  # Para sistemas Windows

class LoginForm(forms.Form):
    correo = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su correo electrónico',
            'id': 'id_correo'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña',
            'id': 'id_password'
        })
    )

from django import forms
from datetime import datetime

class VisitaFilterForm(forms.Form):
    MESES = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]
    
    # Generar años a partir del año actual hasta un rango de 10 años hacia atrás
    AÑOS = [(year, year) for year in range(datetime.now().year, datetime.now().year - 10, -1)]
    
    mes = forms.ChoiceField(choices=MESES, label='Mes', required=True)
    año = forms.ChoiceField(choices=AÑOS, label='Año', required=True)
    vista_opcion = forms.ChoiceField(
        choices=[
            ('nivel', 'Por Nivel'),
            ('unitarias', 'Unitarias')
        ],
        label='Ver por',
        required=True
    )

class ColeccionForm(forms.ModelForm):
    class Meta:
        model = Coleccion
        fields = ['nomb_colecc', 'descripcion']
        labels = {
            'nomb_colecc': 'Nombre de la Colección',
            'descripcion': 'Descripción'
        }
        widgets = {
            'nomb_colecc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre de la colección'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese la descripción de la colección',
                'rows': 3
            })
        }

class RevistaForm(forms.ModelForm):
    class Meta:
        model = Revista
        fields = ['coleccion', 'nro_revista', 'descripcion', 'img_portada', 'pdf', 'url']
        labels = {
            'nro_revista': 'Número de Revista',
            'coleccion': 'Colección',
            'descripcion': 'Descripción',
            'img_portada': 'Imagen de Portada',
            'pdf': 'Archivo PDF',
            'url': 'URL de la Revista'
        }
        

class AutorForm(forms.ModelForm):
    class Meta:
        model = Autor
        fields = ['nombre']

class ImagenForm(forms.ModelForm):
    class Meta:
        model = Imagen
        fields = ['titulo', 'autorImg', 'descripcion', 'img_portada', 'pdf']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class LibroSearchForm(forms.Form):
    query = forms.CharField(max_length=255, required=False, label='Buscar')

class UsuarioForm(forms.ModelForm):
    correo = forms.EmailField(required=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional by default
        for field in self.fields:
            self.fields[field].required = False
        
        # Set required fields
        self.fields['nombres'].required = True
        self.fields['ci'].required = True
        self.fields['correo'].required = True

    class Meta:
        model = Usuario
        fields = [
            'nombres', 
            'apepat', 
            'apemat', 
            'ci', 
            'correo', 
            'extension',
            'complemento',
            'tipo_usuario',
            'ru',
            'nro_celular',
            'esta_activo',
            'fecha_baja'
        ]
        widgets = {
            'fecha_baja': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean_correo(self):
        correo = self.cleaned_data.get('correo')
        if not correo:
            raise forms.ValidationError('El correo es requerido.')
        # Verificar si el correo ya existe, excluyendo el usuario actual
        if Usuario.objects.filter(correo=correo).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este correo ya está registrado.')
        return correo

    def clean_ci(self):
        ci = self.cleaned_data.get('ci')
        # Verificar si el CI ya existe, excluyendo el usuario actual
        if Usuario.objects.filter(ci=ci).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Este CI ya está registrado.')
        return ci

class CambiarPasswordForm(forms.Form):
    password_actual = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña actual'
        })
    )
    password_nuevo = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su nueva contraseña'
        })
    )
    password_confirmacion = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme su nueva contraseña'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password_nuevo = cleaned_data.get('password_nuevo')
        password_confirmacion = cleaned_data.get('password_confirmacion')

        if password_nuevo and password_confirmacion:
            if password_nuevo != password_confirmacion:
                raise forms.ValidationError('Las contraseñas no coinciden')
