import io
import pandas as pd
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.signals import pre_migrate
from .models import Usuario
from pedidos.models import Pedido
from ventas.models import Venta
from reservas.models import Reserva
from mesas.models import Mesa
from menu.models import Menu, CategoriaMenu

def forzar_tablas_test_usuarios(sender, **kwargs):
    Pedido._meta.managed = True
    Venta._meta.managed = True
    Reserva._meta.managed = True
    Mesa._meta.managed = True
    Menu._meta.managed = True           
    CategoriaMenu._meta.managed = True

pre_migrate.connect(forzar_tablas_test_usuarios)

# CLASE LIMPIA: Ya no tiene el decorador que generaba el choque con MySQL
class UsuariosModuleTest(TestCase):

    @classmethod
    def setUpClass(cls):
        """
        Como tus modelos tienen 'managed = False', Django no crea las tablas 
        en la BD temporal de pruebas. Activamos 'managed = True' dinámicamente 
        únicamente para el entorno de test sin alterar tu código original.
        """
        Usuario._meta.managed = True
        if Pedido:
            Pedido._meta.managed = True
        if Reserva:
            Reserva._meta.managed = True
        super().setUpClass()

    def setUp(self):
        # 1. Crear un usuario de prueba en tu tabla personalizada
        self.usuario_test = Usuario.objects.create(
            username='carlos_mesero',
            password='123',  # Sin encriptar, tal como lo requiere tu vista
            rol='mesero'
        )

        # 2. Crear un usuario en la tabla nativa de Django (auth_user) para la vista de registro público
        self.auth_user_test = User.objects.create_user(
            username='cliente_antiguo',
            email='cliente@correo.com',
            password='password123'
        )

    # =====================================================================
    # TEST: VISTA INICIO
    # =====================================================================
    def test_vista_inicio(self):
        response = self.client.get(reverse('inicio'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'usuarios/inicio.html')

    # =====================================================================
    # TEST: REGISTRO PÚBLICO (Formulario de Clientes)
    # =====================================================================
    def test_registro_publico_exitoso(self):
        response = self.client.post(
            reverse('registro'),
            {
                'first_name': 'Adriel',
                'last_name': 'Mendez',
                'email': 'adriel@parrilla.com',
                'username': 'adriel123',
                'password': '12345678',
                'confirm_password': '12345678'
            }
        )
        self.assertRedirects(response, reverse('login'))
        
        self.assertTrue(User.objects.filter(username='adriel123').exists())
        self.assertTrue(Usuario.objects.filter(username='adriel123').exists())

    @override_settings(TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],  
        'APP_DIRS': True,
    }])
    def test_registro_publico_contraseñas_no_coinciden(self):
        response = self.client.post(
            reverse('registro'),
            {
                'first_name': 'Juan',
                'last_name': 'Perez',
                'email': 'juan@correo.com',
                'username': 'juan_perez',
                'password': 'password123',
                'confirm_password': 'otra_cosa_999'
            }
        )
        self.assertEqual(response.status_code, 200)

    # =====================================================================
    # TEST: INICIAR SESIÓN (AUTENTICACIÓN)
    # =====================================================================
    def test_iniciar_sesion_correcto(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'carlos_mesero',
                'password': '123'
            }
        )
        self.assertRedirects(response, reverse('dashboard'))
        session = self.client.session
        self.assertEqual(session['usuario_id'], self.usuario_test.id_usuario)
        self.assertEqual(session['usuario_nombre'], 'carlos_mesero')
        self.assertEqual(session['usuario_rol'], 'mesero')

    def test_iniciar_sesion_incorrecto(self):
        response = self.client.post(
            reverse('login'),
            {
                'username': 'carlos_mesero',
                'password': 'clave_incorrecta'
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('usuario_id', self.client.session)

    # =====================================================================
    # TEST: LISTAR USUARIOS (ADMINISTRACIÓN)
    # =====================================================================
    def test_listar_usuarios_con_sesion(self):
        session = self.client.session
        session['usuario_id'] = self.usuario_test.id_usuario
        session['usuario_rol'] = 'administrador'
        session.save()

        response = self.client.get(reverse('listar_usuarios'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'usuarios/listar.html')
        self.assertIn('usuarios', response.context)

    def test_listar_usuarios_sin_sesion_redirige(self):
        response = self.client.get(reverse('listar_usuarios'))
        self.assertRedirects(response, reverse('login'))

    # =====================================================================
    # TEST: CREAR USUARIO DESDE EL PANEL ADMINISTRATIVO
    # =====================================================================
    def test_registrar_usuario_administrativo(self):
        session = self.client.session
        session['usuario_id'] = self.usuario_test.id_usuario
        session['usuario_rol'] = 'administrador'
        session.save()

        response = self.client.post(
            reverse('registrar_usuario'),
            {
                'usuario': 'nuevo_cajero',
                'contraseña': 'abc',
                'rol': 'cajero'
            }
        )
        self.assertRedirects(response, reverse('listar_usuarios'))
        self.assertTrue(Usuario.objects.filter(username='nuevo_cajero', rol='cajero').exists())

    # =====================================================================
    # TEST: MODIFICACIÓN DE USUARIOS
    # =====================================================================
    def test_pre_editar_usuario(self):
        session = self.client.session
        session['usuario_id'] = self.usuario_test.id_usuario
        session.save()

        response = self.client.get(reverse('pre_editar_usuario', args=[self.usuario_test.id_usuario]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['usuario'], self.usuario_test)

    def test_editar_usuario_post(self):
        session = self.client.session
        session['usuario_id'] = self.usuario_test.id_usuario
        session['usuario_rol'] = 'administrador'
        session.save()

        response = self.client.post(
            reverse('editar_usuario'),
            {
                'id_usuario': self.usuario_test.id_usuario,
                'usuario': 'carlos_modificado',
                'contraseña': '456',
                'rol': 'administrador'
            }
        )
        self.assertRedirects(response, reverse('listar_usuarios'))
        
        self.usuario_test.refresh_from_db()
        self.assertEqual(self.usuario_test.username, 'carlos_modificado')
        self.assertEqual(self.usuario_test.password, '456')
        self.assertEqual(self.usuario_test.rol, 'administrador')

    # =====================================================================
    # TEST: ELIMINAR USUARIO
    # =====================================================================
    def test_eliminar_usuario_sin_vinculos(self):
        session = self.client.session
        session['usuario_id'] = self.usuario_test.id_usuario
        session.save()

        response = self.client.get(reverse('eliminar_usuario', args=[self.usuario_test.id_usuario]))
        self.assertRedirects(response, reverse('listar_usuarios'))
        self.assertFalse(Usuario.objects.filter(id_usuario=self.usuario_test.id_usuario).exists())

    # =====================================================================
    # TEST: CARGA MASIVA MEDIANTE EXCEL (PANDAS)
    # =====================================================================
    def test_carga_masiva_usuarios_excel(self):
        session = self.client.session
        session['usuario_id'] = self.usuario_test.id_usuario
        session['usuario_rol'] = 'administrador'
        session.save()

        data = {
            'usuario': ['excel_user1', 'excel_user2'],
            'password': ['pass1', 'pass2'],
            'rol': ['Administrador', 'Mesero']
        }
        df = pd.DataFrame(data)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        buffer.seek(0)

        archivo_excel = SimpleUploadedFile(
            "usuarios_carga.xlsx",
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        response = self.client.post(
            reverse('carga_masiva_usuarios'),
            {'archivo_excel': archivo_excel}
        )

        self.assertRedirects(response, reverse('listar_usuarios'))
        self.assertEqual(Usuario.objects.count(), 3)
        self.assertTrue(Usuario.objects.filter(username='excel_user1', rol='administrador').exists())