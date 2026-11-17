from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ObjetoForm
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.db import transaction
from .forms import RegistroForm, PerfilForm
from .models import PerfilUsuario
from .forms import FotoPerfilForm
from django.contrib import messages
from .seguridad_respuestas import proteger_respuesta, verificar_respuesta
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from datetime import date
from django.db.models import Q, Exists, OuterRef
from django.core.paginator import Paginator
from django.core import signing
from django.shortcuts import render, get_object_or_404
from .models import Objeto, SolicitudReclamacion
from .forms import EditarObjetoForm
from .models import Objeto, AvisoHallazgo, Notificacion
from .forms_aviso import AvisoHallazgoForm
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from .notificaciones import crear_notificacion
from .coincidencias import actualizar_coincidencias_de_objeto
from .models import Coincidencia


# PÁGINA PRINCIPAL
@login_required(login_url='login')
def inicio(request):

    publicaciones_recientes = Objeto.objects.filter(
        estado__in=['PERDIDO', 'ENCONTRADO']
    ).order_by('-id')[:6]

    return render(
        request,
        'gestion_objetos/index.html',
        {
            'publicaciones_recientes': publicaciones_recientes
        }
    )



# REPORTAR OBJETO PERDIDO
@login_required(login_url='login')
@transaction.atomic
def reportar_perdido(request):

    tipo_reporte = 'PERDIDO'

    if request.method == 'POST':

        form = ObjetoForm(request.POST, request.FILES)

        tipo_reporte = request.POST.get(
            'tipo_reporte',
            ''
        )

        # Validar el tipo de reporte
        if tipo_reporte not in ['PERDIDO', 'ENCONTRADO']:
            form.add_error(
                None,
                'Selecciona un tipo de reporte válido.'
            )

        # Si el objeto es encontrado, se requieren
        # pregunta y respuesta de seguridad
        if tipo_reporte == 'ENCONTRADO':

            if not request.POST.get(
                'pregunta_seguridad', ''
            ).strip():

                form.add_error(
                    'pregunta_seguridad',
                    'Debes escribir una pregunta de seguridad.'
                )

            if not request.POST.get(
                'respuesta_seguridad', ''
            ).strip():

                form.add_error(
                    'respuesta_seguridad',
                    'Debes escribir la respuesta de seguridad.'
                )

        if form.is_valid():

            objeto = form.save(commit=False)

            objeto.estado = tipo_reporte
            objeto.reportado_por = request.user

            if tipo_reporte == 'ENCONTRADO':

                # Guardar la respuesta protegida
                objeto.respuesta_seguridad = proteger_respuesta(
                    form.cleaned_data['respuesta_seguridad']
                )

            else:

                # Los objetos perdidos no requieren
                # preguntas de seguridad
                objeto.pregunta_seguridad = ''
                objeto.respuesta_seguridad = ''

            objeto.save()
            # Compara de inmediato con los reportes del tipo contrario.
            actualizar_coincidencias_de_objeto(objeto)

            messages.success(
                request,
                'Tu reporte se publicó correctamente.'
            )

            return redirect('reportar_perdido')

    else:

        form = ObjetoForm()

    return render(
        request,
        'gestion_objetos/reportar_perdido.html',
        {
            'form': form,
            'tipo_reporte': tipo_reporte
        }
    )


def registro(request):

    # Si ya inició sesión, enviarlo al inicio
    if request.user.is_authenticated:
        return redirect('inicio')

    if request.method == 'POST':
        form = RegistroForm(request.POST)

        if form.is_valid():

            datos = form.cleaned_data

            # Guardar usuario y perfil juntos
            with transaction.atomic():

                usuario = User.objects.create_user(
                    username=datos['correo'],
                    email=datos['correo'],
                    first_name=datos['nombre'],
                    last_name=datos['apellido'],
                    password=datos['password1']
                )

                PerfilUsuario.objects.create(
                    usuario=usuario,
                    telefono=datos['telefono']
                )

            return redirect('inicio')

    else:
        form = RegistroForm()

    return render(
        request,
        'gestion_objetos/registro.html',
        {'form': form}
    )

