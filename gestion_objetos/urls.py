from django.urls import path
from django.contrib.auth import views as auth_views
from . import views, admin_views, entregas
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [

    path(
        '',
        auth_views.LoginView.as_view(
            template_name='gestion_objetos/login.html',
            next_page='inicio',
            redirect_authenticated_user=True
        ),
        name='login'
    ),

    # El sistema identifica si entra un administrador o un estudiante.
    path(
        'inicio/',
        admin_views.inicio_segun_rol,
        name='inicio'
    ),

    path('registro/', views.registro, name='registro'),

    path(
        'perfil/',
        admin_views.solo_estudiantes(views.perfil),
        name='perfil'
    ),

    path(
        'cerrar-sesion/',
        auth_views.LogoutView.as_view(next_page='login'),
        name='logout'
    ),

    path(
        'reportar-perdido/',
        admin_views.solo_estudiantes(views.reportar_perdido),
        name='reportar_perdido'
    ),

    path(
        'recuperar-contrasena/',
        auth_views.PasswordResetView.as_view(
            template_name='gestion_objetos/recuperar.html',
            email_template_name='gestion_objetos/correo_recuperacion.txt',
            subject_template_name='gestion_objetos/asunto_recuperacion.txt',
            extra_context={'pantalla': 'solicitud'}
        ),
        name='password_reset'
    ),

    path(
        'recuperar-contrasena/enviado/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='gestion_objetos/recuperar.html',
            extra_context={'pantalla': 'enviado'}
        ),
        name='password_reset_done'
    ),

    path(
        'restablecer/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='gestion_objetos/recuperar.html',
            extra_context={'pantalla': 'cambio'}
        ),
        name='password_reset_confirm'
    ),

    path(
        'restablecer/completado/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='gestion_objetos/recuperar.html',
            extra_context={'pantalla': 'completo'}
        ),
        name='password_reset_complete'
    ),

    path(
        'actualizar-foto-perfil/',
        admin_views.solo_estudiantes(views.actualizar_foto_perfil),
        name='actualizar_foto_perfil'
    ),

    path(
        'buscar-objeto/',
        admin_views.solo_estudiantes(views.buscar_objeto),
        name='buscar_objeto'
    ),

    path(
        'objeto/<int:objeto_id>/',
        admin_views.solo_estudiantes(views.detalle_objeto),
        name='detalle_objeto'
    ),

    path(
        'mis-reportes/',
        admin_views.solo_estudiantes(views.mis_reportes),
        name='mis_reportes'
    ),

    path(
        'editar-reporte/<int:objeto_id>/',
        admin_views.solo_estudiantes(views.editar_reporte),
        name='editar_reporte'
    ),

    path(
        'eliminar-reporte/<int:objeto_id>/',
        admin_views.solo_estudiantes(views.eliminar_reporte),
        name='eliminar_reporte'
    ),

    path(
        'reclamar-objeto/<int:objeto_id>/',
        admin_views.solo_estudiantes(views.reclamar_objeto),
        name='reclamar_objeto'
    ),

    path(
        'lo-encontre/<int:objeto_id>/',
        admin_views.solo_estudiantes(views.lo_encontre),
        name='lo_encontre'
    ),

    path(
        'notificacion/<int:notificacion_id>/abrir/',
        admin_views.solo_estudiantes(views.abrir_notificacion),
        name='abrir_notificacion'
    ),

    # ==========================================
    # PANEL ADMINISTRATIVO DE SAFEITEMS
    # ==========================================

    path(
        'administracion/',
        admin_views.panel_administrador,
        name='panel_administrador'
    ),

    path(
        'administracion/reclamacion/<int:solicitud_id>/',
        admin_views.detalle_reclamacion_admin,
        name='detalle_reclamacion_admin'
    ),

    path(
        'administracion/reclamacion/<int:solicitud_id>/resolver/',
        admin_views.resolver_reclamacion_admin,
        name='resolver_reclamacion_admin'
    ),

    # Consultar el código desde la cuenta del estudiante.
    path(
        'mi-entrega/<int:solicitud_id>/',
        admin_views.solo_estudiantes(entregas.mi_entrega),
        name='mi_entrega'
    ),

    # Generar código para reclamaciones aprobadas anteriormente.
    path(
        'administracion/reclamacion/<int:solicitud_id>/generar-codigo/',
        entregas.generar_codigo_aprobado_admin,
        name='generar_codigo_aprobado_admin'
    ),

    # Validar código y confirmar la entrega física.
    path(
        'administracion/reclamacion/<int:solicitud_id>/confirmar-entrega/',
        entregas.confirmar_entrega_admin,
        name='confirmar_entrega_admin'
    ),

    path(
        'avisos/<int:aviso_id>/descartar/',
        admin_views.solo_estudiantes(views.descartar_aviso_hallazgo),
        name='descartar_aviso_hallazgo'
    ),

]
