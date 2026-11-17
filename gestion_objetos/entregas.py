
"""Generación, consulta y validación de códigos para entregar objetos SafeItems."""

import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import F

from .models import PerfilUsuario
from .admin_views import solo_administradores
from .coincidencias import actualizar_coincidencias_de_objeto
from .models import Objeto, SolicitudReclamacion
from .notificaciones import crear_notificacion

PUNTOS_POR_ENTREGA = 10

# Se evitan O, 0, I y 1 para que el código sea fácil de leer en persona.
ALFABETO_CODIGO = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
LONGITUD_CODIGO = 10


def generar_codigo_entrega():
    """Genera un código aleatorio que no esté en uso en otro objeto."""
    for _ in range(20):
        codigo = ''.join(
            secrets.choice(ALFABETO_CODIGO)
            for _ in range(LONGITUD_CODIGO)
        )
        if not Objeto.objects.filter(codigo_entrega=codigo).exists():
            return codigo
    raise RuntimeError('No se pudo generar un código de entrega único.')


@login_required(login_url='login')
def mi_entrega(request, solicitud_id):
    """Solo el reclamante aprobado puede consultar su código."""
    solicitud = get_object_or_404(
        SolicitudReclamacion.objects.select_related('objeto'),
        pk=solicitud_id,
        solicitante=request.user,
    )

    codigo = None
    if solicitud.estado == 'APROBADA' and solicitud.objeto.estado == 'ENCONTRADO':
        codigo = solicitud.objeto.codigo_entrega or None

    return render(
        request,
        'gestion_objetos/mi_entrega.html',
        {'solicitud': solicitud, 'codigo': codigo},
    )


@solo_administradores
@require_POST
@transaction.atomic
def generar_codigo_aprobado_admin(request, solicitud_id):
    """Regulariza una aprobación antigua creada antes de este módulo."""
    solicitud_previa = get_object_or_404(SolicitudReclamacion, pk=solicitud_id)

    objeto = get_object_or_404(
        Objeto.objects.select_for_update(),
        pk=solicitud_previa.objeto_id
    )

    solicitud = get_object_or_404(
        SolicitudReclamacion.objects.select_for_update(),
        pk=solicitud_id,
        objeto=objeto,
    )

    if solicitud.estado != 'APROBADA' or objeto.estado != 'ENCONTRADO':
        messages.error(
            request,
            'Esta reclamación no está pendiente de entrega.'
        )

    elif objeto.codigo_entrega:
        messages.info(
            request,
            'Esta reclamación ya tiene un código de entrega.'
        )

    else:
        objeto.codigo_entrega = generar_codigo_entrega()
        objeto.save(update_fields=['codigo_entrega'])

        crear_notificacion(
            destinatario=solicitud.solicitante,
            tipo='ENTREGA',
            titulo='Ya tienes tu código de entrega',
            mensaje=(
                f'El código para recuperar "{objeto.titulo}" '
                'está disponible en tu cuenta de SafeItems.'
            ),
            destino=reverse(
                'mi_entrega',
                kwargs={'solicitud_id': solicitud.pk}
            ),
        )

        messages.success(
            request,
            'Código generado. El estudiante ya puede verlo.'
        )

    return redirect(
        'detalle_reclamacion_admin',
        solicitud_id=solicitud_id
    )


