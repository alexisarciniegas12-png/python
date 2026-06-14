from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from django.db import connection
from decimal import Decimal
from datetime import date
from unittest.mock import patch

# Modelos
from .models import Venta
from usuarios.models import Usuario
from pedidos.models import Pedido
from mesas.models import Mesa
from menu.models import Menu, CategoriaMenu
from eventos.models import Evento, InscripcionEvento
from .utils import obtener_conversion_dinamica

class VentasModuleTest(TransactionTestCase):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Incluimos todos los modelos necesarios en la base de datos de test
        models = [CategoriaMenu, Mesa, Menu, Evento, Usuario, Pedido, InscripcionEvento, Venta]
        with connection.schema_editor() as schema_editor:
            for model in models:
                if model._meta.db_table not in connection.introspection.table_names():
                    schema_editor.create_model(model)

    def setUp(self):
        # 1. Crear usuarios
        self.admin = Usuario.objects.create(username='cajero_test', password='123', rol='administrador')
        self.cliente = Usuario.objects.create(username='cliente_test', password='123', rol='cliente')

        # 2. Crear Categoría
        self.categoria = CategoriaMenu.objects.create(nombre_categoria="Categoría Test")

        # 3. Sesión
        session = self.client.session
        session['usuario_id'] = self.admin.id_usuario
        session['usuario_rol'] = getattr(self.admin, 'role', getattr(self.admin, 'rol', ''))
        session['usuario_nombre'] = self.admin.username
        session.save()

        # 4. Dependencias
        self.mesa = Mesa.objects.create(numero_mesa='5', estado='disponible', capacidad=4)
        
        self.plato = Menu.objects.create(
            nombre_plato='Corte Parrilla', 
            precio=Decimal('35000'), 
            estado='disponible',
            id_categoria=self.categoria 
        )
        
        self.pedido = Pedido.objects.create(
            fecha_pedido=date.today(), 
            hora_pedido=timezone.now().time(),
            id_mesa=self.mesa, 
            id_usuario=self.admin, 
            id_plato=self.plato,
            cantidad=1, 
            total=Decimal('35000'), 
            estado_pedido='pagado'
        )
        
        # Actualizado: Se añade 'cupos_disponibles' para cumplir con la restricción NOT NULL
        self.evento = Evento.objects.create(
            nombre_evento='Cena Empresarial', 
            valor_evento=Decimal('119000'),
            fecha_evento=date.today(),
            hora_evento=timezone.now().time(),
            cupos_disponibles=50  # Valor agregado para evitar el error de integridad
        )
        
        self.inscripcion = InscripcionEvento.objects.create(
            id_evento=self.evento, 
            id_cliente=self.cliente, 
            cantidad_personas=1,
            metodo_pago='Tarjeta', 
            estado_pago='Pendiente'
        )

        # 5. Venta base
        self.venta_base = Venta.objects.create(
            categoria_venta='Restaurante', 
            subtotal=Decimal('29411.76'), 
            iva=Decimal('5588.24'),
            descuento=Decimal('0.00'), 
            total=Decimal('35000'), 
            metodo_pago='Efectivo',
            id_cliente=self.cliente, 
            id_empleado=self.admin, 
            id_pedido=self.pedido
        )

    def tearDown(self):
        # Limpieza de datos
        Venta.objects.all().delete()
        InscripcionEvento.objects.all().delete()
        Pedido.objects.all().delete()
        Evento.objects.all().delete()
        Menu.objects.all().delete()
        CategoriaMenu.objects.all().delete()
        Mesa.objects.all().delete()
        Usuario.objects.all().delete()

    @patch('ventas.views.obtener_conversion_dinamica')
    def test_listar_ventas_con_filtros_y_api(self, mock_conversion):
        mock_conversion.return_value = 0.00025
        response = self.client.get(reverse('ventas:listar_ventas'), {
            'fecha_inicio': date.today().strftime('%Y-%m-%d'), 
            'fecha_fin': date.today().strftime('%Y-%m-%d'),
            'categoria': 'Restaurante', 
            'metodo': 'Efectivo', 
            'moneda': 'USD'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_convertido'], 8.75)

    def test_listar_ventas_sin_sesion_redirecciona(self):
        # 1. Cerramos sesión formalmente
        self.client.logout()
        
        # 2. Intentamos acceder
        response = self.client.get(reverse('ventas:listar_ventas'))
        
        # 3. Verificamos la redirección al login
        self.assertRedirects(response, reverse('login'))

    def test_eliminar_venta_existente(self):
        response = self.client.get(reverse('ventas:eliminar_venta', args=[self.venta_base.id_venta]))
        self.assertRedirects(response, reverse('ventas:listar_ventas'))

    def test_pagar_inscripcion_evento_exitoso(self):
        response = self.client.post(reverse('ventas:pagar_inscripcion', args=[self.inscripcion.id_inscripcion]))
        self.assertRedirects(response, reverse('eventos:listar_inscripciones'))
        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.estado_pago, 'Pagado')

    @patch('ventas.views.obtener_conversion_dinamica')
    def test_exportar_ventas_pdf(self, mock_conversion):
        mock_conversion.return_value = 0.00025
        response = self.client.get(reverse('ventas:exportar_pdf'), {'moneda': 'USD'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_analisis_ventas_kpis_y_charts(self):
        Venta.objects.create(categoria_venta='Reserva', total=Decimal('50000.00'), metodo_pago='Transferencia')
        response = self.client.get(reverse('ventas:analisis_ventas'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_recaudado'], Decimal('85000.00'))

class UtilsTasaCambioTest(TestCase):
    @patch('requests.get')
    def test_obtener_conversion_dinamica_ok(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'rates': {'USD': 0.00025}}
        self.assertEqual(obtener_conversion_dinamica('USD'), 0.00025)

    @patch('requests.get')
    def test_obtener_conversion_dinamica_fallo(self, mock_get):
        mock_get.side_effect = Exception("Error")
        self.assertIsNone(obtener_conversion_dinamica('USD'))