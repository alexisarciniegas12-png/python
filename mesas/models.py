from django.db import models


class Mesa(models.Model):
    id_mesa = models.AutoField(primary_key=True)
    numero_mesa = models.IntegerField()
    capacidad = models.IntegerField()
    estado = models.CharField(max_length=50, default='Libre')

    class Meta:
        db_table = 'mesa'
        managed = False

    def __str__(self):
        return f"Mesa {self.numero_mesa}"
