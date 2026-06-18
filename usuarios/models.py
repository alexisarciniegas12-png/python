from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    # Mantenemos 'id_usuario' como PK para no romper las FK de otras tablas
    id_usuario = models.AutoField(primary_key=True)
    
    # Esto le dice a Django que 'id_usuario' es el campo principal, no 'id'
    # También evitamos que Django cree el campo 'id' automático
    id = None 

    ROL_CHOICES = (
        ('Administrador', 'Administrador'),
        ('empleado', 'empleado'),
        ('cliente', 'cliente'),
    )
    rol = models.CharField(max_length=50, choices=ROL_CHOICES, default='cliente')

    class Meta:
        db_table = 'usuario'
        managed = True # Django controlará esta tabla

    def __str__(self):
        return f"{self.username} ({self.rol})"

class Perfil(models.Model):
    # Relacionamos con la PK correcta
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, to_field='id_usuario')
    telefono = models.CharField(max_length=15, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Perfil de {self.usuario.username}"