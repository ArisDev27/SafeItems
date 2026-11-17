
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import views
from .models import Objeto, SolicitudReclamacion
from .notificaciones import crear_notificacion


def es_administrador_safeitems(usuario):
    return (
        usuario.is_authenticated
        and usuario.is_active
        and usuario.username in settings.SAFEITEMS_ADMIN_USERS
    )


def solo_administradores(vista):

    @wraps(vista)
    @login_required(login_url='login')
    def protegida(request, *args, **kwargs):

        if not es_administrador_safeitems(request.user):
            raise PermissionDenied(
                'No tienes permiso para entrar al panel de SafeItems.'
            )

        return vista(request, *args, **kwargs)

    return protegida


def solo_estudiantes(vista):

    @wraps(vista)
    @login_required(login_url='login')
    def protegida(request, *args, **kwargs):

        if es_administrador_safeitems(request.user):

            messages.error(
                request,
                'Esta sección es exclusiva para estudiantes.'
            )

            return redirect('panel_administrador')

        return vista(request, *args, **kwargs)

    return protegida


@login_required(login_url='login')
def inicio_segun_rol(request):

    if es_administrador_safeitems(request.user):
        return redirect('panel_administrador')

    return views.inicio(request)


@solo_administradores
def panel_administrador(request):

    estado = request.GET.get(
        'estado',
        'PENDIENTE'
    ).strip().upper()

    estados_validos = {
        'TODAS',
        'PENDIENTE',
        'APROBADA',
        'RECHAZADA',
        'ENTREGADA'
    }

    if estado not in estados_validos:
        estado = 'PENDIENTE'

    busqueda = request.GET.get('q', '').strip()

    solicitudes = SolicitudReclamacion.objects.select_related(
        'objeto',
        'solicitante',
        'objeto__reportado_por'
    ).order_by('-fecha_solicitud')

    if estado != 'TODAS':
        solicitudes = solicitudes.filter(
            estado=estado
        )

    if busqueda:

        solicitudes = solicitudes.filter(
            Q(objeto__titulo__icontains=busqueda)
            | Q(solicitante__username__icontains=busqueda)
            | Q(solicitante__first_name__icontains=busqueda)
            | Q(solicitante__last_name__icontains=busqueda)
        )

    pagina = Paginator(
        solicitudes,
        8
    ).get_page(
        request.GET.get('page')
    )

    return render(
        request,
        'gestion_objetos/administracion.html',
        {
            'pantalla': 'panel',
            'page_obj': pagina,
            'estado': estado,
            'busqueda': busqueda,

            'total_pendientes': (
                SolicitudReclamacion.objects.filter(
                    estado='PENDIENTE'
                ).count()
            ),

            'total_aprobadas': (
                SolicitudReclamacion.objects.filter(
                    estado='APROBADA'
                ).count()
            ),

            'total_entregadas': (
                SolicitudReclamacion.objects.filter(
                    estado='ENTREGADA'
                ).count()
            ),

            'total_reportes_activos': (
                Objeto.objects.filter(
                    estado__in=['PERDIDO', 'ENCONTRADO']
                ).count()
            ),
        }
    )


@solo_administradores
def detalle_reclamacion_admin(request, solicitud_id):

    solicitud = get_object_or_404(
        SolicitudReclamacion.objects.select_related(
            'objeto',
            'objeto__reportado_por',
            'solicitante'
        ),
        pk=solicitud_id
    )

    otra_aprobada = SolicitudReclamacion.objects.filter(
        objeto=solicitud.objeto,
        estado='APROBADA'
    ).exclude(
        pk=solicitud.pk
    ).exists()

    pendiente = solicitud.estado == 'PENDIENTE'

    return render(
        request,
        'gestion_objetos/administracion.html',
        {
            'pantalla': 'detalle',
            'solicitud': solicitud,

            'puede_rechazar': pendiente,

            'puede_aprobar': (
                pendiente
                and solicitud.objeto.estado == 'ENCONTRADO'
                and solicitud.respuesta_verificada
                and not otra_aprobada
            ),
        }
    )