@login_required(login_url='login')
def perfil(request):

    perfil_usuario, creado = PerfilUsuario.objects.get_or_create(
        usuario=request.user
    )

    if request.method == 'POST':

        form = PerfilForm(request.POST)

        if form.is_valid():

            with transaction.atomic():

                request.user.first_name = form.cleaned_data['nombre']
                request.user.last_name = form.cleaned_data['apellido']

                request.user.save(
                    update_fields=['first_name', 'last_name']
                )

                perfil_usuario.telefono = form.cleaned_data['telefono']

                perfil_usuario.save(
                    update_fields=['telefono']
                )

            messages.success(
                request,
                'Tu información se actualizó correctamente.'
            )

            return redirect('perfil')

    else:

        form = PerfilForm(initial={
            'nombre': request.user.first_name,
            'apellido': request.user.last_name,
            'telefono': perfil_usuario.telefono or ''
        })

    return render(
        request,
        'gestion_objetos/perfil.html',
        {
            'form': form,
            'perfil_usuario': perfil_usuario
        }
    )


@login_required(login_url='login')
@require_POST
def actualizar_foto_perfil(request):

    perfil_usuario = get_object_or_404(
        PerfilUsuario,
        usuario=request.user
    )

    if 'foto_perfil' not in request.FILES:
        messages.error(
            request,
            'Selecciona una fotografía.'
        )

        return redirect('perfil')

    form = FotoPerfilForm(
        request.POST,
        request.FILES,
        instance=perfil_usuario
    )

    if form.is_valid():

        form.save()

        messages.success(
            request,
            'Tu fotografía de perfil se actualizó correctamente.'
        )

    else:

        errores = form.errors.get('foto_perfil')

        messages.error(
            request,
            errores[0] if errores
            else 'No se pudo guardar la fotografía.'
        )

    return redirect('perfil')


@login_required(login_url='login')
def buscar_objeto(request):

    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    categoria = request.GET.get('categoria', '').strip()
    color = request.GET.get('color', '').strip()
    marca = request.GET.get('marca', '').strip()
    lugar = request.GET.get('lugar', '').strip()
    fecha = request.GET.get('fecha', '').strip()

    objetos = Objeto.objects.filter(
        estado__in=['PERDIDO', 'ENCONTRADO']
    ).order_by('-id')

    if q:
        objetos = objetos.filter(
            Q(titulo__icontains=q) |
            Q(descripcion__icontains=q) |
            Q(categoria__icontains=q) |
            Q(marca__icontains=q) |
            Q(color__icontains=q) |
            Q(lugar__icontains=q)
        )

    if tipo in ['PERDIDO', 'ENCONTRADO']:
        objetos = objetos.filter(estado=tipo)
    else:
        tipo = ''

    if categoria:
        objetos = objetos.filter(categoria=categoria)

    if color:
        objetos = objetos.filter(color__icontains=color)

    if marca:
        objetos = objetos.filter(marca__icontains=marca)

    if lugar:
        objetos = objetos.filter(lugar__icontains=lugar)

    if fecha:
        try:
            fecha_valida = date.fromisoformat(fecha)
            objetos = objetos.filter(fecha_suceso=fecha_valida)
        except ValueError:
            fecha = ''

    paginador = Paginator(objetos, 9)
    page_obj = paginador.get_page(request.GET.get('page'))

    # Coincidencias de los reportes propios, solo en la vista sin filtros.
    coincidencias_destacadas = []
    if not any([q, tipo, categoria, color, marca, lugar, fecha]):
        coincidencias = (
            Coincidencia.objects.filter(
                Q(objeto_perdido__reportado_por=request.user) |
                Q(objeto_encontrado__reportado_por=request.user),
                objeto_perdido__estado='PERDIDO',
                objeto_encontrado__estado='ENCONTRADO',
            )
            .select_related('objeto_perdido', 'objeto_encontrado')
            .order_by('-porcentaje_similitud', '-id')[:6]
        )
        for coincidencia in coincidencias:
            if coincidencia.objeto_perdido.reportado_por_id == request.user.pk:
                coincidencia.mi_reporte = coincidencia.objeto_perdido
                coincidencia.objeto_coincidente = coincidencia.objeto_encontrado
            else:
                coincidencia.mi_reporte = coincidencia.objeto_encontrado
                coincidencia.objeto_coincidente = coincidencia.objeto_perdido
            coincidencias_destacadas.append(coincidencia)

    return render(
        request,
        'gestion_objetos/buscar_objeto.html',
        {
            'page_obj': page_obj,
            'q': q,
            'tipo': tipo,
            'categoria': categoria,
            'color': color,
            'marca': marca,
            'lugar': lugar,
            'fecha': fecha,
            'coincidencias_destacadas': coincidencias_destacadas,
        }
    )


