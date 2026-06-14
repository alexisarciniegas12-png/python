from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Perfil(models.Model):
    # Relaciona este perfil con un usuario de la tabla auth_user
    usuario = models.OneToOneField(User, db_index=True, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Perfil de {self.usuario.username}"
    
class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, db_column='Usuario')
    password = models.CharField(max_length=255, db_column='contraseña')
    rol = models.CharField(max_length=50, db_column='rol')

    class Meta:
        db_table = 'usuario'
        managed = True
        
    def __str__(self):
        return f"{self.username} ({self.rol})"








