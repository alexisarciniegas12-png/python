from django.db import models


class CategoriaMenu(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre_categoria = models.CharField(max_length=100)

    class Meta:
        db_table = 'categoria_menu'
        managed = False

    def __str__(self):
        return self.nombre_categoria

class Menu(models.Model):
    id_plato = models.AutoField(primary_key=True)
    nombre_plato = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=12, decimal_places=0)
    imagen = models.ImageField(upload_to='menu/', null=True, blank=True)
    estado = models.CharField(max_length=20, default='Disponible')
    id_categoria = models.ForeignKey(CategoriaMenu, on_delete=models.CASCADE, db_column='id_categoria')

    class Meta:
        db_table = 'menu'
        managed = False

    def __str__(self):
        return self.nombre_plato