@login_required(login_url='login')
def detalle_objeto(request, objeto_id):

    objetos_visibles = Objeto.objects.filter(
        Q(estado__in=['PERDIDO', 'ENCONTRADO']) |
        Q(reportado_por=request.user)
    )

    objeto = objetos_visibles.filter(pk=objeto_id).first()

    if objeto is None:
        messages.error(
            request,
            'Este objeto ya no está disponible.'
        )
        return redirect('buscar_objeto')

    avisos_recibidos = AvisoHallazgo.objects.none()
    solicitudes_recibidas = SolicitudReclamacion.objects.none()
    coincidencias_del_objeto = []

    # Solo el dueño del reporte puede ver aquí sus posibles coincidencias.
    # El porcentaje es una sugerencia y no autoriza ninguna reclamación.
    if (objeto.reportado_por_id == request.user.id
            and objeto.estado in ('PERDIDO', 'ENCONTRADO')):
        coincidencias = (
            Coincidencia.objects.filter(
                Q(objeto_perdido=objeto) | Q(objeto_encontrado=objeto),
                objeto_perdido__estado='PERDIDO',
                objeto_encontrado__estado='ENCONTRADO',
            )
            .select_related('objeto_perdido', 'objeto_encontrado')
            .order_by('-porcentaje_similitud', '-id')[:8]
        )
        for coincidencia in coincidencias:
            relacionado = (
                coincidencia.objeto_encontrado
                if objeto.estado == 'PERDIDO'
                else coincidencia.objeto_perdido
            )
            coincidencias_del_objeto.append({
                'relacionado': relacionado,
                'porcentaje': coincidencia.porcentaje_similitud,
            })

    if objeto.reportado_por_id == request.user.id:
        if objeto.estado == 'PERDIDO':
            avisos_recibidos = AvisoHallazgo.objects.filter(
                objeto=objeto
            ).select_related('informante').order_by('-fecha_aviso')

        elif objeto.estado in ['ENCONTRADO', 'RECLAMADO']:
            solicitudes_recibidas = SolicitudReclamacion.objects.filter(
                objeto=objeto
            ).select_related('solicitante').order_by('-fecha_solicitud')

    return render(
        request,
        'gestion_objetos/detalle_objeto.html',
        {
            'objeto': objeto,
            'avisos_recibidos': avisos_recibidos,
            'solicitudes_recibidas': solicitudes_recibidas,
            'coincidencias_del_objeto': coincidencias_del_objeto,
        }
    )



