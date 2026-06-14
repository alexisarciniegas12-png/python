from django.db import models
from menu.models import Menu  # Asegúrate de que la ruta a tu app menu sea correcta

class Reserva(models.Model):
    # Opciones para el tipo de reserva
    TIPO_CHOICES = [
        ('solo_mesa', 'Solo lugar (Mesa)'),
        ('mesa_menu', 'Mesa con Menú'),
    ]

    id_reserva = models.AutoField(primary_key=True, db_column='id_reserva')
    nombre_cliente = models.CharField(max_length=100, db_column='nombre_cliente')
    fecha = models.DateField(db_column='fecha')
    hora = models.TimeField(db_column='hora')
    n_personas = models.IntegerField(db_column='n_personas')
    sede = models.CharField(max_length=50, db_column='sede')
    
    # --- LLAVE FORÁNEA AGREGADA ---
    id_plato = models.ForeignKey(
        Menu, 
        on_delete=models.SET_NULL, 
        db_column='id_plato', 
        null=True, 
        blank=True
    )

    # --- CAMPOS DE LÓGICA DE PAGO Y TIPO ---
    tipo_reserva = models.CharField(
        max_length=20, 
        choices=TIPO_CHOICES, 
        default='solo_mesa', 
        db_column='tipo_reserva'
    )
    monto_pago = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00, 
        db_column='monto_pago'
    )
    pago_confirmado = models.BooleanField(
        default=False, 
        db_column='pago_confirmado'
    )

    # --- CAMPO UNIFICADO PARA EL MENÚ ---
    platos_seleccionados = models.TextField(
        db_column='platos_seleccionados', 
        blank=True, 
        null=True
    )

    # --- CAMPOS DE CONTROL ---
    estado = models.CharField(max_length=50, db_column='estado', default='Pendiente')
    fecha_creacion = models.DateTimeField(db_column='fecha_creacion', auto_now_add=True)
    id_cliente = models.IntegerField(db_column='id_cliente', null=True, blank=True)
    id_empleado = models.IntegerField(db_column='id_empleado', null=True, blank=True)
    
    class Meta:
        managed = True
        db_table = 'reserva'

    def __str__(self):
        return f"Reserva {self.id_reserva} - {self.nombre_cliente}"