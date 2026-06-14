from django.test import TestCase, Client
from django.urls import reverse
from django.db.models.signals import pre_migrate
from decimal import Decimal
from datetime import date
from django.utils import timezone

# ==============================================================================
# 1. IMPORTACIONES GLOBALES
# ==============================================================================
from mesas.models import Mesa
from pedidos.models import Pedido
from menu.models import Menu, CategoriaMenu
from ventas.models import Venta
from usuarios.models import Usuario

# ==============================================================================
# 2. INTERCEPTOR PARA FORZAR TABLAS EN EL TEST
# ==============================================================================
def forzar_tablas_test_pedidos(sender, **kwargs):
    Mesa._meta.managed = True
    Pedido._meta.managed = True
    Menu._meta.managed = True
    CategoriaMenu._meta.managed = True
    Venta._meta.managed = True
    Usuario._meta.managed = True

pre_migrate.connect(forzar_tablas_test_pedidos)

class PedidosModuleTest(TestCase):

    def setUp(self):
        # 1. Crear dependencias en orden jerárquico (evita IntegrityError)
        self.usuario = Usuario.objects.create(
            username='admin_test',
            password='123',
            rol='administrador'
        )
        
        self.mesa = Mesa.objects.create(
            numero_mesa='10',
            estado='disponible',
            capacidad=4  
        )
        
        self.categoria = CategoriaMenu.objects.create(
            nombre_categoria="General"
        )
        
        self.plato = Menu.objects.create(
            nombre_plato='Parrillada Familiar',
            precio=Decimal('50000.00'),
            estado='disponible',
            id_categoria=self.categoria # Asociamos la categoría obligatoria
        )

        # 2. Configurar sesión
        session = self.client.session
        session['usuario_id'] = self.usuario.id_usuario
        session['usuario_rol'] = self.usuario.rol
        session['usuario_nombre'] = self.usuario.username
        session.save()

        # 3. Crear pedido
        self.pedido = Pedido.objects.create(
            fecha_pedido=date.today(),
            hora_pedido=timezone.now().time(),
            id_mesa=self.mesa,
            id_usuario=self.usuario,
            id_plato=self.plato,
            cantidad=2,
            total=Decimal('100000.00'),
            estado_pedido='Entregado'
        )

    def test_listar_pedidos_con_sesion(self):
        """Verifica que la vista renderice la lista de pedidos de forma correcta."""
        response = self.client.get(reverse('pedidos:listar_pedidos'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pedido/listar.html')
        self.assertIn('pedidos', response.context)

    def test_listar_pedidos_sin_sesion_redirecciona(self):
        """Si no hay sesión activa, debe expulsar al usuario al login."""
        session = self.client.session
        session.clear()
        session.save()
        
        response = self.client.get(reverse('pedidos:listar_pedidos'))
        self.assertRedirects(response, reverse('login'))

    def test_factura_mesa_calculo_valores(self):
        """Valida que la vista de pre-factura sume correctamente el subtotal e IVA (19%)."""
        response = self.client.get(reverse('pedidos:factura_mesa', args=[self.mesa.id_mesa]))
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(response.context['subtotal'], Decimal('100000.00'))
        self.assertEqual(response.context['iva'], Decimal('19000.00'))
        self.assertEqual(response.context['total'], Decimal('119000.00'))

    def test_confirmar_pago_final_exitoso(self):
        """Verifica el flujo atómico: crea la venta, paga pedidos y libera la mesa."""
        response = self.client.post(
            reverse('pedidos:confirmar_pago_final', args=[self.mesa.id_mesa]),
            {'metodo_pago': 'Efectivo'}
        )
        
        self.assertRedirects(response, reverse('pedidos:listar_pedidos'))
        
        self.pedido.refresh_from_db()
        self.mesa.refresh_from_db()
        
        self.assertEqual(self.pedido.estado_pedido, 'pagado')
        self.assertEqual(self.mesa.estado, 'disponible')
        self.assertTrue(Venta.objects.filter(total=Decimal('119000.00')).exists())

    def test_mostrar_registro_pedido_contexto(self):
        """Prueba que el formulario de registros cargue las mesas y platos disponibles."""
        response = self.client.get(reverse('pedidos:mostrar_registro_pedido'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('mesas', response.context)
        self.assertIn('platos', response.context)

    def test_guardar_pedido_nuevo(self):
        """Prueba el registro masivo de registros mediante vectores/listas POST."""
        self.mesa.estado = 'disponible'
        self.mesa.save()

        data = {
            'id_mesa': self.mesa.id_mesa,
            'platos[]': [self.plato.id_plato],
            'cantidades[]': [3]
        }
        
        response = self.client.post(reverse('pedidos:guardar_pedido'), data)
        self.assertRedirects(response, reverse('pedidos:listar_pedidos'))
        
        self.mesa.refresh_from_db()
        self.assertEqual(self.mesa.estado, 'OCUPADA')
        self.assertTrue(Pedido.objects.filter(cantidad=3, total=Decimal('150000.00')).exists())

    def test_eliminar_pedido(self):
        """Confirma la baja física de un pedido de la base de datos."""
        id_a_borrar = self.pedido.id_pedido
        response = self.client.get(reverse('pedidos:eliminar_pedido', args=[id_a_borrar]))
        
        self.assertRedirects(response, reverse('pedidos:listar_pedidos'))
        self.assertFalse(Pedido.objects.filter(id_pedido=id_a_borrar).exists())

    def test_analisis_pedidos_kpis(self):
        """Prueba que el módulo estadístico envíe correctamente los JSON estructurados para Charts.js."""
        response = self.client.get(reverse('pedidos:analisis_pedidos'))
        self.assertEqual(response.status_code, 200)
        
        self.assertIn('labels_est', response.context)
        self.assertIn('valores_est', response.context)
        self.assertEqual(response.context['total_pedidos'], 1)