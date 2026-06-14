from django.test import TestCase
from django.urls import reverse
from django.db.models.signals import pre_migrate
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib import messages
import json
import io
import pandas as pd

# IMPORTACIONES: Asegúrate de que estos nombres coincidan exactamente con tus archivos models.py
from menu.models import Menu, CategoriaMenu
from pedidos.models import Pedido

# ==============================================================================
# CONFIGURACIÓN DE TABLAS PARA EL ENTORNO DE PRUEBAS
# ==============================================================================
def forzar_tablas_test_menu(sender, **kwargs):
    Menu._meta.managed = True
    CategoriaMenu._meta.managed = True
    Pedido._meta.managed = True

pre_migrate.connect(forzar_tablas_test_menu)

class MenuModuleTest(TestCase):

    def setUp(self):
        """Configuración inicial de dependencias para las pruebas del menú."""
        self.categoria_test = CategoriaMenu.objects.create(
            nombre_categoria='Carnes Parrilla'
        )
        
        self.plato_test = Menu.objects.create(
            nombre_plato='Baby Beef',
            descripcion='Corte tierno a la brasa',
            precio=42000,
            estado='Disponible',
            id_categoria=self.categoria_test
        )

        self.sesion_valida = {
            'usuario_id': 1,
            'usuario_nombre': 'Andrés',
            'usuario_rol': 'Administrador'
        }

    # ==============================================================================
    # 1. SEGURIDAD DE RUTA Y SESIÓN
    # ==============================================================================
    def test_vistas_redirigen_a_login_sin_sesion(self):
        rutas_protegidas = [
            ('menu:listar_menu', None),
            ('menu:mostrar_registro_menu', None),
            ('menu:pre_editar_menu', {'id_plato': self.plato_test.id_plato}),
            ('menu:analisis_menu', None),
        ]

        for nombre_ruta, kwargs in rutas_protegidas:
            url = reverse(nombre_ruta, kwargs=kwargs)
            response = self.client.get(url)
            self.assertRedirects(response, reverse('login'))

    # ==============================================================================
    # 2. PROCESO LECTURA Y FILTRADO (READ)
    # ==============================================================================
    def test_listar_menu_con_sesion(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        response = self.client.get(reverse('menu:listar_menu'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'menu/listar.html')
        self.assertIn('platos', response.context)
        self.assertIn('categorias', response.context)

    def test_filtrar_menu_por_criterios_get(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        cat_bebida = CategoriaMenu.objects.create(nombre_categoria='Bebidas')
        Menu.objects.create(
            nombre_plato='Limonada Cerezada',
            precio=8500,
            estado='No Disponible',
            id_categoria=cat_bebida
        )

        response_texto = self.client.get(reverse('menu:listar_menu'), {'nombre': 'Beef'})
        self.assertEqual(response_texto.context['platos'].count(), 1)

        response_cat = self.client.get(reverse('menu:listar_menu'), {'categoria': cat_bebida.id_categoria})
        self.assertEqual(response_cat.context['platos'].count(), 1)

        response_est = self.client.get(reverse('menu:listar_menu'), {'estado': 'No Disponible'})
        self.assertEqual(response_est.context['platos'].count(), 1)

    # ==============================================================================
    # 3. CREACIÓN (CREATE)
    # ==============================================================================
    def test_registrar_menu_exitoso_con_limpieza_precio(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        data_post = {
            'id_categoria': self.categoria_test.id_categoria,
            'nombre_plato': 'Churrasco Parrillero',
            'descripcion': '350 gramos de lomo',
            'precio': '45.500',
            'estado': 'Disponible'
        }

        response = self.client.post(reverse('menu:registrar_menu'), data_post)
        self.assertRedirects(response, reverse('menu:listar_menu'))
        nuevo_plato = Menu.objects.get(nombre_plato='Churrasco Parrillero')
        self.assertEqual(nuevo_plato.precio, 45500)

    # ==============================================================================
    # 4. EDICIÓN (UPDATE)
    # ==============================================================================
    def test_actualizar_menu_y_mutacion_precio(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        data_update = {
            'id_plato': self.plato_test.id_plato,
            'id_categoria': self.categoria_test.id_categoria,
            'nombre_plato': 'Baby Beef Premium',
            'descripcion': 'Corte madurado',
            'precio': '53000',
            'estado': 'Disponible'
        }

        response = self.client.post(reverse('menu:editar_menu'), data_update)
        self.assertRedirects(response, reverse('menu:listar_menu'))
        self.plato_test.refresh_from_db()
        self.assertEqual(self.plato_test.nombre_plato, 'Baby Beef Premium')

    # ==============================================================================
    # 5. ELIMINACIÓN (DELETE)
    # ==============================================================================
    def test_eliminar_menu_exitoso(self):
        # Para eliminar, primero aseguramos sesión
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()
        
        id_aux = self.plato_test.id_plato
        url = reverse('menu:eliminar_menu', args=[id_aux])
        
        response = self.client.get(url)
        self.assertRedirects(response, reverse('menu:listar_menu'))
        self.assertFalse(Menu.objects.filter(id_plato=id_aux).exists())

    # ==============================================================================
    # 6. REPORTES Y EXCEL
    # ==============================================================================
    def test_exportar_menu_pdf(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        response = self.client.get(reverse('menu:exportar_menu_pdf'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_carga_masiva_excel_exitosa(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        datos_excel = {
            'id_categoria': [self.categoria_test.id_categoria],
            'nombre_plato': ['Costillitas BBQ'],
            'descripcion': ['Costillas de cerdo ahumadas'],
            'precio': [38000]
        }
        df = pd.DataFrame(datos_excel)
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        buffer_excel.seek(0)

        archivo_simulado = SimpleUploadedFile(
            "menu_importar.xlsx",
            buffer_excel.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        response = self.client.post(reverse('menu:carga_masiva_menu'), {'archivo_excel': archivo_simulado})
        self.assertRedirects(response, reverse('menu:listar_menu'))
        self.assertTrue(Menu.objects.filter(nombre_plato='Costillitas BBQ').exists())

    def test_analisis_menu_kpis_y_graficos(self):
        session = self.client.session
        session.update(self.sesion_valida)
        session.save()

        response = self.client.get(reverse('menu:analisis_menu'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_platos'], 1)