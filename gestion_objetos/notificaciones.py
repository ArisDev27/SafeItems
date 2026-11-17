
from .models import Notificacion


def crear_notificacion(destinatario, tipo, titulo, mensaje, destino=''):

    notificacion = Notificacion.objects.create(
        destinatario=destinatario,
        tipo=tipo,
        titulo=titulo,
        mensaje=mensaje,
        url=destino,
        leida=False
    )

    return notificacion
