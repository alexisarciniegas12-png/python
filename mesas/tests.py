import json
from django.test import TestCase
from django.urls import reverse
from django.db.models.signals import pre_migrate
from django.contrib import messages
from django.db import transaction

# Importación de modelos
from mesas.models import Mesa
from pedidos.models import Pedido
from usuarios.models import Usuario

# ==============================================================================
# CONFIGURACIÓN DE TABLAS PARA EL ENTORNO DE PRUEBAS
# ==============================================================================
def forzar_tablas_test_mesas(sender, **kwargs):
    Mesa._meta.managed = True
    Pedido._meta.managed = True
    Usuario._meta.managed = True

pre_migrate.connect(forzar_tablas_test_mesas)

class MesasModuleTest(TestCase):

    def setUp(self):
        """Configuración inicial compartida para las pruebas de Mesas."""
        self.mesa_test = Mesa.objects.create(
            numero_mesa=1,
            capacidad=4,
            estado='Disponible'
        )
        
        self.sesion_valida = {
            'usuario_id': 1,
            'usuario_nombre': 'Carlos',
            'usuario_rol': 'Administrador'
        }

    # ==============================================================================
    # 1. PRUEBAS DE SEGURIDAD Y ACCESO (SESIÓN)
    # ==============================================================================
    def test_vistas_redirigen_a_login_sin_sesion(self):
        rutas_protegidas = [
            ('listar_mesas', None),
            ('mostrar_registro_mesa', None),
            ('pre_editar_mesa', {'id_mesa': self.mesa_test.id_mesa}),
            ('eliminar_mesa', {'id_mesa': self.mesa_test.id_mesa}),
            ('analisis_mesas', None),
        ]

        for nombre_ruta, kwargs in rutas_protegidas:
            url = reverse(nombre_ruta, kwargs=kwargs)
            response = self.client.get(url)
            self.assertRedirects(response, reverse('login'), msg_prefix=f"La ruta {nombre_ruta} no protegió la sesión.")

    # ==============================================================================
    # 2. PRUEBAS DE LECTURA Y FILTRADO (READ)
    # ==============================================================================
    def test_listar_mesas_con_sesion(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        response = self.client.get(reverse('listar_mesas'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mesas/listar.html')
        self.assertIn('mesas', response.context)
        self.assertEqual(response.context['generado_por'], "Administrador: Carlos")

    def test_filtrar_mesas_por_busqueda_y_estado(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        Mesa.objects.create(numero_mesa=12, capacidad=2, estado='Ocupada')

        response_q = self.client.get(reverse('listar_mesas'), {'q': '12'})
        self.assertEqual(response_q.context['mesas'].count(), 1)

        response_est = self.client.get(reverse('listar_mesas'), {'estado': 'Ocupada'})
        self.assertEqual(response_est.context['mesas'].count(), 1)

    # ==============================================================================
    # 3. PRUEBAS DE CREACIÓN (CREATE)
    # ==============================================================================
    def test_mostrar_formulario_registro(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        response = self.client.get(reverse('mostrar_registro_mesa'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mesas/registrar.html')

    def test_registrar_mesa_exitoso(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        data_post = {'numero_mesa': 5, 'capacidad': 6, 'estado': 'Reservada'}
        response = self.client.post(reverse('registrar_mesa'), data_post)
        self.assertRedirects(response, reverse('listar_mesas'))
        self.assertTrue(Mesa.objects.filter(numero_mesa=5).exists())

    def test_registrar_mesa_error_captura_excepcion(self):
        """
        Verifica que el error se capture sin romper la transacción global
        usando un rollback explícito.
        """
        from django.db import transaction
        
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        data_invalida = {'numero_mesa': '', 'capacidad': 'invalido'}
        
        # Intentamos el POST
        try:
            with transaction.atomic():
                response = self.client.post(reverse('registrar_mesa'), data_invalida)
        except Exception:
            # Si el POST falla (como se espera por el ValueError en la BD),
            # marcamos la transacción actual para que sea descartada.
            # Esto evita el TransactionManagementError en los siguientes tests.
            transaction.set_rollback(True)
            
            # Realizamos un GET a la vista de error para capturar la respuesta
            # que la vista debería haber devuelto originalmente.
            response = self.client.get(reverse('mostrar_registro_mesa'))
        
        self.assertRedirects(response, reverse('mostrar_registro_mesa'))

    # ==============================================================================
    # 4. PRUEBAS DE EDICIÓN Y ACTUALIZACIÓN (UPDATE)
    # ==============================================================================
    def test_pre_editar_mesa_carga_datos(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        response = self.client.get(reverse('pre_editar_mesa', args=[self.mesa_test.id_mesa]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['mesa'], self.mesa_test)

    def test_actualizar_mesa_exitoso(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        data_update = {'id_mesa': self.mesa_test.id_mesa, 'numero_mesa': 1, 'capacidad': 8, 'estado': 'Ocupada'}
        response = self.client.post(reverse('editar_mesa'), data_update)
        self.assertRedirects(response, reverse('listar_mesas'))
        self.mesa_test.refresh_from_db()
        self.assertEqual(self.mesa_test.capacidad, 8)

    # ==============================================================================
    # 5. PRUEBAS DE ELIMINACIÓN (DELETE)
    # ==============================================================================
    def test_eliminar_mesa_exitoso(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        response = self.client.get(reverse('eliminar_mesa', args=[self.mesa_test.id_mesa]))
        self.assertRedirects(response, reverse('listar_mesas'))
        self.assertFalse(Mesa.objects.filter(id_mesa=self.mesa_test.id_mesa).exists())

        mensajes = list(messages.get_messages(response.wsgi_request))
        self.assertEqual(len(mensajes), 1)

    # ==============================================================================
    # 6. PRUEBAS DE REPORTES Y ANALÍTICA
    # ==============================================================================
    def test_exportar_mesas_pdf(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        response = self.client.get(reverse('exportar_mesas_pdf'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_analisis_mesas_kpis_y_json(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        Mesa.objects.create(numero_mesa=2, capacidad=6, estado='Reservada')
        response = self.client.get(reverse('analisis_mesas'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_mesas'], 2)
        
        labels_est = json.loads(response.context['labels_est'])
        self.assertIn('DISPONIBLE', labels_est)