@login_required(login_url='login')
def mis_reportes(request):

    reportes_usuario = Objeto.objects.filter(
        reportado_por=request.user
    )

    total_reportes = reportes_usuario.count()

    total_perdidos = reportes_usuario.filter(
        estado='PERDIDO'
    ).count()

    total_encontrados = reportes_usuario.filter(
        estado='ENCONTRADO'
    ).count()

    total_reclamados = reportes_usuario.filter(
        estado='RECLAMADO'
    ).count()

    busqueda = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '').strip()

    estados_validos = ['PERDIDO', 'ENCONTRADO', 'RECLAMADO']

    if estado not in estados_validos:
        estado = ''

    solicitudes = SolicitudReclamacion.objects.filter(
        objeto_id=OuterRef('pk')
    )

    avisos = AvisoHallazgo.objects.filter(
        objeto_id=OuterRef('pk'),
        estado__in=['PENDIENTE', 'CONFIRMADO']
    )
    reportes = reportes_usuario.annotate(
        tiene_reclamacion_en_proceso=Exists(
            solicitudes.filter(
                estado__in=['PENDIENTE', 'APROBADA']
            )
        ),
        tiene_historial_reclamaciones=Exists(
            solicitudes
        ),
        tiene_avisos_hallazgo=Exists(
            avisos
        )
    ).order_by('-id')

    if busqueda:
        reportes = reportes.filter(
            Q(titulo__icontains=busqueda) |
            Q(categoria__icontains=busqueda) |
            Q(color__icontains=busqueda) |
            Q(marca__icontains=busqueda) |
            Q(lugar__icontains=busqueda)
        )

    if estado:
        reportes = reportes.filter(estado=estado)

    paginador = Paginator(reportes, 6)
    page_obj = paginador.get_page(request.GET.get('page'))

    return render(
        request,
        'gestion_objetos/mis_reportes.html',
        {
            'page_obj': page_obj,
            'total_reportes': total_reportes,
            'total_perdidos': total_perdidos,
            'total_encontrados': total_encontrados,
            'total_reclamados': total_reclamados,
            'busqueda': busqueda,
            'estado': estado
        }
    )


@login_required(login_url='login')
@transaction.atomic
def editar_reporte(request, objeto_id):

    objeto = get_object_or_404(
        Objeto.objects.select_for_update(),
        id=objeto_id,
        reportado_por=request.user
    )

    if AvisoHallazgo.objects.filter(
        objeto=objeto,
        estado__in=['PENDIENTE', 'CONFIRMADO']
    ).exists():

        messages.error(
            request,
            'Este reporte ya recibió un aviso de hallazgo y no puede editarse.'
        )

        return redirect('mis_reportes')

    if objeto.solicitudes_reclamacion.filter(
        estado__in=['PENDIENTE', 'APROBADA']
    ).exists():

        messages.error(
            request,
            'Este reporte tiene una reclamación en proceso. No puedes editarlo hasta que se resuelva.'
        )

        return redirect('mis_reportes')

    if objeto.estado == 'RECLAMADO':
        messages.error(
            request,
            'No puedes editar un reporte que ya fue reclamado.'
        )
        return redirect('mis_reportes')

    if request.method == 'POST':

        form = EditarObjetoForm(
            request.POST,
            request.FILES,
            instance=objeto
        )

        if (
            objeto.estado == 'ENCONTRADO'
            and request.POST.get('quitar_foto') == '1'
            and not request.FILES.get('foto')
        ):
            form.add_error(
                'foto',
                'Los objetos encontrados deben conservar una fotografía.'
            )

        if form.is_valid():

            reporte_actualizado = form.save(commit=False)

            if request.POST.get('quitar_foto') == '1':
                reporte_actualizado.foto = ''

            reporte_actualizado.save()
            form.save_m2m()
            actualizar_coincidencias_de_objeto(reporte_actualizado)

            messages.success(
                request,
                'Tu reporte se actualizó correctamente.'
            )

            return redirect('mis_reportes')


    else:

        form = EditarObjetoForm(instance=objeto)

    return render(
        request,
        'gestion_objetos/editar_reporte.html',
        {
            'form': form,
            'objeto': objeto
        }
    )


@login_required(login_url='login')
@require_POST
@transaction.atomic
def eliminar_reporte(request, objeto_id):

    objeto = get_object_or_404(
        Objeto.objects.select_for_update(),
        id=objeto_id,
        reportado_por=request.user
    )

    if AvisoHallazgo.objects.filter(
        objeto=objeto,
        estado__in=['PENDIENTE', 'CONFIRMADO']
    ).exists():

        messages.error(
            request,
            'Este reporte ya recibió un aviso de hallazgo y no puede eliminarse.'
        )

        return redirect('mis_reportes')

    if objeto.solicitudes_reclamacion.exists():

        messages.error(
            request,
            'Este reporte tiene un historial de reclamaciones y no puede eliminarse definitivamente.'
        )

        return redirect('mis_reportes')

    if objeto.estado == 'RECLAMADO':

        messages.error(
            request,
            'No puedes eliminar un reporte que ya fue reclamado.'
        )

        return redirect('mis_reportes')

    AvisoHallazgo.objects.filter(
        objeto=objeto,
        estado='RECHAZADO'
    ).delete()

    objeto.delete()

    messages.success(
        request,
        'Tu reporte fue eliminado correctamente.'
    )

    return redirect('mis_reportes')


