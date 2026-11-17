"""Protección y verificación de respuestas ocultas de SafeItems.

Los reportes nuevos usan una versión marcada del hash para poder normalizar
la respuesta sin perder la compatibilidad con reportes ya almacenados.
"""

from django.contrib.auth.hashers import make_password, check_password


MARCADOR_NORMALIZACION = 'safeitems-normalizada-v1$'


def normalizar_respuesta(texto):
    """Ignora mayúsculas y espacios repetidos, pero conserva las palabras y tildes."""
    return ' '.join((texto or '').casefold().split())


def proteger_respuesta(texto):
    """Devuelve un hash para respuestas NUEVAS, sin guardar texto plano."""
    respuesta = normalizar_respuesta(texto)
    if not respuesta:
        raise ValueError('La respuesta de seguridad no puede estar vacía.')
    return MARCADOR_NORMALIZACION + make_password(respuesta)


def verificar_respuesta(texto, valor_guardado):
    """Verifica respuestas nuevas normalizadas y hashes antiguos sin cambiarlos."""
    if not valor_guardado:
        return False

    if valor_guardado.startswith(MARCADOR_NORMALIZACION):
        hash_real = valor_guardado[len(MARCADOR_NORMALIZACION):]
        return check_password(normalizar_respuesta(texto), hash_real)

    # Compatibilidad: los reportes antiguos usaban make_password(texto.strip()).
    # No se puede recuperar ni normalizar el texto original a partir del hash.
    return check_password((texto or '').strip(), valor_guardado)
