from django.db import models
from django.contrib.auth.models import User

# 1. Perfil para la Gamificación (Se conecta al usuario de Django)
class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    puntos_colaboracion = models.IntegerField(default=0, help_text="Puntos por devolver objetos")
    nivel = models.CharField(max_length=50, default='Novato', help_text="Nivel del usuario (ej. Novato, Héroe)")
    telefono = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.usuario.username} - Nivel: {self.nivel}"

# 2. Tabla de Objetos Perdidos/Encontrados
class Objeto(models.Model):
    ESTADO_CHOICES = [
        ('PERDIDO', 'Perdido'),
        ('ENCONTRADO', 'Encontrado'),
        ('RECLAMADO', 'Reclamado (Entregado)'),
    ]

    titulo = models.CharField(max_length=100) 
    categoria = models.CharField(max_length=50) 
    color = models.CharField(max_length=30)
    marca = models.CharField(max_length=50, blank=True, null=True)
    lugar = models.CharField(max_length=100) 
    foto = models.ImageField(upload_to='objetos_fotos/', blank=True, null=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES)
    reportado_por = models.ForeignKey(User, on_delete=models.CASCADE)

    # Protocolo de Seguridad
    pregunta_seguridad = models.CharField(max_length=150)
    respuesta_seguridad = models.CharField(max_length=100)
    codigo_entrega = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"{self.titulo} - {self.estado}"

# 3. Tabla de Coincidencias (Para tu algoritmo)
class Coincidencia(models.Model):
    objeto_perdido = models.ForeignKey(Objeto, on_delete=models.CASCADE, related_name='posibles_encuentros')
    objeto_encontrado = models.ForeignKey(Objeto, on_delete=models.CASCADE, related_name='posibles_perdidas')
    porcentaje_similitud = models.DecimalField(max_digits=5, decimal_places=2) 

    def __str__(self):
        return f"Coincidencia: {self.porcentaje_similitud}%"