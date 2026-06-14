from django.db import models

class Evento(models.Model):
    id_evento = models.AutoField(primary_key=True)
    nombre_evento = models.CharField(max_length=100)
    descripcion = models.TextField()
    fecha_evento = models.DateField()
    hora_evento = models.TimeField()
    # Nota: Quité max_length de DecimalField, no es un atributo válido para este campo
    valor_evento = models.DecimalField(max_digits=10, decimal_places=2)
    cupos_disponibles = models.IntegerField()
    estado_evento = models.CharField(max_length=20, default='Disponible')

    @property
    def icono_dinamico(self):
        nombre = self.nombre_evento.lower()
        if 'madre' in nombre or 'mujer' in nombre:
            return "🌹"
        elif 'halloween' in nombre:
            return "🎃"
        elif 'navidad' in nombre or 'navideña' in nombre:
            return "🎄"
        elif 'cumpleaños' in nombre:
            return "🎂"
        elif 'fuego' in nombre or 'parrilla' in nombre:
            return "🔥"
        return "📅"  # Icono por defecto (Calendario)
    def __str__(self):
        return self.nombre_evento

    class Meta:
        db_table = 'evento'

class InscripcionEvento(models.Model):
    METODOS_PAGO = [
        ('Efectivo', 'Efectivo'),
        ('Tarjeta', 'Tarjeta'),
        ('Transferencia', 'Transferencia'),
    ]
    ESTADOS_PAGO = [
        ('Pendiente', 'Pendiente'),
        ('Pagado', 'Pagado'),
        ('Cancelado', 'Cancelado'),
    ]

    id_inscripcion = models.AutoField(primary_key=True)
    nombre_cliente = models.CharField(max_length=100)
    
    # --- CORRECCIONES DE RELACIONES ---
    # Usamos 'Evento' (en cadena) porque está en el mismo archivo
    id_evento = models.ForeignKey('Evento', on_delete=models.CASCADE, db_column='id_evento')
    
    # USAMOS 'usuarios.Usuario' para que Django lo busque en la app de usuarios
    id_cliente = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE, db_column='id_cliente')
    
    cantidad_personas = models.IntegerField(default=1) 
    fecha_inscripcion = models.DateField(auto_now_add=True)
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO)
    estado_pago = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='Pendiente')

    class Meta:
        managed = True # Cambiar a False si la tabla ya existe en MySQL y no quieres que Django la altere
        db_table = 'inscripcion_evento'

    def __str__(self):
        # Usamos .id_evento para acceder al objeto relacionado y obtener su nombre
        return f"{self.nombre_cliente} - {self.id_evento.nombre_evento} ({self.cantidad_personas} pers.)"