def _datos_objeto_reclamado(objeto):
    return {
        'titulo': objeto.titulo,
        'categoria': objeto.categoria,
        'color': objeto.color,
        'marca': objeto.marca,
        'lugar': objeto.lugar,
        'fecha_suceso': objeto.fecha_suceso.isoformat() if objeto.fecha_suceso else None,
        'descripcion': objeto.descripcion,
        'foto': objeto.foto.name if objeto.foto else '',
        'pregunta_seguridad': objeto.pregunta_seguridad,
    }


@login_required(login_url='login')
def reclamar_objeto(request, objeto_id):
    if request.method == 'POST':
        with transaction.atomic():
            objeto = Objeto.objects.select_for_update().filter(pk=objeto_id).first()

            if objeto is None or objeto.estado != 'ENCONTRADO':
                messages.error(request, 'Este objeto ya no está disponible para reclamar.')
                return redirect('buscar_objeto')

            if objeto.reportado_por_id == request.user.pk:
                messages.error(request, 'No puedes reclamar un objeto que tú mismo reportaste.')
                return redirect('detalle_objeto', objeto_id=objeto_id)

            if not objeto.pregunta_seguridad or not objeto.respuesta_seguridad:
                messages.error(request, 'Este reporte aún no tiene una verificación de seguridad válida.')
                return redirect('detalle_objeto', objeto_id=objeto_id)

            solicitud_previa = SolicitudReclamacion.objects.filter(
                objeto=objeto,
                solicitante=request.user,
                estado__in=['PENDIENTE', 'APROBADA', 'ENTREGADA']
            ).exists()

            if solicitud_previa:
                messages.info(request, 'Ya tienes una reclamación registrada para este objeto.')
                return redirect('reclamar_objeto', objeto_id=objeto_id)

            if SolicitudReclamacion.objects.filter(objeto=objeto, estado='APROBADA').exists():
                messages.info(request, 'Este objeto ya está en proceso de entrega.')
                return redirect('reclamar_objeto', objeto_id=objeto_id)

            try:
                datos_anteriores = signing.loads(
                    request.POST.get('version_reporte', ''),
                    salt='safeitems-reclamacion',
                    max_age=3600
                )
            except signing.BadSignature:
                messages.error(request, 'La página de reclamación venció o no es válida. Vuelve a revisar el objeto.')
                return redirect('detalle_objeto', objeto_id=objeto_id)

            datos_actuales = _datos_objeto_reclamado(objeto)

            if datos_anteriores != datos_actuales:
                messages.error(request, 'La publicación cambió mientras la consultabas. Revisa los datos actualizados antes de reclamar.')
                return redirect('detalle_objeto', objeto_id=objeto_id)

            respuesta = request.POST.get('respuesta', '').strip()

            if not respuesta:
                messages.error(request, 'Debes responder la pregunta de seguridad.')
                return redirect('reclamar_objeto', objeto_id=objeto_id)

            if not verificar_respuesta(respuesta, objeto.respuesta_seguridad):
                messages.error(request, 'La respuesta no coincide con la registrada para este objeto.')
                return redirect('reclamar_objeto', objeto_id=objeto_id)

            solicitud = SolicitudReclamacion.objects.create(
                objeto=objeto,
                solicitante=request.user,
                estado='PENDIENTE',
                respuesta_verificada=True,
                datos_objeto_al_solicitar=datos_actuales
            )

            crear_notificacion(
                destinatario=objeto.reportado_por,
                tipo='RECLAMACION',
                titulo='Nueva solicitud de reclamación',
                mensaje=f'Un estudiante solicitó recuperar tu objeto: {objeto.titulo}. La solicitud está pendiente de revisión.',
                destino=reverse(
                    'detalle_objeto',
                    kwargs={'objeto_id': objeto.id}
                ) + f'#reclamacion-{solicitud.id}'
            )

            messages.success(request, 'Tu solicitud se envió correctamente y quedó pendiente de revisión.')
            return redirect('reclamar_objeto', objeto_id=objeto_id)

    objeto = Objeto.objects.filter(pk=objeto_id, estado='ENCONTRADO').first()

    if objeto is None:
        messages.error(request, 'Este objeto ya no está disponible.')
        return redirect('buscar_objeto')

    if objeto.reportado_por_id == request.user.pk:
        messages.error(request, 'No puedes reclamar un objeto que tú mismo reportaste.')
        return redirect('detalle_objeto', objeto_id=objeto_id)

    if not objeto.pregunta_seguridad or not objeto.respuesta_seguridad:
        messages.error(request, 'Este reporte aún no tiene una verificación de seguridad válida.')
        return redirect('detalle_objeto', objeto_id=objeto_id)

    solicitud_existente = SolicitudReclamacion.objects.filter(
        objeto=objeto,
        solicitante=request.user,
        estado__in=['PENDIENTE', 'APROBADA', 'ENTREGADA']
    ).order_by('-fecha_solicitud').first()

    aprobacion_en_curso = SolicitudReclamacion.objects.filter(
        objeto=objeto,
        estado='APROBADA'
    ).exists()

    return render(request, 'gestion_objetos/reclamar_objeto.html', {
        'objeto': objeto,
        'solicitud_existente': solicitud_existente,
        'aprobacion_en_curso': aprobacion_en_curso,
        'version_reporte': signing.dumps(
            _datos_objeto_reclamado(objeto),
            salt='safeitems-reclamacion'
        )
    })


