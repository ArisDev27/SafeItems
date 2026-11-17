
"""Comparación y sincronización de posibles coincidencias en SafeItems.

El porcentaje expresa similitud de los datos publicados, NO propiedad verificada.
"""

import re
import unicodedata
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from difflib import SequenceMatcher

# Porcentajes del algoritmo (suman 100).
PESOS = {
    'categoria': 25,
    'titulo': 30,
    'color': 15,
    'marca': 10,
    'lugar': 10,
    'fecha': 10,
}
UMBRAL_COINCIDENCIA = Decimal('70.00')

PALABRAS_GENERICAS = {
    'un', 'una', 'unos', 'unas', 'de', 'del', 'la', 'las', 'el', 'los',
    'con', 'sin', 'para', 'por', 'en', 'y', 'o', 'mi', 'su', 'objeto',
    'perdido', 'perdida', 'encontrado', 'encontrada', 'color', 'marca',
}

# Equivalencias muy específicas de nombres de productos comunes.
NOMBRES_EQUIVALENTES = {
    'audifono': 'audifonos', 'audifonos': 'audifonos',
    'auricular': 'audifonos', 'auriculares': 'audifonos',
    'earbuds': 'audifonos', 'airpods': 'audifonos',
    'celular': 'telefono', 'movil': 'telefono', 'smartphone': 'telefono',
    'telefono': 'telefono',
    'morral': 'mochila', 'mochila': 'mochila',
    'laptop': 'portatil', 'portatil': 'portatil',
}


def normalizar(texto):
    """Elimina diferencias de tildes, mayúsculas y espacios en datos públicos."""
    texto = unicodedata.normalize('NFKD', str(texto or ''))
    texto = ''.join(letra for letra in texto if not unicodedata.combining(letra))
    texto = texto.casefold()
    return ' '.join(re.findall(r'[a-z0-9]+', texto))


def similitud_texto(primero, segundo):
    primero, segundo = normalizar(primero), normalizar(segundo)
    if not primero or not segundo:
        return 0.0
    if primero == segundo:
        return 1.0
    secuencia = SequenceMatcher(None, primero, segundo).ratio()
    p1, p2 = set(primero.split()), set(segundo.split())
    palabras = len(p1 & p2) / max(len(p1), len(p2))
    return max(secuencia, palabras)


def palabras_importantes(objeto):
    """Extrae el tipo de artículo, evitando que solo coincida una marca/color."""
    titulo = set(normalizar(objeto.titulo).split())
    excluir = (
        PALABRAS_GENERICAS
        | set(normalizar(objeto.marca).split())
        | set(normalizar(objeto.color).split())
    )
    return {
        NOMBRES_EQUIVALENTES.get(palabra, palabra)
        for palabra in titulo if palabra not in excluir
    }


def similitud_tipo_articulo(perdido, encontrado):
    p1, p2 = palabras_importantes(perdido), palabras_importantes(encontrado)
    if not p1 or not p2:
        return 0.0
    return len(p1 & p2) / max(len(p1), len(p2))


def similitud_fecha(fecha_perdida, fecha_hallazgo):
    if not isinstance(fecha_perdida, date) or not isinstance(fecha_hallazgo, date):
        return None
    diferencia = (fecha_hallazgo - fecha_perdida).days
    # Fecha aproximada: tolerancia limitada si el hallazgo se reportó antes.
    if diferencia < -2:
        return 0.0
    return max(0.0, 1.0 - abs(diferencia) / 30.0)


