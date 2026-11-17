from django.db import models
from django.contrib.auth.models import User
from django.conf import settings


# 1. Perfil para la gamificación (se conecta al usuario de Django).
class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    puntos_colaboracion = models.IntegerField(default=0, help_text='Puntos por devolver objetos')
    nivel = models.CharField(max_length=50, default='Novato', help_text='Nivel del usuario (ej. Novato, Héroe)')
    telefono = models.CharField(max_length=15, blank=True, null=True)
    foto_perfil = models.ImageField(upload_to='fotos_perfil/', blank=True, null=True)

    def __str__(self):
        return f'{self.usuario.username} - Nivel: {self.nivel}'


# 2. Tabla de objetos perdidos/encontrados.
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
    descripcion = models.TextField(blank=True)
    fecha_suceso = models.DateField(null=True, blank=True)
    foto = models.ImageField(upload_to='objetos_fotos/', blank=True, null=True)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES)
    reportado_por = models.ForeignKey(User, on_delete=models.CASCADE)

    # Protocolo de seguridad.
    pregunta_seguridad = models.CharField(max_length=150, blank=True)
    respuesta_seguridad = models.CharField(max_length=255, blank=True)
    codigo_entrega = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f'{self.titulo} - {self.estado}'


# 3. Tabla de coincidencias.
class Coincidencia(models.Model):
    objeto_perdido = models.ForeignKey(
        Objeto, on_delete=models.CASCADE, related_name='posibles_encuentros'
    )
    objeto_encontrado = models.ForeignKey(
        Objeto, on_delete=models.CASCADE, related_name='posibles_perdidas'
    )
    porcentaje_similitud = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['objeto_perdido', 'objeto_encontrado'],
                name='coincidencia_unica_por_par',
            ),
        ]

    def __str__(self):
        return f'Coincidencia: {self.porcentaje_similitud}%'


class SolicitudReclamacion(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
        ('ENTREGADA', 'Entregada'),
    ]

    objeto = models.ForeignKey(
        'Objeto', on_delete=models.PROTECT, related_name='solicitudes_reclamacion'
    )
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reclamaciones_realizadas'
    )
    estado = models.CharField(max_length=12, choices=ESTADOS, default='PENDIENTE')
    respuesta_verificada = models.BooleanField(default=False)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    observaciones_admin = models.TextField(blank=True)
    datos_objeto_al_solicitar = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-fecha_solicitud']
        verbose_name = 'Solicitud de reclamación'
        verbose_name_plural = 'Solicitudes de reclamación'

    def __str__(self):
        return f'Solicitud #{self.pk} - {self.objeto.titulo} ({self.estado})'


class AvisoHallazgo(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('CONFIRMADO', 'Confirmado'),
        ('RECHAZADO', 'Rechazado'),
    ]

    objeto = models.ForeignKey(
        'Objeto', on_delete=models.PROTECT, related_name='avisos_hallazgo'
    )
    informante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='avisos_hallazgo_enviados'
    )
    lugar_hallazgo = models.CharField(max_length=200)
    descripcion = models.TextField()
    foto = models.ImageField(upload_to='avisos_hallazgo/', blank=False, null=True)
    estado = models.CharField(max_length=12, choices=ESTADOS, default='PENDIENTE')
    fecha_aviso = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_aviso']
        constraints = [
            models.UniqueConstraint(
                fields=['objeto', 'informante'],
                name='unico_aviso_hallazgo_por_usuario'
            )
        ]

    def __str__(self):
        return f'Aviso #{self.pk} - {self.objeto.titulo}'


class Notificacion(models.Model):
    TIPOS = [
        ('HALLAZGO', 'Aviso de hallazgo'),
        ('RECLAMACION', 'Reclamación'),
        ('ESTADO', 'Cambio de estado'),
        ('ENTREGA', 'Entrega de objeto'),
        ('COINCIDENCIA', 'Coincidencia'),
        ('PUNTOS', 'Puntos'),
        ('SISTEMA', 'Sistema'),
    ]

    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='notificaciones'
    )
    tipo = models.CharField(max_length=20, choices=TIPOS, default='SISTEMA')
    titulo = models.CharField(max_length=150)
    mensaje = models.TextField()
    url = models.CharField(max_length=300, blank=True)
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.titulo