def _datos_objeto_para_aviso(objeto):
    return {
        'titulo': objeto.titulo,
        'categoria': objeto.categoria,
        'color': objeto.color,
        'marca': objeto.marca,
        'lugar': objeto.lugar,
        'fecha_suceso': objeto.fecha_suceso.isoformat() if objeto.fecha_suceso else None,
        'descripcion': objeto.descripcion,
        'foto': objeto.foto.name if objeto.foto else ''
    }


@login_required(login_url='login')
def lo_encontre(request, objeto_id):

    if request.method == 'POST':

        with transaction.atomic():

            objeto = Objeto.objects.select_for_update().filter(
                pk=objeto_id,
                estado='PERDIDO'
            ).first()

            if objeto is None:
                messages.error(
                    request,
                    'Este objeto ya no está disponible.'
                )
                return redirect('buscar_objeto')

            if objeto.reportado_por_id == request.user.id:
                messages.error(
                    request,
                    'No puedes enviar un aviso sobre tu propio reporte.'
                )
                return redirect('detalle_objeto', objeto_id=objeto_id)

            if AvisoHallazgo.objects.filter(
                objeto=objeto,
                informante=request.user
            ).exists():

                messages.info(
                    request,
                    'Ya informaste que encontraste este objeto.'
                )
                return redirect('lo_encontre', objeto_id=objeto_id)

            try:
                datos_anteriores = signing.loads(
                    request.POST.get('version_reporte', ''),
                    salt='safeitems-aviso-hallazgo',
                    max_age=3600
                )

            except signing.BadSignature:
                messages.error(
                    request,
                    'La página venció. Revisa nuevamente la publicación.'
                )
                return redirect('detalle_objeto', objeto_id=objeto_id)

            datos_actuales = _datos_objeto_para_aviso(objeto)

            if datos_anteriores != datos_actuales:
                messages.error(
                    request,
                    'La publicación cambió. Revisa los datos actualizados.'
                )
                return redirect('detalle_objeto', objeto_id=objeto_id)

            form = AvisoHallazgoForm(
                request.POST,
                request.FILES
            )

            if form.is_valid():

                aviso = form.save(commit=False)

                aviso.objeto = objeto
                aviso.informante = request.user
                aviso.estado = 'PENDIENTE'

                aviso.save()

                crear_notificacion(
                    destinatario=objeto.reportado_por,
                    tipo='HALLAZGO',
                    titulo='Nuevo aviso de hallazgo',
                    mensaje=f'Un estudiante informó que encontró tu objeto: {objeto.titulo}.',
                    destino=reverse(
                        'detalle_objeto',
                        kwargs={'objeto_id': objeto.id}
                    ) + f'#aviso-{aviso.id}'
                )


                messages.success(
                    request,
                    'Tu aviso se envió correctamente.'
                )

                return redirect('lo_encontre', objeto_id=objeto_id)

    else:
        form = AvisoHallazgoForm()

    objeto = Objeto.objects.filter(
        pk=objeto_id,
        estado='PERDIDO'
    ).first()

    if objeto is None:
        messages.error(
            request,
            'Este objeto ya no está disponible.'
        )
        return redirect('buscar_objeto')

    if objeto.reportado_por_id == request.user.id:
        messages.error(
            request,
            'No puedes informar un hallazgo sobre tu propio reporte.'
        )
        return redirect('detalle_objeto', objeto_id=objeto_id)

    aviso_existente = AvisoHallazgo.objects.filter(
        objeto=objeto,
        informante=request.user
    ).first()

    version_reporte = signing.dumps(
        _datos_objeto_para_aviso(objeto),
        salt='safeitems-aviso-hallazgo'
    )

    return render(
        request,
        'gestion_objetos/lo_encontre.html',
        {
            'objeto': objeto,
            'form': form,
            'aviso_existente': aviso_existente,
            'version_reporte': version_reporte
        }
    )

