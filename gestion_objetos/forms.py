import re
from django import forms
from .models import Objeto, PerfilUsuario
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

# Estilos del formulario de objetos
ESTILO_REPORTE = (
    "w-full px-4 py-3 border border-gray-300 "
    "rounded-xl bg-white focus:outline-none "
    "focus:ring-2 focus:ring-green-600"
)
CATEGORIAS = [
    ('', 'Selecciona una categoría'),
    ('Electrónica', 'Electrónica'),
    ('Llaves', 'Llaves'),
    ('Bolsos', 'Bolsos'),
    ('Útiles académicos', 'Útiles académicos'),
    ('Ropa y accesorios', 'Ropa y accesorios'),
    ('Termos y recipientes', 'Termos y recipientes'),
    ('Artículos deportivos', 'Artículos deportivos'),
    ('Artículos personales', 'Artículos personales'),
    ('Otros', 'Otros'),
]


class ObjetoForm(forms.ModelForm):

    categoria = forms.ChoiceField(
        choices=CATEGORIAS,
        label='Categoría',
        widget=forms.Select(attrs={
            'class': ESTILO_REPORTE
        })
    )

    class Meta:
        model = Objeto

        fields = [
            'titulo',
            'categoria',
            'color',
            'marca',
            'lugar',
            'fecha_suceso',
            'descripcion',
            'foto',
            'pregunta_seguridad',
            'respuesta_seguridad'
        ]

        labels = {
            'titulo': 'Nombre del objeto',
            'categoria': 'Categoría',
            'color': 'Color',
            'marca': 'Marca',
            'lugar': 'Lugar',
            'fecha_suceso': 'Fecha aproximada',
            'descripcion': 'Descripción',
            'foto': 'Fotografía del objeto',
            'pregunta_seguridad': 'Pregunta de seguridad',
            'respuesta_seguridad': 'Respuesta de seguridad',
        }

        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': ESTILO_REPORTE,
                'placeholder': 'Ej: Audífonos inalámbricos'
            }),

            'color': forms.TextInput(attrs={
                'class': ESTILO_REPORTE,
                'placeholder': 'Ej: Negro'
            }),

            'marca': forms.TextInput(attrs={
                'class': ESTILO_REPORTE,
                'placeholder': 'Ej: Samsung'
            }),

            'lugar': forms.TextInput(attrs={
                'class': ESTILO_REPORTE,
                'placeholder': 'Ej: Biblioteca, segundo piso'
            }),

            'fecha_suceso': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': ESTILO_REPORTE,
                    'type': 'date'
                }
            ),

            'descripcion': forms.Textarea(attrs={
                'class': ESTILO_REPORTE,
                'rows': 3,
                'placeholder': 'Describe las características del objeto'
            }),

            'foto': forms.ClearableFileInput(attrs={
                'class': ESTILO_REPORTE,
                'accept': 'image/png,image/jpeg,image/webp'
            }),

            'pregunta_seguridad': forms.TextInput(attrs={
                'class': ESTILO_REPORTE,
                'placeholder': 'Ej: ¿Qué detalle especial tiene el objeto?'
            }),

            'respuesta_seguridad': forms.TextInput(attrs={
                'class': ESTILO_REPORTE,
                'placeholder': 'Respuesta que servirá para verificar al dueño'
            }),
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['marca'].required = False
        self.fields['descripcion'].required = True
        self.fields['foto'].required = False

        if 'pregunta_seguridad' in self.fields:
            self.fields['pregunta_seguridad'].required = False

        if 'respuesta_seguridad' in self.fields:
            self.fields['respuesta_seguridad'].required = False

            
    def clean_foto(self):
        foto = self.cleaned_data.get('foto')

        if foto and isinstance(foto, UploadedFile):

            if foto.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    'La fotografía no puede superar los 5 MB.'
                )

            if foto.content_type not in [
                'image/jpeg',
                'image/png',
                'image/webp'
            ]:
                raise forms.ValidationError(
                    'Solo se permiten imágenes JPG, PNG o WEBP.'
                )

        return foto

    def clean(self):
        cleaned_data = super().clean()

        tipo_reporte = self.data.get('tipo_reporte')

        if (
            tipo_reporte == 'ENCONTRADO'
            and 'pregunta_seguridad' in self.fields
        ):

            if (
                not cleaned_data.get('foto')
                and 'foto' not in self.errors
            ):
                self.add_error(
                    'foto',
                    'Debes adjuntar una fotografía del objeto encontrado.'
                )

            if (
                not cleaned_data.get('pregunta_seguridad')
                and 'pregunta_seguridad' not in self.errors
            ):
                self.add_error(
                    'pregunta_seguridad',
                    'Debes escribir una pregunta de seguridad.'
                )

            if (
                not cleaned_data.get('respuesta_seguridad')
                and 'respuesta_seguridad' not in self.errors
            ):
                self.add_error(
                    'respuesta_seguridad',
                    'Debes escribir una respuesta de seguridad.'
                )

        return cleaned_data



ESTILO_CAMPO = (
    "w-full px-4 py-3 rounded-xl border border-gray-300 "
    "focus:border-[#0B402B] focus:ring-2 "
    "focus:ring-green-100 outline-none"
)