@solo_administradores
@require_POST
@transaction.atomic
def resolver_reclamacion_admin(request, solicitud_id):

    accion = request.POST.get(
        'accion',
        ''
    ).strip()

    observaciones = request.POST.get(
        'observaciones',
        ''
    ).strip()

    if accion not in ('aprobar', 'rechazar'):

        messages.error(
            request,
            'Selecciona una acción válida.'
        )

        return redirect(
            'detalle_reclamacion_admin',
            solicitud_id=solicitud_id
        )

    if len(observaciones) > 1000:

        messages.error(
            request,
            'Las observaciones no pueden superar 1.000 caracteres.'
        )

        return redirect(
            'detalle_reclamacion_admin',
            solicitud_id=solicitud_id
        )

    if accion == 'rechazar' and not observaciones:

        messages.error(
            request,
            'Explica por qué rechazas la reclamación.'
        )

        return redirect(
            'detalle_reclamacion_admin',
            solicitud_id=solicitud_id
        )

    solicitud_inicial = get_object_or_404(
        SolicitudReclamacion,
        pk=solicitud_id
    )

    objeto = get_object_or_404(
        Objeto.objects.select_for_update(),
        pk=solicitud_inicial.objeto_id
    )

    solicitud = get_object_or_404(
        SolicitudReclamacion.objects
        .select_for_update()
        .select_related('solicitante'),
        pk=solicitud_id,
        objeto=objeto
    )

    if solicitud.estado != 'PENDIENTE':

        messages.error(
            request,
            'Esta solicitud ya fue resuelta; no puede modificarse otra vez.'
        )

        return redirect(
            'detalle_reclamacion_admin',
            solicitud_id=solicitud_id
        )

    if accion == 'aprobar':

        if (
            objeto.estado != 'ENCONTRADO'
            or not solicitud.respuesta_verificada
        ):

            messages.error(
                request,
                'Esta solicitud no cumple las condiciones para aprobarse.'
            )

            return redirect(
                'detalle_reclamacion_admin',
                solicitud_id=solicitud_id
            )

        if SolicitudReclamacion.objects.filter(
            objeto=objeto,
            estado='APROBADA'
        ).exclude(
            pk=solicitud.pk
        ).exists():

            messages.error(
                request,
                'Este objeto ya tiene una reclamación aprobada.'
            )

            return redirect(
                'detalle_reclamacion_admin',
                solicitud_id=solicitud_id
            )

        from .entregas import generar_codigo_entrega

        objeto.codigo_entrega = generar_codigo_entrega()

        objeto.save(
            update_fields=['codigo_entrega']
        )

    solicitud.estado = (
        'APROBADA'
        if accion == 'aprobar'
        else 'RECHAZADA'
    )

    solicitud.fecha_revision = timezone.now()
    solicitud.observaciones_admin = observaciones

    solicitud.save(
        update_fields=[
            'estado',
            'fecha_revision',
            'observaciones_admin'
        ]
    )

    destino = reverse(
        'detalle_objeto',
        kwargs={
            'objeto_id': objeto.pk
        }
    )

    destino_estudiante = reverse(
        'mi_entrega',
        kwargs={
            'solicitud_id': solicitud.pk
        }
    )

    crear_notificacion(
        destinatario=solicitud.solicitante,
        tipo='RECLAMACION',

        titulo=(
            'Tu reclamación fue '
            + (
                'aprobada'
                if accion == 'aprobar'
                else 'rechazada'
            )
        ),

        mensaje=(
            f'La reclamación del objeto "{objeto.titulo}" fue '
            + (
                'aprobada. Consulta el código de entrega desde tu cuenta.'
                if accion == 'aprobar'
                else 'rechazada por el administrador.'
            )
        ),

        destino=destino_estudiante
    )

    crear_notificacion(
        destinatario=objeto.reportado_por,
        tipo='ESTADO',
        titulo='Actualización de reclamación',

        mensaje=(
            f'Una solicitud del objeto "{objeto.titulo}" fue '
            + (
                'aprobada.'
                if accion == 'aprobar'
                else 'rechazada.'
            )
        ),

        destino=destino + f'#reclamacion-{solicitud.pk}'
    )

    if accion == 'aprobar':

        otras_pendientes = list(
            SolicitudReclamacion.objects
            .select_for_update()
            .filter(
                objeto=objeto,
                estado='PENDIENTE'
            )
            .select_related('solicitante')
        )

        for otra in otras_pendientes:

            otra.estado = 'RECHAZADA'
            otra.fecha_revision = timezone.now()

            otra.observaciones_admin = (
                'Se aprobó otra reclamación para este objeto.'
            )

            otra.save(
                update_fields=[
                    'estado',
                    'fecha_revision',
                    'observaciones_admin'
                ]
            )

            crear_notificacion(
                destinatario=otra.solicitante,
                tipo='RECLAMACION',

                titulo='Actualización de tu reclamación',

                mensaje=(
                    f'Tu solicitud sobre "{objeto.titulo}" fue '
                    'cerrada porque se aprobó otra reclamación.'
                ),

                destino=reverse(
                    'mi_entrega',
                    kwargs={
                        'solicitud_id': otra.pk
                    }
                )
            )

    messages.success(
        request,
        (
            'Reclamación aprobada correctamente.'
            if accion == 'aprobar'
            else 'Reclamación rechazada correctamente.'
        )
    )

    return redirect(
        'detalle_reclamacion_admin',
        solicitud_id=solicitud_id
    )