@solo_administradores
@require_POST
@transaction.atomic
def confirmar_entrega_admin(request, solicitud_id):
    """Valida el código una sola vez y cierra la devolución física."""

    codigo_recibido = request.POST.get(
        'codigo_entrega', ''
    ).strip().upper()

    if len(codigo_recibido) != LONGITUD_CODIGO:
        messages.error(
            request,
            'Ingresa el código completo de 10 caracteres.'
        )
        return redirect(
            'detalle_reclamacion_admin',
            solicitud_id=solicitud_id
        )

    solicitud_previa = get_object_or_404(
        SolicitudReclamacion,
        pk=solicitud_id
    )

    objeto = get_object_or_404(
        Objeto.objects.select_for_update(),
        pk=solicitud_previa.objeto_id
    )

    solicitud = get_object_or_404(
        SolicitudReclamacion.objects.select_for_update()
        .select_related('solicitante'),
        pk=solicitud_id,
        objeto=objeto,
    )

    if solicitud.estado != 'APROBADA' or objeto.estado != 'ENCONTRADO':
        messages.error(
            request,
            'Este objeto no tiene una entrega pendiente.'
        )
        return redirect(
            'detalle_reclamacion_admin',
            solicitud_id=solicitud_id
        )

    codigo_guardado = objeto.codigo_entrega or ''

    if not codigo_guardado or not secrets.compare_digest(
        codigo_recibido,
        codigo_guardado
    ):
        messages.error(
            request,
            'El código no es válido. No se registró la entrega.'
        )
        return redirect(
            'detalle_reclamacion_admin',
            solicitud_id=solicitud_id
        )

    # El código se invalida y los dos registros cambian de estado juntos.
    solicitud.estado = 'ENTREGADA'
    solicitud.fecha_entrega = timezone.now()
    solicitud.save(
        update_fields=['estado', 'fecha_entrega']
    )

    objeto.estado = 'RECLAMADO'
    objeto.codigo_entrega = None
    objeto.save(
        update_fields=['estado', 'codigo_entrega']
    )

    # ASIGNAR PUNTOS AL ESTUDIANTE QUE REPORTÓ
    # EL OBJETO ENCONTRADO.

    perfil, creado = PerfilUsuario.objects.select_for_update().get_or_create(
        usuario=objeto.reportado_por
    )

    # Sumar los puntos de la entrega confirmada
    PerfilUsuario.objects.filter(
        pk=perfil.pk
    ).update(
        puntos_colaboracion=F('puntos_colaboracion') + PUNTOS_POR_ENTREGA
    )

    # Obtener los puntos actualizados
    perfil.refresh_from_db(fields=['puntos_colaboracion'])

    puntos_totales = perfil.puntos_colaboracion

    # Determinar el nivel del estudiante
    if puntos_totales >= 60:
        nuevo_nivel = 'Héroe'

    elif puntos_totales >= 30:
        nuevo_nivel = 'Ayudante'

    elif puntos_totales >= 10:
        nuevo_nivel = 'Colaborador'

    else:
        nuevo_nivel = 'Novato'

    # Guardar el nivel si cambió
    if perfil.nivel != nuevo_nivel:
        perfil.nivel = nuevo_nivel
        perfil.save(update_fields=['nivel'])


    # Notificar los puntos recibidos.
    crear_notificacion(
        destinatario=objeto.reportado_por,
        tipo='PUNTOS',
        titulo='¡Ganaste puntos de colaboración!',
        mensaje=(
            f'Recibiste {PUNTOS_POR_ENTREGA} puntos por colaborar '
            f'en la devolución de "{objeto.titulo}".'
        ),
        destino=reverse('perfil'),
    )

    # Retirar las coincidencias que ya no deben aparecer.
    actualizar_coincidencias_de_objeto(
        objeto,
        notificar=False
    )

    crear_notificacion(
        destinatario=solicitud.solicitante,
        tipo='ENTREGA',
        titulo='Entrega confirmada',
        mensaje=(
            f'La devolución de "{objeto.titulo}" '
            'fue registrada correctamente.'
        ),
        destino=reverse(
            'mi_entrega',
            kwargs={'solicitud_id': solicitud.pk}
        ),
    )

    crear_notificacion(
        destinatario=objeto.reportado_por,
        tipo='ENTREGA',
        titulo='Objeto entregado',
        mensaje=(
            f'Se confirmó la devolución del objeto "{objeto.titulo}".'
        ),
        destino=reverse(
            'detalle_objeto',
            kwargs={'objeto_id': objeto.pk}
        ),
    )

    messages.success(
        request,
        'Entrega confirmada. El caso quedó cerrado.'
    )

    return redirect(
        'detalle_reclamacion_admin',
        solicitud_id=solicitud_id
    )