class RegistroForm(forms.Form):

    nombre = forms.CharField(
        min_length=2,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': ESTILO_CAMPO,
            'placeholder': 'Ingresa tu nombre',
            'autocomplete': 'given-name'
        })
    )

    apellido = forms.CharField(
        min_length=2,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': ESTILO_CAMPO,
            'placeholder': 'Ingresa tu apellido',
            'autocomplete': 'family-name'
        })
    )

    telefono = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': ESTILO_CAMPO,
            'placeholder': 'Ej. 3001234567',
            'inputmode': 'numeric',
            'maxlength': '10',
            'autocomplete': 'tel'
        })
    )

    correo = forms.EmailField(
        max_length=150,
        widget=forms.EmailInput(attrs={
            'class': ESTILO_CAMPO,
            'placeholder': 'usuario@unisimon.edu.co',
            'autocomplete': 'email'
        })
    )

    password1 = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': ESTILO_CAMPO,
            'placeholder': 'Crea una contraseña',
            'autocomplete': 'new-password'
        })
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': ESTILO_CAMPO,
            'placeholder': 'Repite tu contraseña',
            'autocomplete': 'new-password'
        })
    )

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()

        if not re.fullmatch(
            r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:[ '-][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*",
            nombre
        ):
            raise forms.ValidationError(
                'El nombre solo puede contener letras.'
            )

        return nombre

    def clean_apellido(self):
        apellido = self.cleaned_data['apellido'].strip()

        if not re.fullmatch(
            r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:[ '-][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*",
            apellido
        ):
            raise forms.ValidationError(
                'El apellido solo puede contener letras.'
            )

        return apellido

    def clean_telefono(self):
        telefono = self.cleaned_data['telefono'].strip()

        if not re.fullmatch(r'[0-9]{10}', telefono):
            raise forms.ValidationError(
                'El teléfono debe tener exactamente 10 números.'
            )

        return telefono

    def clean_correo(self):
        correo = self.cleaned_data['correo'].strip().lower()

        if not correo.endswith('@unisimon.edu.co'):
            raise forms.ValidationError(
                'Debes utilizar tu correo institucional @unisimon.edu.co.'
            )

        if (
            User.objects.filter(username__iexact=correo).exists()
            or User.objects.filter(email__iexact=correo).exists()
        ):
            raise forms.ValidationError(
                'Este correo ya está registrado.'
            )

        return correo

    def clean(self):
        datos = super().clean()

        password1 = datos.get('password1')
        password2 = datos.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error(
                'password2',
                'Las contraseñas no coinciden.'
            )

        if password1:
            usuario_temporal = User(
                username=datos.get('correo', ''),
                email=datos.get('correo', ''),
                first_name=datos.get('nombre', ''),
                last_name=datos.get('apellido', '')
            )

            try:
                validate_password(password1, user=usuario_temporal)

            except ValidationError as error:
                self.add_error('password1', error)

        return datos


class PerfilForm(forms.Form):

    nombre = forms.CharField(
        min_length=2,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': ESTILO_CAMPO,
            'placeholder': 'Ingresa tu nombre'
        })
    )

    apellido = forms.CharField(
        min_length=2,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': ESTILO_CAMPO,
            'placeholder': 'Ingresa tu apellido'
        })
    )

    telefono = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': ESTILO_CAMPO,
            'placeholder': 'Ej. 3001234567',
            'inputmode': 'numeric',
            'maxlength': '10'
        })
    )

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()

        if not re.fullmatch(
            r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:[ '-][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*",
            nombre
        ):
            raise forms.ValidationError(
                'El nombre solo puede contener letras.'
            )

        return nombre

    def clean_apellido(self):
        apellido = self.cleaned_data['apellido'].strip()

        if not re.fullmatch(
            r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:[ '-][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)*",
            apellido
        ):
            raise forms.ValidationError(
                'El apellido solo puede contener letras.'
            )

        return apellido

    def clean_telefono(self):
        telefono = self.cleaned_data['telefono'].strip()

        if not re.fullmatch(r'[0-9]{10}', telefono):
            raise forms.ValidationError(
                'El teléfono debe tener exactamente 10 números.'
            )

        return telefono


class FotoPerfilForm(forms.ModelForm):

    class Meta:
        model = PerfilUsuario
        fields = ['foto_perfil']

    def clean_foto_perfil(self):
        foto = self.cleaned_data.get('foto_perfil')

        if foto:
            if foto.size > 3 * 1024 * 1024:
                raise forms.ValidationError(
                    'La fotografía no puede superar los 3 MB.'
                )

            formatos = ['JPEG', 'PNG', 'WEBP']

            if foto.image.format not in formatos:
                raise forms.ValidationError(
                    'Solo se permiten imágenes JPG, PNG o WEBP.'
                )

        return foto

    

class EditarObjetoForm(ObjetoForm):

    class Meta(ObjetoForm.Meta):
        fields = [
            'titulo',
            'categoria',
            'color',
            'marca',
            'lugar',
            'fecha_suceso',
            'descripcion',
            'foto'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields.pop('pregunta_seguridad', None)
        self.fields.pop('respuesta_seguridad', None)

    def clean_foto(self):

        foto = self.cleaned_data.get('foto')

        if foto and isinstance(foto, UploadedFile):

            if foto.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    'La fotografía no puede superar los 5 MB.'
                )

            formatos_permitidos = [
                'image/jpeg',
                'image/png',
                'image/webp'
            ]

            if foto.content_type not in formatos_permitidos:
                raise forms.ValidationError(
                    'Solo se permiten fotografías JPG, PNG o WEBP.'
                )

        return foto


