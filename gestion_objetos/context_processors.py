
from .models import Notificacion


def notificaciones_usuario(request):

    if not request.user.is_authenticated:
        return {
            'notificaciones_recientes': [],
            'notificaciones_sin_leer': 0
        }

    notificaciones = Notificacion.objects.filter(
        destinatario=request.user
    ).order_by('-fecha_creacion', '-id')

    return {
        'notificaciones_recientes': notificaciones[:6],
        'notificaciones_sin_leer': notificaciones.filter(
            leida=False
        ).count()
    }