@login_required(login_url='login')
@require_POST
@transaction.atomic
def descartar_aviso_hallazgo(request, aviso_id):

    aviso = get_object_or_404(
        AvisoHallazgo,
        pk=aviso_id
    )

    # Solo el propietario del reporte puede descartar el aviso.
    objeto = get_object_or_404(
        Objeto.objects.select_for_update(),
        pk=aviso.objeto_id,
        reportado_por=request.user,
        estado='PERDIDO'
    )

    aviso = get_object_or_404(
        AvisoHallazgo.objects.select_for_update(),
        pk=aviso_id,
        objeto=objeto
    )

    # Un aviso resuelto no se puede modificar nuevamente.
    if aviso.estado != 'PENDIENTE':
        messages.info(
            request,
            'Este aviso ya fue revisado.'
        )
        return redirect('detalle_objeto', objeto_id=objeto.id)

    # Marcar el aviso como rechazado, sin borrarlo.
    aviso.estado = 'RECHAZADO'
    aviso.save(update_fields=['estado'])

    # Avisar al estudiante que informó el hallazgo.
    crear_notificacion(
        destinatario=aviso.informante,
        tipo='HALLAZGO',
        titulo='Aviso de hallazgo descartado',
        mensaje=(
            f'El estudiante que publicó "{objeto.titulo}" '
            'indicó que tu aviso no corresponde al objeto perdido.'
        ),
        destino=reverse(
            'lo_encontre',
            kwargs={'objeto_id': objeto.id}
        )
    )

    messages.success(
        request,
        'El aviso fue descartado correctamente.'
    )

    return redirect(
        reverse(
            'detalle_objeto',
            kwargs={'objeto_id': objeto.id}
        ) + f'#aviso-{aviso.id}'
    )



@login_required(login_url='login')
@require_POST
def abrir_notificacion(request, notificacion_id):

    notificacion = get_object_or_404(
        Notificacion,
        pk=notificacion_id,
        destinatario=request.user
    )

    if not notificacion.leida:
        notificacion.leida = True
        notificacion.save(update_fields=['leida'])

    destino = notificacion.url

    if (
        destino
        and destino.startswith('/')
        and not destino.startswith('//')
        and '\\' not in destino
        and url_has_allowed_host_and_scheme(
            destino,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure()
        )
    ):
        return redirect(destino)

    regreso = request.POST.get('siguiente', '')

    if (
        regreso.startswith('/')
        and not regreso.startswith('//')
        and '\\' not in regreso
        and url_has_allowed_host_and_scheme(
            regreso,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure()
        )
    ):
        return redirect(regreso)

    return redirect('inicio')