def calcular_similitud(perdido, encontrado):
    """Devuelve Decimal(0..100) o None si los reportes son incompatibles.

    Se evita relacionar categorías y tipos de artículo contradictorios.
    Los campos opcionales ausentes no cuentan en el denominador.
    """
    if perdido.estado != 'PERDIDO' or encontrado.estado != 'ENCONTRADO':
        return None
    if perdido.pk is not None and perdido.pk == encontrado.pk:
        return None
    if (perdido.reportado_por_id is not None
            and perdido.reportado_por_id == encontrado.reportado_por_id):
        return None
    if not normalizar(perdido.categoria) or normalizar(perdido.categoria) != normalizar(encontrado.categoria):
        return None

    similitud_titulo = similitud_tipo_articulo(perdido, encontrado)
    # Dos productos diferentes de la misma categoría no son una coincidencia.
    if similitud_titulo == 0:
        return None

    marca_perdida, marca_encontrada = normalizar(perdido.marca), normalizar(encontrado.marca)
    if marca_perdida and marca_encontrada and similitud_texto(marca_perdida, marca_encontrada) < 0.70:
        return None

    fechas = similitud_fecha(perdido.fecha_suceso, encontrado.fecha_suceso)
    if fechas == 0 and isinstance(perdido.fecha_suceso, date) and isinstance(encontrado.fecha_suceso, date):
        # Si hay una contradicción temporal fuerte, no sugerir relación.
        return None

    puntuacion = PESOS['categoria'] * 1.0 + PESOS['titulo'] * similitud_titulo
    peso_disponible = PESOS['categoria'] + PESOS['titulo']

    for campo in ('color', 'marca', 'lugar'):
        valor_a, valor_b = getattr(perdido, campo), getattr(encontrado, campo)
        if normalizar(valor_a) and normalizar(valor_b):
            puntuacion += PESOS[campo] * similitud_texto(valor_a, valor_b)
            peso_disponible += PESOS[campo]

    if fechas is not None:
        puntuacion += PESOS['fecha'] * fechas
        peso_disponible += PESOS['fecha']

    porcentaje = Decimal(str(100 * puntuacion / peso_disponible))
    return porcentaje.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def actualizar_coincidencias_de_objeto(objeto, notificar=True):
    """Crea, actualiza o elimina coincidencias de UN objeto (idempotente).

    Se llama después de guardar un reporte y al editarlo. La unicidad del par
    está garantizada por la restricción del modelo Coincidencia.
    """
    from django.db.models import Q
    from django.urls import reverse
    from .models import Coincidencia, Objeto
    from .notificaciones import crear_notificacion

    relacionadas = Coincidencia.objects.filter(
        Q(objeto_perdido_id=objeto.pk) | Q(objeto_encontrado_id=objeto.pk)
    )
    if objeto.estado not in ('PERDIDO', 'ENCONTRADO'):
        relacionadas.delete()
        return 0

    estado_opuesto = 'ENCONTRADO' if objeto.estado == 'PERDIDO' else 'PERDIDO'
    candidatos = (Objeto.objects.filter(estado=estado_opuesto)
                  .exclude(pk=objeto.pk)
                  .exclude(reportado_por_id=objeto.reportado_por_id)
                  .select_related('reportado_por'))

    ids_vigentes = []
    for otro in candidatos.iterator(chunk_size=200):
        perdido, encontrado = (
            (objeto, otro) if objeto.estado == 'PERDIDO' else (otro, objeto)
        )
        porcentaje = calcular_similitud(perdido, encontrado)
        if porcentaje is None or porcentaje < UMBRAL_COINCIDENCIA:
            continue

        coincidencia, creada = Coincidencia.objects.update_or_create(
            objeto_perdido=perdido,
            objeto_encontrado=encontrado,
            defaults={'porcentaje_similitud': porcentaje},
        )
        ids_vigentes.append(coincidencia.pk)

        if creada and notificar:
            for reporte_propio, reporte_relacionado in (
                (perdido, encontrado), (encontrado, perdido)
            ):
                crear_notificacion(
                    destinatario=reporte_propio.reportado_por,
                    tipo='COINCIDENCIA',
                    titulo='Nueva posible coincidencia',
                    mensaje=(
                        f'Se encontró una posible coincidencia del {porcentaje}% '
                        f'para tu reporte: {reporte_propio.titulo}. '
                        'Revisa los detalles antes de tomar una decisión.'
                    ),
                    destino=(
                        reverse('detalle_objeto', kwargs={'objeto_id': reporte_propio.pk})
                        + '#coincidencias-objeto'
                    ),
                )

    # También retira vínculos que dejaron de coincidir tras una edición.
    relacionadas.exclude(pk__in=ids_vigentes).delete()
    return len(ids_vigentes)
