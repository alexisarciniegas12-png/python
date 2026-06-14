from django.db import models
from django.utils import timezone

class Venta(models.Model):
    CATEGORIAS = [
        ('Restaurante', 'Restaurante'),
        ('Evento', 'Evento'),
    ]
    
    METODOS_PAGO = [
        ('Efectivo', 'Efectivo'),
        ('Tarjeta', 'Tarjeta'),
        ('Transferencia', 'Transferencia'),
    ]

    id_venta = models.AutoField(primary_key=True)
    fecha_venta = models.DateTimeField(default=timezone.now)
    categoria_venta = models.CharField(max_length=20, choices=CATEGORIAS)
    
    # Valores monetarios
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO, default='Efectivo')

    # CORRECCIÓN: Relaciones apuntando a las apps correctas
    id_cliente = models.ForeignKey(
        'usuarios.Usuario', # App 'usuarios'
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='id_cliente', 
        related_name='compras_cliente'
    )
    
    id_empleado = models.ForeignKey(
        'usuarios.Usuario', # App 'usuarios'
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='id_empleado', 
        related_name='ventas_realizadas'
    )
    
    id_pedido = models.ForeignKey(
        'pedidos.Pedido', # App 'pedidos'
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='id_pedido'
    )
    
    id_evento = models.ForeignKey(
        'eventos.Evento', # App 'eventos'
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        db_column='id_evento'
    )

    class Meta:
        db_table = 'venta'

    def __str__(self):
        return f"Venta {self.id_venta} - {self.categoria_venta}"