
from django import forms
from .models import AvisoHallazgo


class AvisoHallazgoForm(forms.ModelForm):

    class Meta:
        model = AvisoHallazgo

        fields = [
            'lugar_hallazgo',
            'descripcion',
            'foto'
        ]

        widgets = {
            'lugar_hallazgo': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#0B402B]',
                'placeholder': 'Ejemplo: Biblioteca, segundo piso',
                'maxlength': '200'
            }),

            'descripcion': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-[#0B402B]',
                'placeholder': 'Describe el objeto que encontraste y dónde lo tienes.',
                'rows': 4,
                'maxlength': '2000'
            }),

            'foto': forms.ClearableFileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-xl',
                'accept': 'image/jpeg,image/png,image/webp'
            })
        }

    def clean_descripcion(self):
        descripcion = self.cleaned_data['descripcion'].strip()

        if len(descripcion) < 15:
            raise forms.ValidationError(
                'Escribe al menos 15 caracteres.'
            )

        if len(descripcion) > 2000:
            raise forms.ValidationError(
                'La descripción no puede superar 2000 caracteres.'
            )

        return descripcion

   
    def clean_foto(self):
        foto = self.cleaned_data.get('foto')

        if not foto:
            raise forms.ValidationError(
                'Debes adjuntar una fotografía del objeto.'
            )

        if foto.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                'La fotografía no puede superar 5 MB.'
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

