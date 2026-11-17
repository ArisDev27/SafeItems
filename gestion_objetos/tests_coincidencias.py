
"""Pruebas del módulo de coincidencias: python manage.py test gestion_objetos.tests_coincidencias"""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .coincidencias import calcular_similitud, actualizar_coincidencias_de_objeto
from .models import Objeto, Coincidencia, Notificacion


class CoincidenciasTests(TestCase):
    def setUp(self):
        self.usuario1 = User.objects.create_user(username='perdio', password='clave-no-importa')
        self.usuario2 = User.objects.create_user(username='encontro', password='clave-no-importa')
        self.perdido = Objeto.objects.create(
            titulo='Audífonos Samsung', categoria='Electrónica', color='Negro',
            marca='Samsung', lugar='Biblioteca', fecha_suceso=date(2026, 11, 10),
            estado='PERDIDO', reportado_por=self.usuario1,
        )
        self.encontrado = Objeto.objects.create(
            titulo='Audífonos negros', categoria='Electrónica', color='NEGRO',
            marca='Samsung', lugar='biblioteca', fecha_suceso=date(2026, 11, 11),
            estado='ENCONTRADO', reportado_por=self.usuario2,
        )

    def test_dos_reportes_similares(self):
        porcentaje = calcular_similitud(self.perdido, self.encontrado)
        self.assertIsInstance(porcentaje, Decimal)
        self.assertGreaterEqual(porcentaje, Decimal('70.00'))

    def test_no_confunde_otros_articulos_de_la_misma_categoria(self):
        self.encontrado.titulo = 'Teléfono Samsung'
        self.assertIsNone(calcular_similitud(self.perdido, self.encontrado))

    def test_marca_contradictoria(self):
        self.encontrado.marca = 'Xiaomi'
        self.assertIsNone(calcular_similitud(self.perdido, self.encontrado))

    def test_se_guarda_una_sola_coincidencia_y_notifica_una_vez(self):
        actualizar_coincidencias_de_objeto(self.encontrado)
        actualizar_coincidencias_de_objeto(self.perdido)
        self.assertEqual(Coincidencia.objects.count(), 1)
        self.assertEqual(Notificacion.objects.filter(tipo='COINCIDENCIA').count(), 2)

    def test_editar_un_articulo_elimina_coincidencia_obsoleta(self):
        actualizar_coincidencias_de_objeto(self.encontrado)
        self.encontrado.titulo = 'Teléfono Samsung'
        self.encontrado.save(update_fields=['titulo'])
        actualizar_coincidencias_de_objeto(self.encontrado)
        self.assertEqual(Coincidencia.objects.count(), 0)

    def test_no_se_compara_un_usuario_con_si_mismo(self):
        self.encontrado.reportado_por = self.usuario1
        self.assertIsNone(calcular_similitud(self.perdido, self.encontrado))

    def test_notificaciones_llevan_a_las_coincidencias_del_propio_reporte(self):
        actualizar_coincidencias_de_objeto(self.encontrado)
        avisos = Notificacion.objects.filter(tipo='COINCIDENCIA')
        self.assertEqual(avisos.count(), 2)
        for aviso in avisos:
            id_propio = (self.perdido.pk if aviso.destinatario_id == self.usuario1.pk
                         else self.encontrado.pk)
            self.assertEqual(
                aviso.url,
                reverse('detalle_objeto', kwargs={'objeto_id': id_propio})
                + '#coincidencias-objeto',
            )

    def test_propietario_puede_ver_coincidencias_en_detalle(self):
        actualizar_coincidencias_de_objeto(self.encontrado, notificar=False)
        self.client.force_login(self.usuario1)
        url = reverse('detalle_objeto', kwargs={'objeto_id': self.perdido.pk})
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Posibles coincidencias de tu reporte')
        self.assertContains(respuesta, self.encontrado.titulo)
        self.assertEqual(len(respuesta.context['coincidencias_del_objeto']), 1)

    def test_visitante_no_ve_coincidencias_privadas_del_propietario(self):
        actualizar_coincidencias_de_objeto(self.encontrado, notificar=False)
        visitante = User.objects.create_user(username='visitante', password='clave-no-importa')
        self.client.force_login(visitante)
        url = reverse('detalle_objeto', kwargs={'objeto_id': self.perdido.pk})
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, 'Posibles coincidencias de tu reporte')
        self.assertEqual(respuesta.context['coincidencias_del_objeto'], [])
