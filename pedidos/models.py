from django.db import models

class Pedido(models.Model):
    id_pedido = models.AutoField(primary_key=True)
    # auto_now_add=True captura la fecha al crear el registro automáticamente
    fecha_pedido = models.DateField(auto_now_add=True) 
    # auto_now_add=True captura la hora al crear el registro automáticamente
    hora_pedido = models.TimeField(auto_now_add=True)

    # USAMOS REFERENCIAS DE CADENA: 'nombre_app.NombreModelo'
    id_mesa = models.ForeignKey('mesas.Mesa', on_delete=models.CASCADE, db_column='id_mesa')
    id_usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE, db_column='id_usuario')
    id_plato = models.ForeignKey('menu.Menu', on_delete=models.CASCADE, db_column='id_plato')
    
    cantidad = models.IntegerField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado_pedido = models.CharField(max_length=20, default='Pendiente')

    class Meta:
        db_table = 'pedido'
        managed = False

class DetallePedido(models.Model):
    id_detalle = models.AutoField(primary_key=True)

    id_pedido = models.ForeignKey(
        'Pedido', # Referencia interna a la misma app
        on_delete=models.CASCADE,
        db_column='id_pedido'
    )

    id_plato = models.ForeignKey(
        'menu.Menu', # Referencia a la app menu
        on_delete=models.CASCADE,
        db_column='id_plato'
    )

    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'detalle_pedido'
        managed = True