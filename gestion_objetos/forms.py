from django import forms
from .models import Objeto

class ObjetoForm(forms.ModelForm):
    class Meta:
        model = Objeto
        fields = ['titulo', 'categoria', 'color', 'marca', 'lugar', 'foto', 'pregunta_seguridad', 'respuesta_seguridad']
        
        # Aquí inyectamos Tailwind directamente a las cajas de texto
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-[#0B402B] focus:ring-2 focus:ring-[#0B402B]/20 outline-none transition-all', 'placeholder': 'Ej. Morral HP, Llaves de casa...'}),
            'categoria': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-[#0B402B] focus:ring-2 focus:ring-[#0B402B]/20 outline-none transition-all', 'placeholder': 'Ej. Electrónica, Útiles, Accesorios'}),
            'color': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-[#0B402B] focus:ring-2 focus:ring-[#0B402B]/20 outline-none transition-all', 'placeholder': 'Ej. Negro con rojo'}),
            'marca': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-[#0B402B] focus:ring-2 focus:ring-[#0B402B]/20 outline-none transition-all', 'placeholder': 'Ej. Totto, Apple (Opcional)'}),
            'lugar': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-[#0B402B] focus:ring-2 focus:ring-[#0B402B]/20 outline-none transition-all', 'placeholder': 'Ej. Biblioteca, Cafetería central'}),
            
            # Botón de subir archivo personalizado
            'foto': forms.FileInput(attrs={'class': 'w-full px-4 py-2.5 bg-white rounded-xl border border-gray-300 text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-bold file:bg-[#E8F8EE] file:text-[#135A3E] hover:file:bg-[#D0ECD7] cursor-pointer'}),
            
            'pregunta_seguridad': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-[#0B402B] focus:ring-2 focus:ring-[#0B402B]/20 outline-none transition-all', 'placeholder': 'Ej. ¿Qué hay en el bolsillo pequeño?'}),
            'respuesta_seguridad': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-gray-300 focus:border-[#0B402B] focus:ring-2 focus:ring-[#0B402B]/20 outline-none transition-all', 'placeholder': 'Respuesta exacta para verificar al dueño'}),
        }